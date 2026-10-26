"""Pinpoint which module or binary causes the SIGILL crash on Raspberry Pi."""

from __future__ import annotations


def test_step(name: str, fn) -> None:
    print(f"[*] Testing {name}...", end=" ", flush=True)
    try:
        fn()
        print("[OK]")
    except Exception as exc:
        print(f"[FAILED: {exc}]")


def main() -> None:
    print("=" * 60)
    print(" FingerMaze Step-by-Step Crash Diagnostic")
    print("=" * 60)

    # 1. CPU Features
    def check_cpu():
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "Features" in line or "flags" in line or "model name" in line:
                    print(f"\n    {line.strip()}", end="")
        print()

    test_step("CPU Info", check_cpu)

    # 2. Pygame
    test_step("pygame import", lambda: __import__("pygame"))

    # 3. OpenCV
    def check_cv2():
        cv2 = __import__("cv2")
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        assert ret and frame is not None

    test_step("OpenCV VideoCapture(0)", check_cv2)

    # 4. MediaPipe import
    test_step("mediapipe import", lambda: __import__("mediapipe"))

    # 5. MediaPipe Tasks initialization
    def check_tasks():
        import mediapipe as mp

        base_opts = mp.tasks.BaseOptions(model_asset_path="models/hand_landmarker.task")
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_opts,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_hands=1,
        )
        landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        landmarker.close()

    test_step("MediaPipe HandLandmarker.create_from_options", check_tasks)

    # 6. Fingermaze App
    test_step("fingermaze.app import", lambda: __import__("fingermaze.app"))

    print("=" * 60)
    print("Diagnostic complete!")


if __name__ == "__main__":
    main()
