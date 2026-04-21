from pathlib import Path
from typing import List

from .config import SAVE_DIR

def list_captures() -> List[str]:
    """List all capture files in the save directory."""
    if not SAVE_DIR.exists():
        return []
    return [f.name for f in SAVE_DIR.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.png', '.jpeg']]

def get_capture_path(filename: str) -> Path:
    """Get the full path for a capture file."""
    return SAVE_DIR / filename