'''
Author: Jeff
Date: 2022-11-17
Description: 生成 GFW 域名的 RouterOS DNS 分流脚本，将匹配域名 FWD 到指定 DNS
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import requests

# GFW 域名列表数据源
GFW_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/gfw.txt"
# 输出文件
OUTPUT_FILE = "dns_static_gfw.rsc"
# DNS 转发目标
FORWARD_TO = "8.8.8.8"
# 匹配域名加入的地址列表名称
ADDRESS_LIST = "hk-proxy"
# 规则标签（用于批量删除旧规则）
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
        # v2ray-rules-dat 格式可能有 "full:" 或 "regexp:" 前缀，只保留纯域名
        if ":" in line:
            continue
        domains.append(line)
    return sorted(set(domains))


def write_rsc(domains: list[str], path: str) -> None:
    """生成 RouterOS DNS 静态分流脚本"""
    with open(path, "w") as f:
        # 先删除旧规则
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


def write_txt(domains: list[str], path: str) -> None:
    """生成纯域名文本列表（每行一个域名，供 SmartDNS 等消费）"""
    with open(path, "w") as f:
        f.write("# GFW 域名列表（自动生成，每日更新）\n")
        f.write("# https://github.com/jeffok/ASN-China\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    print(f"下载 GFW 域名列表: {GFW_URL}")
    domains = download_domains(GFW_URL)
    print(f"获取 {len(domains)} 条域名")

    write_rsc(domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")

    write_txt(domains, "gfw-domains.txt")
    print(f"生成 gfw-domains.txt（{len(domains)} 条）")


if __name__ == "__main__":
    main()
