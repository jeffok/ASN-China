'''
Author: Jeff
Date: 2022-11-17
Description: 下载并合并国内域名、Apple 域名、代理域名列表，生成 SmartDNS 可直接使用的纯文本格式
Copyright © 2022 by Jeff, All Rights Reserved.
'''

import requests

# 数据源
SOURCES = {
    # Loyalsoldier 国内直连域名
    "direct-list.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/direct-list.txt",
    # felixonmars 中国加速域名（dnsmasq 格式，需提取域名）
    "accelerated-domains.china.conf": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf",
    # felixonmars Apple 中国域名
    "apple.china.conf": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf",
    # Loyalsoldier Apple 中国域名
    "apple-cn.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/apple-cn.txt",
    # Loyalsoldier 代理域名
    "proxy-list.txt": "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/proxy-list.txt",
}


def download(url: str) -> str:
    """下载文件内容"""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def extract_domains_plain(text: str) -> list[str]:
    """提取纯域名列表（每行一个域名，忽略注释和空行）"""
    domains = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        # 忽略含特殊前缀的行（regexp: full: 等）
        if ":" in line:
            continue
        domains.append(line)
    return domains


def extract_domains_dnsmasq(text: str) -> list[str]:
    """从 dnsmasq 格式提取域名（server=/example.com/...）"""
    domains = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("server=/"):
            parts = line.split("/")
            if len(parts) >= 2:
                domain = parts[1]
                if domain:
                    domains.append(domain)
    return domains


def write_list(domains: list[str], path: str, header: str) -> None:
    """保存域名列表"""
    with open(path, "w") as f:
        f.write(f"# {header}\n")
        f.write("# https://github.com/jeffok/ASN-China\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    # --- 国内域名（合并 Loyalsoldier direct-list + felixonmars accelerated-domains + apple）---
    print("下载国内域名列表...")
    cn_domains = set()

    # Loyalsoldier direct-list
    text = download(SOURCES["direct-list.txt"])
    domains = extract_domains_plain(text)
    print(f"  direct-list.txt: {len(domains)} 条")
    cn_domains.update(domains)

    # felixonmars accelerated-domains.china.conf
    text = download(SOURCES["accelerated-domains.china.conf"])
    domains = extract_domains_dnsmasq(text)
    print(f"  accelerated-domains.china.conf: {len(domains)} 条")
    cn_domains.update(domains)

    # felixonmars apple.china.conf
    text = download(SOURCES["apple.china.conf"])
    domains = extract_domains_dnsmasq(text)
    print(f"  apple.china.conf: {len(domains)} 条")
    cn_domains.update(domains)

    cn_sorted = sorted(cn_domains)
    write_list(cn_sorted, "cn-domains.txt", "国内域名列表（合并去重，每日更新）")
    print(f"生成 cn-domains.txt（{len(cn_sorted)} 条）\n")

    # --- Apple 中国域名 ---
    print("下载 Apple 中国域名...")
    text = download(SOURCES["apple-cn.txt"])
    apple_domains = extract_domains_plain(text)
    apple_sorted = sorted(set(apple_domains))
    write_list(apple_sorted, "apple-cn.txt", "Apple 中国域名列表（每日更新）")
    print(f"生成 apple-cn.txt（{len(apple_sorted)} 条）\n")

    # --- 代理域名 ---
    print("下载代理域名列表...")
    text = download(SOURCES["proxy-list.txt"])
    proxy_domains = extract_domains_plain(text)
    proxy_sorted = sorted(set(proxy_domains))
    write_list(proxy_sorted, "proxy-domains.txt", "代理域名列表（每日更新）")
    print(f"生成 proxy-domains.txt（{len(proxy_sorted)} 条）")


if __name__ == "__main__":
    main()
