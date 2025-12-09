# Peloton CLI

Minimal Peloton command-line interface layered over pluggable API client adapters. The initial implementation uses [`geudrik/peloton-client-library`](https://github.com/geudrik/peloton-client-library) under the hood but the client layer is swappable so we can evaluate other libraries without changing the CLI surface.

## Features
- Fetch your Peloton profile or workout data and emit deterministic, sorted JSON.
- Credentials loaded from environment variables or `.env`/`.envfile` files (with optional overrides).
- [Typer](https://typer.tiangolo.com/) powers the CLI experience with rich help text and validation.
- Client registry allows multiple Peloton API implementations; shipped with both [pylotoncycle](https://github.com/justmedude/pylotoncycle) (default) and the Geudrik adapter.
- Packaged with Hatch via `pyproject.toml`, managed with [uv](https://github.com/astral-sh/uv) for development workflows.

## Requirements
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed and on your `PATH`.
- Peloton credentials available as environment variables (`PELOTON_USERNAME`/`PELOTON_PASSWORD`).

## Setup
1. Install dependencies:
   ```bash
   uv sync
   ```
2. Provide credentials via any of the following methods (first hit wins):
   - Export env vars directly: `export PELOTON_USERNAME=...` and `export PELOTON_PASSWORD=...`.
   - Add them to a `.env` or `.envfile` in the repo root.
   - Point to another env file with `export PELOTON_ENV_FILE=/path/to/file`.
   - Pass `--env-file path/to/file` when running the CLI.
3. Run commands via uv:
   ```bash
   uv run peloton-cli profile
   uv run peloton-cli workouts --limit 5
   uv run peloton-cli workout <workout_id>
   ```
   Use the Geudrik adapter explicitly with `uv run peloton-cli --client geudrik profile`.

All commands print JSON with stable key ordering so you can easily diff responses or feed them to other tooling.

## Client Architecture
`peloton_cli.clients` holds an adapter registry. Each adapter implements `PelotonAPIClient` (see `clients/base.py`) so the CLI can be agnostic to the underlying HTTP library. Additions only need to register their factory in `clients/__init__.py` and implement the three methods (`fetch_profile`, `fetch_workouts`, `fetch_workout`).

Built-in adapters:
- `pylotoncycle` (default) via [`justmedude/pylotoncycle`](https://github.com/justmedude/pylotoncycle)
- `geudrik` via [`geudrik/peloton-client-library`](https://github.com/geudrik/peloton-client-library)

Switch clients at runtime with the `--client` flag as new adapters land.

## Development
- Format/lint: `uv run ruff check .` and `uv run black .`
- Tests (future): `uv run pytest`
- Build an sdist/wheel: `uv build`

Open items and future enhancements live in `TODO.md`.
