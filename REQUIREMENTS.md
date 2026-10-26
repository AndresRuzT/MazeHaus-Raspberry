# Software Requirements Specification

| | |
|---|---|
| **Project** | FingerMaze (working name) |
| **Document version** | 0.1.0 (draft) |
| **Status** | Proposed |
| **Last updated** | 2026-10-26 |
| **Target platform** | Raspberry Pi 4 Model B, 8 GB RAM, Cortex-A72 (aarch64), 64-bit Raspberry Pi OS |

## 1. Purpose and scope

FingerMaze is an interactive maze game controlled through computer vision. Players guide a cursor
through a maze by moving their index finger in front of a camera. The game supports one or two
simultaneous players and is designed to run **smoothly on a Raspberry Pi 4 using only its CPU**.

The project is developed as an open-source repository for a university research centre. It must
serve both as a public demonstration and as a maintainable base for future vision-controlled
games and for research on low-cost human-computer interaction.

### 1.1 In scope

- Hand-based pointer control using a single standard camera.
- A maze game with single-player and two-player (competitive) modes.
- A menu system navigable with the same pointer control.
- A development input mode (mouse/keyboard) that does not require a camera.
- Optional, anonymous, opt-in performance and interaction telemetry.
- An architecture that allows additional games to be added without modifying the core.

### 1.2 Out of scope (for v1.0)

- Face, gaze or full-body tracking.
- Fast-action games (e.g. Pong-style games) that require high-frequency input.
- Online multiplayer, accounts, leaderboards stored on a server.
- Hardware accelerators (Coral TPU, AI HAT, GPU compute).
- Audio synthesis beyond simple sound effects.

## 2. Stakeholders

| Stakeholder | Interest |
|---|---|
| Players (visitors, students) | A responsive, intuitive and fun experience |
| Research centre staff | Reliable demos, optional measurable interaction data |
| Maintainers and contributors | Clean code, clear documentation, predictable releases |
| Educators | A readable reference for vision-based interaction on low-cost hardware |

## 3. Definitions

| Term | Meaning |
|---|---|
| **Pointer** | A 2D position derived from a player's index fingertip |
| **Tracking rate** | Number of hand-landmark results produced per second |
| **Render rate** | Number of frames drawn per second by the game loop |
| **Dwell selection** | Selecting a UI element by keeping the pointer over it for a set time |
| **Landmark** | One of the 21 key points MediaPipe reports for a detected hand |

## 4. Functional requirements

Priority follows MoSCoW: **M**ust, **S**hould, **C**ould.

### 4.1 Input and vision

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-01 | The system shall capture video through a pluggable camera source. USB/V4L2 cameras are required; Raspberry Pi CSI cameras are optional. | M | Both source types can be selected in the configuration and produce frames. |
| FR-02 | The system shall detect up to two hands and extract the index fingertip of each. | M | With two hands visible, two pointer samples are produced per cycle. |
| FR-03 | The system shall assign hands to Player 1 or Player 2 according to the half of the (mirrored) camera image in which they appear. | M | A hand in the left half always maps to Player 1 and the right half to Player 2. |
| FR-04 | The system shall map fingertip positions inside a configurable active region of the camera image to screen coordinates. | M | Moving a finger across the active region moves the pointer across the full player viewport. |
| FR-05 | The system shall smooth pointer motion with an adaptive low-pass filter. | M | Stationary-finger jitter is visibly suppressed while fast motions are not noticeably delayed. |
| FR-06 | The system shall provide an interactive calibration step that sets the active region. | S | Calibration completes in under 15 seconds and its result is persisted. |
| FR-07 | The system shall pause the game when a player's hand has been lost for more than a configurable time (default 1 s) and resume when the hand is found again. | M | Covering the camera pauses the game; showing a hand resumes it without losing progress. |
| FR-08 | The system shall provide a mouse/keyboard input adapter for development and testing. | M | The full game is playable without a camera. |

### 4.2 Game

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-10 | The system shall generate perfect mazes (fully connected, no cycles) deterministically from an integer seed. | M | The same seed and size always produce the same maze, and every cell is reachable from the start. |
| FR-11 | In a maze, the player shall guide the pointer from the entrance to the exit through the corridors. Touching a wall shall apply a time penalty and return the pointer to the last checkpoint. | M | Wall contact is detected reliably and the penalty is applied exactly once per contact. |
| FR-12 | The system shall offer a single-player mode with a timer and a final score. | M | The result screen shows time, penalties and score. |
| FR-13 | The system shall offer a two-player competitive mode in which both players race through the same maze (same seed) in split-screen viewports. | M | The first player to reach the exit wins; both viewports remain responsive at the target frame rate. |
| FR-14 | The system shall provide at least three difficulty levels that vary maze size and corridor width. | S | Difficulty can be chosen from the menu and is reflected in the generated maze. |
| FR-15 | The system shall offer a cooperative two-player mode. | C | Planned for a post-1.0 release. |

