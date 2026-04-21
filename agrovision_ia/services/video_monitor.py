import time
import uuid
import threading
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any

from .config import (
    CAMERA_SOURCE, CAMERA_RECONNECT_SECONDS, MODEL_PATH, CONFIDENCE_THRESHOLD,
    TARGET_CLASSES, MIN_CONSECUTIVE_FRAMES, ALERT_COOLDOWN_SECONDS, SAVE_DIR
)
from .event_repository import save_event

class VideoMonitor:
    def __init__(self):
        self.model = None
        self.model_error = None
        self.last_frame = None
        self.last_frame_lock = threading.Lock()
        self.detection_state = defaultdict(int)
        self.last_alert_time = defaultdict(lambda: 0.0)
        self.is_running = False

    def load_model(self) -> None:
        try:
            from ultralytics import YOLO
            self.model = YOLO(MODEL_PATH)
            self.model_error = None
            print(f"Modelo carregado com sucesso: {MODEL_PATH}")
        except Exception as exc:
            self.model = None
            self.model_error = str(exc)
            print(f"Falha ao carregar modelo YOLO: {exc}")

    def draw_box(self, frame, x1, y1, x2, y2, label, conf) -> None:
        import cv2
        text = f"{label} {conf:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            text,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    def should_alert(self, label: str) -> bool:
        now = time.time()
        return (now - self.last_alert_time[label]) > ALERT_COOLDOWN_SECONDS

    def process_stream(self) -> None:
        import cv2
        while self.is_running:
            cap = cv2.VideoCapture(CAMERA_SOURCE)
            if not cap.isOpened():
                print(f"Erro ao abrir câmera: {CAMERA_SOURCE}. Tentando reconectar em {CAMERA_RECONNECT_SECONDS} segundos.")
                time.sleep(CAMERA_RECONNECT_SECONDS)
                continue

            print(f"Câmera iniciada com sucesso: {CAMERA_SOURCE}")

            while self.is_running:
                ok, frame = cap.read()
                if not ok:
                    print("Falha ao ler frame. Tentando reconectar.")
                    break

                if self.model is not None:
                    results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                    found_labels_in_frame = set()
                    best_conf_by_label = {}

                    for result in results:
                        if result.boxes is None:
                            continue

                        for box in result.boxes:
                            cls_id = int(box.cls[0].item())
                            conf = float(box.conf[0].item())
                            label = self.model.names[cls_id]

                            if label not in TARGET_CLASSES:
                                continue

                            found_labels_in_frame.add(label)
                            if label not in best_conf_by_label or conf > best_conf_by_label[label]:
                                best_conf_by_label[label] = conf

                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            self.draw_box(frame, x1, y1, x2, y2, label, conf)

                    for label in TARGET_CLASSES:
                        if label in found_labels_in_frame:
                            self.detection_state[label] += 1
                        else:
                            self.detection_state[label] = 0

                    for label in found_labels_in_frame:
                        if self.detection_state[label] >= MIN_CONSECUTIVE_FRAMES and self.should_alert(label):
                            event_id = str(uuid.uuid4())[:8]
                            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{label}_{event_id}.jpg"
                            filepath = SAVE_DIR / filename

                            cv2.imwrite(str(filepath), frame)
                            image_path = f"/static/captures/{filename}"
                            confidence = best_conf_by_label.get(label, 0.0)

                            save_event(event_id, label, confidence, image_path)
                            self.last_alert_time[label] = time.time()
                            print(f"[ALERTA] {label} detectado. Evidência salva em {filepath}")

                with self.last_frame_lock:
                    self.last_frame = frame.copy()

                time.sleep(0.05)

            cap.release()

    def start_monitoring(self) -> None:
        if not self.is_running:
            self.is_running = True
            self.load_model()
            thread = threading.Thread(target=self.process_stream, daemon=True)
            thread.start()

    def stop_monitoring(self) -> None:
        self.is_running = False

    def get_current_frame(self):
        with self.last_frame_lock:
            return self.last_frame.copy() if self.last_frame is not None else None

    def get_status(self) -> Dict[str, Any]:
        return {
            "online": self.is_running,
            "connected": self.last_frame is not None,
            "has_live_frame": self.last_frame is not None,
            "source_type": "stream" if isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.startswith("http") else "webcam",
            "model_loaded": self.model is not None,
            "model_error": self.model_error
        }

# Global monitor instance
video_monitor = VideoMonitor()