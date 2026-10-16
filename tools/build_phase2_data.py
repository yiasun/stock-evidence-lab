"""Build reviewed frozen evidence from downloaded public sources.

Run with pypdf installed after fetch_references.py. No model or live quotes used.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "artifacts" / "references"
stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
data_path = ROOT / "data" / "evidence.json"
data = json.loads(data_path.read_text(encoding="utf-8"))

def checked_pdf(name, pages, tokens):
    path = REF / name
    reader = PdfReader(path)
    text = "\n".join(reader.pages[i-1].extract_text() for i in pages)
    for token in tokens:
        if token not in text:
            raise ValueError(f"Reviewed field absent in {name}: {token}")
    return hashlib.sha256(path.read_bytes()).hexdigest()

h1_sha = checked_pdf("maotai_2026h1.pdf", [5,7], ["90,703,260,964.48", "44,516,880,421.86", "70,690,750,119.06", "9,473,762,565.88", "251,253,594,419.50", "1,250,081,601.00"])
fy_sha = checked_pdf("maotai_2025fy.pdf", [6], ["82,320,067,101.68", "168,838,102,514.79"])
peer_sha = checked_pdf("wuliangye_2026h1.pdf", [6,7], ["28,416,674,541.77", "8,752,942,991.31", "-2,153,568,792.32", "23,509,972,048.65", "4,623,850,715.13", "31,136,736,628.58"])
data["verified_at"] = stamp
data["dataset_version"] = "2.0"
source = data["financial_source"]
source["url"] = "https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF"
source["mirror_url"] = "https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12496833&stockid=600519"
source["locator"] = "PDF第5页：主要会计数据；第7页：财务报表相关科目变动分析"
source["sha256"] = h1_sha
source["verification"] = "已下载巨潮原始PDF，提取并视觉核对第5、7页，与公告全文转载一致。"
data["financials"][-1].update(equity_parent=251253594419.50, shares=1250081601)
data["annual"] = {
    "period":"2025FY", "start":"2025-01-01", "end":"2025-12-31", "profit_parent":82320067101.68,
    "revenue":168838102514.79, "source":"S4"
}
data["annual_source"] = {
    "id":"S4", "title":"贵州茅台2025年年度报告", "url":"https://static.cninfo.com.cn/finalpage/2026-04-17/1225114741.PDF",
    "disclosed_at":"2026-04-17", "period":"2025-01-01 / 2025-12-31", "locator":"PDF第6页：近三年主要会计数据",
    "unit":"人民币元", "scope":"合并营业收入、归母净利润；年度报告", "sha256":fy_sha
}
peer_source = {
    "id":"S5", "title":"五粮液2026年半年度报告", "url":"https://static.cninfo.com.cn/finalpage/2026-08-29/1225531252.PDF",
    "disclosed_at":"2026-08-29", "period":"2026-01-01 / 2026-06-30", "locator":"PDF第6–7页：主要会计数据及注1、注2",
    "unit":"人民币元", "scope":"合并口径，归母净利润单列；上年同期列为2025H1", "sha256":peer_sha
}
data["peers"] = {"verified":True, "source":peer_source, "scope":"两家公司定向样本，不代表全行业；不同产品、渠道及财务子公司结构影响可比性。",
    "financials":[
        {"company":"五粮液", "ticker":"000858.SZ", "period":"2025H1", "end":"2025-06-30", "revenue":23509972048.65, "profit_parent":4623850715.13, "operating_cashflow":31136736628.58},
        {"company":"五粮液", "ticker":"000858.SZ", "period":"2026H1", "end":"2026-06-30", "revenue":28416674541.77, "profit_parent":8752942991.31, "operating_cashflow":-2153568792.32}
    ],
    "explanation":"五粮液报告将利润增幅归因于上年同期低基数及动销举措等；现金流下降受收款政策变化及银行承兑汇票到期额度同比减少等影响。"
}
raw_path = REF / "maotai_qq_daily.json"
raw = json.loads(raw_path.read_text(encoding="utf-8"))
if raw.get("code") != 0:
    raise ValueError("Tencent data returned failure")
rows = [r for r in raw["data"]["sh600519"]["day"] if "2026-09-01" <= r[0] <= "2026-10-15"]
if not rows or rows[-1][0] != "2026-10-15":
    raise ValueError("Expected market cutoff not present")
market = pd.DataFrame([dict(date=r[0], open=float(r[1]),close=float(r[2]),high=float(r[3]),low=float(r[4]),volume=float(r[5])*100,amount=float(r[8])*10000) for r in rows])
dest = ROOT / "data" / "market_verified.csv"
market.to_csv(dest,index=False)
raw_dest = ROOT / "data" / "raw" / "maotai_qq_20261016.json"
raw_dest.parent.mkdir(exist_ok=True)
shutil.copyfile(raw_path, raw_dest)
data["market"] = {
    "verified":True, "file":"market_verified.csv", "as_of":"2026-10-15", "start":"2026-09-01", "observations":len(market),
    "adjustment":"不复权", "price_unit":"人民币元", "volume_unit":"股", "amount_unit":"人民币元",
    "reason":"已保存腾讯证券公开历史日线响应并核对字段与范围；单一公开来源，不保证交易日连续或等同交易所最终口径。",
    "source":{"id":"S3", "title":"腾讯证券 · 贵州茅台历史日线冻结快照", "url":"https://gu.qq.com/sh600519/gp",
        "endpoint":"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=sh600519,day,2026-09-01,2026-10-15,60,",
        "disclosed_at":"2026-10-15", "fetched_at":stamp, "period":"2026-09-01 / 2026-10-15",
        "locator":"data.sh600519.day；本地严格筛选date范围，忽略返回的实时qt字段",
        "unit":"价格元 / 成交量股 / 成交额元", "scope":"非复权日线；上交所主板成交量由手×100换算为股，成交额由万元×10000换算为元",
        "mapping_reference":"https://github.com/akfamily/akshare/blob/main/akshare/stock_feature/stock_hist_tx.py",
        "sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest(), "csv_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(), "raw_file":"raw/maotai_qq_20261016.json"}
}
data["valuation"] = {
    "as_of":"2026-10-15", "price":float(market.iloc[-1].close), "shares":1250081601, "shares_as_of":"2026-06-30",
    "equity_parent":251253594419.50, "equity_as_of":"2026-06-30", "ttm_start":"2025-07-01", "ttm_end":"2026-06-30",
    "status":"试算", "assumption":"沿用2026-06-30期末股本，尚未核验期末至估值日的股本变化；因此仅为历史口径试算，非当日官方PE/PB。",
    "sources":["S1","S3","S4"]
}
data_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"version":data["dataset_version"],"market_rows":len(market),"cutoff":data["market"]["as_of"],"verified_at":stamp},ensure_ascii=False))
