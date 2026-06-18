'''
Author: Jeff
Date: 2022-11-17 (rebuilt 2026-06-17)
Description: 生成 AI 域名的通用 RouterOS DNS 分流脚本和纯文本列表。
             AI 域名保持「主机精确」，不做 eTLD+1 塌缩，避免把整个 google.com 拐去 SGP。

  - dns_static_ai.rsc        通用模板：导入前由 RouterOS 设置 aiForwardTo / aiAddressList
  - ai-domains.txt           纯文本（含 SmartDNS 后缀条目），供其它消费

Copyright © 2022 by Jeff, All Rights Reserved.
'''

from __future__ import annotations  # 兼容 Python 3.9 runner

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWLIST_FILE = SCRIPT_DIR / "ai_allowlist.txt"

COMMENT = "AI"
RSC_OUTPUT = "dns_static_ai.rsc"

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


def write_rsc(domains: list[str], path: str) -> None:
    with open(path, "w") as f:
        f.write(":global aiForwardTo\n")
        f.write(":global aiAddressList\n")
        f.write(":global aiComment\n")
        f.write(':if ([:typeof $aiForwardTo] = "nothing") do={ :error "aiForwardTo is required" }\n')
        f.write(':if ([:typeof $aiAddressList] = "nothing") do={ :error "aiAddressList is required" }\n')
        f.write(f':if ([:typeof $aiComment] = "nothing") do={{ :global aiComment "{COMMENT}" }}\n')
        f.write("/ip/dns/static/remove [find where comment=$aiComment]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            if domain.startswith("."):
                continue
            f.write(
                f"add name={domain} type=FWD forward-to=$aiForwardTo "
                f"address-list=$aiAddressList match-subdomain=yes comment=$aiComment\n"
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

    write_rsc(domains, RSC_OUTPUT)
    print(f"生成 {RSC_OUTPUT}（通用模板，导入前设置 aiForwardTo/aiAddressList）")

    write_txt(domains, "ai-domains.txt")
    print(f"生成 ai-domains.txt（{len(domains)} 条）")


if __name__ == "__main__":
    main()
