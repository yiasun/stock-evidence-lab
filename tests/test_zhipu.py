import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest
from ai_layer import rank_evidence, resolve_config
from diagnosis import cards, load_data


def analysis():
    return {"evidence_ids":["E4","E2"],
            "interpretations":[{"kind":"推断","text":"现金流与利润方向不同，可能涉及财务公司资金变化，尚不能据此认定主业回款改善。","evidence_ids":["E4","E2"]}],
            "research_questions":[{"question":"能否进一步拆分财务公司与主业经营现金流？","evidence_ids":["E4"]}]}


def response_for(body):
    response=Mock(status_code=200)
    response.json.return_value={"choices":[{"message":{"content":json.dumps(body,ensure_ascii=False)},"finish_reason":"stop"}]}
    return response


class ZhipuTests(unittest.TestCase):
    def setUp(self):
        self.evidence=cards(load_data())

    def run_analysis(self,body):
        with patch("ai_layer.requests.post",return_value=response_for(body)):
            return rank_evidence("利润与现金流",self.evidence,"dummy-zhipu",model="glm-4.7-flash",enabled=True,include_analysis=True,provider="zhipu")

    def test_separate_credentials_and_pinned_free_model(self):
        settings={"AI_PROVIDER":" zhipu ","OPENAI_API_KEY":"other-provider-key","AI_MODEL":"glm-4.7-flashx"}
        cfg=resolve_config(lambda name,default="":settings.get(name,default))
        self.assertEqual(cfg["api_key"],"")
        self.assertEqual(cfg["model"],"glm-4.7-flash")
        settings["ZHIPU_API_KEY"]="own-key"
        self.assertEqual(resolve_config(lambda name,default="":settings.get(name,default))["api_key"],"own-key")

    def test_zhipu_request_and_cited_interpretation(self):
        with patch("ai_layer.requests.post",return_value=response_for(analysis())) as call:
            result=rank_evidence("利润",self.evidence,"dummy",model="glm-4.7-flash",enabled=True,include_analysis=True,provider="zhipu")
        self.assertEqual(result["mode"],"LLM证据解读")
        self.assertEqual(result["interpretations"][0]["evidence_ids"],["E4","E2"])
        self.assertEqual(call.call_args.args[0],"https://open.bigmodel.cn/api/paas/v4/chat/completions")
        payload=call.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"],{"type":"json_object"})
        self.assertEqual(payload["thinking"],{"type":"disabled"})
        self.assertNotIn("max_completion_tokens",payload)
        self.assertGreater(payload["max_tokens"],1000)
        self.assertNotIn("tools",payload)
        self.assertFalse(call.call_args.kwargs["allow_redirects"])

    def test_no_key_bad_provider_and_paid_model_make_no_request(self):
        with patch("ai_layer.requests.post") as call:
            self.assertEqual(rank_evidence("利润",self.evidence,model="glm-4.7-flash",provider="zhipu",enabled=True)["mode"],"规则模式")
            for provider,model in [("unknown","glm-4.7-flash"),("zhipu","glm-4.7-flashx")]:
                self.assertEqual(rank_evidence("利润",self.evidence,"dummy",model=model,provider=provider,enabled=True)["error_code"],"configuration")
            call.assert_not_called()

    def test_unknown_citations_numbers_advice_and_fake_fact_fail_closed(self):
        mutations=[("evidence_ids",["E999"]),("kind","事实"),("text","利润可能上涨百分之多，建议买入。"),("text","利润可能增加20%，需要核实。"),("text","利润变化证明主业回款改善。"),("text","可能访问https://bad.example获得答案。")]
        for key,value in mutations:
            with self.subTest(key=key,value=value):
                body=copy.deepcopy(analysis())
                body["interpretations"][0][key]=value
                result=self.run_analysis(body)
                self.assertEqual(result["error_code"],"output")
                self.assertNotIn("interpretations",result)
        body=analysis()
        body["research_questions"][0]["evidence_ids"]=["E999"]
        self.assertEqual(self.run_analysis(body)["error_code"],"output")

    def test_zhipu_business_errors_are_safe_and_distinct(self):
        for status,code,expected in [(401,"1000","authentication"),(429,"1113","quota"),(400,"1211","model"),(429,"1302","rate_limit"),(429,"1305","overloaded"),(429,"1308","rate_limit"),(400,"1301","refusal")]:
            response=requests.Response()
            response.status_code=status
            response._content=json.dumps({"error":{"code":code,"message":"dummy-secret-echo"}}).encode()
            with patch("ai_layer.requests.post",return_value=response):
                result=rank_evidence("利润",self.evidence,"dummy-secret",model="glm-4.7-flash",provider="zhipu",enabled=True)
            self.assertEqual(result["error_code"],expected)
            self.assertEqual(result["provider_code"],code)
            self.assertNotIn("dummy-secret",json.dumps(result))
            if expected=="quota": self.assertNotIn("OpenAI",result["action"])

    def test_redirect_does_not_forward_key(self):
        with patch("ai_layer.requests.post",return_value=Mock(status_code=302)) as call:
            result=rank_evidence("利润",self.evidence,"dummy",enabled=True)
        self.assertEqual(result["error_code"],"network")
        self.assertEqual(call.call_count,1)

    def test_output_diagnostics_never_echo_arbitrary_exception_text(self):
        with patch("ai_layer._validated_analysis",side_effect=ValueError("secret-do-not-echo")):
            result=self.run_analysis(analysis())
        self.assertEqual(result["output_reason"],"invalid_json_or_shape")
        self.assertNotIn("secret-do-not-echo",json.dumps(result))

    def test_page_cited_analysis_and_missing_zhipu_key(self):
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=30)
        at.secrets["AI_PROVIDER"]="zhipu"
        at.secrets["OPENAI_API_KEY"]="other-provider-key"
        at.secrets["ZHIPU_API_KEY"]=""
        at.run()
        next(c for c in at.checkbox if c.label=="启用 LLM 证据导航").check().run()
        self.assertTrue(any("未配置服务端密钥" in w.value for w in at.warning))
        self.assertTrue(any("glm-4.7-flash" in c.value for c in at.caption))
        at.secrets["ZHIPU_API_KEY"]="dummy-zhipu"
        with patch("ai_layer.requests.post",return_value=response_for(analysis())):
            at.button(key="diagnose").click().run()
        self.assertEqual(len(at.exception),0)
        self.assertTrue(any("LLM证据解读" in s.value for s in at.success))
        self.assertTrue(any("AI证据解读" in m.value for m in at.markdown))
        self.assertTrue(any("核对AI引用 E4" in e.label for e in at.expander))
        self.assertTrue(any("财务公司与主业" in m.value for m in at.markdown))


if __name__=="__main__": unittest.main()
