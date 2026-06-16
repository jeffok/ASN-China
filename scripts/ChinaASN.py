'''
Author: Jeff
Date: 2022-11-17
Description: 从 APNIC 委托文件提取中国 ASN 列表，生成 Surge 和 RouterOS 格式
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import re
import signal
import time
from contextlib import contextmanager

import requests

# APNIC 委托分配数据源
APNIC_URL = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
FALLBACK_ASN_LIST_URL = (
    "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/"
    "release-files/ASN.China.list"
)
# 匹配中国 ASN 条目的正则
PATTERN = re.compile(r"^apnic\|CN\|asn\|(\d+)\|")
FALLBACK_PATTERN = re.compile(r"^IP-ASN,(\d+)$")


@contextmanager
def time_limit(seconds: int):
    def handle_timeout(signum, frame):
        raise TimeoutError(f"operation timed out after {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def fetch_cn_asns() -> list[int]:
    """从 APNIC 委托文件中提取所有中国 ASN 编号"""
    print(f"下载 APNIC delegated: {APNIC_URL}", flush=True)
    with time_limit(60):
        r = requests.get(APNIC_URL, timeout=(10, 20))
        r.raise_for_status()
        lines = r.text.splitlines()

    asns = []
    for line in lines:
        m = PATTERN.match(line)
        if m:
            asns.append(int(m.group(1)))

    asns.sort()
    return asns


def fetch_fallback_asns() -> list[int]:
    """APNIC 下载异常时，从当前 release-files 读取上一版 ASN 列表。"""
    print(f"回退到 Gitea release-files: {FALLBACK_ASN_LIST_URL}", flush=True)
    r = requests.get(FALLBACK_ASN_LIST_URL, timeout=(10, 20))
    r.raise_for_status()

    asns = []
    for line in r.text.splitlines():
        m = FALLBACK_PATTERN.match(line.strip())
        if m:
            asns.append(int(m.group(1)))

    asns.sort()
    if not asns:
        raise RuntimeError("fallback ASN list is empty")
    return asns


def write_surge_list(asns: list[int], path: str) -> None:
    """生成 Surge/Quantumult X 格式的 ASN 列表"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    with open(path, "w") as f:
        f.write(f"// 中国 ASN 列表（数据源：APNIC delegated）\n")
        f.write(f"// 更新时间: UTC {ts}\n")
        f.write(f"// https://gitea.jeffok.com:4443/jeff/asn-china\n\n")
        for asn in asns:
            f.write(f"IP-ASN,{asn}\n")


def write_ros_numlist(asns: list[int], path: str) -> None:
    """生成 RouterOS BGP 过滤 num-list 脚本"""
    with open(path, "w") as f:
        f.write("/routing/filter/num-list\n")
        for asn in asns:
            f.write(f"add list=China_ASN range={asn}\n")


def main() -> None:
    try:
        asns = fetch_cn_asns()
    except Exception as exc:
        print(f"APNIC ASN 下载失败: {exc}", flush=True)
        asns = fetch_fallback_asns()

    print(f"从 APNIC 获取 {len(asns)} 个中国 ASN")

    write_surge_list(asns, "ASN.China.list")
    print(f"生成 ASN.China.list（{len(asns)} 条）")

    write_ros_numlist(asns, "China_ASN.rsc")
    print(f"生成 China_ASN.rsc（{len(asns)} 条）")


if __name__ == "__main__":
    main()
