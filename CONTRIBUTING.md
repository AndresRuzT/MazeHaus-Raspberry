# Contributing to FingerMaze

Thank you for your interest in contributing. This guide describes how we work so that the repository
stays consistent, reviewable and releasable at any time.

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## 1. Getting started

```bash
git clone https://github.com/<organisation>/fingermaze.git
cd fingermaze
uv sync                      # create the environment from uv.lock
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
uv run python scripts/check_environment.py
```

Without `uv`, create a virtual environment and install with `pip install -e ".[dev]"`
(see the README for details). The full test suite runs without a camera or a display:

```bash
SDL_VIDEODRIVER=dummy uv run pytest
```

Quality gates, all enforced in CI and by the pre-commit hooks:

| Gate | Command |
|---|---|
| Format and lint | `uv run ruff format --check . && uv run ruff check .` |
| Types | `uv run mypy src` |
| Tests and coverage | `uv run pytest --cov=fingermaze --cov-fail-under=85` |
| Architecture rules | `uv run lint-imports` |

## 2. Workflow

- **Trunk-based development.** `main` is always releasable and protected: pull request required,
  CI must pass, at least one approving review, linear history (squash or rebase merge).
- **Short-lived branches** named `<type>/<short-description>`, for example `feat/one-euro-filter`
  or `fix/penalty-double-count`.
- **Issues first** for anything non-trivial. Reference requirement identifiers
  (for example `FR-07`) from [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).
- **Small pull requests.** One logical change per pull request; each commit must build and pass tests.
- **Architecture decisions** that change a port, a dependency or the concurrency model require an ADR in
  `docs/adr/` in the same pull request.

### Definition of done

- [ ] Code is typed, linted and formatted; all gates pass.
- [ ] Behaviour is covered by tests (unit, and integration where a scene or adapter is involved).
- [ ] Public APIs have docstrings; user-visible behaviour is documented.
- [ ] No new dependency without justification in the pull request and in `docs/TECH_STACK.md`.
- [ ] Performance-sensitive changes include a `scripts/benchmark.py` result from a Raspberry Pi.
- [ ] The commit history follows the convention below.

## 3. Commit convention

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), enforced
locally by `commitizen` (`cz check`) in the `commit-msg` hook and again in CI.

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 3.1 Types

| Type | Use for | SemVer effect |
|---|---|---|
| `feat` | A new user-visible capability | minor |
| `fix` | A bug fix | patch |
| `perf` | A performance improvement without behaviour change | patch |
| `refactor` | Code change that neither fixes a bug nor adds a feature | none |
| `test` | Adding or correcting tests | none |
| `docs` | Documentation only | none |
| `build` | Build system, packaging, dependencies | none (patch if runtime impact) |
| `ci` | CI configuration and scripts | none |
| `style` | Formatting with no code change | none |
| `chore` | Maintenance that fits no other type | none |
| `revert` | Reverts a previous commit | depends on the reverted change |

A `!` after the type or scope, or a `BREAKING CHANGE:` footer, marks an incompatible change and
triggers a major bump (after 1.0.0).

### 3.2 Scopes

`core`, `config`, `input`, `camera`, `tracking`, `filters`, `calibration`, `ui`, `maze`, `telemetry`,
`i18n`, `scripts`, `deps`, `release`. Omit the scope when a change is cross-cutting.

### 3.3 Rules

1. Subject: imperative mood, lower case, no trailing period, at most 72 characters
   (`add one euro filter`, not `Added one euro filter.`).
2. Body (optional but encouraged for non-trivial changes): explain **why**, wrapped at 100 characters.
3. Footer: `Refs: FR-07, NFR-02` for requirements, `Closes #123` for issues,
   `BREAKING CHANGE: <description>` when applicable.
4. One logical change per commit; do not mix refactoring with behaviour changes.
5. Never commit generated files, model binaries, credentials or captured images.

Example:

```
feat(input): add latest-value mailbox for pointer snapshots

The vision worker publishes snapshots at tracking rate while the main
loop reads at render rate. A single-slot mailbox avoids queue growth and
guarantees that the game always sees the newest sample.

Refs: FR-02, NFR-02
```

## 4. Versioning and releases

- [Semantic Versioning 2.0.0](https://semver.org/). Versions below `1.0.0` may change the public
  interface in minor releases; this is stated in the changelog.
- The changelog follows [Keep a Changelog](https://keepachangelog.com/) and is generated from the
  commit history by `commitizen`.
- Release procedure (maintainers):

  ```bash
  git switch main && git pull --ff-only
  uv run cz bump --changelog     # computes the version, updates changelog, commits, tags vX.Y.Z
  git push --follow-tags
  ```

  Pushing the tag triggers the release workflow, which builds the distribution, attaches it to a
  GitHub release and publishes the notes from the changelog.
- Every release records its on-device benchmark in `docs/COMPATIBILITY.md`.

## 5. Roadmap and planned commit history

The initial history is built progressively, one milestone at a time. Each line is a planned commit
(or a small group of commits) and every milestone ends with a tag.

### Milestone 0: repository foundation, `v0.0.1`

1. `chore: initialize repository with licence, gitignore and editorconfig`
2. `build: add pyproject with src layout and tooling configuration`
3. `ci: add lint, type-check and test workflow`
4. `build: add pre-commit and commitizen hooks`
5. `docs: add requirements, stack and architecture documents`
6. `docs: add contributing guide, code of conduct and issue templates`

### Milestone 1: environment and core loop, `v0.1.0`

7. `feat(scripts): add environment check for python, wheels and camera`
8. `feat(scripts): add model download with checksum verification`
9. `feat(config): add validated toml settings`
10. `feat(core): add fixed-timestep game loop`
11. `feat(core): add scene manager and scene protocol`
12. `feat(input): add mouse input provider for development`
13. `test(core): add headless integration harness`

### Milestone 2: vision input, `v0.2.0`

14. `feat(camera): add opencv camera source and fake source`
15. `feat(input): add latest-value mailbox`
16. `feat(tracking): add mediapipe hand tracker adapter`
17. `feat(input): add vision worker with stale-frame dropping`
18. `feat(filters): add one euro filter`
19. `feat(input): add camera-to-screen mapping and player assignment`
20. `feat(calibration): add active region calibration`
21. `feat(input): add hand-loss detection and pause`
22. `feat(scripts): add landmark recording and replay input`
23. `perf: add benchmark script and debug overlay`

### Milestone 3: maze game, `v0.3.0`

24. `feat(maze): add deterministic maze generator`
25. `test(maze): add property-based tests for connectivity and determinism`
26. `feat(maze): add collision detection and checkpoints`
27. `feat(maze): add scoring and difficulty presets`
28. `feat(maze): add single-player scene and rendering`
29. `feat(maze): add two-player split-screen mode`

### Milestone 4: interface and polish, `v0.4.0`

30. `feat(ui): add dwell-selection buttons and menu scenes`
31. `feat(ui): add hud, result screen and high-contrast theme`
32. `feat(telemetry): add opt-in csv metrics`
33. `feat(i18n): add english and spanish catalogs`
34. `docs: add raspberry pi installation and troubleshooting guide`

### Milestone 5: hardening, `v1.0.0`

35. `perf(core): optimise hot paths identified by on-device profiling`
36. `fix: resolve issues found in acceptance testing`
37. `docs: record compatibility and benchmark results`
38. `chore(release): v1.0.0`

## 6. Reporting issues and security

- Bugs: open an issue with the output of `scripts/check_environment.py`, the Raspberry Pi model, the
  operating system version and the camera model.
- Security concerns: follow [SECURITY.md](SECURITY.md); do not open a public issue.
