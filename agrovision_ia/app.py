import os

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.auth import verify_api_key
from services.config import STATIC_DIR, TEMPLATES_DIR, SAVE_DIR, MODEL_PATH
from services.event_repository import init_db, list_events
from services.video_monitor import video_monitor
from services.monitoring_agent import get_agent_status
from services.ollama_client import ollama_client
from services.scraper import agricultural_scraper
from services.schemas import ChatRequest

# =========================
# APP
# =========================
app = FastAPI(title="AgroVision AI")

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
SAVE_DIR.mkdir(parents=True, exist_ok=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Dados invalidos ou fora do formato esperado."},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail if isinstance(exc.detail, str) else "Erro de requisição"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Erro interno do servidor"},
    )

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
    market_info = agricultural_scraper.get_latest_insight()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "events": events,
            "model_path": MODEL_PATH,
            "model_error": status.get("model_error"),
            "market_info": market_info,
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


def _events_response(limit: int = 50) -> JSONResponse:
    return JSONResponse(content=list_events(limit))


def _frame_response() -> Response:
    import cv2

    frame = video_monitor.get_current_frame()
    if frame is None:
        return JSONResponse(
            content={"message": "Ainda sem frame disponivel."},
            status_code=503,
        )

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        return JSONResponse(
            content={"message": "Erro ao converter frame."},
            status_code=500,
        )

    return Response(content=buffer.tobytes(), media_type="image/jpeg")


def _chat_response(request: ChatRequest):
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


@app.get("/dashboard/events")
def dashboard_events():
    return _events_response(50)


@app.get("/dashboard/frame")
def dashboard_frame():
    return _frame_response()


@app.post("/dashboard/chat")
def dashboard_chat(request: ChatRequest):
    return _chat_response(request)


@app.get("/events", dependencies=[Depends(verify_api_key)])
def get_events():
    return _events_response(50)

@app.get("/market-info", dependencies=[Depends(verify_api_key)])
def get_market_info():
    return JSONResponse(content=agricultural_scraper.get_latest_insight())


@app.get("/frame", dependencies=[Depends(verify_api_key)])
def get_frame():
    return _frame_response()


@app.get("/camera/status", dependencies=[Depends(verify_api_key)])
def camera_status():
    return video_monitor.get_status()


@app.get("/agent/status", dependencies=[Depends(verify_api_key)])
def agent_status():
    return get_agent_status()


@app.post("/chat", dependencies=[Depends(verify_api_key)])
def chat(request: ChatRequest):
    return _chat_response(request)


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


@app.get("/video_feed", dependencies=[Depends(verify_api_key)])
def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
