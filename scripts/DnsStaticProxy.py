'''
Author: Jeff
Date: 2026-06-16
Description: 生成边缘 RouterOS 使用的代理域名 DNS static 脚本
Copyright © 2026 by Jeff, All Rights Reserved.
'''

from pathlib import Path

import requests

GFW_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/gfw.txt"
AI_ALLOWLIST_FILE = Path(__file__).resolve().parent / "ai_allowlist.txt"

OUTPUT_FILE = "dns_static_proxy.rsc"
FORWARD_TO = "10.100.50.222"
ADDRESS_LIST = "hk-proxy"
COMMENT = "PROXY"


def download_gfw_domains(url: str = GFW_URL) -> list[str]:
    """下载 GFW 域名列表，过滤 regexp/full 等非后缀域名规则。"""
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    domains = set()
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if ":" in line:
            continue
        domains.add(line)
    return sorted(domains)


def load_ai_domains(path: Path = AI_ALLOWLIST_FILE) -> list[str]:
    domains = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.add(line)
    return sorted(domains)


def write_rsc(domains: list[str], path: str) -> None:
    with open(path, "w") as f:
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


def main() -> None:
    print(f"下载 GFW 域名列表: {GFW_URL}")
    gfw_domains = download_gfw_domains()
    print(f"获取 GFW 域名 {len(gfw_domains)} 条")

    ai_domains = load_ai_domains()
    print(f"加载 AI allowlist {len(ai_domains)} 条")

    domains = sorted(set(gfw_domains) | set(ai_domains))
    write_rsc(domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}（{len(domains)} 条）")


if __name__ == "__main__":
    main()
