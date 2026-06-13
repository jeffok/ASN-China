'''
Author: Jeff
Date: 2022-11-17 02:14:24
LastEditors: Jeff
LastEditTime: 2025-08-25 12:19:20
FilePath: /ASN-China/scripts/ChinaIP.py

功能: 从 Loyalsoldier/geoip 下载中国 IP 段，分离 IPv4/IPv6 并保存
数据源: https://github.com/Loyalsoldier/geoip (聚合 APNIC、MaxMind 等)
输出文件:
  - IPv4.China.list  : 中国 IPv4 CIDR（每行一条）
  - IPv6.China.list  : 中国 IPv6 CIDR
  - IP.China.list    : IPv4 + IPv6 合并

Copyright © 2022 by Jeff, All Rights Reserved.
'''

import requests
import ipaddress

# 中国 IP 段数据源（包含 IPv4 + IPv6）
cn_url = "https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/cn.txt"

# 下载数据
r = requests.get(cn_url, timeout=30)
r.raise_for_status()
lines = r.text.splitlines()

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
