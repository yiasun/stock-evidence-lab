from pathlib import Path
import json
import os
import pandas as pd
import streamlit as st
from diagnosis import (DIMENSIONS, load_data, metrics, cards, select_dimensions,
                       is_trade_request, staleness, validate_market, market_metrics)
from ai_layer import rank_evidence

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
except (OSError, ValueError, KeyError) as exc:
    st.error(f"证据包不可用：{exc}。诊断已停止，请恢复完整数据。")
    st.stop()
evidence = cards(data)
m = metrics(data)
current = data["financials"][-1]

def secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name, default)

def apply_question(text):
    st.session_state.question = text
    st.session_state.pop("nav", None)

with st.sidebar:
    st.markdown("### 🔎 证据镜")
    st.caption("Stock Evidence Lab / 研究工作台")
    st.selectbox("研究标的", ["贵州茅台 · 600519.SH"])
    st.caption("公司类型：白酒消费品，含财务子公司")
    st.divider()
    st.markdown("**证据包状态**")
    st.caption("财务：2026H1 / 2025H1\n\n核验日：2026-10-16\n\n行情：待核验\n\n同行与估值：缺失")
    st.info("冻结证据研究版。启动时不抓取实时行情。")
    enabled = st.checkbox("启用 LLM 证据导航", value=False,
        help="需在部署端配置OPENAI_API_KEY。开启后，研究问题及公开证据卡会发送至OpenAI；请勿输入个人持仓或隐私。")
    if enabled and not secret("OPENAI_API_KEY"):
        st.warning("未配置服务端密钥，本次继续使用规则模式。")
    st.caption("数字由程序计算；LLM组织证据；用户沿来源继续研究。")

st.markdown('<div class="eyebrow">EVIDENCE FIRST · COMPANY RESEARCH</div>', unsafe_allow_html=True)
st.title("证据镜 · 看见结论背后的证据")
st.markdown('<p class="hero-note">从一个问题出发，交叉检查经营、财务与事件。让事实、推断和未知各归其位，把下一步研究留给你。</p>', unsafe_allow_html=True)
st.caption("贵州茅台 600519.SH  ·  白酒消费品  ·  人民币 / 合并口径")
st.warning(staleness(data))

cols = st.columns(4)
cols[0].metric("2026H1 营业收入", f"{current['revenue']/1e8:,.2f} 亿元", f"{m['revenue_growth']:+.2f}% 同比", delta_color="off")
cols[1].metric("归母净利润", f"{current['profit_parent']/1e8:,.2f} 亿元", f"{m['profit_growth']:+.2f}% 同比", delta_color="off")
cols[2].metric("经营现金流净额", f"{current['operating_cashflow']/1e8:,.2f} 亿元", f"{m['cashflow_growth']:+.2f}% 同比", delta_color="off")
cols[3].metric("当前估值 / 行情", "待核验", "不参与结论", delta_color="off")
st.caption("以上字段来源 S1 · 2026年半年度报告第二节七（未经审计）；金额由元换算为亿元，均为历史财务事实。")

st.markdown("### 01 / 带着问题进入")
examples = ["利润下降，现金流为什么大增？", "调价能改善业绩吗？", "现在估值便宜吗？"]
for col, text in zip(st.columns(3), examples):
    col.button(text, on_click=apply_question, args=(text,), width='stretch')
if "question" not in st.session_state:
    st.session_state.question = examples[0]
question = st.text_input("你想了解贵州茅台的什么？", key="question", max_chars=2000)
recommended = select_dimensions(question)
# The user may change the scope before running a diagnosis.
selected = st.multiselect("本次诊断维度（可修改）", DIMENSIONS, default=DIMENSIONS,
    help="关键词推荐的维度会在下方展示；默认保留全部维度，避免遗漏相反证据。")
st.caption("问题推荐：" + " / ".join(recommended) + "。消费品模板关注盈利、现金回款和渠道事件。")
if is_trade_request(question):
    st.info("该问题含交易决策意图。本产品只提供可追溯的公司研究证据，不提供买卖、仓位、目标价或收益承诺。")
if st.button("生成证据诊断", type="primary", width='stretch'):
    if not question.strip() or not selected:
        st.error("请输入研究问题，并至少选择一个诊断维度。")
    else:
        with st.spinner("核对证据与研究维度…"):
            st.session_state.nav = rank_evidence(question, evidence, secret("OPENAI_API_KEY"),
                secret("AI_MODEL", "gpt-4.1-mini"), enabled)
            st.session_state.nav_question = question
