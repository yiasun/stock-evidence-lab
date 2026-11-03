"""User-authored claim reviews; a saved judgement is not a verified fact."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

REVIEW_SCHEMA_VERSION = "0.1"
STATUSES = ["支持", "部分支持", "不支持", "证据不足"]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def review_context(question, dimensions, data, mode, provider, model, policy):
    return fingerprint({"question": question, "dimensions": sorted(dimensions),
                        "data": data, "mode": mode, "provider": provider,
                        "model": model, "policy": policy})


def build_claims(evidence, interpretations, context):
    claims = []
    entries = [("本地推断卡", c["body"], [c["id"]]) for c in evidence if c["kind"] == "推断"]
    entries += [("AI推断", c["text"], c["evidence_ids"]) for c in interpretations]
    for origin, text, refs in entries:
        refs = sorted(set(refs))
        content = {"context": context, "origin": origin, "text": text, "evidence_ids": refs}
        claim_id = fingerprint(content)
        if not any(c["claim_id"] == claim_id for c in claims):
            claims.append({"claim_id": claim_id, "content_fingerprint": claim_id,
                           "origin": origin, "text": text, "evidence_ids": refs})
    return claims


def create_review(claim, status, basis, missing_material, evidence, sources, now=None):
    if status not in STATUSES:
        raise ValueError("请选择有效的人工复核判定。")
    allowed = {c["id"]: c for c in evidence}
    source_ids = {s["id"] for s in sources}
    if not isinstance(basis, list):
        raise ValueError("复核依据格式无效。")
    checked = []
    for entry in basis:
        if not isinstance(entry, dict):
            raise ValueError("复核依据格式无效。")
        eid, sid = entry.get("evidence_id"), entry.get("source_id")
        card = allowed.get(eid)
        if eid not in claim["evidence_ids"] or not card or sid not in source_ids or sid not in card.get("sources", [card.get("source")]):
            raise ValueError("复核依据必须来自本条主张实际引用的证据及其来源。")
        locator, note = entry.get("locator"), entry.get("note")
        if not isinstance(locator, str) or not 1 <= len(locator.strip()) <= 300 or not isinstance(note, str) or not 1 <= len(note.strip()) <= 1000:
            raise ValueError("请填写原文定位及复核说明。")
        checked.append({"evidence_id": eid, "source_id": sid,
                        "locator": locator.strip(), "note": note.strip()})
    missing = missing_material.strip() if isinstance(missing_material, str) else ""
    if len(missing) > 1000:
        raise ValueError("缺少的材料说明不能超过1000字。")
    if status == "证据不足":
        if not missing:
            raise ValueError("判为证据不足时，请说明缺少哪些材料。")
    elif not checked:
        raise ValueError("支持、部分支持或不支持的判定，需要引用依据、原文定位及说明。")
    return {"review_schema_version": REVIEW_SCHEMA_VERSION, "review_id": str(uuid4()),
            **copy.deepcopy(claim), "status": status, "basis": checked,
            "missing_material": missing, "review_origin": "user_manual",
            "reviewed_at": now or datetime.now(timezone.utc).isoformat()}


def review_snapshot(claims, history):
    latest = {r["claim_id"]: i for i, r in enumerate(history)}
    current_ids = {c["claim_id"] for c in claims}
    current = []
    for claim in claims:
        index = latest.get(claim["claim_id"])
        current.append({**copy.deepcopy(claim),
                        "review": copy.deepcopy(history[index]) if index is not None else None,
                        "status": history[index]["status"] if index is not None else "待复核"})
    historical = []
    for i, review in enumerate(history):
        validity = "已失效" if review["claim_id"] not in current_ids else "当前有效" if latest[review["claim_id"]] == i else "历史记录"
        historical.append({**copy.deepcopy(review), "validity": validity})
    return {"review_schema_version": REVIEW_SCHEMA_VERSION, "claims": current, "history": historical}
