from pathlib import Path
import json
import os
import pandas as pd
import streamlit as st
from diagnosis import (DIMENSIONS, load_data, metrics, cards, select_dimensions,
                       is_trade_request, staleness, validate_market, market_metrics)
from ai_layer import guarded_rank_evidence, resolve_config, PROVIDERS
from diagnosis import all_sources, load_market, valuation_metrics, peer_comparison, research_brief

st.set_page_config(page_title="证据镜 · Stock Evidence Lab", page_icon="🔎", layout="wide")
st.markdown('''<style>
.stApp {background:#f7f9fc} .block-container {max-width:1260px;padding-top:2rem}
h1 {letter-spacing:-1.5px} h2,h3 {color:#173d55}
[data-testid="stMetric"] {background:white;padding:18px;border:1px solid #e1e8f0;border-radius:12px}
.eyebrow {color:#34748c;font-size:12px;letter-spacing:3px;font-weight:700}
.hero-note {color:#617185;font-size:17px;max-width:760px;line-height:1.7}
</style>''', unsafe_allow_html=True)

try:
    data = load_data()
    evidence = cards(data)
    market = load_market(data)
    valuation = valuation_metrics(data)
except (OSError, ValueError, KeyError) as exc:
    st.error(f"证据包不可用：{exc}。诊断已停止，请恢复完整数据。")
    st.stop()
m = metrics(data)
current = data["financials"][-1]
sources = all_sources(data)
source_by_id = {s["id"]:s for s in sources}

def secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name, default)

def apply_question(text):
    st.session_state.question = text
    st.session_state.pop("nav", None)

ai_config = resolve_config(secret)

def use_recommended():
    st.session_state.dimensions = select_dimensions(st.session_state.question)

def render_source(source):
    st.link_button(f"{source['id']} · {source['title']}", source["url"])
    st.caption(source["locator"])
    st.caption(f"披露/行情截止：{source['disclosed_at']} · 核验：{data['verified_at']} · 单位：{source['unit']}")
    st.caption(source["scope"])
    if source.get("sha256"):
        with st.expander("来源文件 SHA-256"):
            st.code(source["sha256"], language=None)

def selected_tasks():
    return [{"evidence_id":c["id"],"task":c["next_step"],"status":"用户已核对" if st.session_state.get("task_"+c["id"],False) else "待核对"} for c in evidence]

with st.sidebar:
    st.markdown("### 🔎 证据镜")
    st.caption("Stock Evidence Lab / 研究工作台")
    st.selectbox("研究标的", ["贵州茅台 · 600519.SH"])
    st.caption("公司类型：白酒消费品，含财务子公司")
    st.divider()
    st.markdown("**证据包状态**")
    st.caption("财务：2026H1 / 2025H1\n\n核验日：2026-10-16\n\n行情：27个观测点 / 截至10月15日\n\n估值：历史口径试算\n\n同行：茅台 / 五粮液")
    st.info("冻结证据研究版。启动时不抓取实时行情。")
    enabled = st.checkbox("启用 LLM 证据导航", value=False,
        help="启用后，研究问题及公开证据卡会发送至下方所列服务商，生成带引用的定性解读。请勿输入个人持仓或隐私。")
    st.caption(f"AI服务：{ai_config['label']} · {ai_config['model']}")
    if ai_config["provider"] == "zhipu":
        st.caption("智谱接入版 · 仅调用 GLM-4.7-Flash；无付费模型自动切换。")
        st.caption("请求保护：单次处理 · 相同问题缓存5分钟 · 限流后冷却60秒。")
    if enabled and ai_config["provider"] not in PROVIDERS:
        st.warning("AI_PROVIDER配置无效，请设为zhipu或openai。")
    elif enabled and not ai_config["api_key"]:
        st.warning("未配置服务端密钥，本次继续使用规则模式。")
    st.caption("数字由程序计算；LLM选择证据并解释关系；分析推断需沿来源核对。")

st.markdown('<div class="eyebrow">EVIDENCE FIRST · COMPANY RESEARCH</div>', unsafe_allow_html=True)
st.title("证据镜 · 看见结论背后的证据")
st.markdown('<p class="hero-note">从一个问题出发，交叉检查经营、财务与事件。让事实、推断和未知各归其位，把下一步研究留给你。</p>', unsafe_allow_html=True)
st.caption("规则研究版 v2 · 贵州茅台 600519.SH  ·  白酒消费品  ·  人民币 / 合并口径")
st.warning(staleness(data))

