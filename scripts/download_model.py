"""Download the MediaPipe hand_landmarker model task file."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_FILENAME = "hand_landmarker.task"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_model(force: bool = False) -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and not force and MODEL_PATH.stat().st_size > 5_000_000:
        print(f"[OK] Model already exists at: {MODEL_PATH}")
        return MODEL_PATH

    print(f"Downloading model from {MODEL_URL}...")
    temp_path = MODEL_PATH.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(MODEL_URL, temp_path)
        temp_path.replace(MODEL_PATH)
        print(f"[OK] Downloaded model to {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)")
        return MODEL_PATH
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        print(f"[ERROR] Failed to download model: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    download_model(force="--force" in sys.argv)
