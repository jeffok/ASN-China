'''
Author: Jeff
Date: 2022-11-17
Description: 从 Loyalsoldier/geoip 下载中国 IP 段，分离 IPv4/IPv6 并保存为列表文件
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import re
import requests
import ipaddress


def _to_jsdelivr(url: str) -> str | None:
    m = re.match(r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)', url)
    if m:
        user, repo, branch, path = m.groups()
        return f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{path}"
    return None


def download(url: str, timeout: int = 60) -> str:
    cdn = _to_jsdelivr(url)
    urls = [cdn, url] if cdn else [url]
    last_exc: Exception | None = None
    for u in urls:
        try:
            r = requests.get(u, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  ⚠ {u} 失败: {e}")
            last_exc = e
    raise RuntimeError(f"所有镜像均失败: {url}") from last_exc


# 中国 IP 段数据源（包含 IPv4 + IPv6）
cn_url = "https://raw.githubusercontent.com/Loyalsoldier/geoip/release/text/cn.txt"

# 下载数据
text = download(cn_url)
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
