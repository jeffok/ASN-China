'''
Author: Jeff
Date: 2022-11-17
Description: 生成 AI 域名的 RouterOS DNS 分流脚本和 SmartDNS 域名列表
Copyright © 2022 by Jeff, All Rights Reserved.
'''

from pathlib import Path

# DNS 转发目标
FORWARD_TO = "10.100.89.3"
# 匹配域名加入的地址列表名称
ADDRESS_LIST = "ai-sgp"
# 规则标签（用于批量删除旧规则）
COMMENT = "AI"
# 输出文件
OUTPUT_FILE = "dns_static_ai.rsc"

SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWLIST_FILE = SCRIPT_DIR / "ai_allowlist.txt"

# SmartDNS domain-set suffix entries (leading dot = domain + all subdomains).
# These are written to ai-domains.txt only, not RouterOS static rules.
SMARTDNS_SUFFIX_ENTRIES = (
    ".cursor.sh",
    ".cursor-cdn.com",
    ".cursorapi.com",
)


def load_domains(path: Path = ALLOWLIST_FILE) -> list[str]:
    """加载人工审核后的 AI 域名 allowlist。"""
    domains = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.add(line)
    return sorted(domains)


def write_rsc(domains: list[str], path: str) -> None:
    """生成 RouterOS DNS 静态分流脚本"""
    with open(path, "w") as f:
        # 先删除旧规则
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            if domain.startswith("."):
                continue
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


def write_txt(domains: list[str], path: str) -> None:
    """生成纯域名文本列表（每行一个域名，供 SmartDNS 等消费）"""
    smartdns_domains = sorted(set(domains) | set(SMARTDNS_SUFFIX_ENTRIES))
    with open(path, "w") as f:
        f.write("# AI 域名列表（自动生成，每日更新）\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("# Lines starting with '.' are SmartDNS suffix matches.\n")
        f.write("\n".join(smartdns_domains) + "\n")


def main() -> None:
    sorted_domains = load_domains()
    print(f"加载 AI allowlist: {ALLOWLIST_FILE}，共 {len(sorted_domains)} 条")

    write_rsc(sorted_domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")

    write_txt(sorted_domains, "ai-domains.txt")
    print(f"生成 ai-domains.txt（{len(sorted_domains)} 条）")


if __name__ == "__main__":
    main()
