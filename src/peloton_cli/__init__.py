"""Peloton CLI package."""

from importlib import metadata

try:
    __version__ = metadata.version("peloton-cli")
except metadata.PackageNotFoundError:  # pragma: no cover - local execution
    __version__ = "0.0.0"

__all__ = ["__version__"]
