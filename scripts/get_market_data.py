#!/usr/bin/env python
"""
get_market_data.py - 获取 A 股实时行情数据

功能：
  - 大盘指数（上证/深证/创业板/科创50/北证50）
  - 涨跌家数及涨跌比
  - 总成交额（沪深京合计）
  - 涨幅区间分布

数据源：AkShare / 新浪财经

用法：
  .venv/bin/python scripts/get_market_data.py              # 仅打印
  .venv/bin/python scripts/get_market_data.py --save       # 打印 + 保存 CSV
  .venv/bin/python scripts/get_market_data.py --mode close # 收盘模式（输出更详细）

API 报错时优先清除缓存重试：
  rm -rf /tmp/.akshare/ && python scripts/get_market_data.py
"""

import argparse
import csv
import sys
from datetime import datetime

import akshare as ak
import pandas as pd
import requests


from config import DATA_DIR, INDICES_CONFIG, PROJECT_ROOT


def fetch_indices():
    """通过 Sina API 获取主要指数行情"""
    import re
    codes = [code for _, code, _ in INDICES_CONFIG]
    url = f"https://hq.sinajs.cn/list={','.join('s_' + c for c in codes)}"
    resp = requests.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
    resp.encoding = "gbk"

    indices = {}
    for prefix, code, display_name in INDICES_CONFIG:
        m = re.search(rf'hq_str_s_{code}="([^"]+)"', resp.text)
        if not m:
            continue
        fields = m.group(1).split(",")
        # 格式: 名称,当前价,涨跌额,涨跌幅(%),成交量,成交额
        indices[prefix] = {
            "name": display_name,
            "price": float(fields[1]),
            "change": float(fields[3]),
            "change_abs": float(fields[2]),
        }
    return indices


def fetch_stats():
    """获取全 A 行情并计算统计指标，返回 dict"""
    df = ak.stock_zh_a_spot()
    total = len(df)

    up = int((df["涨跌幅"] > 0).sum())
    down = int((df["涨跌幅"] < 0).sum())
    flat = total - up - down
    ratio = round(up / down, 2) if down > 0 else float("inf")
    total_amount = round(df["成交额"].sum() / 1e8, 2)

    limit_up = int((df["涨跌幅"] >= 9.9).sum())
    big_up = int(((df["涨跌幅"] >= 5) & (df["涨跌幅"] < 9.9)).sum())
    small_up = int(((df["涨跌幅"] > 0) & (df["涨跌幅"] < 5)).sum())
    small_down = int(((df["涨跌幅"] < 0) & (df["涨跌幅"] >= -5)).sum())
    big_down = int(((df["涨跌幅"] < -5) & (df["涨跌幅"] >= -9.9)).sum())
    limit_down = int((df["涨跌幅"] <= -9.9).sum())

    avg_change = round(df["涨跌幅"].mean(), 2)
    median_change = round(df["涨跌幅"].median(), 2)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "total": total,
        "up": up,
        "down": down,
        "flat": flat,
        "ratio": ratio,
        "total_amount": total_amount,
        "limit_up": limit_up,
        "big_up": big_up,
        "small_up": small_up,
        "small_down": small_down,
        "big_down": big_down,
        "limit_down": limit_down,
        "avg_change": avg_change,
        "median_change": median_change,
        "indices": fetch_indices(),
    }


