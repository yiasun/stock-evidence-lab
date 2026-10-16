import copy
import json
import tempfile
import unittest
from pathlib import Path
from diagnosis import *

class PhaseTwoEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = load_data()

    def test_ttm_uses_full_year_minus_previous_half_plus_current_half(self):
        value = valuation_metrics(self.data)
        self.assertAlmostEqual(value["ttm_profit"],81433985225.44,places=2)
        self.assertAlmostEqual(value["pe_ttm"],20.1552169542,places=6)
        self.assertAlmostEqual(value["pb"],6.5325220260,places=6)
        self.assertIn("尚未核验",self.data["valuation"]["assumption"])

    def test_peer_comparison_and_negative_cashflow(self):
        result = peer_comparison(self.data)
        self.assertEqual(list(result["期次"]),["2026H1","2026H1"])
        self.assertAlmostEqual(result.iloc[1]["归母利润同比（%）"],89.29986,places=4)
        self.assertLess(result.iloc[1]["经营现金流（亿元）"],0)
        self.assertIn("两家公司",self.data["peers"]["scope"])

    def test_sources_include_original_pdf_page_and_sha(self):
        sources = {s["id"]:s for s in all_sources(self.data)}
        self.assertEqual(set(sources),{"S1","S2","S3","S4","S5"})
        for id in ["S1","S4","S5"]:
            self.assertIn("PDF第",sources[id]["locator"])
            self.assertEqual(len(sources[id]["sha256"]),64)

    def test_market_range_and_no_live_quote_leakage(self):
        frame = load_market(self.data)
        self.assertEqual(len(frame),27)
        self.assertEqual(frame.date.iloc[0].date(),date(2026,9,1))
        self.assertEqual(frame.date.iloc[-1].date(),date(2026,10,15))
        self.assertEqual(frame.close.iloc[-1],1312.97)
        self.assertEqual(frame.volume.iloc[-1],5767700)
        self.assertIn("不复权",self.data["market"]["adjustment"])

    def test_raw_response_hash_matches_manifest(self):
        path = ROOT / "data" / self.data["market"]["source"]["raw_file"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),self.data["market"]["source"]["sha256"])

    def test_tampered_market_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"data").mkdir()
            (root/"data"/self.data["market"]["file"]).write_text("date,close,volume\n2026-10-14,1,1\n2026-10-15,2,2",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"哈希"):
                load_market(self.data,root=root)

    def test_market_hash_survives_windows_linux_line_ending_conversion(self):
        original = (ROOT/"data"/self.data["market"]["file"]).read_bytes().replace(b"\r\n",b"\n")
        for newline in [b"\n",b"\r\n"]:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                (root/"data").mkdir()
                (root/"data"/self.data["market"]["file"]).write_bytes(original.replace(b"\n",newline))
                self.assertEqual(len(load_market(self.data,root=root)),27)

    def test_inconsistent_valuation_and_periods_fail_closed(self):
        for section,key,value in [("valuation","equity_parent",1),("valuation","as_of","2026-10-16"),("valuation","ttm_end","2026-09-30"),("annual","period","2024FY")]:
            bad = copy.deepcopy(self.data)
            bad[section][key] = value
            with self.assertRaises(ValueError):
                validate_extended_data(bad)

    def test_valuation_does_not_claim_official_or_cheapest(self):
        evidence = {c["id"]:c for c in cards(self.data)}
        self.assertEqual(evidence["E8"]["kind"],"推断")
        self.assertEqual(evidence["E11"]["kind"],"未知")
        self.assertIn("不是官方",evidence["E8"]["body"])

    def test_company_name_does_not_trigger_valuation_dimension(self):
        self.assertNotIn("估值",select_dimensions("贵州茅台现金流为何增加"))

    def test_brief_prefers_asked_dimension_and_has_only_known_claims(self):
        evidence = cards(self.data)
        brief = research_brief("估值便宜吗",DIMENSIONS,evidence)
        self.assertEqual(brief["focus"][0]["id"],"E8")
        self.assertTrue(all(c in evidence for c in brief["focus"]))

if __name__ == "__main__":
    unittest.main()
