import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config import (
    STATIC_DIR, TEMPLATES_DIR, SAVE_DIR, DB_PATH,
    CAMERA_SOURCE, MODEL_PATH, CONFIDENCE_THRESHOLD, TARGET_CLASSES
)
from services.event_repository import init_db, list_events
from services.video_monitor import video_monitor
from services.monitoring_agent import get_agent_status
from services.ollama_client import ollama_client
from services.schemas import ChatRequest

# =========================
# APP
# =========================
app = FastAPI(title="AgroVision AI")

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
SAVE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =========================
# INICIALIZACAO
# =========================
@app.on_event("startup")
def startup_event() -> None:
    init_db()
    # Only start monitoring if explicitly enabled
    if os.getenv("START_MONITORING", "true").lower() == "true":
        video_monitor.start_monitoring()
    # Only warmup Ollama if enabled
    if os.getenv("WARMUP_OLLAMA", "false").lower() == "true":
        ollama_client.warmup_model()


# =========================
# ROTAS
# =========================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    events = list_events(20)
    status = video_monitor.get_status()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "events": events,
            "model_path": MODEL_PATH,
            "model_error": status.get("model_error"),
        },
    )


@app.get("/health")
def health():
    status = video_monitor.get_status()
    return {
        "status": "ok",
        "service": "AgroVision AI",
        "model_loaded": status["model_loaded"],
        "model_path": MODEL_PATH,
        "model_error": status["model_error"],
    }


@app.get("/events")
def get_events():
    return JSONResponse(content=list_events(50))


@app.get("/frame")
def get_frame():
    import cv2
    frame = video_monitor.get_current_frame()
    if frame is None:
        return JSONResponse(
            content={"message": "Ainda sem frame disponível."},
            status_code=503,
        )

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        return JSONResponse(
            content={"message": "Erro ao converter frame."},
            status_code=500,
        )

    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.get("/camera/status")
def camera_status():
    return video_monitor.get_status()


@app.get("/agent/status")
def agent_status():
    return get_agent_status()


@app.post("/chat")
def chat(request: ChatRequest):
    from services.monitoring_agent import build_agent_messages
    from services.event_repository import list_events
    from services.config import AGENT_EVENT_LIMIT

    events = list_events(AGENT_EVENT_LIMIT)
    messages = build_agent_messages(request.question, request.history, events)
    response = ollama_client.chat_completion(messages)

    if response is None:
        return JSONResponse(
            content={"error": "Falha ao obter resposta do agente"},
            status_code=500,
        )

    return {"response": response}


def generate_mjpeg():
    """Generator for MJPEG stream."""
    import cv2
    import time
    while True:
        frame = video_monitor.get_current_frame()
        if frame is not None:
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.1)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
