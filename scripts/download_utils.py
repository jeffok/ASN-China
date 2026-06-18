from __future__ import annotations

import re

import requests


GITHUB_PROXY_PREFIXES = (
    "https://gh-proxy.com/",
    "https://ghfast.top/",
)


def _to_jsdelivr(url: str) -> str | None:
    match = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)", url)
    if not match:
        return None

    user, repo, branch, path = match.groups()
    return f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{path}"


def github_mirror_urls(url: str) -> list[str]:
    """Return domestic-friendly mirrors for GitHub raw URLs before the origin URL."""
    urls: list[str] = []

    jsdelivr_url = _to_jsdelivr(url)
    if jsdelivr_url:
        urls.append(jsdelivr_url)

    if url.startswith("https://raw.githubusercontent.com/"):
        urls.extend(f"{prefix}{url}" for prefix in GITHUB_PROXY_PREFIXES)

    urls.append(url)

    seen = set()
    return [candidate for candidate in urls if not (candidate in seen or seen.add(candidate))]


def download_bytes(url: str, timeout: int | tuple[int, int] = 10) -> bytes:
    last_exc: Exception | None = None
    for candidate in github_mirror_urls(url):
        try:
            response = requests.get(candidate, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ {candidate} 失败: {exc}")
            last_exc = exc
    raise RuntimeError(f"所有 GitHub 镜像均失败: {url}") from last_exc


def download_text(url: str, timeout: int | tuple[int, int] = 10) -> str:
    return download_bytes(url, timeout=timeout).decode("utf-8", "ignore")
