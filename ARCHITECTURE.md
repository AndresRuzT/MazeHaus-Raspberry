# Architecture

| | |
|---|---|
| **Document version** | 0.1.0 (draft) |
| **Status** | Proposed |
| **Last updated** | 2026-10-26 |
| **Related** | [REQUIREMENTS.md](REQUIREMENTS.md), [TECH_STACK.md](TECH_STACK.md) |

## 1. Goals and drivers

| Driver | Consequence for the design |
|---|---|
| Smooth gameplay on a Raspberry Pi 4 (NFR-01…NFR-05) | Vision work is decoupled from rendering; render rate never depends on tracking rate |
| Replaceable components (R-1) | Ports and adapters (hexagonal) architecture |
| Future games without core changes (NFR-33) | Games are plugins behind a small interface |
| Testability without hardware (NFR-32) | Pure domain logic, injectable input, headless rendering |
| Research use (FR-30) | Optional telemetry through an observer, never coupled to game logic |

## 2. System context

```
 Player(s) ──hand──▶ [ USB / CSI camera ] ──frames──▶ ┌──────────────┐ ──video──▶ [ Display ]
                                                      │  FingerMaze  │
 Operator  ──config.toml / CLI──────────────────────▶ │  (Raspberry  │ ──CSV──▶ [ Local metrics file ]
                                                      │     Pi)      │             (optional, opt-in)
                                                      └──────────────┘
```

The application is fully offline at runtime and has no external services.

## 3. Architectural style

A **hexagonal (ports and adapters)** structure with a clear dependency rule: dependencies point inward.

```
                  ┌───────────────────────────────────────────────┐
                  │                  Adapters                     │
                  │  camera (OpenCV, Picamera2) · tracker         │
                  │  (MediaPipe) · pygame renderer · CSV sink     │
                  │   ┌───────────────────────────────────────┐   │
                  │   │          Application / Core           │   │
                  │   │  game loop · scenes · input mapping   │   │
                  │   │   ┌───────────────────────────────┐   │   │
                  │   │   │           Domain              │   │   │
                  │   │   │  maze · collision · scoring   │   │   │
                  │   │   └───────────────────────────────┘   │   │
                  │   └───────────────────────────────────────┘   │
                  └───────────────────────────────────────────────┘
```

- **Domain** contains pure Python with no I/O, no pygame and no OpenCV. It is deterministic and fully
  unit-testable.
- **Core** orchestrates the loop, scenes and input state, and defines the ports.
- **Adapters** implement the ports against concrete libraries and hardware.

## 4. Runtime view

### 4.1 Concurrency model

Two execution contexts communicate through a single lock-protected, **latest-value mailbox**:

```
 ┌────────────── Vision worker (background) ───────────────┐      ┌────────── Main thread ──────────┐
 │ camera.read() → mirror/resize → tracker.detect_async()  │      │ poll events                     │
 │        (~15–30 Hz, drops stale frames)                  │      │ read latest PointerState        │
 │                │                                        │      │ smooth + map to screen          │
 │                ▼  publish(PointerSnapshot)              │      │ update(dt) → draw()  (60 FPS)   │
 │          ┌─────────────┐                                │ ───▶ │ present frame                   │
 │          │  Mailbox    │ ◀─────────────────────────────────── │                                 │
 │          └─────────────┘                                │      └─────────────────────────────────┘
 └─────────────────────────────────────────────────────────┘
```

Rules:

1. The main thread **never waits** for the camera or the model. It reads whatever snapshot is newest.
2. The mailbox keeps **only the latest** snapshot (no queue growth, no latency build-up).
3. Each snapshot carries a monotonic timestamp. The game treats snapshots older than a threshold as
   "hand lost" (FR-07).
4. The game loop uses a **fixed-timestep update** with an accumulator and renders every frame, so game
   behaviour is independent of the render rate.
5. The pointer is filtered with a One Euro filter on the main thread, so the cursor moves at render rate
   even though samples arrive at tracking rate.

Whether the vision worker is a thread or a separate process is decided by benchmark (ADR-0003). The
`VisionWorker` interface hides this choice; the default starts as a thread and moves to a process only
if profiling shows contention on the main loop.

### 4.2 Latency budget (target, 95th percentile)

