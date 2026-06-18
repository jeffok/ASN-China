'''
Author: Jeff
Date: 2026-06-17
Description: 生成代理域名分流产物（统一源 = Loyalsoldier proxy-list ∪ gfw，eTLD+1 塌缩）
             - dns_static_proxy.rsc        边缘 RouterOS 中等常用表（FWD → hkros DNS，写 hk-proxy）
             - common-domains-hillstone.txt 山石防火墙精简表（热门交集 + pin + AI，≤3000）
             - proxy-domains.txt            纯文本中等常用域名（供其它消费）
Copyright © 2026 by Jeff, All Rights Reserved.
'''

from __future__ import annotations  # 兼容 Python 3.9 runner：延迟注解，str|None/list[str] 不在运行时求值

import os
from pathlib import Path

import requests
import tldextract

# ── 数据源 ──────────────────────────────────────────────────────────────
# proxy-list = geolocation-!cn + gfw + greatfire（Loyalsoldier 已合并去重）
PROXY_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/proxy-list.txt"
# gfw.txt 并入以保证对历史方案 100% 向后兼容（严格超集）
GFW_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/gfw.txt"
# 热门排名（用于山石精简）。多源在线 + 仓库内置兜底（CI runner 一定能读到 clone 下来的仓库）。
POPULARITY_URLS = (
    ("Umbrella-https", "https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"),
    ("Umbrella-http", "http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"),
    ("Tranco", "https://tranco-list.eu/top-1m.csv.zip"),
)
RELEASE_RAW_BASE = "https://gitea.jeffok.com:4443/jeff/asn-china/raw/branch/release-files"

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ALLOWLIST_FILE = SCRIPT_DIR / "ai_allowlist.txt"
PIN_FILE = SCRIPT_DIR / "pin.txt"
POPULARITY_FALLBACK_FILE = SCRIPT_DIR / "popularity_fallback.txt"   # 内置兜底（rank 序）

# ── 产物参数 ────────────────────────────────────────────────────────────
ROS_OUTPUT = "dns_static_proxy.rsc"
HILLSTONE_OUTPUT = "common-domains-hillstone.txt"
PLAINTEXT_OUTPUT = "proxy-domains.txt"

FORWARD_TO = "10.100.50.254"     # hkros 的 RouterOS DNS（LAN IP），不是 SmartDNS
ADDRESS_LIST = "hk-proxy"
COMMENT = "PROXY"

HILLSTONE_MAX = 3000             # 山石域名地址簿硬上限
HILLSTONE_TARGET = 2800          # 实际目标，留余量

# 中等精简表（低内存 ROS 设备，如 hAP ax lite 256MB），作为 dns_static_proxy.rsc 主产物
# 策略：两层分级
#   第一层（必收）：gfw.txt 全部显式封锁域名 + pin.txt + AI 域名
#   第二层（热门补充）：proxy-list 中非 gfw 的域名，仅保留 Umbrella rank ≤ MEDIUM_RANK_CUTOFF 的
# 参数含义："全球 DNS 查询量排名前 N" 有真实依据，比按条数截断更合理
MEDIUM_RANK_CUTOFF = 90000       # Umbrella rank 门槛（≤此值才纳入第二层）

# 使用 tldextract 内置快照（suffix_list_urls=() → 离线，不依赖网络拉 PSL）
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())


def registrable(domain: str) -> str | None:
    """归一到注册域 eTLD+1，例如 a.b.google.com -> google.com。"""
    e = _EXTRACT(domain.strip().lower().lstrip("."))
    if e.domain and e.suffix:
        return f"{e.domain}.{e.suffix}"
    return None


def _to_jsdelivr(url: str) -> str | None:
    import re
    m = re.match(r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)', url)
    if m:
        user, repo, branch, path = m.groups()
        return f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{path}"
    return None


def download(url: str, timeout: int = 10) -> bytes:
    cdn = _to_jsdelivr(url)
    urls = [cdn, url] if cdn else [url]
    last_exc: Exception | None = None
    for u in urls:
        try:
            r = requests.get(u, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:
            print(f"  ⚠ {u} 失败: {e}")
            last_exc = e
    raise RuntimeError(f"所有镜像均失败: {url}") from last_exc


def download_or_release(url: str, fallback_file: str) -> bytes:
    try:
        return download(url)
    except Exception as exc:
        fallback_url = f"{RELEASE_RAW_BASE}/{fallback_file}"
        print(f"  外部源不可达，回退到 release-files/{fallback_file}: {exc}")
        r = requests.get(fallback_url, timeout=60)
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
    """返回按热度排序、去重的注册域列表（rank 升序）。

    在线多源 → 仓库内置兜底 → 空列表（非致命，山石表跳过但不中断构建）。
    """
    import io
    import zipfile

    if os.environ.get("ASN_CHINA_CI") == "1":
        return load_popularity_fallback("CI 环境跳过在线热门排名")

    raw = None
    for name, url in POPULARITY_URLS:
        try:
            print(f"下载热门排名: {name} {url}")
            blob = download(url)
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                raw = zf.read(zf.namelist()[0]).decode("utf-8", "ignore")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"  {name} 失败: {exc}")

    if raw is not None:
        ordered, seen = [], set()
        for line in raw.splitlines():
            parts = line.strip().split(",", 1)
            if len(parts) != 2:
                continue
            r = registrable(parts[1])
            if r and r not in seen:
                seen.add(r)
                ordered.append(r)
        print(f"  在线热门注册域去重后: {len(ordered)} 条")
        return ordered

    return load_popularity_fallback("在线源不可达")


