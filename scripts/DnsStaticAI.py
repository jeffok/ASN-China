"""
Generate RouterOS dns-static .rsc file for AI domains.

Downloads ai-list.txt from smartdns project,
generates /ip dns static entries with:
  - type=FWD
  - forward-to=10.100.89.3 (SGP internal DNS)
  - address-list=ai-sgp
  - match-subdomain=yes

Output: dns_static_ai.rsc
"""

import requests

AI_URL = "https://raw.githubusercontent.com/jeffok/smartdns/master/data/rules/ai-list.txt"
OUTPUT_FILE = "dns_static_ai.rsc"
FORWARD_TO = "10.100.89.3"
ADDRESS_LIST = "ai-sgp"
COMMENT = "AI"


def download_domains(url: str) -> list[str]:
    """下载域名列表，过滤注释和空行"""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    domains = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.append(line)
    return sorted(set(domains))


def write_rsc(domains: list[str], path: str) -> None:
    """生成 ROS .rsc 导入脚本"""
    with open(path, "w") as f:
        # 先删除旧规则
        f.write(f"/ip dns static remove [find where comment={COMMENT}]\n")
        f.write("/ip dns static\n")
        for domain in domains:
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


def main() -> None:
    print(f"下载 AI 域名列表: {AI_URL}")
    domains = download_domains(AI_URL)
    print(f"获取 {len(domains)} 条域名")

    write_rsc(domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
