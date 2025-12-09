from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pylotoncycle import PylotonCycle
from pylotoncycle.pylotoncycle import PelotonLoginException

from ..config import Credentials
from .base import PelotonAPIClient


class PylotonCycleClient(PelotonAPIClient):
    """Adapter that wraps justmedude/pylotoncycle."""

    def __init__(self, credentials: Credentials):
        self._credentials = credentials
        self._client: PylotonCycle | None = None

    def fetch_profile(self) -> Mapping[str, Any]:
        client = self._ensure_client()
        return client.GetMe()

    def fetch_workouts(self, *, limit: int, page: int = 0) -> Mapping[str, Any]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if page < 0:
            raise ValueError("page must be >= 0")

        client = self._ensure_client()
        if client.userid is None:
            client.GetMe()

        params = {
            "page": page,
            "limit": limit,
            "sort_by": "-created",
            "joins": "ride,ride.instructor",
        }
        payload = self._get_json(
            client,
            f"{client.base_url}/api/user/{client.userid}/workouts",
            params=params,
        )
        payload["limit"] = limit
        payload["page"] = page
        return payload

    def fetch_workout(self, workout_id: str) -> Mapping[str, Any]:
        if not workout_id:
            raise ValueError("workout_id must be provided")

        client = self._ensure_client()
        return client.GetWorkoutById(workout_id)

    def _ensure_client(self) -> PylotonCycle:
        if self._client is None:
            try:
                self._client = PylotonCycle(
                    self._credentials.username,
                    self._credentials.password,
                )
            except PelotonLoginException as exc:  # pragma: no cover - runtime validation
                raise RuntimeError(f"Peloton login failed: {exc}") from exc
        return self._client

    @staticmethod
    def _get_json(client: PylotonCycle, url: str, params: dict[str, Any]) -> Mapping[str, Any]:
        response = client.s.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, Mapping) and data.get("status") not in (None, 0) and data.get("status") >= 400:
            message = data.get("message", "Peloton API error")
            raise RuntimeError(f"{message} (status {data.get('status')})")
        return data
