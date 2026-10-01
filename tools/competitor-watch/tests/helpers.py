"""Shared test helpers. Importing this module makes `competitor_watch` importable however the tests are started."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

from competitor_watch.config import Config, parse_config  # noqa: E402
from competitor_watch.fetch import FetchResult, RawResponse, TransportError  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


KEYWORDS = {
    "contradiction": ["contradict\\w*", "conflict\\w*", "inconsisten\\w*", "discrepanc\\w*"],
    "change_time": ["before (?:you )?publish\\w*", "as you (?:type|write|edit)\\w*", "real[- ]time", "prevent\\w*"],
}


def make_config(sources: list[dict[str, Any]], **over: Any) -> Config:
    obj: dict[str, Any] = {"schema": 1, "user_agent": "test-agent/0 (+https://example.test)", "keywords": KEYWORDS, "sources": sources}
    obj.update(over)
    return parse_config(obj)


def source(id: str, kind: str = "marketplace-listing", **over: Any) -> dict[str, Any]:
    s: dict[str, Any] = {"id": id, "name": id.replace("-", " ").title(), "kind": kind, "role": "competitor", "urls": [f"https://example.test/{id}"], "min_text_chars": 100}
    s.update(over)
    return s


def ok(url: str, html: str, status: int = 200) -> FetchResult:
    return FetchResult(url, True, status, url, "text/html; charset=utf-8", html.encode("utf-8"), None, "2026-10-01T00:00:00Z", 1)


def bad(url: str, error: str = "HTTP 503", status: int | None = 503) -> FetchResult:
    return FetchResult(url, False, status, None, None, b"", error, "2026-10-01T00:00:00Z", 3)


class FakeTransport:
    """Scripted responses per URL: a RawResponse, a TransportError, or a list consumed one per call. Records every call."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float, max_bytes: int) -> RawResponse:
        self.calls.append((url, headers))
        route = self.routes.get(url)
        if route is None:
            return RawResponse(404, {}, b"", url)
        if isinstance(route, list):
            route = route.pop(0) if len(route) > 1 else route[0]
        if isinstance(route, Exception):
            raise route
        return route


def html_response(url: str, html: str, status: int = 200, headers: dict[str, str] | None = None) -> RawResponse:
    h = {"content-type": "text/html; charset=utf-8"}
    h.update(headers or {})
    return RawResponse(status, h, html.encode("utf-8"), url)


__all__ = ["FIXTURES", "FakeTransport", "TransportError", "bad", "fixture", "html_response", "make_config", "ok", "source"]
