"""Regression checks for locale integrity, offline onboarding and review continuity."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from diagnosis import load_data, cards, all_sources, select_dimensions, is_trade_request, english_dimensions, DIMENSIONS
from presentation import english_cards, card_view, source_view, canonical_label, label
from research_export import to_markdown

ROOT = Path(__file__).resolve().parents[1]


class InternationalExperienceTests(unittest.TestCase):
    def app(self, english=False):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.secrets["AI_PROVIDER"] = "openai"
        at.secrets["OPENAI_API_KEY"] = ""
        if english:
            at.query_params["lang"] = "en"
        return at

    def test_translations_preserve_canonical_ids_sources_fields_and_data(self):
        data = load_data()
        before = copy.deepcopy(data)
        evidence = cards(data)
        original = copy.deepcopy(evidence)
        translations = english_cards(data)
        self.assertEqual(set(translations), {c["id"] for c in evidence})
        for card in evidence:
            view = card_view(card, translations, "en")
            for key in ["id", "source", "sources", "fields", "kind", "dimension"]:
                self.assertEqual(view.get(key), card.get(key))
            self.assertTrue(all(view[k] for k in ["title", "body", "formula", "next_step"]))
        for source in all_sources(data):
            view = source_view(source, "en")
            for key in ["id", "url", "sha256", "original_url", "disclosed_at"]:
                self.assertEqual(view.get(key), source.get(key))
        self.assertEqual(data, before)
        self.assertEqual(evidence, original)
        self.assertIn("+1.47%", translations["E1"]["body"])
        self.assertIn("-1.95%", translations["E2"]["body"])
        self.assertIn("+438.84%", translations["E3"]["body"])
        self.assertIn("does not establish", translations["E4"]["body"])

    def test_english_scope_uses_words_without_accidental_pe_matches(self):
        for question in ["cash flow quality", "operating cash flow"]:
            self.assertNotIn("估值", select_dimensions(question))
        self.assertEqual(english_dimensions("type of business"), [])
        self.assertEqual(select_dimensions("type of business"), DIMENSIONS)
        self.assertEqual(select_dimensions("Is valuation cheap?"), ["经营质量", "估值"])
        self.assertIn("财务趋势", select_dimensions("Why did revenue rise while profit fell?"))
        self.assertIn("重要事件与风险", select_dimensions("price adjustment risk"))
        self.assertIn("估值", select_dimensions("PE(TTM) and PB"))
        self.assertFalse(is_trade_request("cash collected from buyers"))
        self.assertTrue(is_trade_request("Give me a target price"))

    def test_english_onboarding_and_export_are_offline_and_complete_when_filtered(self):
        at = self.app(english=True)
        with patch("ai_layer.requests.post") as network, patch("research_export.to_markdown", wraps=to_markdown) as export:
            at.run()
            at.button(key="diagnose").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(at.title[0].value, "Growth tells only part of the story.")
            self.assertTrue(any("Rule mode" in s.value for s in at.success))
            at.radio(key="evidence_kind").set_value("未知").run()
            record = export.call_args.args[0]
            self.assertNotIn("E4", record["visible_evidence_ids"])
            self.assertIn("E4", [c["id"] for c in record["evidence"]])
            note = to_markdown(record)
            self.assertIn("### E4 · Stronger cash flow", note)
            self.assertIn("PDF p.5", note)
            self.assertIn("not official daily PE/PB", note)
            self.assertIn("## Claim reviews (user-authored)", note)
            network.assert_not_called()

    def test_language_switch_preserves_review_task_and_custom_question(self):
        at = self.app().run()
        at.text_input[0].set_value("现金流拆分需要什么材料？").run()
        next(s for s in at.selectbox if s.label == "人工复核判定").set_value("证据不足")
        next(t for t in at.text_area if t.label.startswith("缺少的材料")).set_value("Need core-business cash collection breakdown.")
        next(b for b in at.button if b.label == "保存本条复核").click().run()
        at.checkbox(key="task_E4").check().run()
        with patch("research_export.to_markdown", wraps=to_markdown) as export:
            at.selectbox(key="language").set_value("English").run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(at.session_state["question"], "现金流拆分需要什么材料？")
            self.assertTrue(at.session_state["task_E4"])
            record = export.call_args.args[0]
            self.assertEqual(record["claim_review"]["history"][0]["validity"], "当前有效")
            self.assertIn("Insufficient evidence", to_markdown(record))
            self.assertIn("Need core-business", to_markdown(record))
            at.selectbox(key="language").set_value("中文").run()
            at.selectbox(key="language").set_value("English").run()
            self.assertEqual(export.call_args.args[0]["claim_review"]["history"][0]["validity"], "当前有效")
            self.assertIn("E4", export.call_args.args[0]["visible_evidence_ids"])
            at.text_input(key="question").set_value("A different research question").run()
            self.assertEqual(export.call_args.args[0]["claim_review"]["history"][0]["validity"], "已失效")

    def test_no_key_english_mode_does_not_claim_ai_success(self):
        at = self.app(english=True).run()
        with patch("ai_layer.requests.post") as network:
            at.checkbox(key="enable_ai").check().run()
            at.button(key="diagnose").click().run()
            self.assertTrue(any("No server API key" in w.value for w in at.warning))
            self.assertTrue(any("Rule mode" in s.value for s in at.success))
            self.assertFalse(any("AI interpretation · Inference" in m.value for m in at.markdown))
            network.assert_not_called()

    def test_previously_formatted_browser_labels_are_normalized_before_filtering(self):
        at = self.app(english=True).run()
        at.session_state["dimensions"] = [label(d, "en") for d in DIMENSIONS]
        at.session_state["evidence_kind"] = "All"
        with patch("research_export.to_markdown", wraps=to_markdown) as export:
            at.run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(export.call_args.args[0]["dimensions"], DIMENSIONS)
            self.assertEqual(len(export.call_args.args[0]["visible_evidence_ids"]), 12)
        self.assertEqual(canonical_label("Insufficient evidence"), "证据不足")


if __name__ == "__main__":
    unittest.main()
