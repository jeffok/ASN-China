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

## 发布文件

`release-files` 分支只发布白名单文件，不再把所有生成产物都放进去。

### 设备直接使用

| 文件 | 用途 | 使用方 |
|------|------|--------|
| [`dns_static_proxy_manifest.rsc`][dns_static_proxy_manifest] | 代理域名状态清单，包含 current/previous hash、条数和增量统计 | szhome / devros 定时任务先导入它判断是否需要更新 |
| [`dns_static_proxy_delta.rsc`][dns_static_proxy_delta] | 代理域名增量更新，只删除过期项并新增变化项；导入前设置 `proxyForwardTo`、`proxyAddressList`、`proxyComment`；每 500 个操作自动 `:delay 1s` | szhome / devros 日常更新 |
| [`dns_static_proxy.rsc`][dns_static_proxy] | 代理域名全量模板，约 6-8k，首次安装或 hash 不连续时使用；导入前设置 `proxyForwardTo`、`proxyAddressList`、`proxyComment`；每 500 条自动 `:delay 1s` | szhome / devros 兜底全量导入 |
| [`dns_static_ai.rsc`][dns_static_ai] | 通用 AI 域名模板，导入前由 RouterOS 设置 `aiForwardTo`、`aiAddressList`、`aiComment` | szhome / devros / hkros |
| [`gfw_ip_list.rsc`][gfw_ip_list] | Telegram 等硬编码 IP-CIDR，写入 `hk-proxy` | szhome / devros |
| [`cn_routes.rsc`][cn_routes] | 中国 IP 静态路由，无网关，导入后由设备设置自己的 gateway | hkros / 需要回国路由的节点 |
| [`China_ASN.rsc`][china_asn_rsc] | 中国 ASN num-list | sgpcloud BGP 过滤 |

### CI 兜底快照

这些不是 RouterOS 日常直接拉取的核心文件，主要用于 GitHub/APNIC 全部不可达时让下一次 CI 继续可构建：

| 文件 | 用途 |
|------|------|
| [`IP.China.list`][ip_china] | 中国 IPv4 + IPv6 CIDR 快照，供 `ChinaIP.py` 兜底 |
| [`ASN.China.list`][asn_china] | 中国 ASN 快照，供 `ChinaASN.py` 兜底 |
| [`cn-domains.txt`][cn_domains] | 国内域名快照，供 `DomainLists.py` 兜底 |
| [`apple-cn.txt`][apple_cn] | Apple 中国域名（约 165 条；上游为 `full:` 前缀，由 `DomainLists.py` 解析保留域名本体） |
| [`cn-exceptions.txt`][cn_exceptions] | **国内例外**：`cn-domains` 中比 proxy/gfw/ai 父域更具体的条目（如 `apps.apple.com` vs `apple.com`），下游应**在代理名单之前**匹配（最具体匹配优先），由 `CnExceptions.py` 生成 |
| [`proxy-domains.txt`][proxy_domains] | Loyalsoldier proxy-list 快照，供构建兜底，不是边缘设备使用的 6-8k 表 |
| [`gfw-domains.txt`][gfw_domains] | GFW 域名快照，供 `DnsStaticGFW.py` / `ProxyDomains.py` 兜底 |
| [`gfw-ip-cidrs.txt`][gfw_ip_cidrs] | Telegram 等 IP-CIDR 快照，供 `GfwIpCidr.py` 兜底 |
| [`bogus-nxdomain.china.conf`][bogus_nxdomain] | 虚假 NXDOMAIN IP 过滤快照 |

### 人工参考

| 文件 | 用途 |
|------|------|
| [`ai-domains.txt`][ai_domains] | AI allowlist 展开后的纯文本，便于人工审查 |
| [`common-domains-hillstone.txt`][common_domains_hillstone] | 山石防火墙精简域名表（≤3000） |

### 不再发布

这些文件仍可在 CI 工作区或本地生成，但不再放入 `release-files`：

| 文件 | 原因 |
|------|------|
| `IPv4.China.list` / `IPv6.China.list` | 中间产物，`IP.China.list` 已覆盖兜底需求 |
| `cn_address_list.rsc` | 当前设备未使用，避免增加发布文件数量 |
| `dns_static_gfw.rsc` | 旧模型兼容产物，当前边缘设备使用 `dns_static_proxy*.rsc` |
| `dns_static_ai_edge.rsc` / `dns_static_ai_hkros.rsc` | 已合并为通用 `dns_static_ai.rsc`，由设备脚本传变量 |
| `dns_static_ai_sgpros.rsc` | 不需要在 sgpros 上维护 AI static；hkros 已将 AI FWD 到 sgpros，由 sgpros 自身 DNS 递归 |

