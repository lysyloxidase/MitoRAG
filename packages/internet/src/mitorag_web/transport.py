"""Async HTTP transport used by scientific API clients."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from typing import Dict, Mapping, Optional, Protocol, Tuple

Params = Mapping[str, object]
Headers = Optional[Mapping[str, str]]


class AsyncHTTPTransport(Protocol):
    async def get_json(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Headers = None,
    ) -> object:
        """GET a URL and parse JSON."""
        ...

    async def get_text(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Headers = None,
    ) -> str:
        """GET a URL and return text."""
        ...


class StdlibAsyncHTTPTransport:
    """Async wrapper around urllib.request to keep dependencies light."""

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    async def get_json(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Headers = None,
    ) -> object:
        text = await self.get_text(url, params=params, headers=headers)
        return json.loads(text)

    async def get_text(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Headers = None,
    ) -> str:
        return await asyncio.to_thread(self._get_text_sync, url, params, headers)

    def _get_text_sync(self, url: str, params: Optional[Params], headers: Headers) -> str:
        full_url = build_url(url, params)
        request = urllib.request.Request(
            full_url,
            headers=dict(headers or {}),
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8")


def build_url(url: str, params: Optional[Params]) -> str:
    if not params:
        return url
    encoded = urllib.parse.urlencode(_normalize_params(params), doseq=True)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{encoded}"


def normalized_params(params: Optional[Params]) -> Tuple[Tuple[str, str], ...]:
    if not params:
        return ()
    return tuple(sorted((key, str(value)) for key, value in params.items()))


def _normalize_params(params: Params) -> Dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}

