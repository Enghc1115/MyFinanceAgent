#!/usr/bin/env python
"""
generate_report.py — 生成 A 股市场日度报告 (Markdown)

用法:
  .venv/bin/python scripts/generate_report.py --date 2026-05-08
  .venv/bin/python scripts/generate_report.py  # 默认今天

数据来源:
  - data/{date}.csv          — 日频行情快照（由 get_market_data.py 生成）
  - AkShare 板块资金流向      — stock_fund_flow_industry
  - AkShare 北向资金          — stock_hsgt_fund_flow_summary_em
  - AkShare 历史指数          — stock_zh_index_daily_tx

模块:
  - core_utils.py     — CSV 读取、环比计算、报告组装
  - sector_flow.py    — 板块资金流向
  - northbound.py     — 北向资金
  - us_market.py      — 美股行情
  - cny_rate.py       — 人民币汇率
  - headlines.py      — 多源驱动新闻
  - top_gainers.py    — 涨幅榜
  - market_activity.py— 市场活跃度
  - individual_flow.py— 个股资金流入
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# 确保项目根在 sys.path（兼容直接运行和包导入两种方式）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import DATA_DIR, REPORTS_DIR

from scripts.core_utils import (
    read_csv_data,
    find_prev_csv_date,
    calc_change_vs_prev,
    generate_summary,
    generate_report,
)
from scripts.sector_flow import fetch_industry_flow_with_anomalies
from scripts.northbound import fetch_northbound_deal_amt
from scripts.us_market import fetch_us_market, fetch_us_leader_stocks, fetch_overseas_headlines
from scripts.cny_rate import fetch_cny_rate
from scripts.headlines import fetch_driven_news
from scripts.top_gainers import fetch_top_gainers, fetch_top_losers
from scripts.market_activity import fetch_market_activity
from scripts.individual_flow import fetch_individual_flow
from scripts.us_market import fetch_us_sector_etfs
from scripts.headlines import build_entity_price_table


def main():
    parser = argparse.ArgumentParser(description="A 股市场日度报告生成")
    parser.add_argument("--date", type=str, default=None,
                        help="交易日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV 文件路径，默认 data/{date}.csv")
    parser.add_argument("--deep", action="store_true",
                        help="同时生成深度分析报告")
    args = parser.parse_args()

    # 确定日期
    if args.date:
        date_str = args.date
    else:
        date_str = date.today().isoformat()

    # 验证日期格式
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"[错误] 日期格式不正确，请使用 YYYY-MM-DD 格式: {date_str}", file=sys.stderr)
        sys.exit(1)

    # 确定 CSV 路径
    if args.csv:
        csv_path = Path(args.csv).resolve()
    else:
        csv_path = (DATA_DIR / f"{date_str}.csv").resolve()

    if not csv_path.exists():
        alt_path = DATA_DIR / f"{date_str}.csv"
        if alt_path.exists():
            csv_path = alt_path
        else:
            print(f"[错误] 未找到 CSV 文件: {csv_path}", file=sys.stderr)
            print(f"  data/ 目录下现有文件: {[f.name for f in DATA_DIR.glob('*.csv')] if DATA_DIR.exists() else 'data/ 目录不存在'}", file=sys.stderr)
            sys.exit(1)

    print(f"正在读取数据: {csv_path}")
    try:
        stats = read_csv_data(str(csv_path))
    except Exception as e:
        print(f"[错误] CSV 读取失败: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"数据时间: {stats['time']}  股票总数: {stats['total']}")
    print()

    # 获取板块资金流向（含异动检测）
    print("正在获取板块资金流向...", end=" ", flush=True)
    industry_table, anomaly_section, industry_error = fetch_industry_flow_with_anomalies(date_str)
    if industry_error:
        print(f"[跳过] {industry_error}")
    else:
        print("OK")
    if anomaly_section:
        print("  资金方向变化已检测")

    # 获取北向资金
    print("正在获取北向资金...", end=" ", flush=True)
    northbound_table, northbound_error = fetch_northbound_deal_amt(date_str)
    if northbound_error:
        print(f"[跳过] {northbound_error}")
    else:
        print("OK")

    # 获取美股行情
    print("正在获取美股行情...", end=" ", flush=True)
    us_table, us_error = fetch_us_market(date_str)
    if us_error:
        print(f"[跳过] {us_error}")
    else:
        print("OK")

    # 获取人民币汇率
    print("正在获取人民币汇率...", end=" ", flush=True)
    cny_info, cny_error = fetch_cny_rate(date_str)
    if cny_error:
        print(f"[跳过] {cny_error}")
    else:
        print("OK")

    # 获取多源驱动新闻
    print("正在获取驱动新闻...", end=" ", flush=True)
    driven_news_table, driven_news_error = fetch_driven_news()
    if driven_news_error:
        print(f"[跳过] {driven_news_error}")
    else:
        print("OK")

    # 获取涨幅榜
    print("正在获取涨幅榜...", end=" ", flush=True)
    gainers_table, gainers_error = fetch_top_gainers()
    if gainers_error:
        print(f"[跳过] {gainers_error}")
    else:
        print("OK")

    # 获取跌幅榜
    print("正在获取跌幅榜...", end=" ", flush=True)
    losers_table, losers_error = fetch_top_losers()
    if losers_error:
        print(f"[跳过] {losers_error}")
    else:
        print("OK")

    # 环比前一交易日
    print("计算环比前一交易日...", end=" ", flush=True)
    prev_csv_date = find_prev_csv_date(target_date)
    if prev_csv_date:
        change_vs_prev = calc_change_vs_prev(stats["total_amount"], prev_csv_date)
        print(f"前交易日: {prev_csv_date}, 变化: {change_vs_prev}")
    else:
        change_vs_prev = "暂无历史数据"
        print("未找到前一交易日数据")

    # 获取海外头条
    print("正在获取海外市场消息...", end=" ", flush=True)
    overseas_section, overseas_error = fetch_overseas_headlines()
    if overseas_error:
        print(f"[跳过] {overseas_error}")
    else:
        print("OK")

    # 计算市场活跃度
    print("正在计算市场活跃度...", end=" ", flush=True)
    activity_section, activity_error = fetch_market_activity(stats)
    if activity_error:
        print(f"[跳过] {activity_error}")
    else:
        print("OK")

    # 获取个股资金流入 TOP10
    print("正在获取个股资金流入 TOP10...", end=" ", flush=True)
    individual_flow_table, individual_flow_error = fetch_individual_flow()
    if individual_flow_error:
        print(f"[跳过] {individual_flow_error}")
    else:
        print("OK")

    # 获取美股龙头催化行情
    print("正在获取美股龙头催化行情...", end=" ", flush=True)
    us_leader_table, us_leader_error = fetch_us_leader_stocks(date_str)
    if us_leader_error:
        print(f"[跳过] {us_leader_error}")
    else:
        print("OK")

    # 获取美股板块ETF映射
    print("正在获取美股板块ETF映射...", end=" ", flush=True)
    us_etf_table, us_etf_error = fetch_us_sector_etfs(date_str)
    if us_etf_error:
        print(f"[跳过] {us_etf_error}")
    else:
        print("OK")

    # 获取新闻-个股联动表
    print("正在生成新闻-个股联动表...", end=" ", flush=True)
    entity_price_table, entity_price_error = build_entity_price_table(date_str)
    if entity_price_error:
        print(f"[跳过] {entity_price_error}")
    else:
        print("OK")

    # 生成总结
    summary = generate_summary(stats, industry_error, northbound_error,
                               us_error, cny_error, driven_news_error, gainers_error,
                               losers_error)

    # 生成报告
    report = generate_report(
        stats=stats,
        date_str=date_str,
        change_vs_prev=change_vs_prev,
        industry_table=industry_table,
        northbound_table=northbound_table,
        summary=summary,
        anomaly_section=anomaly_section,
        us_table=us_table,
        cny_info=cny_info,
        gainers_table=gainers_table,
        losers_table=losers_table,
        driven_news_table=driven_news_table,
        overseas_section=overseas_section,
        activity_section=activity_section,
        individual_flow_table=individual_flow_table,
        us_leader_table=us_leader_table,
        us_etf_table=us_etf_table,
        entity_price_table=entity_price_table,
    )

    # 打印
    print("\n" + "=" * 42)
    print(report)
    print("=" * 42)

    # 保存
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"报告已保存: {report_path.resolve()}")

    # 尝试生成深度报告（收盘后）
    if args.deep:
        print("\n正在尝试生成深度报告...")
        try:
            from scripts.generate_deep_report import main as generate_deep
            import sys as _sys
            _orig_argv = _sys.argv[:]
            _sys.argv = ["generate_deep_report.py", "--date", date_str]
            generate_deep()
            _sys.argv = _orig_argv
        except Exception as e:
            print(f"[跳过] 深度报告生成失败: {e}")
    else:
        print("\n使用 --deep 参数可同时生成深度分析报告")


if __name__ == "__main__":
    main()
