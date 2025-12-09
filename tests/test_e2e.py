"""End-to-end tests for Peloton API client.

These tests require valid PELOTON_USERNAME and PELOTON_PASSWORD environment variables.
Run with: uv run pytest tests/test_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from peloton_cli.clients.requests_client import RequestsClient
from peloton_cli.config import Credentials


@pytest.fixture
def credentials() -> Credentials:
    """Get credentials from environment."""
    username = os.environ.get("PELOTON_USERNAME")
    password = os.environ.get("PELOTON_PASSWORD")
    if not username or not password:
        pytest.skip("PELOTON_USERNAME and PELOTON_PASSWORD required")
    return Credentials(username=username, password=password)


@pytest.fixture
def client(credentials: Credentials) -> RequestsClient:
    """Create authenticated client."""
    return RequestsClient(credentials)


class TestOAuthPKCELogin:
    """Test OAuth PKCE authentication flow."""

    def test_fetch_profile(self, client: RequestsClient) -> None:
        """Test that we can authenticate and fetch user profile."""
        profile = client.fetch_profile()

        # Basic structure checks
        assert isinstance(profile, dict)
        assert "id" in profile
        assert "username" in profile
        assert isinstance(profile["id"], str)
        assert len(profile["id"]) > 0

    def test_fetch_workouts(self, client: RequestsClient) -> None:
        """Test that we can fetch workouts list."""
        result = client.fetch_workouts(limit=3)

        assert isinstance(result, dict)
        assert "data" in result
        assert "count" in result
        assert "limit" in result
        assert result["limit"] == 3
        assert isinstance(result["data"], list)

    def test_fetch_workouts_pagination(self, client: RequestsClient) -> None:
        """Test workout pagination."""
        page0 = client.fetch_workouts(limit=2, page=0)
        page1 = client.fetch_workouts(limit=2, page=1)

        assert page0["page"] == 0
        assert page1["page"] == 1

        # If there are enough workouts, pages should be different
        if len(page0["data"]) == 2 and len(page1["data"]) > 0:
            assert page0["data"][0]["id"] != page1["data"][0]["id"]

    def test_fetch_single_workout(self, client: RequestsClient) -> None:
        """Test fetching a single workout by ID."""
        # First get a workout ID from the list
        workouts = client.fetch_workouts(limit=1)
        if not workouts["data"]:
            pytest.skip("No workouts available")

        workout_id = workouts["data"][0]["id"]
        workout = client.fetch_workout(workout_id)

        assert isinstance(workout, dict)
        assert workout["id"] == workout_id
        assert "fitness_discipline" in workout


class TestInputValidation:
    """Test input validation without hitting the API."""

    def test_workouts_limit_must_be_positive(self, client: RequestsClient) -> None:
        """Test that limit must be >= 1."""
        with pytest.raises(ValueError, match="limit must be >= 1"):
            client.fetch_workouts(limit=0)

    def test_workouts_page_must_be_non_negative(self, client: RequestsClient) -> None:
        """Test that page must be >= 0."""
        with pytest.raises(ValueError, match="page must be >= 0"):
            client.fetch_workouts(limit=10, page=-1)

    def test_workout_id_required(self, client: RequestsClient) -> None:
        """Test that workout_id must be provided."""
        with pytest.raises(ValueError, match="workout_id must be provided"):
            client.fetch_workout("")
