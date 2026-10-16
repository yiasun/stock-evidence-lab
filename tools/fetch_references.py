"""Download fixed public reference sources; never reads account credentials."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import requests

DEST = Path(__file__).resolve().parents[1] / "artifacts" / "references"
SOURCES = {
    "maotai_2026h1.pdf": "https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF",
    "maotai_2025fy.pdf": "https://static.cninfo.com.cn/finalpage/2026-04-17/1225114741.PDF",
    "wuliangye_2026h1.pdf": "https://static.cninfo.com.cn/finalpage/2026-08-29/1225531252.PDF",
    "maotai_qq_daily.json": "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=sh600519,day,2026-09-01,2026-10-15,60,",
}

def fetch(item):
    name, url = item
    try:
        response = requests.get(url, timeout=(8, 30))
        response.raise_for_status()
        raw = response.content
        (DEST / name).write_bytes(raw)
        return {"name": name, "url":url, "bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest(), "header":raw[:20].decode("ascii", errors="replace")}
    except requests.RequestException as exc:
        return {"name": name, "error":type(exc).__name__, "detail":str(exc)[:180]}

if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        print(json.dumps(list(pool.map(fetch, SOURCES.items())), ensure_ascii=False, indent=2))
