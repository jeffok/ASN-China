'''
Author: Jeff
Date: 2022-11-17
Description: 下载并合并国内域名、Apple 域名、代理域名列表，生成 SmartDNS 可直接使用的纯文本格式
Copyright © 2022 by Jeff, All Rights Reserved.
'''

from __future__ import annotations

import os
import re

import requests

from download_utils import github_mirror_urls


# 数据源
SOURCES = {
    # Loyalsoldier 国内直连域名
    "direct-list.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/direct-list.txt",
    # felixonmars 中国加速域名（dnsmasq 格式，需提取域名）
    "accelerated-domains.china.conf": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf",
    # felixonmars Apple 中国域名
    "apple.china.conf": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf",
    # Loyalsoldier Apple 中国域名
    "apple-cn.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/apple-cn.txt",
    # Loyalsoldier 代理域名
    "proxy-list.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/proxy-list.txt",
    # felixonmars 虚假 NXDOMAIN IP 过滤
    "bogus-nxdomain.china.conf": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/bogus-nxdomain.china.conf",
}
RELEASE_RAW_BASE = os.environ.get("ASN_CHINA_RELEASE_BASE", "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files").rstrip("/")

# 产物数量下限（2026-11 实测：cn≈110k / proxy≈26.5k / apple=165）；低于下限让 CI 失败，保留上一版 release-files
MIN_COUNTS = {"cn-domains.txt": 80000, "proxy-domains.txt": 15000, "apple-cn.txt": 100}


def download(url: str) -> str:
    """下载文件内容（国内 GitHub 镜像优先，raw 兜底）"""
    last_exc: Exception | None = None
    for u in github_mirror_urls(url):
        try:
            r = requests.get(u, timeout=10)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  ⚠ {u} 失败: {e}")
            last_exc = e
    raise RuntimeError(f"所有 GitHub 镜像均失败: {url}") from last_exc


def download_release_file(name: str) -> str:
    url = f"{RELEASE_RAW_BASE}/{name}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def download_or_release(url: str, fallback_file: str) -> str:
    try:
        return download(url)
    except Exception as exc:
        print(f"  外部源不可达，回退到 release-files/{fallback_file}: {exc}")
        return download_release_file(fallback_file)


_DOMAIN_RE = re.compile(r"^[a-z0-9_]([a-z0-9_.-]*[a-z0-9_])?$")


def extract_domains_plain(text: str) -> list[str]:
    """提取域名列表（每行一个域名，忽略注释和空行）。

    v2ray-rules-dat 格式前缀处理：
      - ``full:x.y`` / ``domain:x.y`` → 保留域名本体（输出为纯文本后缀匹配；
        ``full:`` 的精确语义会略微放宽到子域，对分流场景可接受）
      - ``regexp:`` / ``keyword:`` 及其它未知前缀 → 丢弃（纯文本无法表达）

    历史 bug：原实现对任何含 ``:`` 的行一律跳过，导致 ``full:`` 条目全部丢失
    （apple-cn 165 条全为 full: → 输出为空；direct-list 丢 199 条、proxy-list 丢 95 条）。
    """
    domains = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if ":" in line:
            prefix, _, rest = line.partition(":")
            if prefix not in ("full", "domain"):
                continue
            # 去掉可能的属性后缀，如 ``domain:x.com:@cn``
            line = rest.split(":", 1)[0].strip()
        line = line.lower().rstrip(".")
        if not line or not _DOMAIN_RE.match(line):
            continue
        domains.append(line)
    return domains


def require_min(name: str, count: int, minimum: int) -> None:
    """产物数量下限检查：不足则让 CI 失败，而不是静默发布缩水/空文件。"""
    if count < minimum:
        raise SystemExit(f"{name} 仅 {count} 条，低于下限 {minimum}，拒绝发布")


def extract_domains_dnsmasq(text: str) -> list[str]:
    """从 dnsmasq 格式提取域名（server=/example.com/...）"""
    domains = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("server=/"):
            parts = line.split("/")
            if len(parts) >= 2:
                domain = parts[1]
                if domain:
                    domains.append(domain)
    return domains


def write_list(domains: list[str], path: str, header: str) -> None:
    """保存域名列表"""
    with open(path, "w") as f:
        f.write(f"# {header}\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    # --- 国内域名（合并 Loyalsoldier direct-list + felixonmars accelerated-domains + apple）---
    print("下载国内域名列表...")
    cn_domains = set()

    try:
        # Loyalsoldier direct-list
        text = download(SOURCES["direct-list.txt"])
        domains = extract_domains_plain(text)
        print(f"  direct-list.txt: {len(domains)} 条")
        cn_domains.update(domains)

        # felixonmars accelerated-domains.china.conf
        text = download(SOURCES["accelerated-domains.china.conf"])
        domains = extract_domains_dnsmasq(text)
        print(f"  accelerated-domains.china.conf: {len(domains)} 条")
        cn_domains.update(domains)

        # felixonmars apple.china.conf
        text = download(SOURCES["apple.china.conf"])
        domains = extract_domains_dnsmasq(text)
        print(f"  apple.china.conf: {len(domains)} 条")
        cn_domains.update(domains)
    except Exception as exc:
        print(f"  国内域名外部源不可达，回退到 release-files/cn-domains.txt: {exc}")
        cn_domains = set(extract_domains_plain(download_release_file("cn-domains.txt")))

    cn_sorted = sorted(cn_domains)
    require_min("cn-domains.txt", len(cn_sorted), MIN_COUNTS["cn-domains.txt"])
    write_list(cn_sorted, "cn-domains.txt", "国内域名列表（合并去重，每日更新）")
    print(f"生成 cn-domains.txt（{len(cn_sorted)} 条）\n")

    # --- Apple 中国域名 ---
    print("下载 Apple 中国域名...")
    text = download_or_release(SOURCES["apple-cn.txt"], "apple-cn.txt")
    apple_domains = extract_domains_plain(text)
    apple_sorted = sorted(set(apple_domains))
    require_min("apple-cn.txt", len(apple_sorted), MIN_COUNTS["apple-cn.txt"])
    write_list(apple_sorted, "apple-cn.txt", "Apple 中国域名列表（每日更新）")
    print(f"生成 apple-cn.txt（{len(apple_sorted)} 条）\n")

    # --- 代理域名 ---
    print("下载代理域名列表...")
    text = download_or_release(SOURCES["proxy-list.txt"], "proxy-domains.txt")
    proxy_domains = extract_domains_plain(text)
    proxy_sorted = sorted(set(proxy_domains))
    require_min("proxy-domains.txt", len(proxy_sorted), MIN_COUNTS["proxy-domains.txt"])
    write_list(proxy_sorted, "proxy-domains.txt", "代理域名列表（每日更新）")
    print(f"生成 proxy-domains.txt（{len(proxy_sorted)} 条）\n")

    # --- 虚假 NXDOMAIN IP 过滤（直接下载保留原格式，dnsmasq/SmartDNS 直接 conf-file 引用）---
    print("下载 bogus-nxdomain 列表...")
    text = download_or_release(SOURCES["bogus-nxdomain.china.conf"], "bogus-nxdomain.china.conf")
    with open("bogus-nxdomain.china.conf", "w") as f:
        f.write(text)
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
    print(f"生成 bogus-nxdomain.china.conf（{len(lines)} 条）")


if __name__ == "__main__":
    main()
