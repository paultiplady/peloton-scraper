"""Lightweight requests-based Peloton API client with OAuth PKCE."""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import Mapping
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from ..config import Credentials
from .base import PelotonAPIClient

# OAuth constants from Peloton's web app
AUTH_DOMAIN = "auth.onepeloton.com"
AUTH_CLIENT_ID = "WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM"
AUTH_AUDIENCE = "https://api.onepeloton.com/"
AUTH_SCOPE = "offline_access openid peloton-api.members:default"
AUTH_REDIRECT_URI = "https://members.onepeloton.com/callback"
AUTH0_CLIENT = "eyJuYW1lIjoiYXV0aDAtc3BhLWpzIiwidmVyc2lvbiI6IjIuMS4zIn0="
AUTH0_CLIENT_ULP = "eyJuYW1lIjoiYXV0aDAuanMtdWxwIiwidmVyc2lvbiI6IjkuMTQuMyJ9"


class HiddenFormParser(HTMLParser):
    """Parse HTML to extract form action and hidden input fields."""

    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for k, v in attrs}
        if tag == "form" and "action" in attr_dict:
            self.action = attr_dict["action"]
        elif tag == "input" and attr_dict.get("type", "").lower() == "hidden":
            name = attr_dict.get("name")
            value = attr_dict.get("value", "")
            if name:
                self.fields[name] = value or ""


