"""Process-wide single-flight requests, bounded success cache and backoff.

Only hashes identify credentials and requests. Keys and question text are not
stored here. This coordinates this app process, not other API clients.
"""
import copy
import hashlib
import json
import math
import threading
import time
from collections import OrderedDict


class RequestGate:
    def __init__(self, clock=time.monotonic, cooldown=60, cache_ttl=300):
        self.clock=clock
        self.cooldown=cooldown
        self.cache_ttl=cache_ttl
        self.lock=threading.Lock()
        self.busy=set()
        self.blocked={}
        self.cache=OrderedDict()

    def run(self, account, request_id, invoke, fallback):
        with self.lock:
            now=self.clock()
            for key in list(self.cache):
                if self.cache[key][0] <= now:
                    del self.cache[key]
            for key in list(self.blocked):
                if self.blocked[key][0] <= now:
                    del self.blocked[key]
            cached=self.cache.get((account,request_id))
            if cached:
                result=copy.deepcopy(cached[1])
                result["request_source"]="cache"
                return result
            if account in self.busy:
                return {**fallback("busy"),"request_source":"gate"}
            if account in self.blocked:
                until,previous=self.blocked[account]
                result=copy.deepcopy(previous)
                seconds=max(1,math.ceil(until-now))
                result.update(request_source="gate",retry_after_seconds=seconds,
                              action=f"本应用正在限流冷却，请至少等待{seconds}秒后手动重试。期间不会向API发起请求；持续限流需检查智谱控制台的模型速率上限。")
                return result
            self.busy.add(account)
        try:
            result=invoke()
            result["request_source"]="api"
            with self.lock:
                if result.get("mode") in ("LLM证据解读","LLM证据导航"):
                    self.cache[(account,request_id)]=(self.clock()+self.cache_ttl,copy.deepcopy(result))
                    while len(self.cache)>64:
                        self.cache.popitem(last=False)
                elif result.get("error_code") in ("rate_limit","timeout"):
                    result["retry_after_seconds"]=self.cooldown
                    result["action"] += f" 本应用已启用{self.cooldown}秒冷却，冷却期间重复生成不会再次请求API。"
                    self.blocked[account]=(self.clock()+self.cooldown,copy.deepcopy(result))
                    while len(self.blocked)>64:
                        self.blocked.pop(next(iter(self.blocked)))
            return result
        finally:
            with self.lock:
                self.busy.discard(account)


SHARED_GATE=RequestGate()


def request_identity(provider, model, api_key, question, evidence, include_analysis):
    account=hashlib.sha256((provider+":"+api_key.strip()).encode()).hexdigest()
    payload=json.dumps([model,question,evidence,include_analysis],ensure_ascii=False,sort_keys=True)
    return account,hashlib.sha256(payload.encode()).hexdigest()
