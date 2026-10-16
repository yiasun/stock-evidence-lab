import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppFlowTests(unittest.TestCase):
    def test_main_flow_and_missing_api_key(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
        at.secrets["OPENAI_API_KEY"] = ""
        at.run()
        self.assertEqual(len(at.exception), 0)
        at.button(key="diagnose").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("规则模式" in s.value for s in at.success))
        at.text_input[0].set_value("给我目标价，应该买入吗").run()
        self.assertTrue(any("交易决策意图" in i.value for i in at.info))
        next(c for c in at.checkbox if c.label == "启用 LLM 证据导航").check().run()
        self.assertTrue(any("未配置" in w.value for w in at.warning))
        next(c for c in at.checkbox if c.label == "查看继承行情（待核验样本）").check().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("样本区间价格变化" == m.label for m in at.metric))

    def test_empty_question_and_scope(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        at.text_input[0].set_value("")
        at.multiselect[0].set_value([])
        at.button(key="diagnose").click().run()
        self.assertTrue(any("至少选择" in e.value for e in at.error))
        self.assertEqual(len(at.exception),0)

    def test_recommended_dimensions_and_stale_result(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        at.text_input[0].set_value("当前估值便宜吗？").run()
        at.button(key="use_recommended").click().run()
        self.assertEqual(at.multiselect[0].value,["经营质量","估值"])
        at.button(key="diagnose").click().run()
        self.assertTrue(any("PE(TTM)" in m.value for m in at.markdown))
        at.multiselect[0].set_value(["行业位置"]).run()
        self.assertTrue(any("运行模式已改变" in i.value for i in at.info))
        self.assertEqual(len(at.exception),0)

    def test_research_checklist_persists_through_rerun(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        at.checkbox(key="task_E8").check().run()
        self.assertTrue(at.session_state["task_E8"])
        at.button(key="diagnose").click().run()
        self.assertTrue(at.session_state["task_E8"])
        self.assertEqual(len(at.exception),0)

if __name__ == "__main__":
    unittest.main()
