#!/usr/bin/env python3
"""prep_deep_data.py — 收盘后收集深度分析所需的全量数据，保存为 JSON"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import akshare as ak

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, PROJECT_ROOT
from scripts.knowledge_base import US_SECTOR_ETFS, US_LEADER_STOCKS

DEEP_DIR = DATA_DIR / "deep"


def safe_get(fn, default=None):
    try:
        return fn()
    except Exception as e:
        return default


def _fetch_us_etf_data():
    """Fetch US sector ETF data for all tracked ETFs."""
    results = {}
    for symbol, info in US_SECTOR_ETFS.items():
        try:
            df = ak.stock_us_daily(symbol)
            if df is not None and not df.empty:
                r = df.iloc[-1]
                close = float(r["close"])
                open_p = float(r["open"])
                change = (close - open_p) / open_p * 100
                results[symbol] = {
                    "name": info["name"],
                    "close": close,
                    "change": round(change, 2),
                }
        except Exception:
            results[symbol] = {"name": info["name"], "error": "获取失败"}
    return results


def _fetch_us_leader_data():
    """Fetch US leader stock data for all tracked stocks."""
    results = {}
    for symbol, info in US_LEADER_STOCKS.items():
        try:
            df = ak.stock_us_daily(symbol)
            if df is not None and not df.empty:
                r = df.iloc[-1]
                close = float(r["close"])
                open_p = float(r["open"])
                change = (close - open_p) / open_p * 100
                results[symbol] = {
                    "name": info["name_cn"],
                    "category": info["category"],
                    "close": close,
                    "change": round(change, 2),
                }
        except Exception:
            results[symbol] = {"name": info["name_cn"], "category": info["category"], "error": "获取失败"}
    return results


def collect():
    DEEP_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    today_raw = date.today().strftime("%Y%m%d")
    payload = {"date": today, "collected_at": datetime.now().isoformat(), "sections": {}}

    # 1. 板块资金流向
    sector = safe_get(lambda: ak.stock_fund_flow_industry("即时"))
    if sector is not None:
        payload["sections"]["sector_flow"] = json.loads(sector.to_json(orient="records", force_ascii=False))
    print("  [1/8] 板块资金流向 ✓")

    # 2. 个股资金流入
    individual = safe_get(lambda: ak.stock_fund_flow_individual("即时"))
    if individual is not None:
        payload["sections"]["individual_flow"] = json.loads(individual.to_json(orient="records", force_ascii=False))
    print("  [2/8] 个股资金流入 ✓")

    # 3. 涨停池
    zt = safe_get(lambda: ak.stock_zt_pool_em(date=today_raw))
    if zt is not None:
        payload["sections"]["limit_up_pool"] = json.loads(zt.to_json(orient="records", force_ascii=False))
    print("  [3/8] 涨停池 ✓")

    # 4. 跌停池
    dt = safe_get(lambda: ak.stock_zt_pool_dtgc_em(date=today_raw))
    if dt is not None:
        payload["sections"]["limit_down_pool"] = json.loads(dt.to_json(orient="records", force_ascii=False))
    print("  [4/8] 跌停池 ✓")

    # 5. 昨日涨停
    prev = safe_get(lambda: ak.stock_zt_pool_previous_em(date=today_raw))
    if prev is not None:
        payload["sections"]["prev_limit_up"] = json.loads(prev.to_json(orient="records", force_ascii=False))
    print("  [5/8] 昨日涨停 ✓")

    # 6. 美股板块ETF
    us_etf = safe_get(_fetch_us_etf_data, default={})
    payload["sections"]["us_sector_etfs"] = us_etf
    print("  [6/8] 美股板块ETF ✓")

    # 7. 美股龙头
    us_leader = safe_get(_fetch_us_leader_data, default={})
    payload["sections"]["us_leader_stocks"] = us_leader
    print("  [7/8] 美股龙头 ✓")

    # 8. 炸板率 & 昨日涨停表现
    blowup_info = {"炸板数": 0, "涨停总数": 0, "炸板率": 0, "封板成功率": 0, "prev_limit_up_performance": {}}
    if zt is not None:
        try:
            recs = json.loads(zt.to_json(orient="records", force_ascii=False))
            total = len(recs)
            blown = 0
            for r in recs:
                cur_price = float(r.get("最新价", 0))
                limit_price = float(r.get("涨停价", 0))
                if limit_price > 0 and cur_price < limit_price:
                    blown += 1
            rate = round(blown / total * 100, 2) if total > 0 else 0
            blowup_info = {
                "炸板数": blown,
                "涨停总数": total,
                "炸板率": round(rate, 2),
                "封板成功率": round(100 - rate, 2),
            }
        except Exception:
            pass

    # 昨日涨停今日表现
    if prev is not None:
        try:
            prev_recs = json.loads(prev.to_json(orient="records", force_ascii=False))
            if prev_recs:
                up_count = 0
                down_count = 0
                flat_count = 0
                for r in prev_recs:
                    chg = float(r.get("涨跌幅", 0))
                    if chg > 0:
                        up_count += 1
                    elif chg < 0:
                        down_count += 1
                    else:
                        flat_count += 1
                total_prev = len(prev_recs)
                blowup_info["prev_limit_up_performance"] = {
                    "total": total_prev,
                    "上涨数": up_count,
                    "下跌数": down_count,
                    "平盘数": flat_count,
                    "上涨比例": round(up_count / total_prev * 100, 2) if total_prev > 0 else 0,
                    "下跌比例": round(down_count / total_prev * 100, 2) if total_prev > 0 else 0,
                }
        except Exception:
            pass
    payload["sections"]["blow_up_and_prev_performance"] = blowup_info
    print("  [8/8] 炸板率&昨日涨停表现 ✓")

    out_path = DEEP_DIR / f"{today}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  深度数据已保存: {out_path}")


if __name__ == "__main__":
    collect()
