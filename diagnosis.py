"""Deterministic evidence engine. Numbers never come from an LLM."""
from __future__ import annotations
import io
import json
import math
from datetime import date
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DIMENSIONS = ["经营质量", "财务趋势", "估值", "行情特征", "行业位置", "重要事件与风险"]
KEYWORDS = {
    "经营质量": ["经营", "质量", "毛利", "现金", "渠道", "回款"],
    "财务趋势": ["财务", "增长", "收入", "利润", "营收", "现金", "业绩"],
    "估值": ["估值", "贵", "便宜", "pe", "pb", "市盈率"],
    "行情特征": ["股价", "行情", "波动", "走势", "涨", "跌", "回撤"],
    "行业位置": ["同行", "行业", "龙头", "五粮液", "份额", "排名"],
    "重要事件与风险": ["事件", "风险", "调价", "提价", "公告", "传闻"]
}

def load_data(path=ROOT / "data" / "evidence.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("financials", [])
    if len(rows) != 2 or [r.get("period") for r in rows] != ["2025H1", "2026H1"]:
        raise ValueError("缺少可比的2025H1 / 2026H1财务期次")
    for row in rows:
        for field in ("revenue", "profit_parent", "operating_cashflow", "cost"):
            v = row.get(field)
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"财务字段缺失或无效：{field}")
        if row["revenue"] <= 0 or row["cost"] < 0:
            raise ValueError("营业收入或营业成本口径异常")
    return data

def growth(current, previous):
    # Negative/zero base: ordinary percentage growth is not meaningful.
    if previous <= 0:
        return None
    return (current / previous - 1) * 100

def metrics(data):
    prev, cur = data["financials"]
    return {
        "revenue_growth": growth(cur["revenue"], prev["revenue"]),
        "profit_growth": growth(cur["profit_parent"], prev["profit_parent"]),
        "cashflow_growth": growth(cur["operating_cashflow"], prev["operating_cashflow"]),
        "gross_margin": (1 - cur["cost"] / cur["revenue"]) * 100,
        "gross_margin_previous": (1 - prev["cost"] / prev["revenue"]) * 100,
        "cash_to_parent_profit": cur["operating_cashflow"] / cur["profit_parent"] if cur["profit_parent"] > 0 else None,
    }

def select_dimensions(question):
    text = question.lower()
    selected = [d for d, words in KEYWORDS.items() if any(w in text for w in words)]
    if not selected:
        return DIMENSIONS.copy()
    if "经营质量" not in selected:
        selected.append("经营质量")
    return [d for d in DIMENSIONS if d in selected]

def is_trade_request(question):
    return any(w in question.lower() for w in ["买入", "卖出", "买不买", "能买吗", "该买吗", "目标价", "翻倍", "稳赚", "荐股", "仓位", "buy", "sell"])

