# Technology Stack

| | |
|---|---|
| **Document version** | 0.1.0 (draft) |
| **Status** | Proposed |
| **Last updated** | 2026-10-26 |
| **Related** | [REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md) |

## 1. Selection principles

1. **Available on aarch64.** Every runtime dependency must be installable on 64-bit Raspberry Pi OS
   through `apt` or a PyPI wheel. Nothing that requires compiling a large native library on the device.
2. **CPU-only and lightweight.** Prefer small models and thin libraries; the whole application must stay
   within the budgets defined in NFR-01 to NFR-07.
3. **Replaceable behind a port.** Vision backend, camera backend and renderer are isolated behind
   interfaces so that a dependency problem never forces a rewrite.
4. **Boring, well-maintained tooling.** Mainstream, actively maintained projects with permissive licences.
5. **Reproducible.** Locked dependencies, pinned model checksums, documented installation.

## 2. Runtime stack

| Concern | Choice | Source | Rationale |
|---|---|---|---|
| Operating system | Raspberry Pi OS, 64-bit | Official image | Matches the reference hardware (aarch64) |
| Language | Python 3.11 or 3.12 | See §3 | Best ecosystem support for vision libraries on ARM |
| Hand tracking | MediaPipe Hand Landmarker (Tasks API), CPU delegate | PyPI (`mediapipe`) | Purpose-built for hands: 21 landmarks, two hands, designed for real-time on mobile-class CPUs |
| Image handling | OpenCV (headless build) and NumPy | PyPI | Colour conversion, resize, mirroring; the headless build avoids pulling GUI dependencies |
| Camera (primary) | USB webcam through OpenCV/V4L2 | PyPI + kernel driver | Works with any Python version supported by the tracker |
| Camera (optional) | Picamera2 for CSI cameras | `apt` (`python3-picamera2`) | Official Raspberry Pi camera stack, only distributed through `apt` |
| Game loop and rendering | `pygame-ce` (SDL2) | PyPI | Lightweight 2D rendering, fixed-timestep friendly, works with X11, Wayland and a headless dummy driver for CI |
| Configuration | `pydantic` (v2) and TOML (`tomllib`) | PyPI / stdlib | Typed, validated configuration with clear errors |
| Logging | `logging` (stdlib), structured formatter | stdlib | No extra dependency |
| Telemetry output | `csv` (stdlib) | stdlib | Simple, analysable in any research tool |

### 2.1 Tracking model

- Model: `hand_landmarker.task` (float16), downloaded by an install script and verified against a
  SHA-256 checksum stored in the repository (NFR-21).
- Mode: asynchronous *live stream* inference with `num_hands=2`, so the capture loop is never blocked.
- Input: 320×240 to 640×480 frames, mirrored, RGB. Higher resolutions bring no gameplay benefit.
- Only the index fingertip (landmark 8) drives the pointer; the remaining landmarks are available for
  future gestures (for example pinch to select).

## 3. Python version and camera strategy

Two facts constrain the environment, and both must be checked on the target device before coding:

- MediaPipe's Python build pipeline is documented as tested with Python 3.9, 3.10, 3.11 and 3.12.
  Newer interpreters are therefore not guaranteed to have compatible wheels.
- `picamera2` and `libcamera` are distributed through `apt` and bind to the system Python. A virtual
  environment can only use them with `--system-site-packages`, and a project that needs a different
  interpreter than the system one cannot use that route.

Recent Raspberry Pi OS releases may ship a newer system Python than MediaPipe supports. The decision
is therefore:

| Situation | Camera | Environment |
|---|---|---|
| System Python is 3.11 or 3.12 | USB or CSI | `venv --system-site-packages` (needed only for CSI) |
| System Python is newer than 3.12 | **USB camera** | Project-managed Python 3.12 (for example through `uv python install 3.12`), isolated environment |
| System Python is newer than 3.12 and a CSI camera is required | CSI | Not supported in v1.0; documented limitation |

`scripts/check_environment.py` (first development milestone) prints the interpreter version, checks
that every required wheel imports, opens the camera, and reports a pass/fail summary. It is the
authoritative answer to "will this run on my device?", and its output is requested in every bug report.

If a compatible MediaPipe wheel turns out to be unavailable, the `HandTracker` port (see
[ARCHITECTURE.md](ARCHITECTURE.md)) allows another CPU backend such as TensorFlow Lite or ONNX Runtime
with a lightweight hand model to be added without touching game code.

## 4. Development and quality tooling

| Concern | Tool | Notes |
|---|---|---|
| Dependency and environment management | `uv` with committed `uv.lock` | Falls back to `pip` plus a constraints file; documented in the README |
| Project metadata and build | `pyproject.toml` (PEP 621), `hatchling` backend, `src/` layout | Standard, tool-agnostic layout |
| Lint and format | `ruff` | Single tool for linting, import sorting and formatting |
| Type checking | `mypy --strict` | Applied to `src/`; tests are checked more leniently |
| Testing | `pytest`, `pytest-cov`, `hypothesis` | Property-based tests for maze generation |
| Architecture rules | `import-linter` | Enforces the dependency rule between domain, core and adapters in CI |
| Git hooks | `pre-commit` | Ruff, mypy, whitespace checks, secrets check |
| Commit conventions and releases | `commitizen` | Enforces Conventional Commits in a `commit-msg` hook, bumps SemVer versions and generates the changelog; no Node.js toolchain required |
| Continuous integration | GitHub Actions | Lint, type check, tests on Python 3.11 and 3.12, build, `pip-audit` |
| Dependency updates | Dependabot | Weekly grouped updates |
| Documentation | Markdown in `docs/`, ADRs in `docs/adr/` | Rendered natively by GitHub |

Continuous integration runs on x86-64 runners with `SDL_VIDEODRIVER=dummy` and without a camera.
Hardware-dependent checks live behind a `hardware` pytest marker and are executed manually on a
Raspberry Pi through `scripts/benchmark.py`.

## 5. Alternatives considered

| Option | Decision | Reason |
|---|---|---|
| Face or gaze tracking (Face Mesh, iris landmarks) | Rejected | Heavier models, less precise pointer, not needed for a finger-controlled game |
| Generic object-detection models (YOLO family) through PyTorch | Rejected | Large install, high CPU cost on Cortex-A72, no benefit for a single known object type |
| Classical OpenCV segmentation (colour or contour based) | Kept as research option | Cheap, but fragile under changing light; may serve as a fallback backend |
| Kivy, Godot or a web front end | Rejected | Extra runtime weight and complexity; pygame-ce is sufficient for a 2D maze |
| Hardware accelerators (Coral, AI HAT) | Out of scope | Project targets an unmodified Raspberry Pi 4 |
| `release-please` / `semantic-release` | Rejected | Add a Node.js or CI-only toolchain; `commitizen` keeps everything in Python and runs locally |

## 6. Version policy

- Direct dependencies are declared with compatible ranges in `pyproject.toml` and locked in `uv.lock`.
- The exact versions validated on the reference device are recorded in `docs/COMPATIBILITY.md`
  (created in milestone 1, filled in after the first on-device test).
- Python 3.11 and 3.12 are supported; a version is added only after its full test suite and an
  on-device benchmark pass.

## 7. Licensing

The project licence will be chosen with the research centre (Apache-2.0 or MIT are both compatible
with the dependencies above). A `THIRD_PARTY_NOTICES.md` file will list dependency licences, including
the MediaPipe model, whose terms must be reviewed before the first release.
