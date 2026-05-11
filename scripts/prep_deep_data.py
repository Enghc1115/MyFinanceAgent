#!/usr/bin/env python3
"""prep_deep_data.py — 收盘后收集深度分析所需的全量数据，保存为 JSON"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import akshare as ak

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, PROJECT_ROOT

DEEP_DIR = DATA_DIR / "deep"


def safe_get(fn, default=None):
    try:
        return fn()
    except Exception as e:
        return default


def collect():
    DEEP_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    today_raw = date.today().strftime("%Y%m%d")
    payload = {"date": today, "collected_at": datetime.now().isoformat(), "sections": {}}

    # 1. 板块资金流向
    sector = safe_get(lambda: ak.stock_fund_flow_industry("即时"))
    if sector is not None:
        payload["sections"]["sector_flow"] = json.loads(sector.to_json(orient="records", force_ascii=False))
    print("  [1/5] 板块资金流向 ✓")

    # 2. 个股资金流入
    individual = safe_get(lambda: ak.stock_fund_flow_individual("即时"))
    if individual is not None:
        payload["sections"]["individual_flow"] = json.loads(individual.to_json(orient="records", force_ascii=False))
    print("  [2/5] 个股资金流入 ✓")

    # 3. 涨停池
    zt = safe_get(lambda: ak.stock_zt_pool_em(date=today_raw))
    if zt is not None:
        payload["sections"]["limit_up_pool"] = json.loads(zt.to_json(orient="records", force_ascii=False))
    print("  [3/5] 涨停池 ✓")

    # 4. 跌停池
    dt = safe_get(lambda: ak.stock_zt_pool_dtgc_em(date=today_raw))
    if dt is not None:
        payload["sections"]["limit_down_pool"] = json.loads(dt.to_json(orient="records", force_ascii=False))
    print("  [4/5] 跌停池 ✓")

    # 5. 昨日涨停
    prev = safe_get(lambda: ak.stock_zt_pool_previous_em(date=today_raw))
    if prev is not None:
        payload["sections"]["prev_limit_up"] = json.loads(prev.to_json(orient="records", force_ascii=False))
    print("  [5/5] 昨日涨停 ✓")

    out_path = DEEP_DIR / f"{today}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  深度数据已保存: {out_path}")


if __name__ == "__main__":
    collect()
