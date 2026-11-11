"""Human-readable research notes from the same record as the JSON export."""


def to_markdown(record):
    if record.get("language") == "en":
        return to_english_markdown(record)
    lines=["# 证据镜 · 研究记录", "", f"研究问题：{record['question']}",
           f"标的：{record['company']}  |  模式：{record['mode']}",
           f"数据版本：{record['dataset_version']}  |  核验：{record['verified_at']}",
           "", "> 冻结证据研究记录。事实、推断与未知分别标记；不提供交易建议。", "",
           "## 研究范围", "", " / ".join(record["dimensions"])]
    if record.get("ai_interpretations"):
        lines += ["", "## AI解读（分析推断）", "", f"实际模型：{record['ai_model']}",
                  "引用有效不代表因果已证实，请核对原始披露。"]
        checks=record.get("analysis_checks",{})
        if checks.get("withheld_count"):
            lines += [f"已隐藏 {checks['withheld_count']} 项未通过校验的内容。"]
        for item in record["ai_interpretations"]:
            lines += ["",item["text"],"引用："+" / ".join(item["evidence_ids"])]
        lines += ["", "### AI建议继续验证", ""]
        for item in record.get("ai_research_questions",[]):
            lines += ["- "+item["question"]+"（"+" / ".join(item["evidence_ids"])+"）"]
    lines += ["", "## 证据记录", ""]
    for card in record["evidence"]:
        lines += [f"### {card['id']} · {card['title']}", "",
                  f"{card['dimension']} / {card['kind']} / {card['direction']}证据", "",
                  card["body"], "", "口径："+card["formula"], "",
                  "来源："+" / ".join(card.get("sources",[card["source"]])) if card["source"] else "来源：证据不足，保持未知。",
                  "", "下一步："+card["next_step"], ""]
    lines += ["## 原始来源", ""]
    for source in record["sources"]:
        lines += [f"- [{source['id']} · {source['title']}]({source['url']})：{source['locator']}"]
    lines += ["", "## 研究任务状态", ""]
    for task in record["research_tasks"]:
        mark="x" if task["status"] == "用户已核对" else " "
        lines += [f"- [{mark}] {task['evidence_id']} · {task['task']}"]
    if record.get("claim_review"):
        lines += ["", "## 主张复核（用户人工意见）", "", "复核判定不构成系统自动事实认证；问题、范围、证据、模型输出或策略变化后可能失效。", ""]
        for claim in record["claim_review"]["claims"]:
            lines += ["### " + claim["origin"] + " · " + claim["status"], "", claim["text"],
                      "引用：" + " / ".join(claim["evidence_ids"])]
            review = claim.get("review")
            if review:
                lines += ["人工复核时间：" + review["reviewed_at"]]
                for basis in review["basis"]:
                    lines += [f"- 依据：{basis['evidence_id']} / {basis['source_id']}；定位：{basis['locator']}；说明：{basis['note']}"]
                if review["missing_material"]:
                    lines += ["缺少材料：" + review["missing_material"]]
            lines += [""]
        if record["claim_review"]["history"]:
            lines += ["### 复核历史", ""]
            for review in record["claim_review"]["history"]:
                lines += [f"- {review['validity']} · {review['status']} · {review['reviewed_at']}：{review['text']}"]
                for basis in review["basis"]:
                    lines += [f"  依据：{basis['evidence_id']} / {basis['source_id']}；定位：{basis['locator']}；说明：{basis['note']}"]
                if review["missing_material"]:
                    lines += ["  缺少材料：" + review["missing_material"]]
    lines += ["", "## 边界与假设", "", record["limitations"], "",record["valuation_assumptions"]["assumption"],
              "", "任务勾选仅记录用户操作，不自动证明证据或AI结论正确。", ""]
    return "\n".join(lines)


def to_english_markdown(record):
    """English presentation with unchanged original AI and human-authored text."""
    from presentation import label, VALUATION_ASSUMPTION_EN
    t = lambda value: label(value, "en")
    display = record.get("presentation", {})
    evidence = display.get("evidence", record["evidence"])
    sources = display.get("sources", record["sources"])
    by_id = {c["id"]: c for c in evidence}
    lines = ["# Stock Evidence Lab · Research note", "", f"Question: {record['question']}",
             f"Company: {record['company']} | Mode: {t(record['mode'])}",
             f"Evidence pack: {record['dataset_version']} | Verification record: {record['verified_at']}", "",
             "> Frozen evidence. Facts, inferences and unknowns stay distinct. Not investment advice.", "",
             "## Research scope", "", " / ".join(t(d) for d in record["dimensions"])]
    if record.get("ai_interpretations"):
        lines += ["", "## AI interpretation (inference, original Chinese)", "", f"Actual model: {record['ai_model']}",
                  "Valid citations do not prove causality. Original model text is preserved under the existing validation policy."]
        withheld = record.get("analysis_checks", {}).get("withheld_count", 0)
        if withheld:
            lines += [f"Withheld {withheld} items that failed validation."]
        for item in record["ai_interpretations"]:
            lines += ["", item["text"], "Citations: " + " / ".join(item["evidence_ids"])]
        for item in record.get("ai_research_questions", []):
            lines += ["", item["question"], "Citations: " + " / ".join(item["evidence_ids"])]
    lines += ["", "## Evidence", ""]
    for card in evidence:
        lines += [f"### {card['id']} · {card['title']}", "",
                  f"{t(card['dimension'])} / {t(card['kind'])} / {t(card['direction'])}", "", card["body"], "",
                  "Basis: " + card["formula"], "",
                  "Sources: " + " / ".join(card.get("sources", [card["source"]])) if card["source"] else "Sources: insufficient evidence; remains unknown.",
                  "", "Next: " + card["next_step"], ""]
    lines += ["## Original sources", ""]
    for source in sources:
        lines += [f"- [{source['id']} · {source['title']}]({source['url']}): {source['locator']}"]
    lines += ["", "## Research checklist", ""]
    for task in record["research_tasks"]:
        text = by_id.get(task["evidence_id"], {}).get("next_step", task["task"])
        lines += [f"- [{'x' if task['status'] == '用户已核对' else ' '}] {task['evidence_id']} · {text}"]
    if record.get("claim_review"):
        lines += ["", "## Claim reviews (user-authored)", "",
                  "A review is not system certification. Original claim text and user rationale are retained. Context changes may make reviews stale.", ""]
        for claim in record["claim_review"]["claims"]:
            lines += [f"### {t(claim['origin'])} · {t(claim['status'])}", "", claim["text"],
                      "Citations: " + " / ".join(claim["evidence_ids"])]
            review = claim.get("review")
            if review:
                lines += ["Reviewed at: " + review["reviewed_at"]]
                lines += _english_review_basis(review)
            lines += [""]
        if record["claim_review"]["history"]:
            lines += ["### Review history", ""]
            for review in record["claim_review"]["history"]:
                lines += [f"- {t(review['validity'])} · {t(review['status'])} · {review['reviewed_at']}: {review['text']}"]
                lines += _english_review_basis(review)
    lines += ["", "## Boundaries & assumptions", "", "Frozen evidence; historical valuation estimates; no live diagnosis or investment advice.",
              "", VALUATION_ASSUMPTION_EN, "", "Task checks record user actions; they do not prove evidence or AI claims correct.", ""]
    return "\n".join(lines)


def _english_review_basis(review):
    lines = [f"- Basis: {b['evidence_id']} / {b['source_id']}; locator: {b['locator']}; rationale: {b['note']}" for b in review["basis"]]
    if review["missing_material"]:
        lines += ["Missing evidence: " + review["missing_material"]]
    return lines
