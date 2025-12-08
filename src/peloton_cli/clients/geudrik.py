from __future__ import annotations

import os
from typing import Any, Mapping

from ..config import Credentials
from .base import PelotonAPIClient


class GeudrikPelotonClient(PelotonAPIClient):
    """Adapter around geudrik/peloton-client-library."""

    def __init__(self, credentials: Credentials):
        self._credentials = credentials
        self._peloton_module = None

    def fetch_profile(self) -> Mapping[str, Any]:
        api = self._api()
        response = api._api_request("/api/me")
        return response.json()

    def fetch_workouts(self, *, limit: int, page: int = 0) -> Mapping[str, Any]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        api = self._api()
        if api.user_id is None:
            api._create_api_session()

        params = {
            "page": page,
            "limit": limit,
            "joins": "ride,ride.instructor",
        }
        response = api._api_request(f"/api/user/{api.user_id}/workouts", params=params)
        payload = response.json()
        payload["limit"] = limit
        payload["page"] = page
        return payload

    def fetch_workout(self, workout_id: str) -> Mapping[str, Any]:
        if not workout_id:
            raise ValueError("workout_id must be provided")

        api = self._api()
        response = api._api_request(f"/api/workout/{workout_id}")
        return response.json()

    def _api(self):
        module = self._import_module()
        return module.PelotonAPI

    def _import_module(self):
        if self._peloton_module is None:
            os.environ["PELOTON_USERNAME"] = self._credentials.username
            os.environ["PELOTON_PASSWORD"] = self._credentials.password
            from peloton import peloton as peloton_module

            peloton_module.PelotonAPI.peloton_username = self._credentials.username
            peloton_module.PelotonAPI.peloton_password = self._credentials.password
            peloton_module.PelotonAPI.peloton_session = None
            peloton_module.PelotonAPI.user_id = None
            self._peloton_module = peloton_module
        return self._peloton_module
