"""
sector_flow.py — 板块资金流向分析

提供板块资金流向 TOP 5 获取、主力资金方向异动检测。
"""

import pandas as pd
import akshare as ak
from pathlib import Path

from scripts.config import DATA_DIR

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


