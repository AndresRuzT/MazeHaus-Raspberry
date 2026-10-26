"""Environment and hardware capability check for FingerMaze."""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def check_python_version() -> bool:
    v = sys.version_info
    print(f"[*] Python Version: {platform.python_version()} ({sys.executable})")
    if (3, 11) <= (v.major, v.minor) <= (3, 12):
        print("    [PASS] Python version is within supported range (3.11 - 3.12)")
        return True
    print("    [WARN] Python version is outside the validated range (expected 3.11 or 3.12)")
    return False


def check_platform() -> None:
    machine = platform.machine()
    system = platform.system()
    print(f"[*] Operating System: {system} {platform.release()} ({machine})")
    if "aarch64" in machine or "arm" in machine:
        print("    [INFO] Running on ARM platform (Raspberry Pi compatible)")
    else:
        print(f"    [INFO] Running on development workstation ({machine})")


def check_dependencies() -> bool:
    print("[*] Checking core runtime dependencies...")
    all_ok = True

    modules = [
        ("numpy", "numpy"),
        ("pygame", "pygame-ce"),
        ("cv2", "opencv-python-headless"),
        ("mediapipe", "mediapipe"),
        ("pydantic", "pydantic"),
    ]

    for mod_name, pkg_name in modules:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "unknown")
            print(f"    [PASS] {pkg_name} ({ver})")
        except ImportError as exc:
            print(f"    [FAIL] {pkg_name}: {exc}")
            all_ok = False

    return all_ok


def check_model() -> bool:
    print("[*] Checking Hand Landmarker model file...")
    model_path = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"
    if model_path.exists() and model_path.stat().st_size > 5_000_000:
        print(f"    [PASS] Model found: {model_path} ({model_path.stat().st_size} bytes)")
        return True
    print(f"    [FAIL] Model missing at {model_path}. Run 'python scripts/download_model.py'")
    return False


def check_camera() -> bool:
    print("[*] Probing video capture devices (OpenCV / V4L2)...")
    try:
        import cv2

        found = False
        for index in range(2):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"    [PASS] Camera device found at index {index} ({w}x{h})")
                    found = True
                cap.release()
        if not found:
            print("    [INFO] No active camera device detected. (Mouse fallback mode is available)")
        return found
    except Exception as exc:
        print(f"    [WARN] Camera probe failed: {exc}")
        return False


def main() -> int:
    print("=" * 60)
    print(" FingerMaze Environment Diagnostic Tool")
    print("=" * 60)
    check_platform()
    py_ok = check_python_version()
    deps_ok = check_dependencies()
    model_ok = check_model()
    check_camera()
    print("=" * 60)

    if py_ok and deps_ok and model_ok:
        print("SUMMARY: Environment is ready for FingerMaze!")
        return 0
    else:
        print("SUMMARY: One or more checks failed. Please review above output.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