def print_report(s, mode="default"):
    """打印报告到终端"""
    sep = "=" * 42
    today = s["date"]

    mode_label = {"morning": "早盘", "noon": "午盘", "close": "收盘"}.get(mode, "")

    print(f"\nA 股{mode_label}市场概况  {today}  {s['time']}")
    print(sep)
    print(f"  上涨  {s['up']:>6d}  下跌  {s['down']:>6d}  平盘  {s['flat']:>5d}")
    print(f"  总数  {s['total']:>6d}")
    print(f"  涨跌比           {s['ratio']}")
    print(f"  总成交额         {s['total_amount']:>8.2f} 亿元")
    print()
    print(f"涨幅分布:")
    print(f"  涨停 (>=9.9%)      {s['limit_up']:>5d}")
    print(f"  大涨 (5%~9.9%)    {s['big_up']:>5d}")
    print(f"  小涨 (0%~5%)      {s['small_up']:>5d}")
    print(f"  小跌 (-5%~0%)     {s['small_down']:>5d}")
    print(f"  大跌 (-5%以下)     {s['big_down']:>5d}")
    print(f"  跌停 (<=-9.9%)    {s['limit_down']:>5d}")
    print()
    print(f"  平均涨幅          {s['avg_change']:>6.2f}%")
    print(f"  涨幅中位数        {s['median_change']:>6.2f}%")
    print()

    indices = s.get("indices", {})
    if indices:
        print(f"指数表现:")
        for prefix, idx in indices.items():
            display_change = f"+{idx['change']:.2f}%" if idx["change"] > 0 else f"{idx['change']:.2f}%"
            print(f"  {idx['name']:<6s}  {idx['price']:>8.2f}  {display_change}")
    print(sep)


def save_csv(s, mode="default"):
    """将统计结果追加保存到 CSV 文件"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"{s['date']}.csv"

    headers = [
        "time", "mode", "total", "up", "down", "flat", "ratio",
        "total_amount", "limit_up", "big_up", "small_up",
        "small_down", "big_down", "limit_down", "avg_change", "median_change",
    ]
    # 添加指数列
    for prefix, _, _ in INDICES_CONFIG:
        headers += [f"{prefix}_price", f"{prefix}_change", f"{prefix}_change_abs"]

    is_new = not filepath.exists()
    # 如文件已存在但列不一致，迁移旧数据并重建
    if not is_new:
        with open(filepath, encoding="utf-8") as f:
            existing_headers = f.readline().rstrip("\n").split(",")
        if existing_headers != headers:
            old_rows = []
            with open(filepath, encoding="utf-8") as f:
                next(f)
                for line in f:
                    line = line.rstrip("\n")
                    if line:
                        old_rows.append(dict(zip(existing_headers, line.split(","))))
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=headers)
                w.writeheader()
                for r in old_rows:
                    w.writerow({k: r.get(k, "") for k in headers})
            print(f"  列已更新，旧数据已迁移: {filepath}")

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if is_new:
            writer.writeheader()
        row = {k: s.get(k, "") for k in headers}
        row["mode"] = mode
        # 填充指数数据
        indices = s.get("indices", {})
        for prefix, idx in indices.items():
            row[f"{prefix}_price"] = idx["price"]
            row[f"{prefix}_change"] = idx["change"]
            row[f"{prefix}_change_abs"] = idx["change_abs"]
        writer.writerow(row)

    print(f"  数据已保存: {filepath}")


SECTOR_FLOW_DIR = PROJECT_ROOT / "data" / "sector_flow"


def save_sector_snapshot(mode="default"):
    """获取板块资金流向并保存快照。"""
    try:
        df = ak.stock_fund_flow_industry("即时")
        df["timestamp"] = datetime.now().strftime("%H:%M:%S")
        SECTOR_FLOW_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = SECTOR_FLOW_DIR / f"{date_str}_{mode}.csv"
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"  板块资金流向已保存: {filepath}")
    except Exception as e:
        print(f"  板块资金流向快照保存失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="A 股行情数据抓取")
    parser.add_argument(
        "--mode", choices=["morning", "noon", "close", "default"],
        default="default", help="抓取时段"
    )
    parser.add_argument(
        "--save", action="store_true", help="保存数据到 CSV"
    )
    args = parser.parse_args()

    try:
        print("正在获取 A 股实时行情数据...", end=" ", flush=True)
        stats = fetch_stats()
        print("OK\n")

        print_report(stats, mode=args.mode)

        if args.save:
            save_csv(stats, mode=args.mode)
            save_sector_snapshot(args.mode)

    except Exception as e:
        print(f"\n[错误] 数据获取失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
