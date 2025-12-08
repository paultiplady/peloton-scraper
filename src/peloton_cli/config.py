from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

DEFAULT_ENV_FILES = (".env", ".envfile")


class MissingCredentialsError(RuntimeError):
    """Raised when the required Peloton credentials are not present."""


def load_environment(additional_files: Sequence[str | os.PathLike[str]] | None = None) -> None:
    """Load environment variables from .env-style files if they exist."""

    candidates: list[Path] = []
    override = os.environ.get("PELOTON_ENV_FILE")
    if override:
        candidates.append(Path(override).expanduser())

    if additional_files:
        candidates.extend(Path(f).expanduser() for f in additional_files)

    candidates.extend(Path(name) for name in DEFAULT_ENV_FILES)

    seen: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen or not path.exists():
            continue
        load_dotenv(path, override=False)
        seen.add(path)


@dataclass(slots=True)
class Credentials:
    username: str
    password: str

    @classmethod
    def from_env(cls) -> "Credentials":
        username = os.environ.get("PELOTON_USERNAME")
        password = os.environ.get("PELOTON_PASSWORD")

        missing: list[str] = []
        if not username:
            missing.append("PELOTON_USERNAME")
        if not password:
            missing.append("PELOTON_PASSWORD")

        if missing:
            raise MissingCredentialsError(
                f"Missing required credential(s): {', '.join(missing)}. "
                "Set them in the environment or an env file."
            )

        return cls(username=username or "", password=password or "")
