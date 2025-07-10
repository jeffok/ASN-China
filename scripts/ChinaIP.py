'''
Author: Vincent Young
Date: 2022-11-17 02:14:24
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:19:20
FilePath: /ASN-China/syncIP.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved. 
'''

import requests

v4China = "https://ispip.clang.cn/all_cn_geolite2.txt"

v6China = "https://ispip.clang.cn/all_cn_ipv6.txt"

r = requests.get(v4China) 
with open("IPv4.China.list", "wb") as v4ChinaIP:
         v4ChinaIP.write(r.content)

r = requests.get(v6China) 
with open("IPv6.China.list", "wb") as v6ChinaIP:
         v6ChinaIP.write(r.content)

with open("IP.China.list", "wb") as allIP:
    with open("IPv4.China.list", "rb") as v4:
        allIP.write(v4.read())
    with open("IPv6.China.list", "rb") as v6:
        allIP.write(v6.read())