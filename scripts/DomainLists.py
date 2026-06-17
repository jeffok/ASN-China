'''
Author: Jeff
Date: 2022-11-17
Description: 下载并合并国内域名、Apple 域名、代理域名列表，生成 SmartDNS 可直接使用的纯文本格式
Copyright © 2022 by Jeff, All Rights Reserved.
'''

from __future__ import annotations

import re
import requests


def _to_jsdelivr(url: str) -> str | None:
    m = re.match(r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)', url)
    if m:
        user, repo, branch, path = m.groups()
        return f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{path}"
    return None


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
RELEASE_RAW_BASE = "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files"


def download(url: str) -> str:
    """下载文件内容（jsDelivr 主源，github 备源）"""
    cdn = _to_jsdelivr(url)
    urls = [cdn, url] if cdn else [url]
    last_exc: Exception | None = None
    for u in urls:
        try:
            r = requests.get(u, timeout=60)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  ⚠ {u} 失败: {e}")
            last_exc = e
    raise RuntimeError(f"所有镜像均失败: {url}") from last_exc


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


def extract_domains_plain(text: str) -> list[str]:
    """提取纯域名列表（每行一个域名，忽略注释和空行）"""
    domains = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        # 忽略含特殊前缀的行（regexp: full: 等）
        if ":" in line:
            continue
        domains.append(line)
    return domains


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
    write_list(cn_sorted, "cn-domains.txt", "国内域名列表（合并去重，每日更新）")
    print(f"生成 cn-domains.txt（{len(cn_sorted)} 条）\n")

    # --- Apple 中国域名 ---
    print("下载 Apple 中国域名...")
    text = download_or_release(SOURCES["apple-cn.txt"], "apple-cn.txt")
    apple_domains = extract_domains_plain(text)
    apple_sorted = sorted(set(apple_domains))
    write_list(apple_sorted, "apple-cn.txt", "Apple 中国域名列表（每日更新）")
    print(f"生成 apple-cn.txt（{len(apple_sorted)} 条）\n")

    # --- 代理域名 ---
    print("下载代理域名列表...")
    text = download_or_release(SOURCES["proxy-list.txt"], "proxy-domains.txt")
    proxy_domains = extract_domains_plain(text)
    proxy_sorted = sorted(set(proxy_domains))
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