| Stage | Budget |
|---|---|
| Camera exposure and transfer | 33 ms |
| Pre-processing | 5 ms |
| Hand inference | 50 ms |
| Mailbox, filter, game update | 5 ms |
| Render and display | 17–33 ms |
| **Total** | **≤ 150 ms** (NFR-02) |

### 4.3 Per-frame sequence

```
 Camera ─▶ VisionWorker ─▶ Mailbox            Main loop
   │            │             │                   │
   │ frame      │             │                   │ poll events
   ├───────────▶│ detect()    │                   │
   │            ├────────────▶│ publish           │
   │            │             │                   │ read latest ◀──┐
   │            │             │◀──────────────────┤                │
   │            │             │                   │ filter → map   │
   │            │             │                   │ scene.update(dt, pointers)
   │            │             │                   │ scene.draw(surface)
   │            │             │                   │ display.flip()
```

## 5. Module structure

```
fingermaze/
├── pyproject.toml
├── uv.lock
├── src/fingermaze/
│   ├── __main__.py              # CLI entry point
│   ├── app.py                   # composition root: wires adapters into the core
│   ├── config/                  # pydantic settings models, TOML loading, defaults
│   ├── core/
│   │   ├── loop.py              # fixed-timestep game loop
│   │   ├── scenes.py            # Scene protocol and scene manager (state machine)
│   │   ├── events.py            # lightweight event bus
│   │   ├── ports.py             # CameraSource, HandTracker, InputProvider, Renderer, MetricsSink
│   │   └── types.py             # Pointer, PlayerId, Landmark, Viewport (frozen dataclasses)
│   ├── input/
│   │   ├── camera/              # opencv_source.py, picamera2_source.py, fake_source.py
│   │   ├── tracking/            # mediapipe_tracker.py, replay_tracker.py
│   │   ├── vision_worker.py     # background capture + inference, mailbox publisher
│   │   ├── mailbox.py           # latest-value, thread-safe
│   │   ├── mapping.py           # camera → screen coordinates, player assignment
│   │   ├── filters.py           # One Euro filter
│   │   ├── calibration.py
│   │   └── mouse_input.py       # development input adapter
│   ├── games/
│   │   ├── base.py              # Game protocol and registry
│   │   └── maze/
│   │       ├── domain/          # generator.py, grid.py, collision.py, scoring.py
│   │       ├── scene.py         # gameplay scene (1P and 2P)
│   │       ├── render.py        # drawing helpers
│   │       └── settings.py      # difficulty presets
│   ├── ui/                      # menu scenes, dwell button, HUD, theme, i18n
│   ├── telemetry/               # observer, CSV sink, perf probes
│   └── assets/                  # fonts, sounds (licensed and documented)
├── scripts/                     # check_environment.py, download_model.py, benchmark.py, record_replay.py
├── tests/                       # unit/, integration/, hardware/
├── docs/                        # this folder, plus adr/
└── .github/                     # workflows, issue and PR templates, dependabot.yml
```

Dependency rule enforced in CI with an import-linter contract: `games/*/domain` imports nothing outside
the standard library and `core.types`; `core` imports no adapter; adapters may import `core` only.

## 6. Key interfaces (ports)

```python
class CameraSource(Protocol):
    def open(self) -> None: ...
    def read(self) -> Frame | None: ...  # None when no new frame is available
    def close(self) -> None: ...


class HandTracker(Protocol):
    def submit(self, frame: Frame, timestamp_ms: int) -> None: ...
    def close(self) -> None: ...  # results are delivered through a callback


class InputProvider(Protocol):
    def poll(self, now: float) -> InputSnapshot: ...  # pointers per player, never blocks


class Scene(Protocol):
    def enter(self, ctx: SceneContext) -> None: ...
    def update(self, dt: float, inputs: InputSnapshot) -> SceneResult: ...
    def draw(self, surface: Surface) -> None: ...
    def exit(self) -> None: ...


class Game(Protocol):
    id: str
    title: str

    def create_scene(self, options: GameOptions) -> Scene: ...


class MetricsSink(Protocol):
    def record(self, event: MetricEvent) -> None: ...
```

`InputProvider` has three implementations: `VisionInput` (camera + tracker + mailbox), `MouseInput`
(development) and `ReplayInput` (recorded landmark streams for deterministic tests).