cols = st.columns(4)
cols[0].metric("2026H1 营业收入", f"{current['revenue']/1e8:,.2f} 亿元", f"{m['revenue_growth']:+.2f}% 同比", delta_color="off")
cols[1].metric("归母净利润", f"{current['profit_parent']/1e8:,.2f} 亿元", f"{m['profit_growth']:+.2f}% 同比", delta_color="off")
cols[2].metric("经营现金流净额", f"{current['operating_cashflow']/1e8:,.2f} 亿元", f"{m['cashflow_growth']:+.2f}% 同比", delta_color="off")
cols[3].metric("10月15日历史收盘价", f"{market.close.iloc[-1]:,.2f} 元", "S3 · 不复权冻结快照", delta_color="off")
st.caption("财务字段来源 S1 · 2026年半年度报告第二节七（未经审计），金额由元换算为亿元；历史收盘价来源 S3 · 腾讯证券冻结快照。")

st.markdown("### 01 / 带着问题进入")
examples = ["利润下降，现金流为什么大增？", "调价能改善业绩吗？", "现在估值便宜吗？"]
for col, text in zip(st.columns(3), examples):
    col.button(text, on_click=apply_question, args=(text,), width='stretch')
if "question" not in st.session_state:
    st.session_state.question = examples[0]
question = st.text_input("你想了解贵州茅台的什么？", key="question", max_chars=2000)
recommended = select_dimensions(question)
# The user may change the scope before running a diagnosis.
if "dimensions" not in st.session_state:
    st.session_state.dimensions = DIMENSIONS.copy()
selected = st.multiselect("本次诊断维度（可修改）", DIMENSIONS, key="dimensions",
    help="关键词推荐的维度会在下方展示；默认保留全部维度，避免遗漏相反证据。")
st.caption("问题推荐：" + " / ".join(recommended) + "。消费品模板关注盈利、现金回款和渠道事件。")
st.button("使用问题推荐维度", on_click=use_recommended, key="use_recommended")
if is_trade_request(question):
    st.info("该问题含交易决策意图。本产品只提供可追溯的公司研究证据，不提供买卖、仓位、目标价或收益承诺。")
if st.button("生成证据诊断", type="primary", width='stretch',key="diagnose"):
    if not question.strip() or not selected:
        st.error("请输入研究问题，并至少选择一个诊断维度。")
    else:
        with st.spinner("核对证据与研究维度…"):
            scoped_evidence = [c for c in evidence if c["dimension"] in selected]
            st.session_state.nav = guarded_rank_evidence(question, scoped_evidence, ai_config["api_key"],
                ai_config["model"], enabled,include_analysis=True,provider=ai_config["provider"])
            st.session_state.nav_context = (question, tuple(selected), enabled,ai_config["provider"],ai_config["model"])
nav = st.session_state.get("nav")
if nav and st.session_state.get("nav_context") != (question,tuple(selected),enabled,ai_config["provider"],ai_config["model"]):
    st.info("问题、维度或运行模式已改变，请重新生成证据导航。下方仍可浏览全部证据。")
    nav = None
if nav:
    if nav.get("request_source") == "cache":
        st.caption("复用最近5分钟内相同问题、证据与模型的成功AI结果，本次未重复调用API。")
    elif nav.get("request_source") == "api":
        st.caption("请求记录：本次向智谱API发起1次请求；不自动重试。")
    elif nav.get("request_source") == "gate":
        st.caption("请求记录：本次由并发/冷却保护拦截，未向API发起新请求。")
    if nav["mode"] == "规则回退":
        st.warning(f"{nav['mode']} · {nav['notice']}")
        st.info(nav["action"])
        st.caption(f"诊断代码：{nav['error_code']}" + (f" · HTTP {nav['http_status']}" if nav.get("http_status") else ""))
        if nav.get("provider_code"):
            st.caption("官方错误码：" + nav["provider_code"])
    else:
        st.success(f"{nav['mode']} · {nav['notice']}")
    st.caption("优先核对：" + " → ".join(nav["ids"]) + "。下方保留相反及缺失证据。")

