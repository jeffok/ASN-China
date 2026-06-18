# ASN-China

中国 ASN、IP 段、GFW 域名、AI 域名的自动化整理与分发。

每日通过自建 Gitea Actions 自动从上游数据源更新，生成 RouterOS 脚本及通用格式列表，发布到 [`release-files`](https://gitea.jeffok.com:4443/jeff/asn-china/src/branch/release-files) 分支。

## 数据源

| 数据 | 来源 |
|------|------|
| 中国 IP 段 | [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip)（聚合 APNIC、MaxMind 等） |
| 中国 ASN | [APNIC delegated](https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest) |
| 代理域名（海外） | [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) `proxy-list.txt`（= v2fly geosite `geolocation-!cn` + gfw + greatfire 合并）∪ `gfw.txt`（向后兼容） |
| 热门排名（山石精简） | [Cisco Umbrella top-1m](https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip)，备源 [Tranco](https://tranco-list.eu/) |
| 必保留域名 | `scripts/pin.txt` 人工维护（核心海外域名钉死，不受热门裁剪影响） |
| GFW IP-CIDR | [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)（Telegram 等） |
| AI 域名 | `scripts/ai_allowlist.txt` 人工审核维护（主机精确、保守 allowlist，避免共享 IP 误伤） |

### 域名分流设计（核心）

代理域名分两端、两份产物，遵循「做路由决策的设备自己解析、原子写 address-list」原则：

- **边缘（szhome/devros 或山石）** 判断「要不要出国」：命中代理清单 → FWD 到 **hkros DNS `10.100.50.254`**、写 `hk-proxy` → 经 WG 送到 hkros。
- **hkros** 判断「是不是 AI」：AI 域名 → FWD 到 **sgpros DNS `10.100.89.3`**、写 `ai-sgp` → 经 WG 到 sgpros 出网；其余默认走香港出口。
- **sgpros** 对 AI 域名显式 FWD 到公网 DNS，避免 DHCP 上游或 RouterOS 默认递归对 Cursor 多级 CNAME 返回空答案。

> AI 域名是代理域名的子集；AI 保持「主机精确」（如 `gemini.google.com`），代理大表做 eTLD+1 塌缩。不再依赖 SmartDNS / sync-ai 二次解析。

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
| `proxy-domains.txt` | 需代理域名中等常用表（GFW 全收 + pin + AI + 热门补充，≈6–8k） |
| `common-domains-hillstone.txt` | **山石防火墙常用代理域名**（热门交集 + pin + AI，≤3000，通配 `*.domain` 用） |
| `gfw-domains.txt` | GFW 域名（原始 gfw.txt 纯文本，向后兼容） |
| `ai-domains.txt` | AI 域名（人工审核 allowlist，主机精确） |
| `gfw-ip-cidrs.txt` | GFW 应用 IP-CIDR（Telegram 等硬编码 IP 直连的应用） |
| `bogus-nxdomain.china.conf` | 虚假 NXDOMAIN IP 过滤（dnsmasq/SmartDNS 格式） |

### RouterOS 脚本 (.rsc)

| 文件 | 说明 |
|------|------|
| `cn_routes.rsc` | 中国 IP 静态路由（无网关，导入后自行设置） |
| `cn_address_list.rsc` | 防火墙地址列表（`list=CN`） |
| `China_ASN.rsc` | BGP 过滤 num-list（`list=China_ASN`） |
| `dns_static_gfw.rsc` | GFW 域名 DNS 分流（原始 gfw.txt，向后兼容） |
| `dns_static_proxy.rsc` | **边缘**代理域名 DNS 分流全量表（首次导入/灾难恢复用，中等常用表 ≈6–8k，FWD→hkros `10.100.50.254`，写 `hk-proxy`） |
| `dns_static_proxy_delta.rsc` | **边缘**代理域名 DNS 分流增量表（日常更新用，对比上一版 `dns_static_proxy.rsc`，只删除过期项并新增变化项，避免同名 static 导入失败） |
| `dns_static_proxy_manifest.rsc` | **边缘**代理域名状态清单（发布 current/previous hash 与增量统计，RouterOS 用本地 `asn-proxy-state` 判断跳过/增量/全量） |
| `dns_static_ai_edge.rsc` | **边缘** AI 分流（FWD→hkros `10.100.50.254`，写 `hk-proxy`） |
| `dns_static_ai_hkros.rsc` | **hkros** AI 分流（FWD→sgpros `10.100.89.3`，写 `ai-sgp`） |
| `dns_static_ai_sgpros.rsc` | **sgpros** AI 递归兜底（FWD→公网 DNS，修复 Cursor 多级 CNAME 空答案） |
| `dns_static_ai.rsc` | 向后兼容别名（= hkros 版） |
| `gfw_ip_list.rsc` | GFW 应用 IP-CIDR 地址列表（Telegram 等硬编码 IP 的应用） |

## 更新调度

Gitea Actions 每日 UTC 20:00（北京时间 04:00）自动运行，生成文件 force-push 到 `release-files` 分支。

## RouterOS 使用方法

### 下载基础 URL

```
https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/
```

### 中国 IP 静态路由

`cn_routes.rsc` 不包含网关，适用于所有节点。导入后为路由条目统一设置各节点自己的网关。

```routeros
/system/script/add name="Update_CN_Routes" source={
    :local filename "cn_routes.rsc"
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/cn_routes.rsc"
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
| hkros | `45.250.184.1`（ext-cn 回国出口） |
| szhome | `pppoe-cn` |
| bzhome | `pppoe-cn` |
| sgpros | 走 hkros 转发（无需本地 CN 路由） |

定时任务：

```routeros
/system/scheduler/add name="daily_cn_routes" start-time=03:00:00 interval=1d on-event="Update_CN_Routes"
```

### 中国 IP 防火墙地址列表

```routeros
/system/script/add name="Update_CN_AddressList" source={
    :local filename "cn_address_list.rsc"
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/cn_address_list.rsc"

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
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/China_ASN.rsc"

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
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_gfw.rsc"

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

### 边缘 RouterOS 代理 + AI 域名 DNS 分流

`szhome`、`devros` 边缘路由器导入两份：`dns_static_proxy.rsc`（代理大表）+ `dns_static_ai_edge.rsc`（AI）。两者都 FWD 到 **hkros DNS `10.100.50.254`**、写 `hk-proxy`；AI 的二次分流（→ SGP）由 hkros 完成。

```routeros
/system/script/add name="Update_DNS_Edge" source={
    :local base "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/"
    :foreach fn in={"dns_static_proxy.rsc";"dns_static_ai_edge.rsc"} do={
        :if ([:len [/file/find name=$fn]] > 0) do={ /file/remove $fn }
        /tool/fetch url=($base . $fn) dst-path=$fn
        :delay 5s
        :if ([:len [/file/find name=$fn]] > 0) do={
            /import file-name=$fn
            /file/remove $fn
            :log info ("imported " . $fn)
        } else={ :log error ("download failed: " . $fn) }
    }
    /ip/dns/cache/flush
}

/system/scheduler/add name="daily_dns_edge" start-time=04:30:00 interval=1d on-event="Update_DNS_Edge"
```

### hkros AI 域名 DNS 分流

hkros 导入 `dns_static_ai_hkros.rsc`：AI 域名 FWD 到 **sgpros DNS `10.100.89.3`**、命中写 `ai-sgp`（mangle 再把 `ai-sgp` 标记到 `rt-sgp` 经 WG 到 sgpros 出网）。

```routeros
/system/script/add name="Update_DNS_AI_hkros" source={
    :local fn "dns_static_ai_hkros.rsc"
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_ai_hkros.rsc"
    :if ([:len [/file/find name=$fn]] > 0) do={ /file/remove $fn }
    /tool/fetch url=$url dst-path=$fn
    :delay 5s
    :if ([:len [/file/find name=$fn]] > 0) do={
        /import file-name=$fn
        /file/remove $fn
        :log info "hkros AI DNS rules updated."
    }
    /ip/dns/cache/flush
}

/system/scheduler/add name="daily_dns_ai_hkros" start-time=04:35:00 interval=1d on-event="Update_DNS_AI_hkros"
```

### 山石防火墙

`common-domains-hillstone.txt`（≤3000，通配 `*.domain`）导入山石「域名地址簿」，再用策略路由（PBR）把命中流量下一跳指到 hkros。山石不区分 AI，AI 二次分流仍在 hkros。

> **注意：** 边缘代理大表约 2.6 万条，需增大 DNS 缓存：
>
> ```routeros
> /ip/dns/set cache-size=20480KiB
> ```

## 本地构建

```bash
pip install requests tldextract
python scripts/ChinaIP.py
python scripts/ChinaASN.py
python scripts/ChinaROS.py
python scripts/DnsStaticGFW.py
python scripts/DnsStaticAI.py
python scripts/GfwIpCidr.py
python scripts/ProxyDomains.py
python scripts/DomainLists.py
```

## 项目结构

```
ASN-China/
├── scripts/
│   ├── ChinaASN.py          # 中国 ASN 列表生成
│   ├── ChinaIP.py           # 中国 IP 段列表生成
│   ├── ChinaROS.py          # RouterOS 路由/地址列表脚本生成
│   ├── DnsStaticGFW.py      # GFW 域名 DNS 分流脚本生成（向后兼容）
│   ├── DnsStaticAI.py       # AI 域名 DNS 分流脚本生成（边缘 + hkros 两端）
│   ├── GfwIpCidr.py         # GFW 应用 IP-CIDR 地址列表生成
│   ├── ProxyDomains.py      # 代理域名生成（ROS 全量塌缩 + 山石精简）
│   ├── DomainLists.py       # 域名列表生成（国内/Apple/proxy 等）
│   ├── ai_allowlist.txt     # AI 域名人工审核 allowlist（主机精确）
│   └── pin.txt              # 必保留代理域名（注册域级，钉死不被裁剪）
├── .gitea/workflows/
│   └── ci.yml               # 每日自动构建
├── .gitignore
├── LICENSE
└── README.md
```

## License

[MIT](./LICENSE)
