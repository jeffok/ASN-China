"""
Generate RouterOS dns-static .rsc file for AI domains.

从以下来源自动拉取并合并 AI 域名，无需手动维护：
  - blackmatrix7/ios_rule_script: OpenAI / Claude / Gemini / Copilot / Perplexity / Grok
  - 自定义补充: Cursor / Kiro / X(Twitter)

只提取 DOMAIN 和 DOMAIN-SUFFIX 类型，忽略 IP-CIDR / IP-ASN / DOMAIN-KEYWORD。

Output: dns_static_ai.rsc
"""

import re
import requests

FORWARD_TO = "10.100.89.3"
ADDRESS_LIST = "ai-sgp"
COMMENT = "AI"
OUTPUT_FILE = "dns_static_ai.rsc"

# blackmatrix7 维护的 AI 规则来源
BLACKMATRIX7_SOURCES = {
    "OpenAI":    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/OpenAI/OpenAI.list",
    "Claude":    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Claude/Claude.list",
    "Gemini":    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Gemini/Gemini.list",
    "Copilot":   "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Copilot/Copilot.list",
    "Perplexity":"https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Perplexity/Perplexity.list",
}

# 自定义补充域名（blackmatrix7 暂未收录）
CUSTOM_DOMAINS = [
    # ====== Cursor（来源：cursor.com/docs/enterprise/network-configuration）======
    "cursor.sh",          # *.cursor.sh 通配，含所有 api2/api3/api4/api5 子域
    "cursor.com",         # 主站、下载
    "cursorapi.com",      # *.cursorapi.com，含 marketplace
    "cursor-cdn.com",     # CDN 资源
    "download.todesktop.com",   # 客户端更新
    "anysphere-binaries.s3.us-east-1.amazonaws.com",  # 安装包

    # ====== Amazon Kiro（来源：kiro.dev/docs/privacy-and-security/firewalls）======
    "kiro.dev",           # *.kiro.dev 通配（含所有 runtime/management/telemetry 子域）
    "app.kiro.dev",       # 登录门户（match-subdomain 已覆盖，显式列出更安全）
    # Cognito 认证
    "cognito-idp.us-east-1.amazonaws.com",
    "cognito-identity.us-east-1.amazonaws.com",
    # Amazon Q（Kiro 后端，legacy endpoint）
    "q.us-east-1.amazonaws.com",
    "q.eu-central-1.amazonaws.com",
    # Stripe（订阅计费）
    "billing.stripe.com",
    "checkout.stripe.com",
    # 扩展市场
    "open-vsx.org",
    "openvsx.eclipsecontent.org",

    # ====== Claude（blackmatrix7 仅收录了 3 条，补充完整）======
    "claudeusercontent.com",   # Claude 生成的图片/文件
    "usefathom.com",           # 统计分析

    # ====== Perplexity（blackmatrix7 暂无）======
    "perplexity.ai",
    "api.perplexity.ai",

    # ====== X / Twitter（AI 功能相关）======
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
        # 忽略 DOMAIN-KEYWORD, IP-CIDR, IP-ASN 等
    return domains


def write_rsc(domains: list[str], path: str) -> None:
    """生成 ROS .rsc 导入脚本"""
    with open(path, "w") as f:
        f.write(f"/ip dns static remove [find where comment={COMMENT}]\n")
        f.write("/ip dns static\n")
        for domain in domains:
            f.write(
                f"add name={domain} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes "
                f"comment={COMMENT}\n"
            )


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


if __name__ == "__main__":
    main()
