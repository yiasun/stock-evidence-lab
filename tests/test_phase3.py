import json
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from streamlit.testing.v1 import AppTest
from ai_layer import _validated_analysis, _without_declared_citations
from diagnosis import cards,load_data
from research_export import to_markdown
from request_gate import request_identity
from tools.evaluate_analysis import evaluate


class SubmissionTests(unittest.TestCase):
    def test_curated_validator_regression(self):
        result=evaluate()
        self.assertEqual(result["model_calls"],0)
        for case in result["cases"]:
            with self.subTest(case=case["id"]): self.assertTrue(case["passed"])

    def test_bad_event_paragraph_is_withheld_without_losing_valid_analysis(self):
        raw={"interpretations":[
            {"kind":"推断","text":"调价可能影响后续业绩，尚需期后数据才能判断。","evidence_ids":["E6","E7"]},
            {"kind":"推断","text":"调价影响可能有限，需核实资金变化。","evidence_ids":["E4"]}],
            "research_questions":[{"question":"调价后销量与库存如何变化？","evidence_ids":["E6","E7"]}]}
        interpretations,questions,checks=_validated_analysis(raw,cards(load_data()))
        self.assertEqual(len(interpretations),1)
        self.assertEqual(checks,{"withheld_count":1,"reasons":["event_grounding"]})
        self.assertNotIn("有限",interpretations[0]["text"])

    def test_policy_changes_invalidate_cached_analysis(self):
        args=("zhipu","glm-4.7-flash","dummy","调价",cards(load_data()),True)
        old=request_identity(*args,policy_version="old")
        new=request_identity(*args,policy_version="new")
        self.assertEqual(old[0],new[0])
        self.assertNotEqual(old[1],new[1])

    def test_declared_citation_formatting_does_not_hide_financial_numbers(self):
        text="现金流变化尚不能证明主业改善。[E3 / E4]"
        cleaned=_without_declared_citations(text,["E3","E4"])
        self.assertEqual(cleaned,"现金流变化尚不能证明主业改善。")
        self.assertIn("20%",_without_declared_citations("利润可能增加20%，尚需核实。[E2]",["E2"]))
        self.assertIn("E999",_without_declared_citations("尚需核对[E999]",["E2"]))

    def test_readable_export_keeps_ai_citations_when_visual_filter_hides_cards(self):
        response=Mock(status_code=200)
        response.json.return_value={"choices":[{"message":{"content":json.dumps({
            "evidence_ids":["E4"],"interpretations":[{"kind":"推断","text":"现金流增强尚不能认定主业经营质量改善，需要核对资金变化。","evidence_ids":["E4"]}],
            "research_questions":[{"question":"财务公司资金变化具体来自何处？","evidence_ids":["E4"]}]},ensure_ascii=False)}}]}
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=30)
        at.secrets["AI_PROVIDER"]="openai"
        at.secrets["OPENAI_API_KEY"]="dummy-phase3"
        with patch("research_export.to_markdown",wraps=to_markdown) as export:
            at.run()
            next(c for c in at.checkbox if c.label=="启用 AI 证据解读").check().run()
            with patch("ai_layer.requests.post",return_value=response):
                at.button(key="diagnose").click().run()
            next(r for r in at.radio if r.label=="证据类型").set_value("未知").run()
            record=export.call_args.args[0]
            self.assertEqual(len(at.exception),0)
            self.assertNotIn("E4",record["visible_evidence_ids"])
            self.assertIn("E4",[c["id"] for c in record["evidence"]])
            note=to_markdown(record)
            self.assertIn("### E4",note)
            self.assertIn("AI解读（分析推断）",note)
            self.assertIn("https://static.cninfo.com.cn",note)
            self.assertNotIn("dummy-phase3",note)


if __name__=="__main__": unittest.main()
