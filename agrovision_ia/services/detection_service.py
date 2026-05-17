import time
from typing import Dict, List, Optional, Tuple

from .config import MODEL_PATH, CONFIDENCE_THRESHOLD, TARGET_CLASSES


class DetectionResult:
    def __init__(self, label: str, confidence: float, bbox: Tuple[int, int, int, int]):
        self.label = label
        self.confidence = confidence
        self.bbox = bbox

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


class YOLODetector:
    def __init__(self):
        self.model = None
        self.model_error: Optional[str] = None
        self.last_loaded: Optional[float] = None

    def load_model(self) -> None:
        try:
            from ultralytics import YOLO

            self.model = YOLO(MODEL_PATH)
            self.model_error = None
            self.last_loaded = time.time()
            print(f"Modelo YOLO carregado com sucesso: {MODEL_PATH}")
        except Exception as exc:
            self.model = None
            self.model_error = str(exc)
            print(f"Falha ao carregar modelo YOLO: {exc}")

    def is_ready(self) -> bool:
        return self.model is not None

    def detect(self, frame) -> List[DetectionResult]:
        if not self.is_ready():
            return []

        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        detections: List[DetectionResult] = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                label = self.model.names[cls_id]
                if label not in TARGET_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(DetectionResult(label, conf, (x1, y1, x2, y2)))

        return detections

    def draw_boxes(self, frame, detections: List[DetectionResult]) -> None:
        import cv2

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            label = detection.label
            conf = detection.confidence
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


yolo_detector = YOLODetector()
