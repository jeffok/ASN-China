'''
Author: Jeff
'''


# 读取 IP 列表
with open("IPv4.China.list", "r") as f:
    cidrs = [line.strip() for line in f if line.strip()]

# 网关或接口名称
local_gateway="pppoe-out1"
net_name = "l2tp-cn"
wg_name = "wg-home"

# 写 static_router.rsc
with open("static_router.rsc", "w") as f:
    f.write("/ip route\n")
    for cidr in cidrs:
        f.write(f"add dst-address={cidr} gateway={local_gateway} comment=CN\n")

# 写 wg_static_router.rsc
with open("wg_static_router.rsc", "w") as f:
    f.write("/ip route\n")
    for cidr in cidrs:
        f.write(f"add dst-address={cidr} gateway={wg_name} comment=CN\n")


# 写 static_address_list.rsc
with open("static_address_list.rsc", "w") as f:
    f.write("/ip firewall address-list\n")
    for cidr in cidrs:
        f.write(f"add list=CN address={cidr} comment=CN\n")

# 写 dbx_static_router.rsc
with open("dbx_static_router.rsc", "w") as f:
    f.write("/ip route\n")
    # DC addresses
    dc_routes = [
        "66.22.212.0/22",
        "66.22.218.0/23",
        "185.151.204.0/24",
        "162.159.128.232/29",
        "162.159.129.232/29",
        "162.159.130.232/29",
        "162.159.133.232/29",
        "162.159.134.232/29",
        "162.159.135.232/29",
        "162.159.136.232/29",
        "162.159.137.232/29",
        "162.159.138.232/29",
    ]
    for route in dc_routes:
        f.write(f"add dst-address={route} gateway={net_name} comment=DC\n")

    # Whatsapp
    whatsapp_routes = [
        "31.13.0.0/16",
        "157.240.0.0/16"
    ]
    for route in whatsapp_routes:
        f.write(f"add dst-address={route} gateway={net_name} comment=Whatsapp\n")

    # Wechat
    wechat_routes = [
        "14.22.9.0/24",
        "119.147.4.0/24",
        "129.226.0.0/16",
        "163.60.15.0/24",
        "183.3.224.0/20",
        "203.105.235.0/24"
    ]
    for route in wechat_routes:
        f.write(f"add dst-address={route} gateway={net_name} comment=Wechat\n")

    # China CIDRs
    for cidr in cidrs:
        f.write(f"add dst-address={cidr} gateway={net_name} comment=CN\n")
