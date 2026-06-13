# ASN-China

中国 ASN、IP 段、GFW 域名、AI 域名的自动化整理与分发。

每日通过 GitHub Actions 自动从上游数据源更新，生成 RouterOS 脚本及通用格式列表，发布到 [`release-files`](https://github.com/jeffok/ASN-China/tree/release-files) 分支。

## 数据源

| 数据 | 来源 |
|------|------|
| 中国 IP 段 | [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip)（聚合 APNIC、MaxMind 等） |
| 中国 ASN | [APNIC delegated](https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest) |
| GFW 域名 | [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) |
| AI 域名 | [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) + 自定义补充 |

## 生成文件

所有文件发布到 `release-files` 分支，可通过 raw URL 直接下载。

### 通用列表

| 文件 | 说明 |
|------|------|
| `IPv4.China.list` | 中国 IPv4 CIDR（纯文本，每行一条） |
| `IPv6.China.list` | 中国 IPv6 CIDR |
| `IP.China.list` | IPv4 + IPv6 合并 |
| `ASN.China.list` | 中国 ASN 列表（Surge/Quantumult X 格式） |

### 域名列表（纯文本，每行一个域名，供 SmartDNS 等消费）

| 文件 | 说明 |
|------|------|
| `cn-domains.txt` | 国内域名（Loyalsoldier + felixonmars 合并去重） |
| `apple-cn.txt` | Apple 中国域名 |
| `proxy-domains.txt` | 需代理域名 |
| `gfw-domains.txt` | GFW 域名 |
| `ai-domains.txt` | AI 域名（blackmatrix7 + 自定义补充） |
| `bogus-nxdomain.china.conf` | 虚假 NXDOMAIN IP 过滤（dnsmasq/SmartDNS 格式） |

### RouterOS 脚本 (.rsc)

| 文件 | 说明 |
|------|------|
| `cn_routes.rsc` | 中国 IP 静态路由（无网关，导入后自行设置） |
| `cn_address_list.rsc` | 防火墙地址列表（`list=CN`） |
| `China_ASN.rsc` | BGP 过滤 num-list（`list=China_ASN`） |
| `dns_static_gfw.rsc` | GFW 域名 DNS 分流（FWD 到指定 DNS） |
| `dns_static_ai.rsc` | AI 域名 DNS 分流（FWD 到指定 DNS） |

## 更新调度

GitHub Actions 每日 UTC 20:00（北京时间 04:00）自动运行，生成文件 force-push 到 `release-files` 分支。

## RouterOS 使用方法

### 下载基础 URL

```
https://raw.githubusercontent.com/jeffok/ASN-China/release-files/
```

### 中国 IP 静态路由

`cn_routes.rsc` 不包含网关，适用于所有节点。导入后为路由条目统一设置各节点自己的网关。

```routeros
/system/script/add name="Update_CN_Routes" source={
    :local filename "cn_routes.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/cn_routes.rsc"
    :local commentTag "CN"
    :local gateway "YOUR_GATEWAY"

    :if ([:len [/file/find name=$filename]] > 0) do={
        /file/remove $filename
    }

    :log info "Downloading $filename ..."
    /tool/fetch url=$url dst-path=$filename
    :delay 5s

    :log info "Removing old $commentTag routes ..."
    /ip/route/remove [/ip/route/find comment=$commentTag]

    :if ([:len [/file/find name=$filename]] > 0) do={
        :log info "Importing $filename ..."
        /import file-name=$filename
    } else={
        :log error "Download failed: $filename not found"
        :error "abort"
    }

    :log info "Setting gateway=$gateway for $commentTag routes ..."
    /ip/route/set [/ip/route/find comment=$commentTag] gateway=$gateway

    :log info "$commentTag routes updated."
}
```

将 `YOUR_GATEWAY` 替换为实际网关，例如：

| 节点 | 网关 |
|------|------|
| hkcloud | `45.250.184.1`（ext-cn 接口） |
| szhome | `pppoe-cn` |
| dxbhome | WireGuard peer 地址 |

定时任务：

```routeros
/system/scheduler/add name="daily_cn_routes" start-time=03:00:00 interval=1d on-event="Update_CN_Routes"
```

### 中国 IP 防火墙地址列表

```routeros
/system/script/add name="Update_CN_AddressList" source={
    :local filename "cn_address_list.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/cn_address_list.rsc"

    :if ([:len [/file/find name=$filename]] > 0) do={
        /file/remove $filename
    }

    /tool/fetch url=$url dst-path=$filename
    :delay 5s

    /ip/firewall/address-list/remove [/ip/firewall/address-list/find list=CN comment=CN]

    :if ([:len [/file/find name=$filename]] > 0) do={
        /import file-name=$filename
        :log info "CN address-list updated."
    }
}
```

### China ASN（BGP 过滤）

```routeros
/system/script/add name="Update_China_ASN" source={
    :local filename "China_ASN.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/China_ASN.rsc"

    :if ([:len [/file/find name=$filename]] > 0) do={
        /file/remove $filename
    }

    /tool/fetch url=$url dst-path=$filename
    :delay 10s

    /routing/filter/num-list/remove [/routing/filter/num-list/find list="China_ASN"]
    /import file-name=$filename
    :log info "China ASN list updated."
}

/system/scheduler/add name="daily_china_asn" start-time=04:00:00 interval=1d on-event="Update_China_ASN"
```

### GFW 域名 DNS 分流

```routeros
/system/script/add name="Update_DNS_GFW" source={
    :local filename "dns_static_gfw.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/dns_static_gfw.rsc"

    :if ([:len [/file/find name=$filename]] > 0) do={
        /file/remove $filename
    }

    /tool/fetch url=$url dst-path=$filename
    :delay 5s

    :if ([:len [/file/find name=$filename]] > 0) do={
        /import file-name=$filename
        /file/remove $filename
        :log info "GFW DNS rules updated."
    }
}

/system/scheduler/add name="daily_dns_gfw" start-time=04:10:00 interval=1d on-event="Update_DNS_GFW"
```

### AI 域名 DNS 分流

```routeros
/system/script/add name="Update_DNS_AI" source={
    :local filename "dns_static_ai.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/dns_static_ai.rsc"

    :if ([:len [/file/find name=$filename]] > 0) do={
        /file/remove $filename
    }

    /tool/fetch url=$url dst-path=$filename
    :delay 5s

    :if ([:len [/file/find name=$filename]] > 0) do={
        /import file-name=$filename
        /file/remove $filename
        :log info "AI DNS rules updated."
    }
}

/system/scheduler/add name="daily_dns_ai" start-time=04:20:00 interval=1d on-event="Update_DNS_AI"
```

> **注意：** DNS 静态规则较多时，需增大 DNS 缓存：
>
> ```routeros
> /ip/dns/set cache-size=20480KiB
> ```

## 本地构建

```bash
pip install requests
python scripts/ChinaIP.py
python scripts/ChinaASN.py
python scripts/ChinaROS.py
python scripts/DnsStaticGFW.py
python scripts/DnsStaticAI.py
```

## 项目结构

```
ASN-China/
├── scripts/
│   ├── ChinaASN.py          # 中国 ASN 列表生成
│   ├── ChinaIP.py           # 中国 IP 段列表生成
│   ├── ChinaROS.py          # RouterOS 路由/地址列表脚本生成
│   ├── DnsStaticGFW.py      # GFW 域名 DNS 分流脚本生成
│   └── DnsStaticAI.py       # AI 域名 DNS 分流脚本生成
├── .github/workflows/
│   └── ci.yml               # 每日自动构建
├── .gitignore
├── LICENSE
└── README.md
```

## License

[MIT](./LICENSE)
