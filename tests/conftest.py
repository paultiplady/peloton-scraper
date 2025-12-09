"""Pytest configuration for e2e tests."""

from __future__ import annotations

from dotenv import load_dotenv


def pytest_configure() -> None:
    """Load environment variables before tests run."""
    load_dotenv(".env")
    load_dotenv(".envfile")
