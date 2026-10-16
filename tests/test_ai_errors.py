import json
import unittest
from unittest.mock import Mock,patch
import requests
from ai_layer import rank_evidence
from diagnosis import cards,load_data

class APIErrorsTests(unittest.TestCase):
    def setUp(self):
        self.evidence=cards(load_data())

    def test_http_errors_are_actionable_and_never_echo_key(self):
        for status,code,expected in [(401,"invalid_api_key","authentication"),(403,"permission_denied","permission"),(404,"model_not_found","model"),(429,"insufficient_quota","quota"),(429,"rate_limit_exceeded","rate_limit"),(400,"invalid_parameter","request"),(503,"server_error","server")]:
            response=requests.Response()
            response.status_code=status
            response._content=json.dumps({"error":{"code":code,"message":"sk-secret-do-not-display"}}).encode()
            response.raise_for_status=Mock(side_effect=requests.HTTPError("sk-secret-do-not-display",response=response))
            with patch("ai_layer.requests.post",return_value=response):
                result=rank_evidence("利润",self.evidence,"sk-secret-do-not-display",enabled=True)
                self.assertEqual(result["error_code"],expected)
                self.assertEqual(result["http_status"],status)
                self.assertNotIn("sk-secret",json.dumps(result))
                self.assertTrue(result["action"])

    def test_timeout_and_network_are_distinct(self):
        for exc,expected in [(requests.Timeout,"timeout"),(requests.ConnectionError,"network")]:
            with patch("ai_layer.requests.post",side_effect=exc):
                self.assertEqual(rank_evidence("利润",self.evidence,"dummy",enabled=True)["error_code"],expected)

    def test_quota_codes_and_quota_type_are_not_transient_rate_limits(self):
        for code in ["credit_balance_exhausted","project_spend_limit_exceeded","organization_spend_limit_exceeded","organization_usage_limit_exceeded",None]:
            response=requests.Response()
            response.status_code=429
            response._content=json.dumps({"error":{"code":code,"type":"insufficient_quota","message":"secret"}}).encode()
            with patch("ai_layer.requests.post",return_value=response):
                result=rank_evidence("利润",self.evidence,"dummy",enabled=True)
                self.assertEqual(result["error_code"],"quota")
                self.assertNotIn("secret",json.dumps(result))

    def test_key_whitespace_is_removed_without_exposing_it(self):
        response=Mock()
        response.json.return_value={"choices":[{"message":{"content":'{"evidence_ids":["E1"]}'}}]}
        with patch("ai_layer.requests.post",return_value=response) as call:
            result=rank_evidence("利润",self.evidence,"  dummy\n",enabled=True)
            self.assertEqual(call.call_args.kwargs["headers"]["Authorization"],"Bearer dummy")
            self.assertEqual(result["mode"],"LLM证据导航")

    def test_schema_constrains_citations_to_supplied_evidence(self):
        with patch("ai_layer.requests.post",side_effect=requests.Timeout) as call:
            rank_evidence("利润",self.evidence[:2],"dummy",enabled=True)
            fmt=call.call_args.kwargs["json"]["response_format"]
            self.assertTrue(fmt["json_schema"]["strict"])
            self.assertEqual(fmt["json_schema"]["schema"]["properties"]["evidence_ids"]["items"]["enum"],["E1","E2"])

    def test_refusal_is_not_success(self):
        response=Mock()
        response.json.return_value={"choices":[{"message":{"refusal":"拒绝","content":None}}]}
        with patch("ai_layer.requests.post",return_value=response):
            self.assertEqual(rank_evidence("利润",self.evidence,"dummy",enabled=True)["error_code"],"refusal")

if __name__=="__main__": unittest.main()
