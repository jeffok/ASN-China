'''
Author: Jeff
Date: 2022-11-17
Description: 从 Loyalsoldier/geoip 下载中国 IP 段，分离 IPv4/IPv6 并保存为列表文件
Copyright © 2022 by Jeff, All Rights Reserved.
'''

from __future__ import annotations

import ipaddress

from download_utils import download_text


def download(url: str, timeout: int = 10) -> str:
    return download_text(url, timeout=timeout)


# 中国 IP 段数据源（包含 IPv4 + IPv6）
cn_url = "https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/cn.txt"
fallback_ip_url = (
    "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/"
    "release-files/IP.China.list"
)

# 下载数据
try:
    text = download(cn_url)
except Exception as exc:
    print(f"外部中国 IP 源不可达，回退到 release-files: {exc}", flush=True)
    text = download(fallback_ip_url)
lines = text.splitlines()

# 分开存放 IPv4 和 IPv6
ipv4_list = []
ipv6_list = []

for line in lines:
    try:
        net = ipaddress.ip_network(line.strip())
        if isinstance(net, ipaddress.IPv4Network):
            ipv4_list.append(line.strip())
        elif isinstance(net, ipaddress.IPv6Network):
            ipv6_list.append(line.strip())
    except ValueError:
        # 忽略非 IP 段的行
        continue

# 保存 IPv4 列表
with open("IPv4.China.list", "w") as f:
    f.write("\n".join(ipv4_list))

# 保存 IPv6 列表
with open("IPv6.China.list", "w") as f:
    f.write("\n".join(ipv6_list))

# 保存合并列表
with open("IP.China.list", "w") as f:
    f.write("\n".join(ipv4_list + ipv6_list))

print(f"共获取 IPv4 段 {len(ipv4_list)} 条，IPv6 段 {len(ipv6_list)} 条。")
