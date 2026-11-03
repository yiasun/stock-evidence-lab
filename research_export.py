"""Human-readable research notes from the same record as the JSON export."""


def to_markdown(record):
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