class RequestsClient(PelotonAPIClient):
    """Direct requests-based Peloton API client using OAuth PKCE."""

    BASE_URL = "https://api.onepeloton.com"

    def __init__(self, credentials: Credentials):
        self._credentials = credentials
        self._session: requests.Session | None = None
        self._bearer_token: str | None = None
        self._user_id: str | None = None

    def fetch_profile(self) -> Mapping[str, Any]:
        session, headers = self._ensure_authenticated()
        response = session.get(f"{self.BASE_URL}/api/me", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def fetch_workouts(self, *, limit: int, page: int = 0) -> Mapping[str, Any]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if page < 0:
            raise ValueError("page must be >= 0")

        session, headers = self._ensure_authenticated()
        user_id = self._ensure_user_id()

        params = {
            "page": page,
            "limit": limit,
            "sort_by": "-created",
            "joins": "ride,ride.instructor",
        }
        response = session.get(
            f"{self.BASE_URL}/api/user/{user_id}/workouts",
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        payload["limit"] = limit
        payload["page"] = page
        return payload

    def fetch_workout(self, workout_id: str) -> Mapping[str, Any]:
        if not workout_id:
            raise ValueError("workout_id must be provided")

        session, headers = self._ensure_authenticated()
        response = session.get(
            f"{self.BASE_URL}/api/workout/{workout_id}",
            params={"joins": "ride,ride.instructor"},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def _ensure_authenticated(self) -> tuple[requests.Session, dict[str, str]]:
        if self._session is None:
            self._session = requests.Session()
            self._login_oauth()
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        return self._session, headers

    def _ensure_user_id(self) -> str:
        if self._user_id is None:
            profile = self.fetch_profile()
            self._user_id = profile["id"]
        return self._user_id

    def _login_oauth(self) -> None:
        """Perform OAuth PKCE login flow."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        # Generate PKCE parameters
        code_verifier = _generate_random_string(64)
        code_challenge = _generate_code_challenge(code_verifier)
        state = _generate_random_string(32)
        nonce = _generate_random_string(32)

        # Step 1: Initiate auth flow
        authorize_url = _build_authorize_url(code_challenge, state, nonce)
        csrf_token, login_state = self._initiate_auth_flow(authorize_url, state)

        # Step 2: Submit credentials
        next_url = self._submit_credentials(csrf_token, login_state, nonce, code_challenge)

        # Step 3: Follow redirects to get authorization code
        auth_code = self._follow_auth_redirects(next_url)

        # Step 4: Exchange code for token
        self._bearer_token = self._exchange_code_for_token(auth_code, code_verifier)

    def _initiate_auth_flow(self, authorize_url: str, state: str) -> tuple[str, str]:
        """Start OAuth flow and extract CSRF token."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        # Follow redirects to login page
        response = self._session.get(authorize_url, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Extract state from final URL
        final_url = response.url
        parsed = urlparse(final_url)
        query_state = parse_qs(parsed.query).get("state", [state])[0]

        # Get CSRF token from cookies
        csrf_token = None
        for cookie in self._session.cookies:
            if cookie.name == "_csrf" and cookie.domain.endswith("onepeloton.com"):
                csrf_token = cookie.value
                break

        if not csrf_token:
            raise RuntimeError("Failed to get CSRF token from auth flow")

        return csrf_token, query_state

    def _submit_credentials(
        self, csrf_token: str, state: str, nonce: str, code_challenge: str
    ) -> str:
        """Submit username/password to Auth0."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        login_url = f"https://{AUTH_DOMAIN}/usernamepassword/login"
        payload = {
            "client_id": AUTH_CLIENT_ID,
            "redirect_uri": AUTH_REDIRECT_URI,
            "tenant": "peloton-prod",
            "response_type": "code",
            "scope": AUTH_SCOPE,
            "audience": AUTH_AUDIENCE,
            "_csrf": csrf_token,
            "state": state,
            "_intstate": "deprecated",
            "nonce": nonce,
            "username": self._credentials.username,
            "password": self._credentials.password,
            "connection": "pelo-user-password",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        response = self._session.post(
            login_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": f"https://{AUTH_DOMAIN}",
                "Auth0-Client": AUTH0_CLIENT_ULP,
            },
            timeout=30,
            allow_redirects=False,
        )

        # Check for redirect
        if response.status_code in (301, 302, 303, 307, 308):
            return response.headers.get("Location", "")

        # Otherwise parse HTML form and submit it
        if response.status_code != 200:
            raise RuntimeError(f"Login failed with status {response.status_code}: {response.text[:500]}")

        parser = HiddenFormParser()
        parser.feed(response.text)

        if not parser.action:
            raise RuntimeError(f"No form action found in login response: {response.text[:500]}")

        return self._submit_hidden_form(parser.action, parser.fields)

    def _submit_hidden_form(self, action: str, fields: dict[str, str]) -> str:
        """Submit the hidden callback form."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        # Make action URL absolute if needed
        if not action.startswith("http"):
            action = f"https://{AUTH_DOMAIN}{action}"

        response = self._session.post(
            action,
            data=fields,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
            timeout=30,
            allow_redirects=False,
        )

        location = response.headers.get("Location", "")
        if location:
            if not location.startswith("http"):
                location = f"https://{AUTH_DOMAIN}{location}"
            return location

        # If no redirect, return final URL
        return response.url

    def _follow_auth_redirects(self, start_url: str) -> str:
        """Follow redirects until we get the authorization code."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        current_url = start_url
        for _ in range(10):  # Max 10 redirects
            response = self._session.get(
                current_url,
                timeout=30,
                allow_redirects=False,
            )

            # Check current URL for code
            parsed = urlparse(response.url)
            code = parse_qs(parsed.query).get("code", [None])[0]
            if code:
                return code

            # Check Location header
            location = response.headers.get("Location", "")
            if location:
                parsed_loc = urlparse(location)
                code = parse_qs(parsed_loc.query).get("code", [None])[0]
                if code:
                    return code
                current_url = location
                if not current_url.startswith("http"):
                    current_url = f"https://{parsed.netloc}{location}"
            else:
                break

        raise RuntimeError("Failed to get authorization code from OAuth flow")

    def _exchange_code_for_token(self, code: str, code_verifier: str) -> str:
        """Exchange authorization code for access token."""
        if self._session is None:
            raise RuntimeError("Session not initialized")

        token_url = f"https://{AUTH_DOMAIN}/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": AUTH_CLIENT_ID,
            "code_verifier": code_verifier,
            "code": code,
            "redirect_uri": AUTH_REDIRECT_URI,
        }

        response = self._session.post(
            token_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise RuntimeError("No access token in token response")

        return access_token


def _generate_random_string(length: int) -> str:
    """Generate a URL-safe random string."""
    random_bytes = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(random_bytes).decode("ascii")[:length]


def _generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _build_authorize_url(code_challenge: str, state: str, nonce: str) -> str:
    """Build the OAuth authorize URL."""
    params = {
        "client_id": AUTH_CLIENT_ID,
        "audience": AUTH_AUDIENCE,
        "scope": AUTH_SCOPE,
        "response_type": "code",
        "response_mode": "query",
        "redirect_uri": AUTH_REDIRECT_URI,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "auth0Client": AUTH0_CLIENT,
    }
    return f"https://{AUTH_DOMAIN}/authorize?{urlencode(params)}"
