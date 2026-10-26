"""Download MediaPipe ONNX models for hardware-independent hand tracking."""

from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "onnx"


@dataclass
class ModelInfo:
    filename: str
    url: str
    min_size: int


MODELS: list[ModelInfo] = [
    ModelInfo(
        filename="palm_detection_mediapipe_2023feb.onnx",
        url="https://huggingface.co/opencv/palm_detection_mediapipe/resolve/main/palm_detection_mediapipe_2023feb.onnx",
        min_size=3_500_000,
    ),
    ModelInfo(
        filename="handpose_estimation_mediapipe_2023feb.onnx",
        url="https://huggingface.co/opencv/opencv_zoo/resolve/d4938dfc9d4ec5d098bfa33e98b3f3345a236586/models/handpose_estimation_mediapipe/handpose_estimation_mediapipe_2023feb.onnx",
        min_size=3_500_000,
    ),
]


def download_models(force: bool = False) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for item in MODELS:
        dest = MODEL_DIR / item.filename
        if dest.exists() and not force and dest.stat().st_size >= item.min_size:
            print(f"[OK] Model already present: {dest.name} ({dest.stat().st_size} bytes)")
            continue

        print(f"Downloading {item.filename} from {item.url}...")
        temp_dest = dest.with_suffix(".tmp")
        try:
            req = urllib.request.Request(item.url, headers={"User-Agent": "FingerMaze/1.0"})
            with urllib.request.urlopen(req) as resp, temp_dest.open("wb") as out_f:
                while chunk := resp.read(65536):
                    out_f.write(chunk)
            temp_dest.replace(dest)
            print(f"[OK] Downloaded {dest.name} ({dest.stat().st_size} bytes)")
        except Exception as exc:
            if temp_dest.exists():
                temp_dest.unlink()
            print(f"[ERROR] Failed to download {item.filename}: {exc}", file=sys.stderr)
            raise


if __name__ == "__main__":
    download_models(force="--force" in sys.argv)
