from pathlib import Path
import json
import os
import pandas as pd
import streamlit as st
from diagnosis import (DIMENSIONS, load_data, metrics, cards, select_dimensions,
                       is_trade_request, staleness, validate_market, market_metrics,
                       all_sources, load_market, valuation_metrics, peer_comparison, research_brief)
from ai_layer import guarded_rank_evidence, resolve_config, PROVIDERS, POLICY_VERSION
from research_export import to_markdown
from review_records import review_context, build_claims, create_review, review_snapshot, fingerprint, STATUSES
from presentation import (label, canonical_label, localize_frame, english_cards, card_view, source_view,
                          EXAMPLES, CASHFLOW_EN, PEER_EN, VALUATION_ASSUMPTION_EN)

st.set_page_config(page_title="Stock Evidence Lab · 证据镜", page_icon="🔎", layout="wide")
st.markdown((Path(__file__).parent / "styles.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
# Locale affects presentation only; canonical records and review fingerprints stay stable.
if "language" not in st.session_state:
    st.session_state.language = "English" if st.query_params.get("lang") == "en" else "中文"
with st.sidebar:
    st.selectbox("Language / 语言", ["中文", "English"], key="language")
lang = "en" if st.session_state.language == "English" else "zh"
st.query_params["lang"] = lang


def L(zh, en):
    return en if lang == "en" else zh


def T(value):
    return label(value, lang)


try:
    data = load_data()
    evidence = cards(data)
    market = load_market(data)
    valuation = valuation_metrics(data)
except (OSError, ValueError, KeyError):
    st.error(L("证据包不可用。诊断已停止，请恢复完整数据。", "Evidence pack unavailable. Research stopped; restore the complete dataset."))
    st.stop()
m = metrics(data)
current = data["financials"][-1]
sources = all_sources(data)
source_by_id = {s["id"]: s for s in sources}
translations = english_cards(data) if lang == "en" else {}


def C(card):
    return card_view(card, translations, lang)


def secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name, default)


def apply_question(text):
    st.session_state.question = text
    st.session_state.pop("nav", None)


def use_recommended():
    st.session_state.dimensions = select_dimensions(st.session_state.question)


def render_source(source):
    view = source_view(source, lang)
    st.link_button(f"{source['id']} · {view['title']}", source["url"])
    st.caption(view["locator"])
    st.caption(L("披露/行情截止", "Disclosure / price cutoff") + f": {source['disclosed_at']} · " +
               L("包内核验记录", "Pack verification record") + f": {data['verified_at'][:10]} · {view['unit']}")
    st.caption(view["scope"])
    if source.get("sha256"):
        with st.expander(L("来源文件 SHA-256", "Source file SHA-256")):
            st.code(source["sha256"], language=None)
            st.caption(L("哈希识别包内记录的文件，不证明内容真实或持续有效。", "Identifies the file recorded in this pack; does not prove truth or continued availability."))


def selected_tasks():
    return [{"evidence_id": c["id"], "task": c["next_step"],
             "status": "用户已核对" if st.session_state.get("task_" + c["id"], False) else "待核对"} for c in evidence]


def evidence_detail(card):
    st.markdown("**" + L("计算 / 判断口径", "Calculation / reasoning basis") + "**")
    st.write(C(card)["formula"])
    if card["source"] == "S1":
        st.dataframe(pd.DataFrame(data["financials"])[["period"] + card["fields"]], hide_index=True, width="stretch")
        st.caption(L("原始单位：人民币元；2025H1采用2026H1报告中的上年同期列。", "Raw unit: CNY. 2025H1 uses the comparative column in the 2026H1 report."))
        st.write(L(data["cashflow_explanation"], CASHFLOW_EN))
    elif card["source"] == "S2":
        st.caption(L("披露/生效：2026-07-18，晚于半年报期末2026-06-30。", "Disclosed / effective: 2026-07-18, after the half-year end, 2026-06-30."))
    elif card["id"] == "E8":
        st.json({"2025FY_parent_profit_CNY": data["annual"]["profit_parent"],
                 "2025H1_parent_profit_CNY": data["financials"][0]["profit_parent"],
                 "2026H1_parent_profit_CNY": current["profit_parent"], "TTM_parent_profit_CNY": valuation["ttm_profit"],
                 "price_CNY": data["valuation"]["price"], "shares": data["valuation"]["shares"],
                 "shares_as_of": data["valuation"]["shares_as_of"], "equity_parent_CNY": data["valuation"]["equity_parent"]})
        st.warning(L(data["valuation"]["assumption"], VALUATION_ASSUMPTION_EN))
    elif card["source"] == "S3":
        st.dataframe(market, hide_index=True, width="stretch")
    elif card["source"] == "S5":
        st.dataframe(localize_frame(peer_comparison(data).round(2), lang), hide_index=True, width="stretch")
        st.caption(L(data["peers"]["explanation"], PEER_EN))
    if not card["source"]:
        st.warning(L("没有满足口径要求的已核验证据，结论保持未知。", "Required evidence is missing. The conclusion remains unknown."))
    for sid in card.get("sources", [card["source"]]):
        if sid:
            render_source(source_by_id[sid])
    st.markdown("**" + L("下一步验证", "Next verification step") + "**")
    st.write(C(card)["next_step"])


ai_config = resolve_config(secret)
with st.sidebar:
    st.markdown("### ◈ Stock Evidence Lab")
    st.caption(L("证据镜 / 公司研究工作台", "Company research workspace"))
    st.selectbox(L("研究标的", "Coverage"), [L("贵州茅台 · 600519.SH", "Kweichow Moutai · 600519.SH")])
    st.caption(L("白酒消费品，含财务子公司 · 单标的原型", "Baijiu producer with a finance subsidiary · Single-company prototype"))
    st.divider()
    st.markdown("**" + L("运行模式", "Research mode") + "**")
    enabled = st.checkbox(L("启用 AI 证据解读", "Enable AI interpretation"), value=False, key="enable_ai",
        help=L("启用后，研究问题及公开证据发送给下列服务商。CSV不会发送。请勿输入隐私。",
               "When enabled, questions and public evidence are sent to the provider below. CSVs are excluded. Do not enter private information."))
    st.caption(f"{ai_config['label']} · {ai_config['model']}")
    if enabled and ai_config["provider"] not in PROVIDERS:
        st.warning(L("AI_PROVIDER配置无效，请设为zhipu或openai。", "Invalid AI_PROVIDER. Use zhipu or openai."))
    elif enabled and not ai_config["api_key"]:
        st.warning(L("未配置服务端密钥，本次继续使用规则模式。", "No server API key configured. Continuing in rule mode."))
    st.caption(L("默认规则模式，无需密钥。程序计算数字，AI解释证据关系。", "Rules by default; no key required. Code calculates figures; AI explains evidence relationships."))
    if lang == "en":
        st.caption("AI responses retain original Chinese for the existing validation policy. Evidence and controls are available in English.")
    with st.expander(L("数据与请求保护", "Data & request controls")):
        st.write(L("冻结包v2.0 · 核验记录2026-10-16。财务截至2026-06-30，未经审计。", "Frozen pack v2.0 · Verification record 2026-10-16. Financials end 2026-06-30, unaudited."))
        st.write(L("启动不抓取实时接口。智谱：同一进程/密钥单请求、成功缓存5分钟、限流冷却60秒；仅1305过载时顺序尝试一次备用。",
                   "No live fetch on startup. Zhipu: one in-flight request per key/process, 5-minute success cache, 60-second cooldown; one sequential backup only after 1305 overload."))
        st.caption(L("模型配置沿用原仓库，实际价格与可用性以服务商为准。本次未重新验收在线模型。", "Model configuration is inherited. Pricing and availability depend on the provider; no new live-model acceptance is claimed."))

st.markdown('<div class="eyebrow">STOCK EVIDENCE LAB / RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
st.title(L("增长的背后，证据说了什么？", "Growth tells only part of the story."))
st.markdown('<p class="hero-note">' + L("用贵州茅台的三项背离指标，体验从财务事实到可追溯研究判断的完整路径。",
    "Investigate three diverging Moutai metrics. Follow every research judgement back to its evidence.") + '</p>', unsafe_allow_html=True)
st.markdown('<a class="start-link" href="#research-start">' + L("开始三分钟案例演示 ↓", "Explore the three-minute case ↓") + '</a>', unsafe_allow_html=True)
st.markdown('<div class="status-strip">' + L(
    "贵州茅台 600519.SH &nbsp; / &nbsp; 2026H1 对比 2025H1 &nbsp; / &nbsp; 冻结证据 · 非实时 &nbsp; / &nbsp; 未经审计",
    "KWEICHOW MOUTAI 600519.SH &nbsp; / &nbsp; 2026H1 vs 2025H1 &nbsp; / &nbsp; FROZEN · NOT LIVE &nbsp; / &nbsp; UNAUDITED") + '</div>', unsafe_allow_html=True)
for col, field, growth_key, zh, en, eid in zip(st.columns(3),
        ["revenue", "profit_parent", "operating_cashflow"], ["revenue_growth", "profit_growth", "cashflow_growth"],
        ["营业收入", "归母净利润", "经营现金流净额"], ["Revenue", "Profit attributable to owners", "Net operating cash flow"], ["E1", "E2", "E3"]):
    col.metric(L(zh, en), L(f"{current[field]/1e8:,.2f} 亿元", f"CNY {current[field]/1e9:,.2f}bn"),
               f"{m[growth_key]:+.2f}% " + L("同比", "YoY"), delta_color="off")
    col.caption(f"{eid} → S1 · " + L("合并口径", "Consolidated"))
st.caption(L("包内字段换算；同比=(本期/上年同期−1)×100%。S1，第5、7页。本次未重新认证原始披露。",
             "Computed from packaged fields; YoY=(current/prior comparable−1)×100%. S1, pp.5 & 7. Original disclosures not re-certified in this upgrade."))
with st.container(border=True):
    st.markdown("#### " + L("核心研究判断 / E4 · 推断", "The research tension / E4 · Inference"))
    st.write(C(next(c for c in evidence if c["id"] == "E4"))["body"])
    st.caption(L(data["cashflow_explanation"], CASHFLOW_EN))
st.markdown('<div class="journey">' + ''.join('<div><span>' + n + '</span><strong>' + title + '</strong><small>' + desc + '</small></div>'
    for n, title, desc in [
        ("01 / 0:00–0:45", L("看见矛盾", "Spot the divergence"), L("收入、利润与现金流", "Revenue, profit, cash flow")),
        ("02 / 0:45–1:45", L("追到原始证据", "Trace the evidence"), L("字段 → 算式 → 公告页码", "Field → formula → disclosure page")),
        ("03 / 1:45–3:00", L("复核并导出", "Review & export"), L("记录依据与缺失材料", "Record rationale and missing evidence"))]) + '</div>', unsafe_allow_html=True)
tabs = st.tabs([L("研究案例与解读", "Case & interpretation"), L("来源与数据核验", "Sources & verification"),
                L("人工复核", "Human review"), L("研究工具与边界", "Tools & boundaries")])
with tabs[0]:
    st.markdown('<div id="research-start"></div>', unsafe_allow_html=True)
    st.markdown("### " + L("01 / 从一个研究问题开始", "01 / Start with a research question"))
    examples = [pair[1 if lang == "en" else 0] for pair in EXAMPLES]
    for index, (col, text) in enumerate(zip(st.columns(3), examples)):
        col.button(text, key=f"example_{index}", on_click=apply_question, args=(text,), width="stretch")
    if "question" not in st.session_state:
        st.session_state.question = examples[0]
    question = st.text_input(L("你想了解贵州茅台的什么？", "What would you like to investigate about Moutai?"), key="question", max_chars=2000)
    recommended = select_dimensions(question)
    if "dimensions" not in st.session_state:
        st.session_state.dimensions = DIMENSIONS.copy()
    st.session_state.dimensions = [canonical_label(d) for d in st.session_state.dimensions]
    with st.expander(L("研究范围 / 默认保留全部维度", "Research scope / all dimensions by default")):
        selected = [canonical_label(d) for d in st.multiselect(L("本次诊断维度（可修改）", "Research dimensions (editable)"), DIMENSIONS, key="dimensions", format_func=T)]
        st.caption(L("问题推荐：", "Suggested: ") + " / ".join(T(d) for d in recommended))
        st.button(L("使用问题推荐维度", "Apply suggested dimensions"), on_click=use_recommended, key="use_recommended")
    if is_trade_request(question):
        st.info(L("该问题含交易决策意图。本产品只提供可追溯的公司研究证据，不提供买卖、仓位、目标价或收益承诺。",
                  "Trading intent detected. Traceable company evidence only; no buy/sell decisions, position sizing, price targets or return promises."))
    if st.button(L("生成证据诊断", "Generate evidence brief"), type="primary", width="stretch", key="diagnose"):
        if not question.strip() or not selected:
            st.error(L("请输入研究问题，并至少选择一个诊断维度。", "Enter a question and select at least one dimension."))
        else:
            with st.spinner(L("核对证据与研究维度…", "Checking evidence and scope…")):
                scoped_evidence = [c for c in evidence if c["dimension"] in selected]
                st.session_state.nav = guarded_rank_evidence(question, scoped_evidence, ai_config["api_key"],
                    ai_config["model"], enabled, include_analysis=True, provider=ai_config["provider"])
                st.session_state.nav_context = (question, tuple(selected), enabled, ai_config["provider"], ai_config["model"])
    nav = st.session_state.get("nav")
    if nav and st.session_state.get("nav_context") != (question, tuple(selected), enabled, ai_config["provider"], ai_config["model"]):
        st.info(L("问题、维度或运行模式已改变，请重新生成证据导航。下方仍可浏览全部证据。", "Question, scope or mode changed. Generate a new brief; scoped evidence remains browsable below."))
        nav = None
    if nav:
        if nav["mode"] == "规则回退":
            st.warning(L(f"{nav['mode']} · {nav['notice']}", f"Rule fallback · AI unavailable ({nav['error_code']}). Local evidence remains available."))
            st.info(L(nav["action"], "Check credentials, quota or connectivity as appropriate. Retry manually after resolving the issue."))
        else:
            st.success(L(f"{nav['mode']} · {nav['notice']}", T(nav['mode']) + " · " + ("Cited qualitative inference; verify disclosures." if nav.get("interpretations") else "No LLM call. Evidence selected by rules.")))
        st.caption(L("优先核对：", "Review first: ") + " → ".join(nav["ids"]) + L("。相反及缺失证据仍保留。", ". Opposing and missing evidence is retained."))
        with st.expander(L("本次运行记录", "Run details")):
            st.json({k: nav[k] for k in ["request_source", "attempts", "elapsed_seconds", "model_used", "fallback_from", "fallback_reason", "error_code", "http_status", "provider_code", "output_reason"] if k in nav})
    if nav and nav.get("interpretations"):
        st.markdown("### " + L("AI证据解读 · 分析推断", "AI interpretation · Inference"))
        st.caption(L("引用有效不等于结论已证明。请沿来源核对；模型原文保留。", "Valid citations do not prove a conclusion. Verify sources; AI text retains original Chinese."))
        if nav.get("analysis_checks", {}).get("withheld_count"):
            count = nav['analysis_checks']['withheld_count']
            st.warning(L(f"已隐藏{count}项未通过校验的AI内容。", f"Withheld {count} AI items that failed validation."))
        for interpretation in nav["interpretations"]:
            with st.container(border=True):
                st.write(interpretation["text"])
                st.caption(L("分析推断 · 引用：", "Inference · Citations: ") + " / ".join(interpretation["evidence_ids"]))
                for eid in interpretation["evidence_ids"]:
                    cited = next(c for c in evidence if c["id"] == eid)
                    with st.expander(L(f"核对AI引用 {eid} · {cited['title']}", f"Check AI citation {eid} · {C(cited)['title']}")):
                        st.write(C(cited)["body"])
                        evidence_detail(cited)
        for followup in nav.get("research_questions", []):
            st.write(followup["question"])
            st.caption(L("对应证据：", "Evidence: ") + " / ".join(followup["evidence_ids"]))
    if nav:
        st.markdown("#### " + L("本次研究归纳 / 规则生成", "Research synthesis / rule generated"))
        brief = research_brief(question, selected, evidence)
        for claim in brief["focus"]:
            st.write(f"[{claim['id']} · {T(claim['kind'])}] {C(claim)['body']}")
        st.caption(L("规则归纳不是LLM生成；推断仍需人工复核。", "Rule synthesis is not LLM output. Inferences require human review."))
    st.markdown("### " + L("02 / 核对证据与替代解释", "02 / Inspect evidence & alternatives"))
    st.caption(L("展开证据核对字段、算式和来源。类型筛选只改变展示，不裁剪导出或复核依据。", "Expand evidence for fields, formulas and sources. Type filters affect the view, not exports or review basis."))
    if "evidence_kind" in st.session_state:
        st.session_state.evidence_kind = canonical_label(st.session_state.evidence_kind)
    kind = canonical_label(st.radio(L("证据类型", "Evidence type"), ["全部", "事实", "推断", "未知"], format_func=T, horizontal=True, key="evidence_kind"))
    order = {eid: i for i, eid in enumerate(nav["ids"])} if nav else {eid: i for i, eid in enumerate(["E4", "E1", "E2", "E3"])}
    shown = [c for c in sorted(evidence, key=lambda c: order.get(c["id"], 100)) if c["dimension"] in selected and (kind == "全部" or c["kind"] == kind)]
    if not shown:
        st.info(L("当前筛选没有证据，切换维度或类型继续。", "No matching evidence. Change the scope or type."))
    for card in shown:
        # Keep the core contradiction visible; secondary context uses progressive disclosure.
        surface = st.container(border=True) if card["id"] in {"E1", "E2", "E3", "E4"} else st.expander(f"{card['id']} · {C(card)['title']}")
        with surface:
            st.caption(f"{card['id']} / {T(card['kind'])} / {T(card['direction'])} / {T(card['dimension'])}")
            st.markdown(f"#### {C(card)['title']}")
            st.write(C(card)["body"])
            with st.expander(L(f"沿证据继续研究 · {card['id']}", f"Trace evidence · {card['id']}")):
                evidence_detail(card)
    for index, (zh, en) in enumerate([("核对回款质量", "Investigate cash collection"), ("核对事件时间", "Check event timing"), ("补齐估值证据", "Resolve valuation gaps")]):
        st.button(L(zh, en), key=f"follow_{index}", on_click=apply_question, args=(examples[index],))

# Canonical review inputs; locale is deliberately excluded from the fingerprint.
scoped_cards = [c for c in evidence if c["dimension"] in selected]
context = review_context(question, selected, data, nav["mode"] if nav else ("AI待生成" if enabled else "证据浏览"),
                         ai_config["provider"] if enabled else "rules", nav.get("model_used", ai_config["model"]) if nav and enabled else "", POLICY_VERSION)
claims = build_claims(scoped_cards, nav.get("interpretations", []) if nav else [], context)
if "claim_review_history" not in st.session_state:
    st.session_state.claim_review_history = []
claim_review = review_snapshot(claims, st.session_state.claim_review_history)

with tabs[1]:
    st.markdown("### " + L("从展示数字回到原始字段", "From displayed figures to raw fields"))
    st.caption(L(staleness(data), f"Financial observation ends {current['end']}. Frozen evidence, not a live view."))
    st.dataframe(pd.DataFrame(data["financials"]), hide_index=True, width="stretch")
    st.caption(L("金额：人民币元。营业收入不等于营业总收入；归母利润不等于合并净利润。", "Amounts: CNY. Revenue excludes interest income; parent profit differs from total consolidated profit."))
    st.info(L("应用检查期次、有限数值和行情哈希。PDF页码和哈希来自既有核验记录；启动不会重新下载或认证PDF。",
              "The app checks periods, finite values and the price-file hash. PDF pages and hashes are inherited verification records; startup does not re-download or authenticate PDFs."))
    for source in sources:
        with st.container(border=True):
            render_source(source)
            if "original_url" in source:
                st.link_button(L("上交所原始PDF", "SSE original PDF"), source["original_url"])
    st.caption(L("未连接扶摇/iFinD；来源更新后需重新核验冻结包。", "No Fuyao/iFinD connection. Source updates require a new pack review."))

with tabs[2]:
    st.markdown("### " + L("03 / 把判断和依据留在一起", "03 / Keep judgement and rationale together"))
    st.caption(L("程序校验不等于语义核验。人工意见仅本会话保存，请导出留存。任务勾选不会完成主张复核。", "Code validation is not semantic verification. User-authored, session-only reviews; export to retain them. Task checkboxes do not review claims."))
    pending = sum(c["status"] == "待复核" for c in claim_review["claims"])
    st.info(L(f"当前范围{len(claims)}条推断，{pending}条待复核。仅本会话状态，不是产品准确率。", f"{len(claims)} inference claims; {pending} pending review. Session status, not product accuracy."))
    if st.session_state.pop("review_saved_notice", False):
        st.success(L("复核已保存。你可继续复核，或导出含依据和历史的研究记录。", "Review saved. Continue or export the record with rationale and history."))
    if claims:
        claim_by_id = {c["claim_id"]: c for c in claims}

        def claim_display(claim_id):
            item = claim_by_id[claim_id]
            text = item["text"] if lang == "zh" or item["origin"] == "AI推断" else C(next(c for c in scoped_cards if c["id"] == item["evidence_ids"][0]))["body"]
            return T(item["origin"]) + " · " + text

        selected_claim_id = st.selectbox(L("选择待复核主张", "Select a claim to review"), list(claim_by_id), format_func=claim_display,
                                         key="review_claim_" + fingerprint(list(claim_by_id)))
        claim = claim_by_id[selected_claim_id]
        current_review = next(c for c in claim_review["claims"] if c["claim_id"] == selected_claim_id)
        st.write(claim_display(selected_claim_id))
        st.caption(L("当前状态：", "Current status: ") + T(current_review["status"]) + " · " + " / ".join(claim["evidence_ids"]))
        choices = []
        for eid in claim["evidence_ids"]:
            card = next(c for c in scoped_cards if c["id"] == eid)
            with st.expander(L("复核依据 · ", "Review basis · ") + eid):
                st.write(C(card)["body"])
                evidence_detail(card)
                choices.extend(eid + " / " + sid for sid in card.get("sources", [card["source"]]) if sid)
        with st.form("review_form_" + selected_claim_id):
            status = canonical_label(st.selectbox(L("人工复核判定", "Your judgement"), STATUSES, format_func=T))
            basis_choice = st.selectbox(L("依据证据与来源", "Evidence & source used"), ["未选择"] + choices,
                                       format_func=lambda value: L(value, "Select a source" if value == "未选择" else value))
            locator = st.text_input(L("原文定位（页码/章节）", "Disclosure locator (page / section)"), max_chars=300)
            note = st.text_area(L("复核说明", "Review rationale"), max_chars=1000)
            missing = st.text_area(L("缺少的材料（证据不足时必填）", "Missing evidence (required for insufficient evidence)"), max_chars=1000)
            if st.form_submit_button(L("保存本条复核", "Save this review")):
                basis = []
                if basis_choice != "未选择":
                    eid, sid = basis_choice.split(" / ")
                    basis = [{"evidence_id": eid, "source_id": sid, "locator": locator, "note": note}]
                try:
                    st.session_state.claim_review_history.append(create_review(claim, status, basis, missing, scoped_cards, sources))
                    st.session_state.review_saved_notice = True
                    st.rerun()
                except ValueError as exc:
                    st.error(L(str(exc), "Review not saved. A cited source, locator and rationale are required; for insufficient evidence, describe missing material."))
    else:
        st.info(L("当前范围没有可复核推断，请修改范围。", "No inference claims in scope. Adjust research dimensions."))
    stale_count = sum(r["validity"] == "已失效" for r in claim_review["history"])
    if stale_count:
        st.warning(L(f"有{stale_count}条历史复核已失效，不用于当前主张。", f"{stale_count} prior reviews are stale; they do not apply to current claims."))
    with st.expander(L("查看复核与历史记录 / 原始JSON", "Review history / canonical JSON")):
        st.json(claim_review)

# Export after review controls, using the existing canonical schema and full scope.
report = {"question": question, "company": data["ticker"], "mode": nav["mode"] if nav else "证据浏览",
          "dataset_version": data["dataset_version"], "app_version": "4.0", "language": lang,
          "claim_review": claim_review, "verified_at": data["verified_at"], "dimensions": selected,
          "evidence": scoped_cards, "visible_evidence_ids": [c["id"] for c in shown], "sources": sources,
          "valuation_assumptions": data["valuation"], "research_tasks": selected_tasks(),
          "limitations": "冻结证据包；估值为有假设的历史试算；非实时诊断，不提供投资建议"}
if nav:
    report.update(ai_provider=ai_config["provider"], ai_model=nav.get("model_used", ai_config["model"]),
                  ai_interpretations=nav.get("interpretations", []), analysis_checks=nav.get("analysis_checks", {}),
                  ai_research_questions=nav.get("research_questions", []))
    report["ai_request"] = {k: nav[k] for k in ["request_source", "attempts", "elapsed_seconds", "fallback_from", "fallback_reason"] if k in nav}
    report["api_diagnostic"] = {k: nav[k] for k in ["error_code", "http_status", "provider_code", "output_reason"] if k in nav}
if lang == "en":
    report["presentation"] = {"evidence": [C(card) for card in scoped_cards],
                              "sources": [source_view(source, lang) for source in sources]}
with tabs[0]:
    st.markdown("### " + L("保存这次研究", "Take the research with you"))
    st.caption(L("包含范围内全部证据、来源、假设和复核历史。JSON保留中文原始记录。", "Includes all scoped evidence, sources, assumptions and review history. JSON retains canonical Chinese records."))
    a, b = st.columns(2)
    a.download_button(L("导出本次研究记录（JSON）", "Download research record (JSON)"), json.dumps(report, ensure_ascii=False, indent=2), "stock-evidence-research.json", "application/json", width="stretch")
    b.download_button(L("导出可读研究笔记（Markdown）", "Download research note (Markdown)"), to_markdown(report), "stock-evidence-research.md", "text/markdown", width="stretch")
    with st.expander(L("预览可读研究笔记", "Preview research note")):
        st.code(to_markdown(report), language="markdown")
with tabs[2]:
    st.markdown("#### " + L("保存复核与研究记录", "Save reviews & research"))
    st.caption(L("包含完整范围的证据与复核历史。", "Includes full scoped evidence and review history."))
    a, b = st.columns(2)
    a.download_button(L("保存复核记录（JSON）", "Save reviewed record (JSON)"), json.dumps(report, ensure_ascii=False, indent=2), "stock-evidence-research.json", "application/json", key="review_json", width="stretch")
    b.download_button(L("保存复核笔记（Markdown）", "Save reviewed note (Markdown)"), to_markdown(report), "stock-evidence-research.md", "text/markdown", key="review_markdown", width="stretch")

with tabs[3]:
    tools_tabs = st.tabs([L("行情与估值", "Prices & valuation"), L("同行对比", "Peer comparison"), L("研究清单", "Research checklist"), L("行情核验沙盒", "CSV validation"), L("研究边界", "Boundaries")])
    with tools_tabs[0]:
        st.markdown("### " + L("历史行情 / 有来源、有区间", "Historical prices / bounded & sourced"))
        st.caption("S3 · Tencent · 2026-09-01 → 2026-10-15 · " + L("不复权 · 价格元、成交量股", "Unadjusted · CNY / shares"))
        start, end = st.select_slider(L("查看区间", "Date range"), options=list(market.date.dt.date), value=(market.date.iloc[0].date(), market.date.iloc[-1].date()))
        window = market[(market.date.dt.date >= start) & (market.date.dt.date <= end)]
        if len(window) < 2:
            st.warning(L("区间需包含至少两个观测点。", "Select at least two observations."))
        else:
            wm = market_metrics(window)
            a, b, c = st.columns(3)
            a.metric(L("区间价格变化", "Price change"), f"{wm['return_pct']:+.2f}%")
            b.metric(L("区间最大回撤", "Sample maximum drawdown"), f"{wm['max_drawdown_pct']:.2f}%")
            c.metric(L("观测点", "Observations"), len(window))
            st.line_chart(window.set_index("date")[["close"]], y_label=L("不复权收盘价（元）", "Unadjusted close (CNY)"))
            st.dataframe(window, hide_index=True, width="stretch")
        st.caption(L("不含股息，不等同总回报；交易日覆盖完整性未核验。", "Excludes dividends; not total return. Full trading-calendar coverage unverified."))
        render_source(source_by_id["S3"])
        st.markdown("### " + L("历史估值试算 / 先看假设", "Historical valuation / assumptions first"))
        st.warning(L(data["valuation"]["assumption"], VALUATION_ASSUMPTION_EN))
        a, b, c = st.columns(3)
        a.metric(L("PE(TTM)试算", "Estimated PE(TTM)"), f"{valuation['pe_ttm']:.2f}×")
        b.metric(L("PB试算", "Estimated PB"), f"{valuation['pb']:.2f}×")
        c.metric(L("截至2026H1的TTM归母利润", "TTM parent profit through 2026H1"), L(f"{valuation['ttm_profit']/1e8:.2f} 亿元", f"CNY {valuation['ttm_profit']/1e9:.2f}bn"))
        st.write(C(next(c for c in evidence if c["id"] == "E8"))["formula"])
        st.caption(L("TTM：2025-07-01至2026-06-30；股本/净资产：2026-06-30；股价：2026-10-15。区间筛选不改变估值日。", "TTM: 2025-07-01 to 2026-06-30; shares/equity: 2026-06-30; price: 2026-10-15. Range selection does not change valuation dates."))
        st.info(C(next(c for c in evidence if c["id"] == "E11"))["body"] + " [E11]")
    with tools_tabs[1]:
        st.markdown("### " + L("同期同行 / 先对齐口径", "Peer comparison / align the basis first"))
        st.info(L(data["peers"]["scope"], "Two-company sample, not the full industry. Product, channel and finance-subsidiary differences limit comparability."))
        comparison = peer_comparison(data)
        st.dataframe(localize_frame(comparison.round(2), lang), hide_index=True, width="stretch")
        chart = localize_frame(comparison.set_index("公司")[["营业收入（亿元）", "归母净利润（亿元）"]], lang)
        chart.index = [T(name) for name in chart.index]
        st.bar_chart(chart, y_label=L("亿元", "CNY 100m"))
        st.write(L(data["peers"]["explanation"], PEER_EN))
        st.write(L(data["cashflow_explanation"], CASHFLOW_EN))
        for sid in ["S1", "S5"]:
            render_source(source_by_id[sid])
    with tools_tabs[2]:
        st.markdown("### " + L("把未知变成研究任务", "Turn unknowns into research tasks"))
        st.caption(L("仅本会话记录；勾选不代表自动验证。刷新可能清空，请导出保存。", "Session-only. Checking is not verification. Export before leaving."))
        completed = sum(bool(st.session_state.get("task_" + c["id"], False)) for c in evidence)
        st.progress(completed / len(evidence), text=L(f"用户已核对 {completed} / {len(evidence)} 项", f"User checked {completed} / {len(evidence)} tasks"))
        for card in evidence:
            with st.container(border=True):
                st.markdown(f"**{card['id']} · {C(card)['title']}**")
                st.write(C(card)["next_step"])
                st.checkbox(L("我已沿来源核对本项", "I checked this task against its source"), key="task_" + card["id"])
        st.download_button(L("导出研究清单", "Download checklist"), json.dumps({"company": data["ticker"], "dataset_version": data["dataset_version"], "tasks": selected_tasks()}, ensure_ascii=False, indent=2), "research-checklist.json", "application/json")
    with tools_tabs[3]:
        st.markdown("### " + L("先验证，再计算", "Validate before calculating"))
        st.warning(L("仅用户CSV或继承待核验样本，不进入公司事实。已溯源行情见“行情与估值”。", "Sandbox for your CSV or unverified legacy sample. Results do not become company facts. Sourced prices are in Prices & valuation."))
        use_legacy = st.checkbox(L("查看继承行情（待核验样本）", "Use legacy prices (unverified sample)"), key="legacy_prices")
        upload = st.file_uploader(L("上传自己的行情CSV（仅在本会话使用）", "Upload price CSV (this session only)"), type=["csv"])
        st.download_button(L("下载CSV模板", "Download CSV template"), "date,close,volume\n", "market_template.csv", "text/csv")
        content = None
        if upload:
            if upload.size > 1_000_000:
                st.error(L("文件不能超过1MB。", "Maximum file size: 1MB."))
            else:
                try:
                    content = upload.getvalue().decode("utf-8-sig")
                except UnicodeDecodeError:
                    st.error(L("请使用UTF-8编码CSV。", "Use a UTF-8 encoded CSV."))
        elif use_legacy:
            try:
                content = (Path(__file__).parent / "data" / "market_snapshot.csv").read_text(encoding="utf-8")
            except OSError:
                st.error(L("继承行情文件缺失。", "Legacy price file missing."))
        if content:
            try:
                frame = validate_market(content)
                mm = market_metrics(frame)
                st.caption(L("待核验来源；收盘价假定人民币元、成交量单位未知。不回写公司事实、不发送给LLM。", "Unverified source; close assumed CNY, volume unit unknown. Not written into company facts or sent to an LLM."))
                a, b, c = st.columns(3)
                a.metric(L("样本区间价格变化", "Sample price change"), f"{mm['return_pct']:+.2f}%")
                b.metric(L("样本内最大回撤", "Sample maximum drawdown"), f"{mm['max_drawdown_pct']:.2f}%")
                c.metric(L("观测点数", "Observation count"), mm["observations"])
                st.caption(L("价格变化=期末/期初−1；回撤=min(收盘价/历史峰值−1)。不含股息，连续性未核验。", "Price change=last/first−1; drawdown=min(close/running peak−1). Excludes dividends; continuity unverified."))
                st.line_chart(frame.set_index("date")[["close"]], y_label=L("收盘价（元，待核验）", "Close (CNY assumed, unverified)"))
                st.dataframe(frame, hide_index=True, width="stretch")
            except ValueError as exc:
                st.error(L(str(exc), "Invalid data. Require date, close, volume; 2–10,000 rows; unique ascending dates, no future dates, finite values, positive close and non-negative volume."))
    with tools_tabs[4]:
        st.markdown("### " + L("分工清晰，边界可见", "Clear responsibilities, visible limits"))
        for zh, en in [
            ("程序：计算同比、毛利率、价格变化、回撤和估值试算；检查字段、日期和引用。", "Code: calculates growth, gross margin, price changes, drawdown and valuation estimates; checks fields, dates and citations."),
            ("AI（可选）：选择并解释已有证据，不新增公司事实或替代人工核验。", "AI (optional): selects and explains existing evidence; does not add company facts or replace human verification."),
            ("人工：核对原文，记录主张判定、定位、理由和缺失材料。问题、数据或模型输出改变时旧复核失效。", "Human: checks disclosures and records judgement, locator, rationale and missing evidence. Changes to question, data or model output invalidate old reviews."),
            ("事实、推断、未知分别展示。证据方向不是评级，不提供交易建议、实时行情或收益承诺。", "Facts, inferences and unknowns remain distinct. Evidence direction is not a rating. No trading advice, live quotes or return promises."),
            ("未完成：多标的、实时接口、自动公告更新、历史估值分位、估值日股本核验和全行业样本。", "Not implemented: multi-company coverage, live feeds, automatic filings updates, historical valuation percentiles, valuation-date shares or full-industry samples."),
            ("三分钟为设计的演示路径，尚未经招聘人员或真实用户验证。", "Three minutes is the designed demo path, not a recruiter-tested or user-validated metric."),
        ]:
            st.write(L(zh, en))
st.divider()
st.caption(L("证据镜 · v4.0 / 冻结证据研究 / 非投资建议", "Stock Evidence Lab · v4.0 / Frozen-evidence research / Not investment advice"))
