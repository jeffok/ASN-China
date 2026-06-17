'''
Author: Jeff
Date: 2022-11-17 (rebuilt 2026-06-17)
Description: 生成 AI 域名的 RouterOS DNS 分流脚本（边缘 + hkros 两端）和纯文本列表。
             AI 域名保持「主机精确」，不做 eTLD+1 塌缩，避免把整个 google.com 拐去 SGP。

  - dns_static_ai_edge.rsc   边缘用：FWD → hkros DNS(10.100.50.254)，写 hk-proxy
                             （让 AI 流量先进 hk-proxy → rt-hk → 送到 hkros）
  - dns_static_ai_hkros.rsc  hkros 用：FWD → sgpros DNS(10.100.89.3)，写 ai-sgp
                             （hkros 原子写表 → rt-sgp → 经 WG 到 sgpros 出网）
  - dns_static_ai.rsc        向后兼容别名 = hkros 版
  - ai-domains.txt           纯文本（含 SmartDNS 后缀条目），供其它消费

Copyright © 2022 by Jeff, All Rights Reserved.
'''

from __future__ import annotations  # 兼容 Python 3.9 runner

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWLIST_FILE = SCRIPT_DIR / "ai_allowlist.txt"

COMMENT = "AI"

# 边缘端：把 AI 域名送到 hkros
EDGE_FORWARD_TO = "10.100.50.254"
EDGE_ADDRESS_LIST = "hk-proxy"
EDGE_OUTPUT = "dns_static_ai_edge.rsc"

# hkros 端：把 AI 域名解析交给 sgpros、命中写 ai-sgp
HKROS_FORWARD_TO = "10.100.89.3"
HKROS_ADDRESS_LIST = "ai-sgp"
HKROS_OUTPUT = "dns_static_ai_hkros.rsc"
COMPAT_OUTPUT = "dns_static_ai.rsc"   # 向后兼容别名

# SmartDNS domain-set 后缀条目（仅写入 ai-domains.txt，不进 RouterOS static）
SMARTDNS_SUFFIX_ENTRIES = (
    ".cursor.sh",
    ".cursor-cdn.com",
    ".cursorapi.com",
)


def load_domains(path: Path = ALLOWLIST_FILE) -> list[str]:
    domains = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.add(line)
    return sorted(domains)


def write_rsc(domains: list[str], path: str, forward_to: str, address_list: str) -> None:
    with open(path, "w") as f:
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            if domain.startswith("."):
                continue
            f.write(
                f"add name={domain} type=FWD forward-to={forward_to} "
                f"address-list={address_list} match-subdomain=yes comment={COMMENT}\n"
            )


def write_txt(domains: list[str], path: str) -> None:
    smartdns_domains = sorted(set(domains) | set(SMARTDNS_SUFFIX_ENTRIES))
    with open(path, "w") as f:
        f.write("# AI 域名列表（自动生成，每日更新）\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("# Lines starting with '.' are SmartDNS suffix matches.\n")
        f.write("\n".join(smartdns_domains) + "\n")


def main() -> None:
    domains = load_domains()
    print(f"加载 AI allowlist: {ALLOWLIST_FILE}，共 {len(domains)} 条")

    write_rsc(domains, EDGE_OUTPUT, EDGE_FORWARD_TO, EDGE_ADDRESS_LIST)
    print(f"生成 {EDGE_OUTPUT}（边缘 → hkros，写 {EDGE_ADDRESS_LIST}）")

    write_rsc(domains, HKROS_OUTPUT, HKROS_FORWARD_TO, HKROS_ADDRESS_LIST)
    print(f"生成 {HKROS_OUTPUT}（hkros → sgpros，写 {HKROS_ADDRESS_LIST}）")

    write_rsc(domains, COMPAT_OUTPUT, HKROS_FORWARD_TO, HKROS_ADDRESS_LIST)
    print(f"生成 {COMPAT_OUTPUT}（向后兼容别名 = hkros 版）")

    write_txt(domains, "ai-domains.txt")
    print(f"生成 ai-domains.txt（{len(domains)} 条）")


if __name__ == "__main__":
    main()
