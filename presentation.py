"""Bilingual views of canonical evidence. Never mutate research or review records.

English text is an authored presentation of the frozen dataset, not model output.
Amounts are derived from the same fields as diagnosis.py; IDs and URLs are stable.
"""
from diagnosis import metrics, market_metrics, load_market, valuation_metrics, peer_comparison

LABELS = {
    "经营质量": "Operating quality", "财务趋势": "Financial trends", "估值": "Valuation",
    "行情特征": "Price history", "行业位置": "Peer context", "重要事件与风险": "Events & risk",
    "事实": "Fact", "推断": "Inference", "未知": "Unknown", "全部": "All",
    "正面": "Positive", "负面": "Negative", "矛盾": "Divergent", "中性": "Neutral",
    "支持": "Supported", "部分支持": "Partly supported", "不支持": "Not supported",
    "证据不足": "Insufficient evidence", "待复核": "Pending review", "已失效": "Stale",
    "当前有效": "Current", "历史记录": "Superseded", "本地推断卡": "Rule inference",
    "AI推断": "AI inference", "用户已核对": "User checked", "待核对": "Not checked",
    "规则模式": "Rule mode", "规则回退": "Rule fallback", "证据浏览": "Evidence browsing",
    "LLM证据解读": "AI interpretation", "LLM证据导航": "AI navigation", "AI待生成": "AI not run",
    "贵州茅台": "Kweichow Moutai", "五粮液": "Wuliangye",
    "公司": "Company", "期次": "Period", "来源": "Source",
    "营业收入（亿元）": "Revenue (CNY 100m)", "归母净利润（亿元）": "Parent profit (CNY 100m)",
    "经营现金流（亿元）": "Operating cash flow (CNY 100m)", "营收同比（%）": "Revenue YoY (%)",
    "归母利润同比（%）": "Parent profit YoY (%)",
}

EXAMPLES = [
    ("利润下降，现金流为什么大增？", "Why did profit fall while operating cash flow surged?"),
    ("调价能改善业绩吗？", "Can the price adjustment improve future earnings?"),
    ("现在估值便宜吗？", "Is the valuation cheap?"),
]

VALUATION_ASSUMPTION_EN = (
    "Uses shares outstanding at 2026-06-30 with the price at 2026-10-15. Changes in shares "
    "between those dates have not been verified. Historical estimates only; not official daily PE/PB."
)
CASHFLOW_EN = (
    "The company attributes the operating cash flow change mainly to increased member-company "
    "deposits at its finance subsidiary and a decrease in interbank deposits not withdrawable on demand."
)
PEER_EN = (
    "Wuliangye attributes profit growth to a low prior-period base and sales initiatives, among other "
    "factors. Cash flow was affected by collection-policy changes and fewer maturing bank acceptance bills."
)


def label(value, language):
    return LABELS.get(value, value) if language == "en" else value


def canonical_label(value):
    """Recover stable values when a browser sends a previously formatted label."""
    return next((key for key, translated in LABELS.items() if translated == value), value)


def localize_frame(frame, language):
    if language != "en":
        return frame
    result = frame.copy()
    for column in result.select_dtypes(include="object"):
        result[column] = result[column].map(lambda value: LABELS.get(value, value))
    return result.rename(columns=LABELS)


