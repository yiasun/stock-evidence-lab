import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from diagnosis import cards, load_data, all_sources, DIMENSIONS
from review_records import review_context, build_claims, create_review, review_snapshot
from research_export import to_markdown


class ReviewRecordsTests(unittest.TestCase):
    def setUp(self):
        self.data = load_data()
        self.cards = cards(self.data)
        self.sources = all_sources(self.data)
        self.context = review_context("现金流为何增加", DIMENSIONS, self.data, "rules", "rules", "", "policy")
        self.claims = build_claims(self.cards, [], self.context)
        self.claim = next(c for c in self.claims if c["evidence_ids"] == ["E4"])
        self.basis = [{"evidence_id": "E4", "source_id": "S1", "locator": "第7页现金流说明", "note": "合并口径包括财务公司资金变化。"}]

    def save(self, status="部分支持", basis=None, missing=""):
        return create_review(self.claim, status, self.basis if basis is None else basis,
                             missing, self.cards, self.sources, now="2026-10-27T06:00:00+00:00")

    def test_pending_is_not_automatically_verified(self):
        snapshot = review_snapshot(self.claims, [])
        self.assertTrue(all(c["status"] == "待复核" and c["review"] is None for c in snapshot["claims"]))

    def test_support_requires_locator_note_and_a_real_cited_source(self):
        for basis in [[], [{**self.basis[0], "locator": " "}], [{**self.basis[0], "note": ""}],
                      [{**self.basis[0], "source_id": "S5"}], [{**self.basis[0], "evidence_id": "E6"}]]:
            with self.subTest(basis=basis), self.assertRaises(ValueError):
                self.save(basis=basis)
        self.assertEqual(self.save()["review_origin"], "user_manual")

    def test_insufficient_evidence_requires_missing_material_not_fabricated_locator(self):
        with self.assertRaises(ValueError):
            self.save("证据不足", [], " ")
        result = self.save("证据不足", [], "需要主业销售收现与财务公司资金的拆分披露。")
        self.assertEqual(result["basis"], [])
        self.assertEqual(result["status"], "证据不足")

    def test_meaningful_context_changes_invalidate_but_order_does_not(self):
        args = ["现金流为何增加", DIMENSIONS, self.data, "rules", "rules", "", "policy"]
        self.assertEqual(self.context, review_context(*[args[0], list(reversed(DIMENSIONS)), *args[2:]]))
        for index, value in [(0, "另一个问题"), (1, DIMENSIONS[:2]), (2, {**self.data, "dataset_version": "changed"}),
                             (3, "LLM"), (4, "zhipu"), (5, "different-model"), (6, "new-policy")]:
            changed = args.copy()
            changed[index] = value
            claims = build_claims(self.cards, [], review_context(*changed))
            result = review_snapshot(claims, [self.save()])
            with self.subTest(index=index):
                self.assertEqual(result["history"][0]["validity"], "已失效")
                self.assertTrue(all(c["status"] == "待复核" for c in result["claims"]))

    def test_changed_interpretation_cannot_inherit_an_old_judgement(self):
        first = build_claims(self.cards, [{"text": "现有材料尚不足以判断主业改善。", "evidence_ids": ["E4"]}], self.context)
        ai = next(c for c in first if c["origin"] == "AI推断")
        saved = create_review(ai, "证据不足", [], "缺少主业拆分", self.cards, self.sources)
        changed = build_claims(self.cards, [{"text": "主业可能已改善但需核对。", "evidence_ids": ["E4"]}], self.context)
        result = review_snapshot(changed, [saved])
        self.assertEqual(result["history"][0]["validity"], "已失效")

    def test_revisions_keep_history_and_return_detached_copies(self):
        old = self.save()
        new = self.save("不支持")
        history = [old, new]
        result = review_snapshot(self.claims, history)
        self.assertEqual([r["validity"] for r in result["history"]], ["历史记录", "当前有效"])
        selected = next(c for c in result["claims"] if c["claim_id"] == self.claim["claim_id"])
        self.assertEqual(selected["status"], "不支持")
        selected["review"]["basis"][0]["note"] = "changed"
        self.assertNotEqual(new["basis"][0]["note"], "changed")

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            self.save("系统认证正确")


class ReviewPageTests(unittest.TestCase):
    def app(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
        at.secrets["AI_PROVIDER"] = "openai"
        return at.run()

    def test_review_save_exports_and_question_change_marks_history_stale(self):
        at = self.app()
        self.assertEqual(len(at.exception), 0)
        next(s for s in at.selectbox if s.label == "人工复核判定").set_value("证据不足")
        next(t for t in at.text_area if t.label.startswith("缺少的材料")).set_value("还需要主业销售收现拆分披露。")
        next(b for b in at.button if b.label == "保存本条复核").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.session_state["claim_review_history"]), 1)
        with patch("research_export.to_markdown", wraps=to_markdown) as export:
            at.run()
            record = export.call_args.args[0]
            self.assertTrue(any(c["status"] == "证据不足" for c in record["claim_review"]["claims"]))
            self.assertIn("主张复核（用户人工意见）", to_markdown(record))
            next(t for t in at.text_input if t.label == "你想了解贵州茅台的什么？").set_value("调价影响如何？").run()
            record = export.call_args.args[0]
            self.assertEqual(record["claim_review"]["history"][0]["validity"], "已失效")
            self.assertIn("已失效", to_markdown(record))
        self.assertEqual(len(at.exception), 0)

    def test_missing_basis_does_not_create_review(self):
        at = self.app()
        next(b for b in at.button if b.label == "保存本条复核").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["claim_review_history"], [])
        self.assertTrue(any("需要引用依据" in e.value for e in at.error))

    def test_ai_review_remains_available_when_visual_filter_hides_the_cited_card(self):
        at = self.app()
        at.secrets["OPENAI_API_KEY"] = "dummy-review"
        next(c for c in at.checkbox if c.label == "启用 AI 证据解读").check().run()
        response = Mock(status_code=200)
        response.json.return_value = {"choices": [{"message": {"content": json.dumps({
            "evidence_ids": ["E4"], "interpretations": [{"kind": "推断", "text": "现金流增强尚不能认定主业改善，需核对资金变化。", "evidence_ids": ["E4"]}],
            "research_questions": [{"question": "还需补哪些资金拆分披露？", "evidence_ids": ["E4"]}]}, ensure_ascii=False)}}]}
        with patch("ai_layer.requests.post", return_value=response):
            at.button(key="diagnose").click().run()
        next(r for r in at.radio if r.label == "证据类型").set_value("未知").run()
        self.assertEqual(len(at.exception), 0)
        choices = next(s for s in at.selectbox if s.label == "选择待复核主张").options
        self.assertTrue(any("AI推断" in c for c in choices))
