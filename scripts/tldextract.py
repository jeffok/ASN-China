from __future__ import annotations

from dataclasses import dataclass


MULTI_LABEL_SUFFIXES = {
    "ac.cn",
    "co.jp",
    "co.kr",
    "co.nz",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.hk",
    "com.my",
    "com.sg",
    "com.tr",
    "com.tw",
    "edu.cn",
    "gov.cn",
    "net.cn",
    "ne.jp",
    "org.cn",
    "org.uk",
}


@dataclass(frozen=True)
class ExtractResult:
    subdomain: str
    domain: str
    suffix: str


class TLDExtract:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def __call__(self, host: str) -> ExtractResult:
        labels = [part for part in host.strip().strip(".").lower().split(".") if part]
        if len(labels) < 2:
            return ExtractResult("", labels[0] if labels else "", "")

        suffix_len = 1
        if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
            suffix_len = 2

        suffix = ".".join(labels[-suffix_len:])
        domain_index = len(labels) - suffix_len - 1
        if domain_index < 0:
            return ExtractResult("", "", suffix)

        domain = labels[domain_index]
        subdomain = ".".join(labels[:domain_index])
        return ExtractResult(subdomain, domain, suffix)
