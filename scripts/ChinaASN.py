'''
Author: Jeff
Date: 2022-11-17
Description: 从 APNIC 委托文件提取中国 ASN 列表，生成 Surge 和 RouterOS 格式
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import re
import time
from urllib.request import urlopen, Request

# APNIC 委托分配数据源
APNIC_URL = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
# 匹配中国 ASN 条目的正则
PATTERN = re.compile(r"^apnic\|CN\|asn\|(\d+)\|")


def fetch_cn_asns() -> list[int]:
    """从 APNIC 委托文件中提取所有中国 ASN 编号"""
    req = Request(APNIC_URL, headers={"User-Agent": "ASN-China-CI/1.0"})
    with urlopen(req, timeout=30) as resp:
        lines = resp.read().decode("utf-8").splitlines()

    asns = []
    for line in lines:
        m = PATTERN.match(line)
        if m:
            asns.append(int(m.group(1)))

    asns.sort()
    return asns


def write_surge_list(asns: list[int], path: str) -> None:
    """生成 Surge/Quantumult X 格式的 ASN 列表"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    with open(path, "w") as f:
        f.write(f"// 中国 ASN 列表（数据源：APNIC delegated）\n")
        f.write(f"// 更新时间: UTC {ts}\n")
        f.write(f"// https://github.com/jeffok/ASN-China\n\n")
        for asn in asns:
            f.write(f"IP-ASN,{asn}\n")


def write_ros_numlist(asns: list[int], path: str) -> None:
    """生成 RouterOS BGP 过滤 num-list 脚本"""
    with open(path, "w") as f:
        f.write("/routing/filter/num-list\n")
        for asn in asns:
            f.write(f"add list=China_ASN range={asn}\n")


def main() -> None:
    asns = fetch_cn_asns()
    print(f"从 APNIC 获取 {len(asns)} 个中国 ASN")

    write_surge_list(asns, "ASN.China.list")
    print(f"生成 ASN.China.list（{len(asns)} 条）")

    write_ros_numlist(asns, "China_ASN.rsc")
    print(f"生成 China_ASN.rsc（{len(asns)} 条）")


if __name__ == "__main__":
    main()
