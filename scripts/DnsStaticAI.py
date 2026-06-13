'''
Author: Jeff
Date: 2022-11-17
Description: 生成 AI 域名的 RouterOS DNS 分流脚本，从 blackmatrix7 拉取规则并合并自定义域名
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import requests

# DNS 转发目标
FORWARD_TO = "10.100.89.3"
# 匹配域名加入的地址列表名称
ADDRESS_LIST = "ai-sgp"
# 规则标签（用于批量删除旧规则）
COMMENT = "AI"
# 输出文件
OUTPUT_FILE = "dns_static_ai.rsc"

# blackmatrix7 维护的 AI 规则来源
BLACKMATRIX7_SOURCES = {
    "OpenAI":     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/OpenAI/OpenAI.list",
    "Claude":     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Claude/Claude.list",
    "Gemini":     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Gemini/Gemini.list",
    "Copilot":    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Copilot/Copilot.list",
    "Perplexity": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Perplexity/Perplexity.list",
}

# 自定义补充域名（blackmatrix7 暂未收录或收录不全）
CUSTOM_DOMAINS = [
    # ====== Cursor（来源：cursor.com/docs/enterprise/network-configuration）======
    "cursor.sh",          # *.cursor.sh 通配，含 api2/api3/api4/api5 子域
    "cursor.com",         # 主站、下载
    "cursorapi.com",      # *.cursorapi.com，含 marketplace
    "cursor-cdn.com",     # CDN 资源
    "download.todesktop.com",   # 客户端更新
    "anysphere-binaries.s3.us-east-1.amazonaws.com",  # 安装包

    # ====== Amazon Kiro（来源：kiro.dev/docs/privacy-and-security/firewalls）======
    "kiro.dev",           # *.kiro.dev 通配（runtime/management/telemetry）
    "app.kiro.dev",       # 登录门户
    # Cognito 认证
    "cognito-idp.us-east-1.amazonaws.com",
    "cognito-identity.us-east-1.amazonaws.com",
    # Amazon Q（Kiro 后端）
    "q.us-east-1.amazonaws.com",
    "q.eu-central-1.amazonaws.com",
    # Stripe（订阅计费）
    "billing.stripe.com",
    "checkout.stripe.com",
    # 扩展市场
    "open-vsx.org",
    "openvsx.eclipsecontent.org",

    # ====== Claude 补充 ======
    "claudeusercontent.com",   # Claude 生成的图片/文件
    "usefathom.com",           # 统计分析

    # ====== Perplexity 补充 ======
    "perplexity.ai",
    "api.perplexity.ai",

    # ====== X / Twitter ======
    "x.com",
    "api.x.com",
    "twitter.com",
    "api.twitter.com",
    "t.co",
    "abs.twimg.com",
    "pbs.twimg.com",
    "video.twimg.com",

    # ====== xAI / Grok ======
    "x.ai",
    "grok.com",
    "api.x.ai",

    # ====== Meta AI ======
    "meta.ai",
    "www.meta.ai",
]


def fetch_domains(url: str) -> list[str]:
    """从 Surge 格式的规则文件提取 DOMAIN 和 DOMAIN-SUFFIX 条目"""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  警告: 下载失败 {url}: {e}")
        return []

    domains = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DOMAIN-SUFFIX,"):
            domains.append(line.split(",")[1].strip())
        elif line.startswith("DOMAIN,"):
            domains.append(line.split(",")[1].strip())
        # 忽略 DOMAIN-KEYWORD, IP-CIDR, IP-ASN 等类型
    return domains


def write_rsc(domains: list[str], path: str) -> None:
    """生成 RouterOS DNS 静态分流脚本"""
    with open(path, "w") as f:
        # 先删除旧规则
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for domain in domains:
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


def write_txt(domains: list[str], path: str) -> None:
    """生成纯域名文本列表（每行一个域名，供 SmartDNS 等消费）"""
    with open(path, "w") as f:
        f.write("# AI 域名列表（自动生成，每日更新）\n")
        f.write("# https://github.com/jeffok/ASN-China\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    all_domains = set()

    # 拉取 blackmatrix7 的各 AI 规则
    for name, url in BLACKMATRIX7_SOURCES.items():
        print(f"下载 {name}: {url}")
        domains = fetch_domains(url)
        print(f"  获取 {len(domains)} 条")
        all_domains.update(domains)

    # 加入自定义补充
    all_domains.update(CUSTOM_DOMAINS)

    # 排序去重
    sorted_domains = sorted(all_domains)
    print(f"\n合并后共 {len(sorted_domains)} 条域名")

    write_rsc(sorted_domains, OUTPUT_FILE)
    print(f"生成 {OUTPUT_FILE}")

    write_txt(sorted_domains, "ai-domains.txt")
    print(f"生成 ai-domains.txt（{len(sorted_domains)} 条）")


if __name__ == "__main__":
    main()
