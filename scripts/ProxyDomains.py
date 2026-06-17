'''
Author: Jeff
Date: 2026-06-17
Description: 生成代理域名分流产物（统一源 = Loyalsoldier proxy-list ∪ gfw，eTLD+1 塌缩）
             - dns_static_proxy.rsc        边缘 RouterOS 全量表（FWD → hkros DNS，写 hk-proxy）
             - common-domains-hillstone.txt 山石防火墙精简表（热门交集 + pin + AI，≤3000）
             - proxy-domains.txt            纯文本全量塌缩域名（供其它消费）
Copyright © 2026 by Jeff, All Rights Reserved.
'''

from pathlib import Path

import requests
import tldextract

# ── 数据源 ──────────────────────────────────────────────────────────────
# proxy-list = geolocation-!cn + gfw + greatfire（Loyalsoldier 已合并去重）
PROXY_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/proxy-list.txt"
# gfw.txt 并入以保证对历史方案 100% 向后兼容（严格超集）
GFW_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/gfw.txt"
# 热门排名（用于山石精简）。主源 Umbrella，备源 Tranco。
UMBRELLA_URL = "http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ALLOWLIST_FILE = SCRIPT_DIR / "ai_allowlist.txt"
PIN_FILE = SCRIPT_DIR / "pin.txt"

# ── 产物参数 ────────────────────────────────────────────────────────────
ROS_OUTPUT = "dns_static_proxy.rsc"
HILLSTONE_OUTPUT = "common-domains-hillstone.txt"
PLAINTEXT_OUTPUT = "proxy-domains.txt"

FORWARD_TO = "10.100.50.254"     # hkros 的 RouterOS DNS（LAN IP），不是 SmartDNS
ADDRESS_LIST = "hk-proxy"
COMMENT = "PROXY"

HILLSTONE_MAX = 3000             # 山石域名地址簿硬上限
HILLSTONE_TARGET = 2800          # 实际目标，留余量

# 使用 tldextract 内置快照（suffix_list_urls=() → 离线，不依赖网络拉 PSL）
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())


def registrable(domain: str) -> str | None:
    """归一到注册域 eTLD+1，例如 a.b.google.com -> google.com。"""
    e = _EXTRACT(domain.strip().lower().lstrip("."))
    if e.domain and e.suffix:
        return f"{e.domain}.{e.suffix}"
    return None


def download(url: str, timeout: int = 60) -> bytes:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def parse_domain_list(text: str) -> set[str]:
    """解析 Loyalsoldier 域名列表，丢弃 regexp，塌缩到注册域。"""
    out = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line.startswith("regexp:"):
            continue
        for prefix in ("full:", "domain:"):
            if line.startswith(prefix):
                line = line[len(prefix):]
        if ":" in line:        # 其余带前缀的规则一律跳过
            continue
        r = registrable(line)
        if r:
            out.add(r)
    return out


def load_simple(path: Path) -> set[str]:
    out = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line.lower())
    return out


def load_ai_registrable() -> set[str]:
    return {r for d in load_simple(AI_ALLOWLIST_FILE) if (r := registrable(d))}


def download_popularity() -> list[str]:
    """返回按热度排序、去重的注册域列表（rank 升序）。"""
    import io
    import zipfile

    for name, url in (("Umbrella", UMBRELLA_URL), ("Tranco", TRANCO_URL)):
        try:
            print(f"下载热门排名: {name} {url}")
            blob = download(url)
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                raw = zf.read(zf.namelist()[0]).decode("utf-8", "ignore")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"  {name} 失败: {exc}")
            raw = None
    if raw is None:
        raise RuntimeError("热门排名主备源均不可用，无法生成山石精简表")

    ordered, seen = [], set()
    for line in raw.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) != 2:
            continue
        r = registrable(parts[1])
        if r and r not in seen:
            seen.add(r)
            ordered.append(r)
    print(f"  热门注册域去重后: {len(ordered)} 条")
    return ordered


def write_ros(domains: list[str]) -> None:
    with open(ROS_OUTPUT, "w") as f:
        f.write(f"/ip/dns/static/remove [find where comment={COMMENT}]\n")
        f.write("/ip/dns/static\n")
        for d in domains:
            f.write(
                f"add name={d} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes comment={COMMENT}\n"
            )


def write_plaintext(domains: list[str], path: str, header: str) -> None:
    with open(path, "w") as f:
        f.write(f"# {header}\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    print(f"下载代理源: {PROXY_URL}")
    proxy = parse_domain_list(download(PROXY_URL).decode("utf-8", "ignore"))
    print(f"  proxy-list 塌缩注册域: {len(proxy)}")
    print(f"下载 GFW 源（向后兼容）: {GFW_URL}")
    gfw = parse_domain_list(download(GFW_URL).decode("utf-8", "ignore"))
    print(f"  gfw.txt 塌缩注册域: {len(gfw)}")

    ai_reg = load_ai_registrable()
    pin = load_simple(PIN_FILE)
    print(f"AI 注册域: {len(ai_reg)}  PIN: {len(pin)}")

    # 统一源：proxy ∪ gfw ∪ pin（保证严格超集 + 核心域钉死）
    full = proxy | gfw | pin
    # ROS 全量表去掉与 AI 完全相同的注册域（这些由 dns_static_ai_edge.rsc 单独提供，避免重复条目）
    ros_domains = sorted(full - ai_reg)
    write_ros(ros_domains)
    print(f"\n生成 {ROS_OUTPUT}（ROS 全量，{len(ros_domains)} 条）")
    write_plaintext(sorted(full), PLAINTEXT_OUTPUT, "代理域名（注册域塌缩，每日更新）")
    print(f"生成 {PLAINTEXT_OUTPUT}（{len(full)} 条）")

    # 山石精简：热门交集（按热度截断）+ pin + AI，去重，≤3000
    pop = download_popularity()
    inter = [d for d in pop if d in full]
    keep = HILLSTONE_TARGET - len(pin | ai_reg)
    keep = max(keep, 0)
    hillstone = sorted(set(inter[:keep]) | pin | ai_reg)
    if len(hillstone) > HILLSTONE_MAX:
        # 极端兜底：超限则在保留 pin+AI 的前提下再砍热门尾部
        head = sorted(set(inter[:keep - (len(hillstone) - HILLSTONE_MAX)]) | pin | ai_reg)
        hillstone = head
    write_plaintext(hillstone, HILLSTONE_OUTPUT,
                    f"山石防火墙常用代理域名（热门交集+pin+AI，≤{HILLSTONE_MAX}，每日更新）")
    print(f"生成 {HILLSTONE_OUTPUT}（山石精简，{len(hillstone)} 条，上限 {HILLSTONE_MAX}）")


if __name__ == "__main__":
    main()
