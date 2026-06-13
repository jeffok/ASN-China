"""
Generate RouterOS dns-static .rsc file for GFW domains.

Downloads geosite-gfw domain list from Loyalsoldier/v2ray-rules-dat,
generates /ip dns static entries with:
  - type=FWD
  - forward-to=8.8.8.8
  - address-list=hk-proxy
  - match-subdomain=yes

Output: dns_static_gfw.rsc
"""

import requests

GFW_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/gfw.txt"
OUTPUT_FILE = "dns_static_gfw.rsc"
FORWARD_TO = "8.8.8.8"
ADDRESS_LIST = "hk-proxy"
COMMENT = "GFW"


def download_domains(url: str) -> list[str]:
    """下载域名列表，过滤注释和空行"""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    domains = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        # v2ray-rules-dat 格式可能有前缀如 "full:" 或 "regexp:"，只保留纯域名
        if ":" in line:
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
    print(f"下载 GFW 域名列表: {GFW_URL}")
    domains = download_domains(GFW_URL)
    print(f"获取 {len(domains)} 条域名")

    write_rsc(domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