tabs = st.tabs(["多维诊断", "证据账本", "行情与估值", "同行对比", "研究清单", "行情核验沙盒", "研究边界"])
with tabs[0]:
    if nav and nav.get("interpretations"):
        st.markdown("### AI证据解读 · 分析推断")
        st.caption("以下为模型对已列证据的解释，并非新增公司事实。引用通过校验不等于结论已被证明，请展开证据卡核对。")
        for interpretation in nav["interpretations"]:
            with st.container(border=True):
                st.write(interpretation["text"])
                st.caption("分析推断 · 引用：" + " / ".join(interpretation["evidence_ids"]))
                for evidence_id in interpretation["evidence_ids"]:
                    cited=next(c for c in evidence if c["id"] == evidence_id)
                    with st.expander(f"核对AI引用 {evidence_id} · {cited['title']}"):
                        st.write(cited["body"])
                        st.caption(cited["kind"] + " · " + cited["formula"])
                        for sid in cited.get("sources",[cited["source"]]):
                            if sid:
                                render_source(source_by_id[sid])
        st.markdown("**AI建议继续验证的问题**")
        for followup in nav["research_questions"]:
            st.write(followup["question"])
            st.caption("对应证据：" + " / ".join(followup["evidence_ids"]))
    if nav:
        st.markdown("### 本次研究归纳")
        brief = research_brief(question, selected, evidence)
        for claim in brief["focus"]:
            st.write(f"[{claim['id']} · {claim['kind']}] {claim['body']}")
        if brief["unknowns"]:
            st.warning("仍待验证：" + "；".join(c["title"] for c in brief["unknowns"]))
        st.caption("规则归纳仅引用已核对证据，不是LLM生成；请同时检查下方相反证据。")
    st.markdown("### 02 / 先看矛盾，再看解释")
    st.info("研究焦点 · 收入增长与归母利润下降并存；经营现金流受财务公司资金变化影响，不能单凭现金流增幅认定主业改善。[E1–E4]")
    kind = st.radio("证据类型", ["全部", "事实", "推断", "未知"], horizontal=True)
    ordered = evidence
    if nav:
        order = {id: i for i, id in enumerate(nav["ids"])}
        ordered = sorted(evidence, key=lambda c: order.get(c["id"], 100))
    shown = [c for c in ordered if c["dimension"] in selected and (kind == "全部" or c["kind"] == kind)]
    if not shown:
        st.info("当前筛选没有证据，切换维度或类型继续。")
    for card in shown:
        with st.container(border=True):
            st.caption(f"{card['id']}  /  {card['dimension']}  /  {card['kind']}  /  {card['direction']}证据")
            st.markdown(f"#### {card['title']}")
            st.write(card["body"])
            with st.expander(f"沿证据继续研究 · {card['id']}"):
                st.markdown("**计算 / 判断口径**")
                st.write(card["formula"])
                if card["source"] == "S1":
                    st.dataframe(pd.DataFrame(data["financials"])[["period"] + card["fields"]], hide_index=True, width='stretch')
                    st.caption("原始单位：人民币元；2025H1数值采用2026H1报告中的上年同期列。")
                    st.write(data["cashflow_explanation"])
                elif card["source"] == "S2":
                    st.caption("披露日 2026-07-18；生效时间 2026-07-18 00:00（北京时间）。晚于半年报期末，不能用于解释上半年业绩。")
                elif card["id"] == "E8":
                    st.json({"2025FY归母利润_元":data["annual"]["profit_parent"],"2025H1归母利润_元":data["financials"][0]["profit_parent"],"2026H1归母利润_元":current["profit_parent"],"TTM归母利润_元":valuation["ttm_profit"],"收盘价_元":data["valuation"]["price"],"股本_股":data["valuation"]["shares"],"股本时点":data["valuation"]["shares_as_of"],"归母净资产_元":data["valuation"]["equity_parent"]})
                    st.warning(data["valuation"]["assumption"])
                elif card["source"] == "S3":
                    st.dataframe(market,hide_index=True,width="stretch")
                elif card["source"] == "S5":
                    st.dataframe(peer_comparison(data).round(2),hide_index=True,width="stretch")
                    st.caption(data["peers"]["explanation"])
                if not card["source"]:
                    st.warning("没有满足口径要求的已核验证据，结论保持未知。")
                for source_id in card.get("sources",[card["source"]]):
                    if source_id:
                        render_source(source_by_id[source_id])
                st.markdown("**下一步验证**")
                st.write(card["next_step"])
    st.markdown("### 03 / 把未知变成研究任务")
    for label, q in [("核对回款质量", examples[0]), ("核对事件时间", examples[1]), ("补齐估值证据", examples[2])]:
        st.button(label, key="follow_"+label, on_click=apply_question, args=(q,))
    report = {"question": question, "company": data["ticker"], "mode": nav["mode"] if nav else "证据浏览",
              "verified_at": data["verified_at"], "dimensions": selected, "evidence": shown,
              "sources": sources, "valuation_assumptions":data["valuation"],"research_tasks":selected_tasks(), "limitations": "冻结证据包；估值为有假设的历史试算；非实时诊断，不提供投资建议"}
    if nav:
        report["ai_provider"] = ai_config["provider"]
        report["ai_model"] = ai_config["model"]
        report["ai_interpretations"] = nav.get("interpretations",[])
        report["ai_research_questions"] = nav.get("research_questions",[])
        report["api_diagnostic"] = {k:nav[k] for k in ["error_code","http_status","provider_code"] if k in nav}
    st.download_button("导出本次研究记录（JSON）", json.dumps(report, ensure_ascii=False, indent=2),
                       "stock-evidence-research.json", "application/json")

