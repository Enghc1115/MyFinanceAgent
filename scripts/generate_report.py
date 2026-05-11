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
"""

import argparse
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

import akshare as ak
import pandas as pd


from config import DATA_DIR, REPORTS_DIR, INDICES_CONFIG

# 指数前缀 → 显示名
INDICES_MAP = [(p, n) for p, _, n in INDICES_CONFIG]


def read_csv_data(csv_path: str) -> dict:
    """从 CSV 末行解析行情统计数据，返回 dict。"""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV 文件为空: {csv_path}")
    row = df.iloc[-1]  # 最后一行 = 最新快照

    stats = {
        "time":       str(row.get("time", "")),
        "total":      int(row.get("total", 0)),
        "up":         int(row.get("up", 0)),
        "down":       int(row.get("down", 0)),
        "flat":       int(row.get("flat", 0)),
        "ratio":      _safe_float(row.get("ratio", 0)),
        "total_amount": _safe_float(row.get("total_amount", 0)),
        "limit_up":   int(row.get("limit_up", 0)),
        "big_up":     int(row.get("big_up", 0)),
        "small_up":   int(row.get("small_up", 0)),
        "small_down": int(row.get("small_down", 0)),
        "big_down":   int(row.get("big_down", 0)),
        "limit_down": int(row.get("limit_down", 0)),
        "avg_change":    _safe_float(row.get("avg_change", 0)),
        "median_change": _safe_float(row.get("median_change", 0)),
    }

    # 指数行情
    indices = {}
    for prefix, name in INDICES_MAP:
        price = _safe_float(row.get(f"{prefix}_price", None))
        change = _safe_float(row.get(f"{prefix}_change", None))
        if price is not None and change is not None:
            indices[prefix] = {"name": name, "price": price, "change": change}
    stats["indices"] = indices

    return stats


def _safe_float(val, default=None):
    """安全转 float，不可转时返回 default。"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ----- 板块资金流向 -----

