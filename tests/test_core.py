import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import requests
from diagnosis import *
from ai_layer import rank_evidence

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = load_data()
        self.evidence = cards(self.data)

    def test_recomputed_financial_numbers(self):
        m = metrics(self.data)
        self.assertAlmostEqual(m["revenue_growth"], 1.469869, places=5)
        self.assertAlmostEqual(m["profit_growth"], -1.951595, places=5)
        self.assertAlmostEqual(m["cashflow_growth"], 438.840013, places=5)
        self.assertAlmostEqual(m["gross_margin"], 89.555213, places=5)

    def test_zero_or_negative_growth_base(self):
        self.assertIsNone(growth(1, 0))
        self.assertIsNone(growth(1, -1))

    def test_missing_and_nonfinite_fields_fail_closed(self):
        for value in [None, float("nan"), float("inf")]:
            bad = copy.deepcopy(self.data)
            bad["financials"][0]["revenue"] = value
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "evidence.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_data(path)

    def test_period_mismatch(self):
        bad = copy.deepcopy(self.data)
        bad["financials"][0]["period"] = "2025FY"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_data(path)

    def test_sources_and_opposing_evidence(self):
        self.assertEqual(len({c["id"] for c in self.evidence}), len(self.evidence))
        self.assertEqual({c["direction"] for c in self.evidence}, {"正面", "负面", "矛盾", "中性", "未知"})
        for c in self.evidence:
            if c["kind"] != "未知":
                self.assertIn(c["source"], [s["id"] for s in all_sources(self.data)])
        self.assertTrue(self.data["market"]["verified"])

    def test_event_after_financial_period(self):
        self.assertGreater(self.data["event"]["disclosed_at"], self.data["financials"][-1]["end"])

    def test_dimensions_and_unknown_question(self):
        self.assertIn("估值", select_dimensions("现在便宜吗？"))
        self.assertIn("经营质量", select_dimensions("估值"))
        self.assertEqual(select_dimensions("你好"), DIMENSIONS)

    def test_trade_request_boundary(self):
        for question in ["该买吗", "给我目标价", "稳赚翻倍", "buy now"]:
            self.assertTrue(is_trade_request(question))

    def test_no_key_never_calls_network(self):
        with patch("ai_layer.requests.post") as call:
            self.assertEqual(rank_evidence("利润", self.evidence, enabled=True)["mode"], "规则模式")
            call.assert_not_called()

    def test_interface_failures_are_labelled(self):
        with patch("ai_layer.requests.post", side_effect=requests.Timeout):
            result = rank_evidence("利润", self.evidence, "dummy", enabled=True)
            self.assertEqual(result["mode"], "规则回退")

    def test_malformed_and_hallucinated_ai_references(self):
        for content in ["bad json", '{"evidence_ids":["E999"]}', '{"evidence_ids":[]}', '{"evidence_ids":[["E1"]]}']:
            response = Mock()
            response.json.return_value = {"choices":[{"message":{"content":content}}]}
            with patch("ai_layer.requests.post", return_value=response):
                self.assertEqual(rank_evidence("利润", self.evidence, "dummy", enabled=True)["mode"], "规则回退")

    def test_successful_ai_selection_has_no_free_prose(self):
        response = Mock()
        response.json.return_value = {"choices":[{"message":{"content":'{"evidence_ids":["E2","E1","E2"],"advice":"买入"}'}}]}
        with patch("ai_layer.requests.post", return_value=response):
            result = rank_evidence("利润", self.evidence, "dummy", enabled=True)
            self.assertEqual(result["ids"], ["E2", "E1"])
            self.assertNotIn("advice", result)

    def test_market_return_drawdown(self):
        frame = validate_market("date,close,volume\n2025-01-01,100,1\n2025-01-02,80,2\n2025-01-03,110,3\n")
        m = market_metrics(frame)
        self.assertAlmostEqual(m["return_pct"], 10)
        self.assertAlmostEqual(m["max_drawdown_pct"], -20)

    def test_market_bad_inputs(self):
        for content in ["date,close\n2025-01-01,10", "date,close,volume\n2025-01-01,10,1", "date,close,volume\n2025-01-01,0,1\n2025-01-02,2,2", "date,close,volume\n2025-01-01,10,1\n2025-01-01,2,2", "date,close,volume\n2099-01-01,10,1\n2099-01-02,2,2", "date,close,volume\n2025-01-01,NaN,1\n2025-01-02,2,2", "date,close,volume\n2025-01-01,10,-1\n2025-01-02,2,2"]:
            with self.assertRaises(ValueError, msg=content):
                validate_market(content)

    def test_staleness_is_explicit(self):
        self.assertIn("108", staleness(self.data, date(2026,10,16)))

if __name__ == "__main__":
    unittest.main()
