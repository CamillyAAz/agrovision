import time
import uuid
import threading
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any

from .config import (
    CAMERA_SOURCE,
    CAMERA_RECONNECT_SECONDS,
    MIN_CONSECUTIVE_FRAMES,
    ALERT_COOLDOWN_SECONDS,
    SAVE_DIR,
)
from .detection_service import yolo_detector
from .event_repository import save_event


class VideoMonitor:
    def __init__(self):
        self.last_frame = None
        self.last_frame_lock = threading.Lock()
        self.detection_state = defaultdict(int)
        self.last_alert_time = defaultdict(lambda: 0.0)
        self.is_running = False

    def load_model(self) -> None:
        yolo_detector.load_model()

    def should_alert(self, label: str) -> bool:
        now = time.time()
        return (now - self.last_alert_time[label]) > ALERT_COOLDOWN_SECONDS

    def process_stream(self) -> None:
        import cv2

        while self.is_running:
            cap = cv2.VideoCapture(CAMERA_SOURCE)
            if not cap.isOpened():
                print(
                    f"Erro ao abrir câmera: {CAMERA_SOURCE}. Tentando reconectar em {CAMERA_RECONNECT_SECONDS} segundos."
                )
                time.sleep(CAMERA_RECONNECT_SECONDS)
                continue

            print(f"Câmera iniciada com sucesso: {CAMERA_SOURCE}")

            while self.is_running:
                ok, frame = cap.read()
                if not ok:
                    print("Falha ao ler frame. Tentando reconectar.")
                    break

                detections = yolo_detector.detect(frame)
                if detections:
                    yolo_detector.draw_boxes(frame, detections)

                    found_labels = {d.label for d in detections}
                    best_conf_by_label = {}
                    for detection in detections:
                        best_conf_by_label[detection.label] = max(
                            best_conf_by_label.get(detection.label, 0.0), detection.confidence
                        )

                    for label in found_labels:
                        self.detection_state[label] += 1

                    for label in set(self.detection_state) - found_labels:
                        self.detection_state[label] = 0

                    for label in found_labels:
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
        model_status = {
            "model_loaded": yolo_detector.is_ready(),
            "model_error": yolo_detector.model_error,
        }
        return {
            "online": self.is_running,
            "connected": self.last_frame is not None,
            "has_live_frame": self.last_frame is not None,
            "source_type": "stream" if isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.startswith("http") else "webcam",
            **model_status,
        }


# Global monitor instance
video_monitor = VideoMonitor()