def cards(data):
    m = metrics(data)
    cur = data["financials"][1]
    def c(id, dim, kind, direction, title, body, source, fields, formula, next_step):
        return dict(id=id, dimension=dim, kind=kind, direction=direction, title=title,
                    body=body, source=source, fields=fields, formula=formula, next_step=next_step)
    return [
      c("E1", "财务趋势", "事实", "正面", "营业收入仍有增长",
        f"2026H1营业收入 {cur['revenue']/1e8:.2f} 亿元，同比 {m['revenue_growth']:+.2f}%。", "S1",
        ["revenue"], "(本期营业收入 / 上年同期营业收入 - 1) × 100%", "拆分销量、吨价、产品和渠道变化，验证增长来源。"),
      c("E2", "财务趋势", "事实", "负面", "归母净利润同比下降",
        f"2026H1归母净利润 {cur['profit_parent']/1e8:.2f} 亿元，同比 {m['profit_growth']:+.2f}%。", "S1",
        ["profit_parent"], "(本期归母净利润 / 上年同期归母净利润 - 1) × 100%", "检查营业成本、税金及产品结构，不能将利润下降等同于收入萎缩。"),
      c("E3", "经营质量", "事实", "正面", "经营现金流净额上升",
        f"2026H1合并经营现金流净额 {cur['operating_cashflow']/1e8:.2f} 亿元，同比 {m['cashflow_growth']:+.2f}%。", "S1",
        ["operating_cashflow"], "(本期经营现金流 / 上年同期经营现金流 - 1) × 100%", "先看财务公司存款和同业款项变化，再判断主业回款。"),
      c("E4", "经营质量", "推断", "矛盾", "现金流增强与盈利走弱并存",
        "收入增长、归母利润下降、经营现金流上升同时出现。现金流包含财务公司资金变化，不能直接认定白酒主业经营质量全面改善。", "S1",
        ["revenue", "profit_parent", "operating_cashflow"], "联合核对E1、E2、E3及公司对现金流的解释；非因果证明", "追查现金流附注与销售收现，区分主业和财务子公司贡献。"),
      c("E5", "经营质量", "事实", "负面", "营业收入口径毛利率下降",
        f"按营业收入与营业成本计算：{m['gross_margin_previous']:.2f}% → {m['gross_margin']:.2f}%，变化 {m['gross_margin']-m['gross_margin_previous']:+.2f} 个百分点。", "S1",
        ["revenue", "cost"], "(1 - 营业成本 / 营业收入) × 100%；不含利息收入，不是净利率", "继续核对产品结构与成本变化；两个半年期不能代表长期趋势。"),
      c("E6", "重要事件与风险", "事实", "中性", "飞天指定产品调整价格",
        "2026-07-18起，指定飞天产品i茅台零售价1539→1639元/瓶，销售合同价1269→1369元/瓶。", "S2",
        ["retail_before", "retail_after", "contract_before", "contract_after"], "公告原始价格字段；限定产品、规格、渠道", "调价发生在半年报期末之后，验证后续销量与执行情况，不能倒推其影响2026H1。"),
      c("E7", "重要事件与风险", "未知", "未知", "调价的利润兑现尚待验证",
        "公告说明价格调整将影响经营业绩，但本证据包没有调价后的销量、渠道库存和完整财务期次。", "S2", [], "不以价格变化线性外推利润", "获取后续季报、经营数据和执行公告；将传闻与公司披露分别核验。"),
      c("E8", "估值", "未知", "未知", "当前估值无法确认",
        "缺少同一估值日的已核验股价、TTM归母净利润、净资产与总股本；不输出当前PE/PB或贵便宜标签。", "", [],
        "PE = 市值 / TTM归母净利润；PB = 市值 / 归母净资产。半年EPS不可直接当TTM EPS。", "补齐同一时点字段及历史分位，再比较估值假设。"),
      c("E9", "行情特征", "未知", "未知", "继承行情尚未核验",
        data["market"]["reason"], "", [], "仅允许在独立沙盒中对用户数据计算区间涨跌与最大回撤", "补齐数据商、采集时间、复权方式、交易日历和成交量单位。"),
      c("E10", "行业位置", "未知", "未知", "同行位置仍缺证据",
        data["peers"]["reason"], "", [], "需同期同口径的收入、利润率、估值和样本范围", "比较五粮液、泸州老窖等同口径报告；不以品牌知名度替代排名。"),
    ]

def staleness(data, today=None):
    today = today or date.today()
    end = date.fromisoformat(data["financials"][-1]["end"])
    days = (today - end).days
    return f"财务观察截至 {end.isoformat()}，距研究日 {days} 天；这是冻结证据包，不代表实时状态。"

def validate_market(content):
    try:
        frame = pd.read_csv(io.StringIO(content))
        if not {"date", "close", "volume"}.issubset(frame.columns):
            raise ValueError("CSV需包含date、close、volume列")
        if not 2 <= len(frame) <= 10000:
            raise ValueError("至少2行，最多10000行行情")
        frame = frame[["date", "close", "volume"]].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="raise", format="%Y-%m-%d")
        if frame["date"].duplicated().any() or not frame["date"].is_monotonic_increasing:
            raise ValueError("日期必须唯一并按升序排列")
        if (frame["date"].dt.date > date.today()).any():
            raise ValueError("不能包含未来日期")
        for col in ["close", "volume"]:
            frame[col] = pd.to_numeric(frame[col], errors="raise")
            if not frame[col].map(math.isfinite).all():
                raise ValueError("不能含空值或无穷值")
        if (frame.close <= 0).any() or (frame.volume < 0).any():
            raise ValueError("收盘价必须大于零，成交量不能为负")
        return frame
    except (ValueError, TypeError, pd.errors.ParserError) as exc:
        raise ValueError(f"行情数据无效：{exc}") from exc

def market_metrics(frame):
    return {"return_pct": (frame.close.iloc[-1] / frame.close.iloc[0] - 1) * 100,
            "max_drawdown_pct": (frame.close / frame.close.cummax() - 1).min() * 100,
            "observations": len(frame)}
