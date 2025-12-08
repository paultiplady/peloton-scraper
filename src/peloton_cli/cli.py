from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .clients import available_clients, get_client
from .config import Credentials, MissingCredentialsError, load_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="peloton-cli",
        description="Minimal Peloton CLI with pluggable API backends.",
    )
    parser.add_argument(
        "--client",
        default="geudrik",
        choices=list(available_clients()),
        help="Peloton API client implementation to use.",
    )
    parser.add_argument(
        "--env-file",
        dest="env_files",
        action="append",
        default=[],
        help="Additional env files to load (in addition to .env/.envfile).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("profile", help="Fetch the profile for the authenticated user.")

    workouts_parser = subparsers.add_parser("workouts", help="List workouts for the authenticated user.")
    workouts_parser.add_argument("--limit", type=int, default=10, help="Maximum number of workouts to request.")
    workouts_parser.add_argument("--page", type=int, default=0, help="Page index to request from the API.")

    workout_parser = subparsers.add_parser("workout", help="Fetch a single workout by workout_id.")
    workout_parser.add_argument("workout_id", help="Peloton workout identifier.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_environment(additional_files=args.env_files)

    try:
        credentials = Credentials.from_env()
    except MissingCredentialsError as exc:
        parser.error(str(exc))

    try:
        client = get_client(args.client, credentials)
    except ValueError as exc:  # pragma: no cover - defensive
        parser.error(str(exc))

    try:
        payload = execute_command(args, client)
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    emit_json(payload)
    return 0


def execute_command(args: argparse.Namespace, client) -> Any:
    if args.command == "profile":
        return client.fetch_profile()

    if args.command == "workouts":
        if args.limit < 1:
            raise ValueError("--limit must be >= 1")
        if args.page < 0:
            raise ValueError("--page must be >= 0")
        return client.fetch_workouts(limit=args.limit, page=args.page)

    if args.command == "workout":
        return client.fetch_workout(args.workout_id)

    raise ValueError(f"Unknown command '{args.command}'")


def emit_json(payload: Any) -> None:
    print(json.dumps(payload, sort_keys=True, indent=2))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
