import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SAVE_DIR = STATIC_DIR / "captures"
DB_PATH = BASE_DIR / "detections.db"

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# Agent configuration
AGENT_EVENT_LIMIT = int(os.getenv("AGENT_EVENT_LIMIT", "12"))

# Camera configuration
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")  # Default to webcam if not set
CAMERA_RECONNECT_SECONDS = int(os.getenv("CAMERA_RECONNECT_SECONDS", "5"))

# YOLO configuration
MODEL_PATH = os.getenv("MODEL_PATH", "yolo11n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
TARGET_CLASSES_STR = os.getenv("TARGET_CLASSES", "person,car,motorcycle,truck,bus")
TARGET_CLASSES: Set[str] = set(TARGET_CLASSES_STR.split(","))
MIN_CONSECUTIVE_FRAMES = int(os.getenv("MIN_CONSECUTIVE_FRAMES", "3"))
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "20"))