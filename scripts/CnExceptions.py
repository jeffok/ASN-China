'''
Description: 生成 cn-exceptions.txt —— 「国内域名里比代理名单父域更具体」的例外条目。

背景：
  proxy-domains（Loyalsoldier proxy-list，非 CN 域名）里有 apple.com / microsoft.com 等父域，
  而 cn-domains 里有 apps.apple.com / 各类 Microsoft 中国 CDN 等更具体的子域。
  下游若按「先匹配 proxy、再匹配 cn」的顺序分流，这些更具体的国内子域会被父域抢先判为代理。
  本脚本把这类「cn 更具体」的条目单独发布，供下游**放在 proxy 之前**匹配（最具体匹配优先）。

规则（纯文本后缀匹配语义，与 mosdns domain_set 一致）：
  d ∈ cn-domains，且 d 存在**真父域**（不含 d 自身、不含 TLD）s ∈ (proxy ∪ gfw ∪ ai)  →  d 为例外。
  相同条目（d 本身同时在 cn 与 proxy/gfw/ai）不是例外：它们由下游统一走「国内优先、按应答 IP 判定」路径。

输入（当前目录，由前序脚本生成）：cn-domains.txt、proxy-domains.txt、gfw-domains.txt、ai-domains.txt（后两者可缺失）
输出：cn-exceptions.txt
'''

from __future__ import annotations

import os
import sys

MIN_EXCEPTIONS = 50  # 线上实测约 256；显著偏低说明上游输入异常，宁可让 CI 失败


def read_domains(path: str) -> set[str]:
    out: set[str] = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.split("#", 1)[0].strip().lower().lstrip(".")
            if s:
                out.add(s)
    return out


def strict_parents(domain: str):
    """真父域：d=a.b.c.d → b.c.d, c.d（不含自身，不含单标签 TLD）。"""
    labels = domain.split(".")
    for i in range(1, len(labels) - 1):
        yield ".".join(labels[i:])


def compute_exceptions(cn: set[str], parents: set[str]) -> list[str]:
    return sorted(d for d in cn if any(p in parents for p in strict_parents(d)))


def shadowed_by_exceptions(exceptions: list[str], hard: set[str]) -> list[str]:
    """硬名单（gfw/ai）条目若落在某个 cn 例外之下，下游先匹配例外会把它判成国内——给出告警清单。"""
    exc = set(exceptions)
    return sorted(h for h in hard if h not in exc and any(p in exc for p in strict_parents(h)))


def main() -> None:
    cn = read_domains("cn-domains.txt")
    proxy = read_domains("proxy-domains.txt")
    gfw = read_domains("gfw-domains.txt")
    ai = read_domains("ai-domains.txt")
    if not cn or not proxy:
        raise SystemExit("缺少 cn-domains.txt 或 proxy-domains.txt，请先运行 DomainLists.py")

    hard = gfw | ai
    exceptions = compute_exceptions(cn, proxy | hard)
    if len(exceptions) < MIN_EXCEPTIONS:
        raise SystemExit(f"cn-exceptions 仅 {len(exceptions)} 条，低于下限 {MIN_EXCEPTIONS}，拒绝发布")

    shadowed = shadowed_by_exceptions(exceptions, hard)
    if shadowed:
        print(f"  ⚠ {len(shadowed)} 个硬名单条目位于 cn 例外之下（下游先匹配例外会判为国内）: {shadowed[:10]}")

    with open("cn-exceptions.txt", "w") as f:
        f.write("# 国内例外域名：cn 比 proxy/gfw/ai 父域更具体，下游应在代理名单之前匹配（每日更新）\n")
        f.write("# https://gitea.jeffok.com:4443/jeff/asn-china\n")
        f.write("\n".join(exceptions) + "\n")
    print(f"生成 cn-exceptions.txt（{len(exceptions)} 条）", file=sys.stdout)


if __name__ == "__main__":
    main()
