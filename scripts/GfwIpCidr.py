'''
Author: Jeff
Date: 2025-06-13
Description: 生成 GFW 相关应用的 IP-CIDR 地址列表 RouterOS 脚本
             解决 Telegram 等应用使用硬编码 IP 直连、不经过 DNS 解析的问题
Copyright © 2025 by Jeff, All Rights Reserved.
'''

import ipaddress
import requests

# 输出文件
OUTPUT_FILE = "gfw_ip_list.rsc"
# 匹配地址加入的地址列表名称
ADDRESS_LIST = "hk-proxy"
# 规则标签（用于批量删除旧规则）
COMMENT = "GFW-IP"
# 最大允许的 IPv4 前缀长度（/xx 中 xx 的最小值），太大的段会误匹配
# /16 = 65536 IP，再大就有误伤风险
MAX_PREFIX_SIZE = 16

# 数据源：blackmatrix7 维护的规则（Surge 格式）
# 只提取 IP-CIDR 条目，域名由 dns_static_gfw.rsc 覆盖
SOURCES = {
    "Telegram": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Telegram/Telegram.list",
}

# 自定义补充 IP-CIDR（上游未收录或需要手动维护的）
CUSTOM_CIDRS = [
    # 可在此添加其他硬编码 IP 段
]


def fetch_ip_cidrs(url: str) -> list[str]:
    """从 Surge 格式的规则文件提取 IPv4 IP-CIDR 条目"""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  警告: 下载失败 {url}: {e}")
        return []

    cidrs = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("IP-CIDR,"):
            parts = line.split(",")
            if len(parts) >= 2:
                cidr = parts[1].strip()
                cidrs.append(cidr)
        # 忽略 IP-CIDR6、DOMAIN、IP-ASN 等
    return cidrs


def validate_cidrs(cidrs: list[str], source_name: str) -> list[str]:
    """验证并过滤 CIDR，排除过大的网段"""
    valid = []
    for cidr in cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            print(f"  跳过无效 CIDR: {cidr} ({e})")
            continue

        # 只处理 IPv4
        if net.version != 4:
            continue

        # 过滤过大的网段
        if net.prefixlen < MAX_PREFIX_SIZE:
            print(f"  跳过过大网段: {cidr}（/{net.prefixlen} < /{MAX_PREFIX_SIZE}）[{source_name}]")
            continue

        valid.append(str(net))
    return valid


def write_rsc(cidrs: list[str], path: str) -> None:
    """生成 RouterOS 防火墙地址列表导入脚本"""
    with open(path, "w") as f:
        # 先删除旧规则
        f.write(f"/ip/firewall/address-list/remove [find where comment={COMMENT}]\n")
        f.write("/ip/firewall/address-list\n")
        for cidr in cidrs:
            f.write(
                f"add list={ADDRESS_LIST} address={cidr} "
                f"comment={COMMENT}\n"
            )


def write_txt(cidrs: list[str], path: str) -> None:
    """生成纯 CIDR 文本列表"""
    with open(path, "w") as f:
        f.write("# GFW 应用 IP-CIDR 列表（自动生成，每日更新）\n")
        f.write("# 用于硬编码 IP 直连的应用（如 Telegram）\n")
        f.write("# https://github.com/jeffok/ASN-China\n")
        f.write("\n".join(cidrs) + "\n")


def main() -> None:
    all_cidrs: set[str] = set()

    # 拉取各数据源
    for name, url in SOURCES.items():
        print(f"下载 {name}: {url}")
        raw_cidrs = fetch_ip_cidrs(url)
        print(f"  原始 IP-CIDR: {len(raw_cidrs)} 条")
        valid = validate_cidrs(raw_cidrs, name)
        print(f"  有效 IP-CIDR: {len(valid)} 条")
        all_cidrs.update(valid)

    # 加入自定义补充
    if CUSTOM_CIDRS:
        valid = validate_cidrs(CUSTOM_CIDRS, "Custom")
        all_cidrs.update(valid)

    # 排序（按 IP 地址排序）
    sorted_cidrs = sorted(all_cidrs, key=lambda x: ipaddress.ip_network(x, strict=False))
    print(f"\n合并后共 {len(sorted_cidrs)} 条 IP-CIDR")

    write_rsc(sorted_cidrs, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")

    write_txt(sorted_cidrs, "gfw-ip-cidrs.txt")
    print(f"生成 gfw-ip-cidrs.txt（{len(sorted_cidrs)} 条）")


if __name__ == "__main__":
    main()