[dns_static_proxy_manifest]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_proxy_manifest.rsc
[dns_static_proxy_delta]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_proxy_delta.rsc
[dns_static_proxy]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_proxy.rsc
[dns_static_ai]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_ai.rsc
[gfw_ip_list]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/gfw_ip_list.rsc
[cn_routes]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/cn_routes.rsc
[china_asn_rsc]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/China_ASN.rsc
[ip_china]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/IP.China.list
[asn_china]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/ASN.China.list
[cn_domains]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/cn-domains.txt
[apple_cn]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/apple-cn.txt
[cn_exceptions]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/cn-exceptions.txt
[proxy_domains]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/proxy-domains.txt
[gfw_domains]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/gfw-domains.txt
[gfw_ip_cidrs]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/gfw-ip-cidrs.txt
[bogus_nxdomain]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/bogus-nxdomain.china.conf
[ai_domains]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/ai-domains.txt
[common_domains_hillstone]: https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/common-domains-hillstone.txt

## 更新调度

Gitea Actions 每日 UTC 20:00（北京时间 04:00）自动运行，生成文件 force-push 到 `release-files` 分支。

## 数据源下载策略

GitHub raw 数据源优先通过国内可访问镜像下载，顺序为：

1. `cdn.jsdelivr.net`
2. `gh-proxy.com`
3. `ghfast.top`
4. `raw.githubusercontent.com`

仅当以上 GitHub 镜像全部失败时，才回退到 `release-files` 中的上一版产物，避免国内网络下直接使用旧文件作为首选数据源。

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

`szhome`、`devros` 边缘路由器导入代理表和通用 AI 模板。两个模板都在导入前设置变量，让代理/AI 域名 FWD 到 **hkros DNS `10.100.50.254`**、写 `hk-proxy`；AI 的二次分流（→ SGP）由 hkros 完成。

```routeros
/system/script/add name="Update_DNS_Edge" source={
    :local base "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/"

    # 代理域名：日常建议使用 manifest + delta 状态机；首次安装可直接导入全量表。
    :global proxyForwardTo "10.100.50.254"
    :global proxyAddressList "hk-proxy"
    :global proxyComment "PROXY"
    :local fn "dns_static_proxy.rsc"
    :if ([:len [/file/find name=$fn]] > 0) do={ /file/remove $fn }
    /tool/fetch url=($base . $fn) dst-path=$fn
    :delay 5s
    :if ([:len [/file/find name=$fn]] > 0) do={
        /import file-name=$fn
        /file/remove $fn
        :log info ("imported " . $fn)
    } else={ :log error ("download failed: " . $fn) }

    # AI 域名：同一个 dns_static_ai.rsc，通过变量决定转发目标和写入地址列表。
    :global aiForwardTo "10.100.50.254"
    :global aiAddressList "hk-proxy"
    :global aiComment "AI"
    :set fn "dns_static_ai.rsc"
    :if ([:len [/file/find name=$fn]] > 0) do={ /file/remove $fn }
    /tool/fetch url=($base . $fn) dst-path=$fn
    :delay 5s
    :if ([:len [/file/find name=$fn]] > 0) do={
        /import file-name=$fn
        /file/remove $fn
        :log info ("imported " . $fn)
    } else={ :log error ("download failed: " . $fn) }
    /ip/dns/cache/flush
}

/system/scheduler/add name="daily_dns_edge" start-time=04:30:00 interval=1d on-event="Update_DNS_Edge"
```

### hkros AI 域名 DNS 分流

hkros 也导入同一个 `dns_static_ai.rsc`，只是变量不同：AI 域名 FWD 到 **sgpros DNS `10.100.89.3`**、命中写 `ai-sgp`（mangle 再把 `ai-sgp` 标记到 `rt-sgp` 经 WG 到 sgpros 出网）。

```routeros
/system/script/add name="Update_DNS_AI_hkros" source={
    :global aiForwardTo "10.100.89.3"
    :global aiAddressList "ai-sgp"
    :global aiComment "AI"
    :local fn "dns_static_ai.rsc"
    :local url "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files/dns_static_ai.rsc"
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
│   ├── DomainLists.py       # 域名列表生成（国内/Apple/proxy 等；解析 full:/domain: 前缀，产物带数量下限）
│   ├── CnExceptions.py      # 国内例外域名（cn 比 proxy/gfw/ai 父域更具体）
│   ├── ai_allowlist.txt     # AI 域名人工审核 allowlist（主机精确）
│   └── pin.txt              # 必保留代理域名（注册域级，钉死不被裁剪）
├── tests/
│   └── test_domain_lists.py # 离线单元测试（CI 中运行）
├── .gitea/workflows/
│   └── ci.yml               # 每日自动构建
├── .gitignore
├── LICENSE
└── README.md
```

## License

[MIT](./LICENSE)