def load_popularity_fallback(reason: str) -> list[str]:
    # 在线不可用或 CI 明确跳过 → 用仓库内置兜底（已是 rank 序的注册域）
    if POPULARITY_FALLBACK_FILE.exists():
        fallback = [
            line.strip()
            for line in POPULARITY_FALLBACK_FILE.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        print(f"  {reason}，使用内置兜底 popularity_fallback.txt: {len(fallback)} 条")
        return fallback

    print("  警告：在线源与内置兜底均不可用，跳过山石精简表生成（不中断构建）")
    return []


def write_ros(domains: list[str], path: str = ROS_OUTPUT, comment: str = COMMENT) -> None:
    with open(path, "w") as f:
        f.write(f"/ip/dns/static/remove [find where comment={comment}]\n")
        f.write("/ip/dns/static\n")
        for d in domains:
            f.write(
                f"add name={d} type=FWD forward-to={FORWARD_TO} "
                f"address-list={ADDRESS_LIST} match-subdomain=yes comment={comment}\n"
            )


def write_plaintext(domains: list[str], path: str, header: str) -> None:
    with open(path, "w") as f:
        f.write(f"# {header}\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("\n".join(domains) + "\n")


def main() -> None:
    print(f"下载代理源: {PROXY_URL}")
    proxy = parse_domain_list(download_or_release(PROXY_URL, "proxy-domains.txt").decode("utf-8", "ignore"))
    print(f"  proxy-list 塌缩注册域: {len(proxy)}")
    print(f"下载 GFW 源（向后兼容）: {GFW_URL}")
    gfw = parse_domain_list(download_or_release(GFW_URL, "gfw-domains.txt").decode("utf-8", "ignore"))
    print(f"  gfw.txt 塌缩注册域: {len(gfw)}")

    ai_hosts = load_simple(AI_ALLOWLIST_FILE)
    ai_reg = {r for d in ai_hosts if (r := registrable(d))}
    pin = load_simple(PIN_FILE)
    print(f"AI 注册域: {len(ai_reg)}  PIN: {len(pin)}")

    # 统一候选源
    full = proxy | gfw | pin

    # 热门排名数据（中等表 + 山石表共用）
    pop = download_popularity()
    if not pop:
        print(f"跳过 {ROS_OUTPUT} 和 {HILLSTONE_OUTPUT}（无热门排名数据）")
        return

    # 热门域名集合（带 rank 索引，供不同门槛查询）
    pop_rank: dict[str, int] = {d: i for i, d in enumerate(pop, 1)}

    def trim_by_popularity(target: int, hard_max: int) -> list[str]:
        """山石表专用：按热度截断到 target 条（含 pin + ai_reg），不超过 hard_max。"""
        required = pin | ai_reg
        inter = [d for d in pop if d in full]
        keep = max(target - len(required), 0)
        result = sorted(set(inter[:keep]) | required)
        if len(result) > hard_max:
            keep2 = max(keep - (len(result) - hard_max), 0)
            result = sorted(set(inter[:keep2]) | required)
        return result

    def build_medium(rank_cutoff: int) -> list[str]:
        """两层分级中等表：
        第一层：gfw 全部显式封锁域名 + pin + ai（必收，不受排名约束）
        第二层：proxy-only 域名中，Umbrella rank ≤ rank_cutoff 的（热门外国服务补充）
        """
        # 第一层：GFW 显式封锁 + 核心固定
        tier1 = gfw | pin | ai_reg

        # 第二层：proxy 独有（非 gfw）且在热门排名门槛内
        proxy_only = proxy - gfw
        tier2 = {d for d in proxy_only if pop_rank.get(d, 10**9) <= rank_cutoff}

        result = sorted(tier1 | tier2)
        return result

    # 山石精简表（≤3000，按数量截断）
    hillstone = trim_by_popularity(HILLSTONE_TARGET, HILLSTONE_MAX)
    write_plaintext(hillstone, HILLSTONE_OUTPUT,
                    f"山石防火墙常用代理域名（热门交集+pin+AI，≤{HILLSTONE_MAX}，每日更新）")
    print(f"生成 {HILLSTONE_OUTPUT}（山石精简，{len(hillstone)} 条，上限 {HILLSTONE_MAX}）")

    # 中等精简表（两层分级，rank 门槛）
    medium_domains = build_medium(MEDIUM_RANK_CUTOFF)
    tier1_count = len(gfw | pin | ai_reg)
    tier2_count = len(medium_domains) - tier1_count
    print(f"\n中等表构成：第一层（GFW+pin+AI）{tier1_count} 条 + 第二层（rank≤{MEDIUM_RANK_CUTOFF}补充）{tier2_count} 条")
    write_ros(sorted(set(medium_domains) - ai_reg), ROS_OUTPUT, comment=COMMENT)
    write_plaintext(medium_domains, PLAINTEXT_OUTPUT,
                    f"代理域名中等精简（GFW全收+rank≤{MEDIUM_RANK_CUTOFF}热门补充，每日更新）")
    print(f"生成 {ROS_OUTPUT}（中等精简，{len(medium_domains)} 条）")


if __name__ == "__main__":
    main()