def english_cards(data):
    """ID-keyed presentation fields; numerical claims always use canonical data."""
    m = metrics(data)
    cur = data["financials"][-1]
    val = valuation_metrics(data)
    frame = load_market(data)
    mm = market_metrics(frame)
    peer = peer_comparison(data)
    event = data["event"]
    entries = [
        ("E1", "Revenue increased",
         f"2026H1 revenue was CNY {cur['revenue']/1e9:,.2f}bn, {m['revenue_growth']:+.2f}% year on year.",
         "(Current revenue / prior-year comparable revenue - 1) × 100%",
         "Separate volume, unit price, product mix and channel changes to investigate growth."),
        ("E2", "Profit attributable to owners declined",
         f"2026H1 profit attributable to owners was CNY {cur['profit_parent']/1e9:,.2f}bn, {m['profit_growth']:+.2f}% year on year.",
         "(Current parent profit / prior-year comparable parent profit - 1) × 100%",
         "Check operating costs, taxes and product mix. Falling profit does not imply falling revenue."),
        ("E3", "Operating cash flow increased",
         f"2026H1 consolidated net operating cash flow was CNY {cur['operating_cashflow']/1e9:,.2f}bn, {m['cashflow_growth']:+.2f}% year on year.",
         "(Current operating cash flow / prior-year comparable cash flow - 1) × 100%",
         "Inspect finance-subsidiary deposits and interbank funds before judging core-business collections."),
        ("E4", "Stronger cash flow, weaker profitability",
         "Revenue growth, declining parent profit and rising operating cash flow coexist. Cash flow includes "
         "finance-subsidiary fund movements; it does not establish a broad improvement in the liquor business.",
         "Cross-check E1, E2, E3 and the company's cash flow explanation. This is not causal proof.",
         "Inspect cash flow notes and cash collected from sales; separate the core business and finance subsidiary."),
        ("E5", "Revenue-based gross margin declined",
         f"Computed from revenue and operating cost: {m['gross_margin_previous']:.2f}% → {m['gross_margin']:.2f}%, "
         f"a change of {m['gross_margin']-m['gross_margin_previous']:+.2f} percentage points.",
         "(1 - Operating cost / revenue) × 100%. Excludes interest income; not net margin.",
         "Check product mix and cost changes. Two half-year periods do not establish a long-term trend."),
        ("E6", "Price adjustment for specified Feitian products",
         f"Effective {event['disclosed_at']}: specified iMoutai retail price CNY {event['retail_before']} → "
         f"{event['retail_after']}/bottle; sales contract price CNY {event['contract_before']} → {event['contract_after']}/bottle.",
         "Original announcement price fields, limited to specified products, specifications and channels.",
         "The adjustment follows the half-year end. Verify subsequent volume and execution; it cannot explain 2026H1 results."),
        ("E7", "Earnings impact remains unverified",
         "The announcement says the adjustment will affect performance. This evidence pack has no post-adjustment "
         "sales volumes, channel inventories or complete financial period.",
         "Do not extrapolate price changes linearly into profit.",
         "Obtain later reports, operating data and execution disclosures; verify rumours separately."),
        ("E8", "Historical valuation with explicit assumptions",
         f"Using the 2026-10-15 close and 2026-06-30 shares: estimated PE(TTM) {val['pe_ttm']:.2f}× and PB "
         f"{val['pb']:.2f}×. Intervening share changes are unverified; these are not official daily valuations.",
         "TTM parent profit = 2025FY - 2025H1 + 2026H1. Estimated market cap = historical price × period-end shares. "
         "PE = estimated cap / TTM parent profit; PB = estimated cap / period-end parent equity.",
         "Verify shares on the valuation date, dividends and buybacks; add historical percentiles and peer valuations."),
        ("E9", "Traceable historical price observations",
         f"Tencent unadjusted snapshot: {data['market']['start']} to {data['market']['as_of']}, {len(frame)} observations. "
         f"Endpoint price change {mm['return_pct']:+.2f}%; sample maximum drawdown {mm['max_drawdown_pct']:.2f}%. Excludes dividends.",
         "Price change = final close / first close - 1. Maximum drawdown = min(close / running peak close - 1).",
         "Check dates and raw observations; verify trading-calendar coverage, adjustments and a second source."),
        ("E10", "Peer comparison covers two companies only",
         f"2026H1 revenue: Kweichow Moutai CNY {peer.iloc[0]['营业收入（亿元）']/10:.2f}bn; "
         f"Wuliangye CNY {peer.iloc[1]['营业收入（亿元）']/10:.2f}bn. Comparable consolidated periods, not an industry ranking.",
         "Extract 2026H1 consolidated revenue, parent profit and net operating cash flow for each company.",
         "Check comparison bases, products and channels; broaden the sample before assessing industry position."),
        ("E11", "Insufficient evidence to judge valuation",
         "Estimated multiples do not establish cheapness or expensiveness. Verified valuation-date shares, "
         "historical percentiles and same-date peer valuations are missing.",
         "Assumptions have limits. Do not present estimates as official daily PE/PB.",
         "Obtain same-date shares, valuation history and peer data; compare earnings definitions and risk assumptions."),
        ("E12", "Profit and cash flow diverge across the sample",
         "Wuliangye's parent profit rose while operating cash flow turned negative. Moutai's parent profit fell "
         "while cash flow surged. A single growth rate cannot summarise operating quality.",
         "Check comparable financial fields and both companies' cash flow explanations. No causal proof.",
         "Compare finance-subsidiary fund movements, collection policies and bank acceptance bills."),
    ]
    return {eid: dict(title=title, body=body, formula=formula, next_step=task)
            for eid, title, body, formula, task in entries}


SOURCE_COPY = {
    "S1": dict(title="Kweichow Moutai 2026 interim report (unaudited)",
               locator="PDF p.5: key accounting data; p.7: changes in financial statement items",
               unit="CNY", scope="Consolidated; parent profit separately identified; revenue excludes interest income"),
    "S2": dict(title="Kweichow Moutai material announcement (2026-028)",
               locator="China Securities Journal, B052, price-adjustment paragraph",
               unit="CNY per bottle", scope="Specified Feitian 53%vol 500ml (2026) products; iMoutai retail and contract prices only"),
    "S3": dict(title="Tencent Securities · Moutai frozen historical daily prices",
               locator="data.sh600519.day; local date filter; live qt fields excluded",
               unit="Price CNY / volume shares / turnover CNY",
               scope="Unadjusted; lots × 100 → shares; turnover in CNY 10,000 × 10,000 → CNY"),
    "S4": dict(title="Kweichow Moutai 2025 annual report",
               locator="PDF p.6: key accounting data for the last three years",
               unit="CNY", scope="Annual consolidated revenue and profit attributable to owners"),
    "S5": dict(title="Wuliangye 2026 interim report",
               locator="PDF pp.6–7: key accounting data and notes 1–2",
               unit="CNY", scope="Consolidated; parent profit separately identified; comparative column is 2025H1"),
}


def card_view(card, translations, language):
    return {**card, **translations[card["id"]]} if language == "en" else card.copy()


def source_view(source, language):
    return {**source, **SOURCE_COPY[source["id"]]} if language == "en" else source.copy()
