'''
Author: Jeff
Date: 2022-11-17
Description: 基于中国 IPv4 段生成 RouterOS 静态路由和防火墙地址列表脚本
Copyright © 2022 by Jeff, All Rights Reserved.
'''

# 输入文件路径
INPUT_FILE = "IPv4.China.list"
# 路由和地址列表的 comment 标签
COMMENT = "CN"
# 静态路由 distance 值
DISTANCE = 50


def read_cidrs(path: str) -> list[str]:
    """读取 CIDR 列表文件"""
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def write_routes(cidrs: list[str], path: str) -> None:
    """生成 RouterOS 静态路由脚本（不含网关）"""
    with open(path, "w") as f:
        f.write("/ip/route\n")
        for cidr in cidrs:
            f.write(f"add dst-address={cidr} distance={DISTANCE} comment={COMMENT}\n")


def write_address_list(cidrs: list[str], path: str) -> None:
    """生成 RouterOS 防火墙地址列表脚本"""
    with open(path, "w") as f:
        f.write("/ip/firewall/address-list\n")
        for cidr in cidrs:
            f.write(f"add list={COMMENT} address={cidr} comment={COMMENT}\n")


def main() -> None:
    cidrs = read_cidrs(INPUT_FILE)
    print(f"读取 {len(cidrs)} 条 IPv4 CIDR（来源：{INPUT_FILE}）")

    write_routes(cidrs, "cn_routes.rsc")
    print(f"生成 cn_routes.rsc（{len(cidrs)} 条）")

    write_address_list(cidrs, "cn_address_list.rsc")
    print(f"生成 cn_address_list.rsc（{len(cidrs)} 条）")


if __name__ == "__main__":
    main()
