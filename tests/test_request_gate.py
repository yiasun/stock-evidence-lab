import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import requests
from ai_layer import guarded_rank_evidence
from diagnosis import cards, load_data, select_dimensions
from request_gate import RequestGate, request_identity


class RequestGateTests(unittest.TestCase):
    def setUp(self):
        self.now=100
        self.gate=RequestGate(clock=lambda:self.now)
        self.evidence=cards(load_data())

    def run_request(self,question="利润",evidence=None,key="dummy-gate-key"):
        return guarded_rank_evidence(question,self.evidence if evidence is None else evidence,key,
                                     "glm-4.7-flash",True,provider="zhipu",gate=self.gate)

    def success(self):
        response=Mock(status_code=200)
        response.json.return_value={"choices":[{"message":{"content":'{"evidence_ids":["E1"]}'}}]}
        return response

    def test_duplicate_success_uses_cache_with_correct_invalidation(self):
        with patch("ai_layer.requests.post",return_value=self.success()) as post:
            first=self.run_request()
            second=self.run_request()
            self.assertEqual(post.call_count,1)
            self.assertEqual(first["request_source"],"api")
            self.assertEqual(second["request_source"],"cache")
            second["ids"].append("E999")
            self.assertNotIn("E999",self.run_request()["ids"])
            self.run_request("现金流")
            changed=[dict(c) for c in self.evidence]
            changed[0]["body"]="更新证据"
            self.run_request(evidence=changed)
            self.run_request(key="another-credential")
            self.assertEqual(post.call_count,4)
            self.now+=301
            self.run_request()
            self.assertEqual(post.call_count,5)

    def test_concurrent_sessions_share_one_inflight_request(self):
        started=threading.Event()
        release=threading.Event()
        def delayed(*args,**kwargs):
            started.set()
            self.assertTrue(release.wait(5))
            return self.success()
        with patch("ai_layer.requests.post",side_effect=delayed) as post,ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.run_request)
            try:
                self.assertTrue(started.wait(5))
                blocked=self.run_request("现金流")
                self.assertEqual(blocked["error_code"],"busy")
                self.assertEqual(post.call_count,1)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=5)["mode"],"LLM证据导航")

    def test_rate_limit_cooldown_is_local_and_never_auto_retries(self):
        response=requests.Response()
        response.status_code=429
        response._content=b'{"error":{"code":"1302"}}'
        with patch("ai_layer.requests.post",return_value=response) as post:
            first=self.run_request()
            self.assertEqual(first["provider_code"],"1302")
            self.assertEqual(first["retry_after_seconds"],60)
            second=self.run_request("估值")
            self.assertEqual(second["request_source"],"gate")
            self.assertEqual(second["ids"],[c["id"] for c in self.evidence if c["dimension"] in select_dimensions("估值")])
            self.assertEqual(post.call_count,1)
            self.now+=61
            self.assertEqual(post.call_count,1)
            self.run_request()
            self.assertEqual(post.call_count,2)

    def test_timeout_releases_lock_but_preserves_cooldown(self):
        with patch("ai_layer.requests.post",side_effect=requests.Timeout) as post:
            self.assertEqual(self.run_request()["error_code"],"timeout")
            self.assertEqual(self.run_request()["request_source"],"gate")
            self.assertEqual(post.call_count,1)
        self.now+=61
        with patch("ai_layer.requests.post",return_value=self.success()):
            self.assertEqual(self.run_request()["mode"],"LLM证据导航")

    def test_unexpected_failure_does_not_leave_busy_lock(self):
        with patch("ai_layer.requests.post",side_effect=RuntimeError("test")):
            with self.assertRaises(RuntimeError): self.run_request()
        with patch("ai_layer.requests.post",return_value=self.success()):
            self.assertEqual(self.run_request()["mode"],"LLM证据导航")

    def test_identifiers_do_not_store_keys_or_question_and_cache_is_bounded(self):
        account,request_id=request_identity("zhipu","glm-4.7-flash","sensitive-key","私人问题",self.evidence,True)
        self.assertEqual(len(account),64)
        self.assertEqual(len(request_id),64)
        self.assertNotIn("sensitive-key",account+request_id)
        with patch("ai_layer.requests.post",return_value=self.success()):
            for i in range(70): self.run_request(str(i))
        self.assertEqual(len(self.gate.cache),64)
        self.assertNotIn("dummy-gate-key",json.dumps(list(self.gate.cache)))


if __name__=="__main__": unittest.main()