nav = st.session_state.get("nav")
if nav and st.session_state.get("nav_question") != question:
    st.info("问题已改变，请重新生成证据导航。下方仍可浏览全部证据。")
    nav = None
if nav:
    st.success(f"{nav['mode']} · {nav['notice']}")
    st.caption("优先核对：" + " → ".join(nav["ids"]) + "。下方保留相反及缺失证据。")

tabs = st.tabs(["多维诊断", "证据账本", "行情核验沙盒", "研究边界"])
with tabs[0]:
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
                    source = data["financial_source"]
                    st.dataframe(pd.DataFrame(data["financials"])[["period"] + card["fields"]], hide_index=True, width='stretch')
                    st.caption("原始单位：人民币元；2025H1数值采用2026H1报告中的上年同期列。")
                    st.write(data["cashflow_explanation"])
                elif card["source"] == "S2":
                    source = data["event"]
                    st.caption("披露日 2026-07-18；生效时间 2026-07-18 00:00（北京时间）。晚于半年报期末，不能用于解释上半年业绩。")
                else:
                    source = None
                    st.warning("没有满足口径要求的已核验证据，结论保持未知。")
                if source:
                    st.link_button(source["title"], source["url"])
                    st.caption(source["locator"])
                    st.caption(f"披露日：{source['disclosed_at']} · 核验时间：{data['verified_at']} · 范围：{source['scope']}")
                st.markdown("**下一步验证**")
                st.write(card["next_step"])
    st.markdown("### 03 / 把未知变成研究任务")
    for label, q in [("核对回款质量", examples[0]), ("核对事件时间", examples[1]), ("补齐估值证据", examples[2])]:
        st.button(label, key="follow_"+label, on_click=apply_question, args=(q,))
    report = {"question": question, "company": data["ticker"], "mode": nav["mode"] if nav else "证据浏览",
              "verified_at": data["verified_at"], "dimensions": selected, "evidence": shown,
              "sources": [data["financial_source"], data["event"]], "limitations": "冻结证据包；非实时诊断，不提供投资建议"}
    st.download_button("导出本次研究记录（JSON）", json.dumps(report, ensure_ascii=False, indent=2),
                       "stock-evidence-research.json", "application/json")

with tabs[1]:
    st.markdown("### 每一个数字都有来处")
    st.dataframe(pd.DataFrame(data["financials"]), hide_index=True, width='stretch')
    st.caption("金额：人民币元。营业收入不等于营业总收入；归母利润不等于合并净利润。")
    for source in [data["financial_source"], data["event"]]:
        with st.container(border=True):
            st.markdown(f"**{source['id']} · {source['title']}**")
            st.write(source["locator"])
            st.caption(f"披露：{source['disclosed_at']} / 核验：{data['verified_at']} / 单位：{source['unit']}")
            st.write(source["scope"])
            st.link_button("查看公告正文", source["url"])
            if "original_url" in source:
                st.link_button("上交所原始PDF", source["original_url"])
                st.warning(source["verification"])
    st.caption("尚未连接扶摇 / iFinD；没有声称调用这些接口。网页或公告更新后需重新核验冻结证据包。")

with tabs[2]:
    st.markdown("### 对行情先验证，再计算")
    st.warning(data["market"]["reason"])
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

with tabs[3]:
    st.markdown("### 研究边界与分工")
    st.write("面向希望追问证据的个人研究者。单标的MVP，不评价好坏、不承诺涨跌、不输出交易建议。")
    st.markdown("- **程序**：同比、毛利率、样本区间收益与回撤，以及字段、日期、引用校验。\n- **LLM（可选）**：根据自然语言选择、排序现有证据卡；不生成数字或独立金融结论。\n- **用户**：核对原文、修改维度，沿未知证据继续研究。")
    st.write("正面/负面表示单项指标的研究方向，并非综合评级。事实为已披露字段或明确算式；推断有证据但不证明因果；未知不会补成正常值。")
    st.write("已知缺口：实时行情、完整TTM估值、同行比较、公告更新监控、自动财报解析与多标的支持。没有使用受限接口或用户持仓数据。")
    st.write("半年报未经审计；原始PDF当前遇到验证页，财务字段通过公告全文转载核对。新闻传闻、股价归因及提价后的业绩兑现均不作确定性判断。")

st.divider()
st.caption("证据镜 · Stock Evidence Lab  |  历史证据研究演示  |  非投资建议")