with tabs[1]:
    st.markdown("### 每一个数字都有来处")
    st.dataframe(pd.DataFrame(data["financials"]), hide_index=True, width='stretch')
    st.caption("金额：人民币元。营业收入不等于营业总收入；归母利润不等于合并净利润。")
    for source in sources:
        with st.container(border=True):
            st.markdown(f"**{source['id']} · {source['title']}**")
            render_source(source)
            if "original_url" in source:
                st.link_button("上交所原始PDF", source["original_url"])
                st.info(source["verification"])
    st.caption("尚未连接扶摇 / iFinD；没有声称调用这些接口。网页或公告更新后需重新核验冻结证据包。")

with tabs[2]:
    st.markdown("### 历史行情 / 有来源、有区间")
    st.caption("S3 · 腾讯证券 · 冻结区间2026-09-01至2026-10-15 · 不复权 · 价格元、成交量股")
    start,end = st.select_slider("查看区间",options=list(market.date.dt.date),value=(market.date.iloc[0].date(),market.date.iloc[-1].date()))
    window = market[(market.date.dt.date >= start)&(market.date.dt.date <= end)]
    if len(window) < 2:
        st.warning("区间需包含至少两个观测点。")
    else:
        wm = market_metrics(window)
        a,b,c = st.columns(3)
        a.metric("区间价格变化",f"{wm['return_pct']:+.2f}%")
        b.metric("区间最大回撤",f"{wm['max_drawdown_pct']:.2f}%")
        c.metric("观测点",len(window))
        st.line_chart(window.set_index("date")[["close"]],y_label="不复权收盘价（元）")
        st.dataframe(window,hide_index=True,width="stretch")
    st.caption("价格变化 = 期末价 / 期初价 - 1；最大回撤 = min(收盘价 / 截至当日峰值 - 1)。不含股息，不等同投资总回报；未核验交易日覆盖完整性。")
    render_source(source_by_id["S3"])
    st.markdown("### 历史估值试算 / 先看假设")
    st.warning(data["valuation"]["assumption"])
    a,b,c = st.columns(3)
    a.metric("PE(TTM)试算",f"{valuation['pe_ttm']:.2f} 倍")
    b.metric("PB试算",f"{valuation['pb']:.2f} 倍")
    c.metric("截至2026H1的TTM归母利润",f"{valuation['ttm_profit']/1e8:.2f} 亿元")
    st.caption("TTM区间2025-07-01至2026-06-30；归母净资产时点2026-06-30；股价时点2026-10-15。行情区间筛选不改变这组固定日期的估值试算。")
    st.code("TTM归母利润 = 2025FY归母利润 - 2025H1归母利润 + 2026H1归母利润\n试算市值 = 2026-10-15收盘价 × 2026-06-30股本\nPE(TTM) = 试算市值 / TTM归母利润\nPB = 试算市值 / 2026-06-30归母净资产",language=None)
    st.info("现有倍数不足以得出便宜或昂贵；缺少历史分位、同日同行估值及期间股本核验。[E11]")

with tabs[3]:
    st.markdown("### 同期同行样本 / 比较之前先对齐口径")
    st.info(data["peers"]["scope"])
    comparison = peer_comparison(data)
    st.dataframe(comparison.round(2),hide_index=True,width="stretch")
    st.bar_chart(comparison.set_index("公司")[["营业收入（亿元）","归母净利润（亿元）"]],y_label="亿元")
    st.warning("财务公司资金变化、渠道与产品结构影响现金流可比性。两家公司样本不能推出全行业排名或市场份额。")
    st.write(data["peers"]["explanation"])
    st.write(data["cashflow_explanation"])
    st.dataframe(pd.DataFrame(data["peers"]["financials"]),hide_index=True,width="stretch")
    for source_id in ["S1","S5"]:
        render_source(source_by_id[source_id])