def fetch_industry_flow() -> tuple:
    """获取板块资金流向 Top 5（含龙头个股）。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_fund_flow_industry("即时")
        name_col = "行业"
        net_col = "净额"
        leader_col = "领涨股"
        leader_change_col = "领涨股-涨跌幅"
        needed = [name_col, net_col, leader_col, leader_change_col]
        if not all(c in df.columns for c in needed):
            return None, f"未找到所需列，实际列: {list(df.columns)}"

        top5 = df.sort_values(net_col, ascending=False).head(5)
        lines = ["| 板块 | 净额(亿) | 龙头个股 | 龙头涨跌幅 |",
                  "|------|----------|----------|------------|"]
        for _, r in top5.iterrows():
            change = r[leader_change_col]
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(f"| {r[name_col]} | {r[net_col]:.2f} | {r[leader_col]} | {change_str} |")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"板块资金流向获取失败: {e}"


def detect_flow_anomalies(target_date_str: str, current_df) -> str:
    """检测板块主力资金方向变化。

    比较当前板块资金流向与当日历史快照，
    标记由净流入<->净流出的方向转换。

    Returns:
        markdown section or empty string
    """
    sector_flow_dir = DATA_DIR / "sector_flow"
    if not sector_flow_dir.exists():
        return ""

    # 确定 mode 顺序，找当日最新的历史快照
    mode_order = {"morning": 0, "noon": 1, "close": 2}
    candidates = []
    for f in sector_flow_dir.glob(f"{target_date_str}_*.csv"):
        stem = f.stem  # e.g. "2026-05-08_morning"
        parts = stem.split("_", 1)
        if len(parts) == 2 and parts[1] in mode_order:
            candidates.append((mode_order[parts[1]], f))

    if not candidates:
        return ""

    candidates.sort(key=lambda x: x[0])
    prev_path = candidates[-1][1]  # 取最晚保存的快照

    try:
        prev_df = pd.read_csv(prev_path)
        name_col = "行业"
        net_col = "净额"

        if name_col not in prev_df.columns or net_col not in prev_df.columns:
            return ""

        merged = current_df[[name_col, net_col]].merge(
            prev_df[[name_col, net_col]],
            on=name_col,
            suffixes=("_current", "_prev"),
            how="inner",
        )

        anomalies = []
        for _, r in merged.iterrows():
            prev_net = r[f"{net_col}_prev"]
            curr_net = r[f"{net_col}_current"]

            if prev_net >= 0 and curr_net < 0:
                anomalies.append(
                    (r[name_col], "⚠️ 由净流入转为净流出", prev_net, curr_net)
                )
            elif prev_net < 0 and curr_net >= 0:
                anomalies.append(
                    (r[name_col], "↑ 由净流出转为净流入", prev_net, curr_net)
                )

        if not anomalies:
            return ""

        lines = [
            "## 异动监测",
            "",
            "### ⚠️ 主力资金方向变化",
            "",
            "| 板块 | 方向变化 | 前净额(亿) | 现净额(亿) |",
            "|------|---------|-----------|-----------|",
        ]
        for name, direction, prev_val, curr_val in anomalies:
            lines.append(
                f"| {name} | {direction} | {prev_val:.2f} | {curr_val:.2f} |"
            )
        return "\n".join(lines)
    except Exception:
        return ""


def fetch_industry_flow_with_anomalies(target_date_str: str) -> tuple:
    """获取板块资金流向 Top 5（含龙头个股）并检测资金方向异动。

    Returns:
        (markdown_table_or_None, anomaly_section_or_None, error_or_None)
    """
    try:
        df = ak.stock_fund_flow_industry("即时")
        name_col = "行业"
        net_col = "净额"
        leader_col = "领涨股"
        leader_change_col = "领涨股-涨跌幅"
        needed = [name_col, net_col, leader_col, leader_change_col]
        if not all(c in df.columns for c in needed):
            return None, None, f"未找到所需列，实际列: {list(df.columns)}"

        # TOP 5 表（含龙头个股）
        top5 = df.sort_values(net_col, ascending=False).head(5)
        lines = [
            "| 板块 | 净额(亿) | 龙头个股 | 龙头涨跌幅 |",
            "|------|----------|----------|------------|",
        ]
        for _, r in top5.iterrows():
            change = r[leader_change_col]
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(
                f"| {r[name_col]} | {r[net_col]:.2f} | {r[leader_col]} | {change_str} |"
            )
        table = "\n".join(lines)

        # 异动检测
        anomaly_section = detect_flow_anomalies(target_date_str, df)

        return table, anomaly_section, None
    except Exception as e:
        return None, None, f"板块资金流向获取失败: {e}"


# ----- 北向资金 -----

def fetch_northbound_deal_amt(target_date_str: str) -> tuple:
    """通过 East Money 数据中心获取北向资金日度成交额。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        import requests as _req
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_MUTUAL_DEALAMT",
            "columns": "TRADE_DATE,NF_DEAL_AMT,SSC_DEAL_AMT,ST_DEAL_AMT",
            "filter": f"(TRADE_DATE='{target_date_str}')",
            "pageNumber": "1", "pageSize": "5",
            "source": "WEB", "client": "WEB",
        }
        r = _req.get(url, params=params,
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = r.json()
        rows = (data.get("result") or {}).get("data", [])
        if not rows:
            return None, f"未找到 {target_date_str} 北向资金数据"

        rec = rows[0]
        # 单位: 百万元 → 亿元 (/100)
        nf = rec["NF_DEAL_AMT"] / 100
        ssc = rec["SSC_DEAL_AMT"] / 100
        st = rec["ST_DEAL_AMT"] / 100

        lines = [
            "| 通道 | 成交额(亿) |",
            "|------|-----------|",
            f"| 沪股通 | {ssc:.2f} |",
            f"| 深股通 | {st:.2f} |",
            f"| 北向合计 | {nf:.2f} |",
        ]
        return "\n".join(lines), None
    except Exception as e:
        return None, f"北向资金获取失败: {e}"


# ----- 美股行情 -----

def fetch_us_market(target_date_str: str) -> tuple:
    """获取美股三大指数行情（SPY、QQQ、DIA），含隔夜涨跌方向和 A 股映射提示。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        symbols = {"SPY": "S&P 500(SPY)", "QQQ": "Nasdaq(QQQ)", "DIA": "Dow(DIA)"}
        lines = ["| 指数 | 收盘价 | 涨跌幅 | 方向 |", "|------|--------|--------|------|"]
        directions = []
        for symbol, name in symbols.items():
            df = ak.stock_us_daily(symbol)
            df["date"] = df["date"].astype(str)
            row = df[df["date"] == target_date_str]
            if row.empty:
                lines.append(f"| {name} | - | - | - |")
                continue
            r = row.iloc[0]
            close = float(r["close"])
            open_ = float(r["open"])
            change = (close - open_) / open_ * 100
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            direction = "🟢 上涨" if change > 0 else ("🔴 下跌" if change < 0 else "⚪ 平盘")
            directions.append(direction)
            lines.append(f"| {name} | {close:.2f} | {change_str} | {direction} |")

        # 整体方向判断
        table = "\n".join(lines)

        # A 股映射提示
        mapping_notes = []
        if "S&P" in table:
            mapping_notes.append("美股走势影响次日北向资金方向和 A 股开盘情绪")
        if "Nasdaq" in table:
            mapping_notes.append("纳指走势映射 A 股科技/半导体/AI 算力板块")
        if "Dow" in table:
            mapping_notes.append("道指走势映射 A 股金融/消费/周期板块")

        result = table + "\n\n**A 股映射**：" + "；".join(mapping_notes)
        return result, None
    except Exception as e:
        return None, f"美股行情获取失败: {e}"


def fetch_overseas_headlines() -> tuple:
    """从财联社头条中筛选海外相关新闻，补充海外市场动态。

    Returns:
        (markdown_list_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_info_global_cls()
        # 海外关键词
        overseas_kw = ["美股", "美元", "美联储", "原油", "黄金", "英伟达", "NVIDIA",
                       "AMD", "英特尔", "美光", "特斯拉", "苹果", "OpenAI",
                       "欧洲", "日本", "韩国", "台积电", "安森美", "美伊",
                       "伊朗", "战争", "原油", "北约", "API", "全球"]
        matches = []
        for _, r in df.iterrows():
            text = str(r.get("标题", "")) + str(r.get("内容", ""))
            if any(kw in text for kw in overseas_kw):
                title = r.get("标题", "")
                if title and title not in matches:
                    matches.append(f"- 🌍 {title}")
        if matches:
            return "\n".join(matches[:8]), None  # 最多8条
        return "*当日财联社头条中未发现海外相关新闻*", None
    except Exception as e:
        return None, f"海外头条筛选失败: {e}"


# ----- 人民币汇率 -----

def fetch_cny_rate(target_date_str: str) -> tuple:
    """获取 USD/CNY 人民币汇率。

    Returns:
        (info_str_or_None, error_str_or_None)
    """
    try:
        from datetime import date
        target = date.fromisoformat(target_date_str)
        df = ak.currency_boc_safe()
        row = df[df["日期"] == target]
        if row.empty:
            latest = df["日期"].iloc[-1]
            return None, f"未找到 {target_date_str} 汇率数据，最新可用: {latest}"
        rate = float(row["美元"].iloc[0]) / 100
        return f"USD/CNY: {rate:.4f}", None
    except Exception as e:
        return None, f"汇率获取失败: {e}"


# ----- 涨幅榜 -----

def fetch_top_gainers() -> tuple:
    """获取 A 股涨幅榜 Top 10。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_zh_a_spot()
        df = df.sort_values("涨跌幅", ascending=False).head(10)
        lines = ["| 代码 | 名称 | 最新价 | 涨跌幅 |", "|------|------|--------|--------|"]
        for _, r in df.iterrows():
            code = r.get("代码", "")
            name = r.get("名称", "")
            price = r.get("最新价", 0)
            change = r.get("涨跌幅", 0)
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(f"| {code} | {name} | {price:.2f} | {change_str} |")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"涨幅榜获取失败: {e}"


# ----- 财联社头条 -----

def fetch_cls_headlines() -> tuple:
    """获取财联社全球财经头条 Top 5。

    Returns:
        (markdown_list_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_info_global_cls()
        top5 = df.head(5)
        lines = []
        for _, r in top5.iterrows():
            title = r.get("标题", "")
            if title:
                lines.append(f"- {title}")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"头条获取失败: {e}"


def fetch_overseas_headlines() -> tuple:
    """从财联社头条中筛选海外相关新闻，补充海外市场动态。

    Returns:
        (markdown_list_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_info_global_cls()
        # 海外关键词
        overseas_kw = ["美股", "美元", "美联储", "原油", "黄金", "英伟达", "NVIDIA",
                       "AMD", "英特尔", "美光", "特斯拉", "苹果", "OpenAI",
                       "欧洲", "日本", "韩国", "台积电", "安森美", "美伊",
                       "伊朗", "战争", "原油", "北约", "API", "全球"]
        matches = []
        for _, r in df.iterrows():
            text = str(r.get("标题", "")) + str(r.get("内容", ""))
            if any(kw in text for kw in overseas_kw):
                title = r.get("标题", "")
                if title and title not in matches:
                    matches.append(f"- 🌍 {title}")
        if matches:
            return "\n".join(matches[:8]), None  # 最多8条
        return "*当日财联社头条中未发现海外相关新闻*", None
    except Exception as e:
        return None, f"海外头条筛选失败: {e}"


# ----- 市场活跃度 -----

def fetch_market_activity(stats: dict) -> tuple:
    """基于现有数据计算市场活跃度指标。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        total = stats["total"]
        up = stats["up"]
        down = stats["down"]
        limit_up = stats["limit_up"]
        total_amount = stats["total_amount"]
        ratio = stats["ratio"]
        avg_change = stats["avg_change"]

        # 涨停密度：涨停家数占比
        limit_up_density = limit_up / total * 100 if total > 0 else 0

        # 上涨占比
        up_ratio = up / total * 100 if total > 0 else 0

        # 涨跌强度：(上涨+涨停) / (下跌+跌停)
        big_up = stats["big_up"]
        big_down = stats["big_down"]
        limit_down = stats["limit_down"]
        strength_up = up + limit_up
        strength_down = down + limit_down
        strength_ratio = f"{strength_up / strength_down:.2f}" if strength_down > 0 else "∞"

        # 综合判定
        if ratio >= 2 and limit_up_density >= 2:
            verdict = "🔥🔥 非常活跃"
            detail = "市场赚钱效应强，资金参与度高"
        elif ratio >= 1.5 and limit_up_density >= 1:
            verdict = "🔥 活跃"
            detail = "市场有一定赚钱效应"
        elif ratio >= 1:
            verdict = "⚪ 一般"
            detail = "涨跌均衡，无明显偏向"
        elif ratio < 0.8:
            verdict = "❄️ 低迷"
            detail = "市场情绪偏弱"
        else:
            verdict = "⚪ 一般"
            detail = "市场处于观望状态"

        lines = [
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 总成交额 | {total_amount:.2f}亿 | 资金参与规模 |",
            f"| 涨跌比 | {ratio} | 多头/空头力量对比 |",
            f"| 上涨占比 | {up_ratio:.1f}% | 市场宽度 |",
            f"| 涨停密度 | {limit_up_density:.2f}% | 追涨意愿 |",
            f"| 涨跌强度比 | {strength_ratio} | 多空极端值对比 |",
            f"| 市场活跃度 | {verdict} | {detail} |",
        ]
        return "\n".join(lines), None
    except Exception as e:
        return None, f"市场活跃度计算失败: {e}"


# ----- 个股资金流入 TOP10 -----

def fetch_individual_flow() -> tuple:
    """获取全市场个股资金净流入 TOP10。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_fund_flow_individual("即时")
        # 解析净额（"1.96亿" → 数值）用于排序
        def parse_val(val):
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).replace(",", "").strip()
            if "亿" in s:
                return float(s.replace("亿", "")) * 1e8
            if "万" in s:
                return float(s.replace("万", "")) * 1e4
            if s.endswith("%"):
                return float(s.rstrip("%"))
            try:
                return float(s) if s else 0
            except ValueError:
                return 0
        df["_net_sort"] = df["净额"].apply(parse_val)
        top10 = df.sort_values("_net_sort", ascending=False).head(10)
        lines = ["| 排名 | 代码 | 名称 | 最新价 | 涨跌幅 | 净流入 |",
                  "|------|------|------|--------|--------|--------|"]
        for i, (_, r) in enumerate(top10.iterrows(), 1):
            change = parse_val(r.get("涨跌幅", 0))
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(f"| {i} | {r.get('股票代码', '')} | {r.get('股票简称', '')} | {r.get('最新价', 0):.2f} | {change_str} | {r.get('净额', '')} |")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"个股资金流入获取失败: {e}"


# ----- 美股龙头催化行情 -----

def fetch_us_leader_stocks(target_date_str: str) -> tuple:
    """获取美股龙头股（NVDA/AMD/AAPL/TSLA/TSM）当日行情及 A 股映射方向。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        leaders = {"NVDA": "英伟达", "AMD": "AMD", "AAPL": "苹果", "TSLA": "特斯拉", "TSM": "台积电"}
        mapping = {
            "NVDA": "AI 算力/光模块/液冷",
            "AMD": "CPU 链/服务器",
            "AAPL": "消费电子/果链",
            "TSLA": "智能驾驶/机器人",
            "TSM": "半导体/芯片",
        }
        lines = ["| 个股 | 收盘价 | 涨跌幅 | A 股映射 |", "|------|--------|--------|----------|"]
        for symbol, name in leaders.items():
            df = ak.stock_us_daily(symbol)
            df["date"] = df["date"].astype(str)
            row = df[df["date"] == target_date_str]
            if row.empty:
                lines.append(f"| {name} | - | - | {mapping.get(symbol, '')} |")
                continue
            r = row.iloc[0]
            close = float(r["close"])
            change = (close - float(r["open"])) / float(r["open"]) * 100
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(f"| {name} | {close:.2f} | {change_str} | {mapping.get(symbol, '')} |")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"美股龙头行情获取失败: {e}"


# ----- 环比前一交易日 -----

def find_prev_csv_date(target_date: date) -> str | None:
    """在 DATA_DIR 中查找 target_date 之前的最新 CSV 日期。

    Returns:
        date_str (YYYY-MM-DD) 或 None
    """
    if not DATA_DIR.exists():
        return None
    candidates = []
    for f in DATA_DIR.iterdir():
        if f.suffix == ".csv" and f.stem.count("-") == 2:
            try:
                d = datetime.strptime(f.stem, "%Y-%m-%d").date()
                if d < target_date:
                    candidates.append((d, f.stem))
            except ValueError:
                continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]  # YYYY-MM-DD


def calc_change_vs_prev(current_amount: float, prev_csv_date: str) -> str:
    """计算总成交额环比前一交易日的变化率。"""
    prev_path = DATA_DIR / f"{prev_csv_date}.csv"
    if not prev_path.exists():
        return "暂无历史数据"
    try:
        prev_df = pd.read_csv(prev_path)
        if prev_df.empty:
            return "暂无历史数据"
        prev_amount = _safe_float(prev_df.iloc[-1].get("total_amount", None))
        if prev_amount is None or prev_amount == 0:
            return "暂无历史数据"
        pct = (current_amount - prev_amount) / prev_amount * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.2f}%"
    except Exception:
        return "暂无历史数据"


# ----- 总结生成 -----

def generate_summary(stats: dict,
                     industry_error: str | None,
                     northbound_error: str | None,
                     us_error: str | None = None,
                     cny_error: str | None = None,
                     cls_error: str | None = None,
                     gainers_error: str | None = None) -> str:
    """生成 2-3 句市场概况总结。"""
    parts = []
    ratio = stats["ratio"]
    avg = stats["avg_change"]
    up = stats["up"]
    down = stats["down"]

    # 1. 大盘强弱
    if ratio > 2:
        parts.append(f"市场表现强势，上涨家数{up}家远超下跌{down}家，涨跌比{ratio}，平均涨幅{avg:.2f}%。")
    elif ratio > 1:
        parts.append(f"市场整体偏强，上涨{up}家 vs 下跌{down}家（涨跌比{ratio}），平均涨幅{avg:.2f}%。")
    elif ratio == 1:
        parts.append(f"市场涨跌均衡（涨跌比{ratio}），平均涨幅{avg:.2f}%。")
    else:
        parts.append(f"市场表现偏弱，下跌{down}家多于上涨{up}家（涨跌比{ratio}），平均涨幅{avg:.2f}%。")

    # 2. 指数分化
    indices = stats.get("indices", {})
    changes = {p: idx["change"] for p, idx in indices.items()}
    if changes:
        max_prefix = max(changes, key=changes.get)
        min_prefix = min(changes, key=changes.get)
        spread = changes[max_prefix] - changes[min_prefix]
        if spread > 1.5:
            name_max = indices[max_prefix]["name"]
            name_min = indices[min_prefix]["name"]
            parts.append(f"指数分化明显，{name_max}领涨（{changes[max_prefix]:.2f}%），{name_min}承压（{changes[min_prefix]:.2f}%）。")

    # 3. 备注错误
    if industry_error:
        parts.append(f"（板块数据: {industry_error}）")
    if northbound_error:
        parts.append(f"（北向数据: {northbound_error}）")
    if us_error:
        parts.append(f"（美股数据: {us_error}）")
    if cny_error:
        parts.append(f"（汇率数据: {cny_error}）")
    if cls_error:
        parts.append(f"（头条数据: {cls_error}）")
    if gainers_error:
        parts.append(f"（涨幅榜数据: {gainers_error}）")

    return " ".join(parts)


# ----- 报告生成 -----

def generate_report(stats: dict, date_str: str,
                    change_vs_prev: str,
                    industry_table: str | None,
                    northbound_table: str | None,
                    summary: str,
                    anomaly_section: str | None = None,
                    us_table: str | None = None,
                    cny_info: str | None = None,
                    gainers_table: str | None = None,
                    cls_table: str | None = None,
                    overseas_section: str | None = None,
                    activity_section: str | None = None,
                    individual_flow_table: str | None = None,
                    us_leader_table: str | None = None) -> str:
    """组装完整 Markdown 报告。"""
    idx = stats["indices"]

    # 大盘指数表
    idx_lines = ["| 指数 | 收盘价 | 涨跌幅 |", "|------|--------|--------|"]
    for prefix, name in INDICES_MAP:
        if prefix in idx:
            i = idx[prefix]
            change_str = f"+{i['change']:.2f}%" if i["change"] > 0 else f"{i['change']:.2f}%"
            idx_lines.append(f"| {name} | {i['price']:.2f} | {change_str} |")
        else:
            idx_lines.append(f"| {name} | - | - |")
    index_table = "\n".join(idx_lines)

    # 环比说明
    change_desc = f"环比前一交易日: {change_vs_prev}" if change_vs_prev != "暂无历史数据" else "暂无历史数据"

    # 涨幅分布表
    dist_lines = [
        "| 区间 | 家数 |",
        "|------|------|",
        f"| 涨停 (>=9.9%) | {stats['limit_up']} |",
        f"| 大涨 (5%~9.9%) | {stats['big_up']} |",
        f"| 小涨 (0%~5%) | {stats['small_up']} |",
        f"| 小跌 (-5%~0%) | {stats['small_down']} |",
        f"| 大跌 (-5%以下) | {stats['big_down']} |",
        f"| 跌停 (<=-9.9%) | {stats['limit_down']} |",
    ]
    dist_table = "\n".join(dist_lines)

    # 板块
    industry_section = industry_table or "*数据获取失败*"
    # 异动监测
    anomaly_display = f"\n{anomaly_section}\n" if anomaly_section else ""
    # 北向
    northbound_section = northbound_table or "*数据获取失败*"
    # 宏观
    us_section = us_table or "*数据获取失败*"
    cny_section = cny_info or "*数据获取失败*"
    # 海外头条
    overseas_display = f"\n{overseas_section}\n" if overseas_section else ""
    # 美股龙头催化
    us_leader_display = f"\n{us_leader_table}\n" if us_leader_table else ""
    # 市场活跃度
    activity_display = f"\n{activity_section}\n" if activity_section else ""
    # 涨幅榜
    gainers_section = gainers_table or "*数据获取失败*"
    # 个股资金流入
    individual_flow_display = f"\n{individual_flow_table}\n" if individual_flow_table else ""
    # 头条
    cls_section = cls_table or "*数据获取失败*"

    report = f"""# A 股市场日报 — {date_str}

## 大盘指数

{index_table}

## 宏观市场

{us_section}

{cny_section}

## 海外市场

{overseas_display}

### 海外龙头催化

{us_leader_display}

## 市场活跃度

{activity_display}

## 市场概况

- **上涨家数**: {stats["up"]}  **下跌家数**: {stats["down"]}  **平盘**: {stats["flat"]}
- **涨跌比**: {stats["ratio"]}
- **总成交额**: {stats["total_amount"]:.2f} 亿元
- **{change_desc}**

### 涨幅分布

{dist_table}

- **平均涨幅**: {stats["avg_change"]:.2f}%
- **涨幅中位数**: {stats["median_change"]:.2f}%

## 板块资金流向

{industry_section}
{anomaly_display}
## 个股资金流入 TOP10

{individual_flow_display}
## 北向资金

> 注：北向净额数据暂不可用，以下为成交额数据。

{northbound_section}

## 涨幅榜

{gainers_section}

## 今日头条

{cls_section}

## 总结

{summary}
"""
    return report


def main():
    parser = argparse.ArgumentParser(description="A 股市场日度报告生成")
    parser.add_argument("--date", type=str, default=None,
                        help="交易日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV 文件路径，默认 data/{date}.csv")
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
        # 尝试在 data/ 下找（当传入相对路径但不在 data/ 下时）
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

    # 获取财联社头条
    print("正在获取今日头条...", end=" ", flush=True)
    cls_table, cls_error = fetch_cls_headlines()
    if cls_error:
        print(f"[跳过] {cls_error}")
    else:
        print("OK")

    # 获取涨幅榜
    print("正在获取涨幅榜...", end=" ", flush=True)
    gainers_table, gainers_error = fetch_top_gainers()
    if gainers_error:
        print(f"[跳过] {gainers_error}")
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

    # 生成总结
    summary = generate_summary(stats, industry_error, northbound_error,
                               us_error, cny_error, cls_error, gainers_error)

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
        cls_table=cls_table,
        overseas_section=overseas_section,
        activity_section=activity_section,
        individual_flow_table=individual_flow_table,
        us_leader_table=us_leader_table,
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


if __name__ == "__main__":
    main()
