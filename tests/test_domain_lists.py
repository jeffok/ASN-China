"""离线单元测试（无需网络）：python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import CnExceptions  # noqa: E402
import DomainLists  # noqa: E402


class ExtractDomainsPlain(unittest.TestCase):
    def test_full_prefix_kept(self):
        # 回归：apple-cn 上游全部是 full: 前缀，旧实现输出为空
        text = "full:a1.mzstatic.com\nfull:apps.apple.com\n"
        self.assertEqual(DomainLists.extract_domains_plain(text), ["a1.mzstatic.com", "apps.apple.com"])

    def test_domain_prefix_and_attrs(self):
        self.assertEqual(DomainLists.extract_domains_plain("domain:example.com:@cn\n"), ["example.com"])

    def test_regexp_keyword_dropped(self):
        text = "regexp:^ad\\..+$\nkeyword:track\nplain.example\n"
        self.assertEqual(DomainLists.extract_domains_plain(text), ["plain.example"])

    def test_comments_blank_and_normalize(self):
        text = "# c\n! c2\n\n  Example.COM.  \n"
        self.assertEqual(DomainLists.extract_domains_plain(text), ["example.com"])

    def test_invalid_lines_dropped(self):
        self.assertEqual(DomainLists.extract_domains_plain("bad domain\nhttp://x/y\nok.com\n"), ["ok.com"])

    def test_single_label_tld_kept(self):
        # 品牌 TLD（如 baidu、alibaba）在名单里是合法的单标签条目
        self.assertEqual(DomainLists.extract_domains_plain("baidu\n"), ["baidu"])


class RequireMin(unittest.TestCase):
    def test_below_min_fails(self):
        with self.assertRaises(SystemExit):
            DomainLists.require_min("x", 10, 100)

    def test_ok(self):
        DomainLists.require_min("x", 100, 100)


class CnExceptions_(unittest.TestCase):
    def test_cn_more_specific_than_proxy_parent(self):
        cn = {"apps.apple.com", "baidu.com", "a1.mzstatic.com"}
        parents = {"apple.com", "mzstatic.com"}
        self.assertEqual(CnExceptions.compute_exceptions(cn, parents), ["a1.mzstatic.com", "apps.apple.com"])

    def test_identical_entries_are_not_exceptions(self):
        # 相同条目不算例外（下游统一走「国内优先、按应答 IP 判定」）
        self.assertEqual(CnExceptions.compute_exceptions({"moonshot.ai"}, {"moonshot.ai"}), [])

    def test_proxy_more_specific_than_cn_parent_not_exception(self):
        # proxy 更具体（如 bbs.naixi.net vs naixi.net）不属于 cn 例外
        self.assertEqual(CnExceptions.compute_exceptions({"naixi.net"}, {"bbs.naixi.net"}), [])

    def test_tld_not_a_parent(self):
        self.assertEqual(CnExceptions.compute_exceptions({"x.com"}, {"com"}), [])

    def test_shadow_warning(self):
        # 硬名单条目落在 cn 例外之下 → 告警
        exceptions = ["apps.apple.com"]
        self.assertEqual(CnExceptions.shadowed_by_exceptions(exceptions, {"evil.apps.apple.com", "x.com"}),
                         ["evil.apps.apple.com"])


if __name__ == "__main__":
    unittest.main()
