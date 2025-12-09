from __future__ import annotations

from typing import Callable, Iterable, Mapping

from ..config import Credentials
from .base import PelotonAPIClient
from .geudrik import GeudrikPelotonClient
from .pylotoncycle_client import PylotonCycleClient
from .requests_client import RequestsClient

ClientFactory = Callable[[Credentials], PelotonAPIClient]

_CLIENTS: Mapping[str, ClientFactory] = {
    "geudrik": GeudrikPelotonClient,
    "pylotoncycle": PylotonCycleClient,
    "requests": RequestsClient,
}


def available_clients() -> Iterable[str]:
    return sorted(_CLIENTS.keys())


def get_client(name: str, credentials: Credentials) -> PelotonAPIClient:
    try:
        factory = _CLIENTS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown client '{name}'. Available: {', '.join(available_clients())}") from exc
    return factory(credentials)
