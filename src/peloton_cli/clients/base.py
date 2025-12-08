from __future__ import annotations

from typing import Any, Mapping, Protocol


class PelotonAPIClient(Protocol):
    """Common interface that Peloton API clients should implement."""

    def fetch_profile(self) -> Mapping[str, Any]: ...

    def fetch_workouts(self, *, limit: int, page: int = 0) -> Mapping[str, Any]: ...

    def fetch_workout(self, workout_id: str) -> Mapping[str, Any]: ...