### 4.3 Interface and configuration

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-20 | Menus shall be operable using dwell selection with the pointer. | M | Every menu action can be triggered without keyboard or mouse. |
| FR-21 | The HUD shall display the timer and player state; a debug overlay shall show tracking rate, render rate and CPU usage. | S | The overlay can be toggled at runtime. |
| FR-22 | All tunable parameters shall be defined in a validated TOML configuration file with documented defaults. | M | Invalid values produce a clear error message at start-up. |
| FR-23 | The user interface shall support English and Spanish. | C | Language can be switched through configuration. |
| FR-24 | The application shall be exitable at any time through a documented, deliberate action (keyboard shortcut or long dwell on an exit control). | M | The application terminates cleanly and releases the camera. |

### 4.4 Telemetry

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-30 | The system may record performance and interaction metrics to a local CSV file. This feature shall be disabled by default and require explicit opt-in. | S | No file is written unless telemetry is enabled; no image data is ever recorded. |

## 5. Non-functional requirements

All performance targets apply to the reference platform (Section 1) with a USB camera at
640×480 and a 1080p display, measured with `scripts/benchmark.py` over a 5-minute session.

### 5.1 Performance and efficiency

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Render rate | ≥ 60 FPS average; 1 % low ≥ 50 FPS |
| NFR-02 | Input-to-display latency (finger movement to pointer drawn) | ≤ 150 ms at the 95th percentile |
| NFR-03 | Sustained tracking rate | ≥ 15 Hz (goal: 20–30 Hz) |
| NFR-04 | Average CPU use of the whole application | ≤ 60 % of total capacity (4 cores) |
| NFR-05 | Resident memory | ≤ 1 GiB |
| NFR-06 | Thermal behaviour | No CPU throttling during a 30-minute session with adequate cooling |
| NFR-07 | Start-up time to the main menu | ≤ 10 s |

### 5.2 Reliability and usability

| ID | Requirement | Target |
|---|---|---|
| NFR-10 | Robustness | A camera disconnection, tracking loss or invalid configuration shall never crash the application; it shall show an actionable message. |
| NFR-11 | Accessibility | High-contrast theme, large interaction targets and configurable dwell time. |
| NFR-12 | Lighting tolerance | Usable in typical indoor lighting; documentation lists recommended conditions. |

### 5.3 Privacy and security

| ID | Requirement |
|---|---|
| NFR-20 | Camera frames are processed in memory only; they are never written to disk or sent over a network. |
| NFR-21 | The application shall not require network access at runtime. Model files are fetched at install time and verified with a SHA-256 checksum. |
| NFR-22 | Recorded replay data (for tests) contains landmark coordinates only, never images. |
| NFR-23 | Dependencies are pinned in a lockfile and monitored for known vulnerabilities in CI. |

### 5.4 Maintainability and quality

| ID | Requirement | Target |
|---|---|---|
| NFR-30 | Test coverage of domain and core logic | ≥ 85 % line coverage |
| NFR-31 | Static quality | Linting, formatting and strict type checking pass in CI on every pull request |
| NFR-32 | Hardware independence in CI | The full test suite runs without camera or display (headless SDL) |
| NFR-33 | Extensibility | A new game can be added without modifying `core/` |
| NFR-34 | Documentation | Public APIs have docstrings; architecture decisions are recorded as ADRs |
| NFR-35 | Reproducibility | A fresh clone can be installed and run following the documentation only |
| NFR-36 | Portability | Development and CI on x86-64 Linux; runtime target Raspberry Pi OS 64-bit |

## 6. Constraints and assumptions

- **C-1** CPU-only inference on 4 × Cortex-A72 cores; no GPU compute.
- **C-2** Only components installable on aarch64 Raspberry Pi OS through `apt` or PyPI wheels are used (see `TECH_STACK.md`).
- **C-3** The main thread is reserved for input polling, game logic and rendering; vision runs off the main thread.
- **A-1** The player stands or sits roughly 0.5–1.5 m from the camera with the hand visible.
- **A-2** One camera is shared by both players.
- **A-3** The device has adequate cooling and a stable power supply.

## 7. Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| R-1 | The system Python version is not supported by the chosen MediaPipe wheels | Cannot install the tracker | `scripts/check_environment.py` verifies the toolchain before development; the vision layer sits behind a port so another backend can replace it |
| R-2 | Tracking rate too low under load | Sluggish control | Latest-frame-only queue, low capture resolution, adaptive tracking rate, frame-rate-independent rendering |
| R-3 | Poor lighting or busy backgrounds degrade detection | Lost or erratic pointer | Tracking-loss handling (FR-07), lighting guidance, configurable confidence thresholds |
| R-4 | Thermal throttling in long sessions | Frame drops | Cooling recommendation, throttling indicator in the debug overlay |
| R-5 | Fatigue from holding an arm raised | Poor usability | Short rounds, relaxed active region, forearm-resting guidance |

## 8. Traceability and acceptance

Each requirement has an identifier used in issues, pull requests and tests (for example
`Refs: FR-07`). A release is accepted when all **Must** requirements pass their acceptance
criteria and the benchmark report for the reference platform meets the NFR targets.
