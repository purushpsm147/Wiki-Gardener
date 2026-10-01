"""Polite fetching: a descriptive User-Agent, robots.txt respected, bounded retries, a size cap, and failures reported, never hidden.

The network sits behind a `Transport` so tests run with no network. `urllib_transport` is the real one.
"""
from __future__ import annotations

import re
import socket
import ssl
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlsplit

MAX_BYTES = 5_000_000
RETRY_AFTER_CAP_SECONDS = 30.0


class TransportError(Exception):
    """The request never produced an HTTP response: DNS, TLS, connection reset, timeout."""


@dataclass
class RawResponse:
    status: int
    headers: dict[str, str]  # lower-case names
    body: bytes
    final_url: str
    truncated: bool = False


Transport = Callable[[str, dict[str, str], float, int], RawResponse]


def urllib_transport(url: str, headers: dict[str, str], timeout: float, max_bytes: int) -> RawResponse:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # redirects are followed by urllib
            body = response.read(max_bytes + 1)
            return RawResponse(
                status=response.status,
                headers={k.lower(): v for k, v in response.headers.items()},
                body=body[:max_bytes],
                final_url=response.geturl(),
                truncated=len(body) > max_bytes,
            )
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2000)
        except Exception:  # noqa: BLE001 - the status is what matters
            body = b""
        return RawResponse(status=e.code, headers={k.lower(): v for k, v in (e.headers or {}).items()}, body=body, final_url=url)
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise TransportError(f"{type(e).__name__}: {reason}") from None


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None
    final_url: str | None
    content_type: str | None
    body: bytes
    error: str | None
    fetched_at: str
    attempts: int = 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Fetcher:
    def __init__(
        self,
        user_agent: str,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
        timeout: float = 20.0,
        retries: int = 2,
        max_bytes: int = MAX_BYTES,
        respect_robots: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.transport = transport
        self.sleep = sleep
        self.timeout = timeout
        self.retries = retries
        self.max_bytes = max_bytes
        self.respect_robots = respect_robots
        self._robots: dict[str, urllib.robotparser.RobotFileParser | str] = {}

    def _headers(self) -> dict[str, str]:
        # identity: urllib does not decompress, and a gzip body would be unreadable
        return {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5", "Accept-Language": "en", "Accept-Encoding": "identity"}

    def _robots_verdict(self, url: str) -> str | None:
        """None when the fetch is allowed, otherwise the reason it is not."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            try:
                res = self.transport(f"{origin}/robots.txt", self._headers(), self.timeout, 500_000)
            except TransportError as e:
                self._robots[origin] = f"robots.txt unreachable ({e})"
            else:
                if res.status == 200:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(res.body.decode("utf-8", "replace").splitlines())
                    self._robots[origin] = rp
                elif 400 <= res.status < 500:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse([])  # no robots.txt: everything is allowed
                    self._robots[origin] = rp
                else:
                    self._robots[origin] = f"robots.txt unavailable (HTTP {res.status})"  # RFC 9309: treat as disallowed
        entry = self._robots[origin]
        if isinstance(entry, str):
            return entry
        return None if entry.can_fetch(self.user_agent, url) else "blocked by robots.txt"

    def fetch(self, url: str) -> FetchResult:
        def failed(error: str, status: int | None = None, attempts: int = 0) -> FetchResult:
            return FetchResult(url, False, status, None, None, b"", error, _now(), attempts)

        if self.respect_robots:
            verdict = self._robots_verdict(url)
            if verdict:
                return failed(verdict)

        last_error = "no attempt made"
        status: int | None = None
        for attempt in range(1, self.retries + 2):
            wait = 2.0 * (3 ** (attempt - 1))
            try:
                res = self.transport(url, self._headers(), self.timeout, self.max_bytes)
            except TransportError as e:
                last_error, status = str(e), None
            else:
                status = res.status
                if 200 <= res.status < 300:
                    ctype = res.headers.get("content-type", "")
                    if res.truncated:
                        return failed(f"response larger than {self.max_bytes} bytes", status, attempt)
                    if ctype and not re.search(r"html|json|xml|text/", ctype, re.I):
                        return failed(f"unexpected content type {ctype!r}", status, attempt)
                    return FetchResult(url, True, res.status, res.final_url, ctype or None, res.body, None, _now(), attempt)
                last_error = f"HTTP {res.status}"
                if res.status == 429 or res.status >= 500:
                    retry_after = res.headers.get("retry-after", "")
                    if retry_after.isdigit():
                        wait = min(float(retry_after), RETRY_AFTER_CAP_SECONDS)
                else:
                    return failed(last_error, res.status, attempt)  # 3xx left over, 401, 403, 404, ...: retrying will not help
            if attempt <= self.retries:
                self.sleep(wait)
        return failed(last_error, status, self.retries + 1)


def decode_body(body: bytes, content_type: str | None) -> str:
    """Decode with the charset the server declared, else the one in a <meta>, else UTF-8; never raise."""
    charset = None
    if content_type:
        m = re.search(r"charset=([\w-]+)", content_type, re.I)
        if m:
            charset = m.group(1)
    if charset is None:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        if m:
            charset = m.group(1).decode("ascii", "replace")
    try:
        return body.decode(charset or "utf-8", "replace")
    except LookupError:
        return body.decode("utf-8", "replace")