## 7. Domain design: the maze

- **Representation.** A rectangular grid of cells; each cell stores wall flags as a bit mask.
- **Generation.** Iterative depth-first "recursive backtracker" using an explicit stack (no Python
  recursion limit issues) and `random.Random(seed)` for determinism (FR-10). Output is a perfect maze.
- **Rendering geometry.** Cells are scaled to pixels with a configurable corridor width; walls have a
  thickness that is derived from the difficulty preset.
- **Collision.** The pointer is a circle. The collision test queries only the cell the pointer occupies
  and its immediate neighbours, giving O(1) cost per frame.
- **Checkpoints.** Placed at regular path distances; a wall hit returns the pointer to the last
  checkpoint and applies the time penalty once per contact (FR-11), using an edge-triggered contact
  state to avoid repeated penalties.
- **Two players.** Both players receive the same maze (same seed) and each has an independent
  `PlayerState`; split-screen viewports are produced by clipped sub-surfaces. The winner is decided by
  the first completed exit event.

## 8. Cross-cutting concerns

| Concern | Approach |
|---|---|
| **Configuration** | One TOML file validated by pydantic models; command-line flags override file values; invalid input fails fast with a readable message (FR-22) |
| **Error handling** | Adapters raise typed exceptions (`CameraUnavailableError`, `TrackerInitError`); the app catches them at the composition root and shows an on-screen actionable message (NFR-10); the render loop never dies because of a vision failure |
| **Resource management** | Context managers for camera and tracker; the vision worker is stopped and joined on every exit path (FR-24) |
| **Logging** | Standard `logging` with levels; per-second performance summary at DEBUG |
| **Telemetry** | Event bus subscribers write CSV rows only when enabled (FR-30); no frame data ever crosses the port boundary into telemetry |
| **Privacy** | Frames exist only in the vision worker's memory; replay files store landmark coordinates only (NFR-20, NFR-22) |
| **Internationalisation** | Message catalog keyed by identifiers; English default, Spanish planned (FR-23) |
| **Performance guard rails** | `scripts/benchmark.py` measures render rate, tracking rate, latency and CPU; thresholds mirror NFR-01…NFR-06 and results are recorded in `docs/COMPATIBILITY.md` |

## 9. Testing strategy

| Level | What | How |
|---|---|---|
| Unit | Maze generation, collision, scoring, filters, mapping, config | Pure functions, `pytest`, `hypothesis` for generator invariants (connectivity, determinism) |
| Integration | Scene + input + renderer | `SDL_VIDEODRIVER=dummy`, `FakeCameraSource` and `ReplayTracker`, no hardware |
| Contract | Every `CameraSource`, `HandTracker` and `InputProvider` implementation | Shared test suite parametrised over implementations |
| Architecture | Dependency rules | `import-linter` contract in CI |
| Hardware / performance | Real camera, real device | `pytest -m hardware` and `scripts/benchmark.py`, run manually on the Raspberry Pi |

## 10. Extending the system

Adding a new game requires no change in `core/`:

1. Create `games/<name>/` with a `Game` implementation and its scene.
2. Register it in the games registry (later through the `fingermaze.games` entry-point group, so that
   third-party packages can contribute games).
3. Add unit tests for its domain and an integration test with `ReplayInput`.
4. Document it in `docs/games/<name>.md`.

Planned candidates that reuse the same input model: turn-based games with dwell selection (for example
Connect Four), memory games and connect-the-dots precision tasks.

## 11. Architecture decision records

| ADR | Title | Status |
|---|---|---|
| 0001 | Use a hexagonal architecture with Python protocols | Proposed |
| 0002 | Control by index fingertip using MediaPipe Hand Landmarker | Proposed |
| 0003 | Vision worker as thread first; process only if benchmarks require it | Proposed |
| 0004 | pygame-ce for rendering and the game loop | Proposed |
| 0005 | USB camera as primary; CSI as optional adapter | Proposed |
| 0006 | commitizen for Conventional Commits, versioning and changelog | Proposed |

Each ADR is stored in `docs/adr/NNNN-title.md` using the context / decision / consequences format and
is added in the same pull request that introduces the decision.