with tabs[4]:
    st.markdown("### 将结论留在证据里，将未知变成任务")
    st.caption("仅在当前会话记录用户核对状态；勾选不代表系统已自动补齐或验证新证据。刷新可能清空，请导出保存。")
    completed = sum(bool(st.session_state.get("task_"+c["id"],False)) for c in evidence)
    st.progress(completed/len(evidence),text=f"用户已核对 {completed} / {len(evidence)} 项")
    for card in evidence:
        with st.container(border=True):
            st.markdown(f"**{card['id']} · {card['title']}**")
            st.write(card["next_step"])
            st.checkbox("我已沿来源核对本项",key="task_"+card["id"])
    st.download_button("导出研究清单",json.dumps({"company":data["ticker"],"dataset_version":data["dataset_version"],"tasks":selected_tasks()},ensure_ascii=False,indent=2),"research-checklist.json","application/json")

with tabs[5]:
    st.markdown("### 对行情先验证，再计算")
    st.warning("此处仅用于用户CSV或第一版待核验样本。已溯源的腾讯行情在“行情与估值”页，沙盒数据不会进入公司事实。")
    st.caption("沙盒结果只描述所选数据，不回写为公司事实。区间涨跌为价格变化，不含股息收益；不保证交易日连续。")
    use_legacy = st.checkbox("查看继承行情（待核验样本）")
    upload = st.file_uploader("上传自己的行情CSV（仅在本会话使用）", type=["csv"])
    st.download_button("下载CSV模板", "date,close,volume\n", "market_template.csv", "text/csv")
    content = None
    label = ""
    if upload:
        if upload.size > 1_000_000:
            st.error("文件不能超过1MB。")
        else:
            try:
                content = upload.getvalue().decode("utf-8-sig")
                label = "用户上传 · 未核验来源"
            except UnicodeDecodeError:
                st.error("请使用UTF-8编码CSV。")
    elif use_legacy:
        try:
            content = (Path(__file__).parent / "data" / "market_snapshot.csv").read_text(encoding="utf-8")
            label = "继承样本 · 未核验来源"
        except OSError:
            st.error("继承行情文件缺失，沙盒无法读取。")
    if content:
        try:
            frame = validate_market(content)
            mm = market_metrics(frame)
            st.caption(f"{label} · 收盘价假定人民币元；volume单位未知，暂不绘图或用于结论")
            a, b, c = st.columns(3)
            a.metric("样本区间价格变化", f"{mm['return_pct']:+.2f}%")
            b.metric("样本内最大回撤", f"{mm['max_drawdown_pct']:.2f}%")
            c.metric("观测点数", mm["observations"])
            st.caption(f"区间 {frame.date.iloc[0].date()} 至 {frame.date.iloc[-1].date()}；首尾价格比 - 1；回撤 = 当日价格 / 截至当日峰值 - 1 的最小值。")
            st.line_chart(frame.set_index("date")[["close"]], y_label="收盘价（元，待核验）")
            st.dataframe(frame, hide_index=True, width='stretch')
        except ValueError as exc:
            st.error(str(exc))

with tabs[6]:
    st.markdown("### 研究边界与分工")
    st.write("面向希望追问证据的个人研究者。单标的MVP，不评价好坏、不承诺涨跌、不输出交易建议。")
    st.markdown("- **程序**：同比、毛利率、样本区间收益与回撤，以及字段、日期、引用校验。\n- **LLM（可选）**：选择证据，解释证据关系和矛盾，输出带引用的定性推断及继续验证的问题；不计算财务数字。\n- **用户**：核对原文、修改维度，沿未知证据继续研究。")
    st.write("正面/负面表示单项指标的研究方向，并非综合评级。事实为已披露字段或明确算式；推断有证据但不证明因果；未知不会补成正常值。")
    st.write("已补齐：巨潮原始财报关键页核验、腾讯历史行情、明确假设的TTM/PB试算及茅台/五粮液同期样本对比。仍缺：实时行情、估值日实际股本核验、历史估值分位、全行业样本、公告更新监控、自动财报解析与多标的支持。")
    st.write("半年报未经审计；已下载巨潮PDF并核对关键页，证据账本保留页码和SHA-256。新闻传闻、股价归因及调价后的业绩兑现仍不作确定性判断。LLM真实可用性以本次运行结果为准；规则回退不能视为AI验收通过。")

st.divider()
st.caption("证据镜 · Stock Evidence Lab  |  历史证据研究演示  |  非投资建议")
