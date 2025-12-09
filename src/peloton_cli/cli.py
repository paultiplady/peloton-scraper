from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from .clients import available_clients, get_client
from .clients.base import PelotonAPIClient
from .config import Credentials, MissingCredentialsError, load_environment

app = typer.Typer(
    add_completion=False,
    help="Minimal Peloton CLI with pluggable API backends.",
)


def _client_completions(_: str, incomplete: str) -> list[str]:
    return [name for name in available_clients() if name.startswith(incomplete)]


@app.callback()
def initialize(
    ctx: typer.Context,
    client: str = typer.Option(
        "requests",
        "--client",
        "-c",
        help="Peloton API client implementation.",
        show_default=True,
        autocompletion=_client_completions,
    ),
    env_file: list[Path] = typer.Option(
        None,
        "--env-file",
        help="Additional env files to load (in addition to .env/.envfile).",
    ),
) -> None:
    """Load credentials and initialize the requested client."""

    ctx.ensure_object(dict)
    env_files = [str(path) for path in env_file] if env_file else None
    load_environment(additional_files=env_files)

    try:
        credentials = Credentials.from_env()
    except MissingCredentialsError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        ctx.obj["client"] = get_client(client, credentials)
    except ValueError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2)


@app.command()
def profile(ctx: typer.Context) -> None:
    """Fetch the profile for the authenticated user."""

    client: PelotonAPIClient = ctx.obj["client"]
    emit_json(client.fetch_profile())


@app.command()
def workouts(
    ctx: typer.Context,
    limit: int = typer.Option(
        10, "--limit", "-l", min=1, help="Maximum number of workouts."
    ),
    page: int = typer.Option(0, "--page", "-p", min=0, help="Page index to request."),
) -> None:
    """List workouts for the authenticated user."""

    client: PelotonAPIClient = ctx.obj["client"]
    emit_json(client.fetch_workouts(limit=limit, page=page))


@app.command()
def workout(
    ctx: typer.Context,
    workout_id: str = typer.Argument(..., help="Peloton workout identifier."),
) -> None:
    """Fetch a single workout by workout_id."""

    if not workout_id:
        typer.secho("workout_id must be provided", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=3)

    client: PelotonAPIClient = ctx.obj["client"]
    emit_json(client.fetch_workout(workout_id))


def emit_json(payload: Any) -> None:
    print(json.dumps(payload, sort_keys=True, indent=2))


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
