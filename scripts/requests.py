from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass
class Response:
    url: str
    status_code: int
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "ignore")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPError(self.url, self.status_code, f"HTTP {self.status_code}", hdrs=None, fp=None)


def _timeout_seconds(timeout: Any) -> float:
    if isinstance(timeout, tuple):
        return float(max(timeout))
    if timeout is None:
        return 60.0
    return float(timeout)


def get(url: str, timeout: Any = 60, **_: Any) -> Response:
    req = Request(url, headers={"User-Agent": "ASN-China/ci"})
    with urlopen(req, timeout=_timeout_seconds(timeout)) as resp:
        return Response(url=url, status_code=resp.status, content=resp.read())
