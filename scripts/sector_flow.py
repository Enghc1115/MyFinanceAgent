"""
sector_flow.py — 板块资金流向分析

提供板块资金流向 TOP 5 获取、主力资金方向异动检测。
"""

import pandas as pd
import akshare as ak
from pathlib import Path

from scripts.config import DATA_DIR, SECTOR_FLOW_DIR

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


def detect_cross_session_anomalies(target_date_str: str) -> str:
    """跨时段异动检测：比较同日的早盘→午盘→收盘板块资金流向快照。

    加载 data/sector_flow/ 下同日不同时段的 CSV 快照，
    检测连续时段间的资金方向变化：
    - 净流入→净流出 = ⚠️ 风险
    - 净流出→净流入 = ↑ 反转

    Returns:
        markdown section or empty string
    """
    if not SECTOR_FLOW_DIR.exists():
        return ""

    mode_order = ["morning", "noon", "close"]
    mode_labels = {"morning": "早盘", "noon": "午盘", "close": "收盘"}
    name_col = "行业"
    net_col = "净额"

    # 加载所有可用的当日快照
    snapshots: dict[str, pd.DataFrame] = {}
    for mode in mode_order:
        fp = SECTOR_FLOW_DIR / f"{target_date_str}_{mode}.csv"
        if fp.exists():
            try:
                df = pd.read_csv(fp)
                if name_col in df.columns and net_col in df.columns:
                    snapshots[mode] = df
            except Exception:
                pass

    if len(snapshots) < 2:
        return ""

    # 用实际存在的快照构建连续对比对
    available = [m for m in mode_order if m in snapshots]
    pairs = [(available[i], available[i + 1]) for i in range(len(available) - 1)]
    if not pairs:
        return ""

    # 收集所有板块
    all_sectors: set[str] = set()
    for df in snapshots.values():
        all_sectors.update(df[name_col].tolist())

    # 板块 → {时段: 净额}
    sector_nets: dict[str, dict[str, float]] = {}
    for sector in all_sectors:
        sector_nets[sector] = {}
        for mode, df in snapshots.items():
            rows = df[df[name_col] == sector]
            if not rows.empty:
                sector_nets[sector][mode] = rows[net_col].iloc[0]

    # 逐对检测方向变化
    table_rows: list[tuple[str, list[str], str]] = []
    for sector, nets in sector_nets.items():
        changes: list[str] = []
        signals: list[str] = []

        for m1, m2 in pairs:
            v1 = nets.get(m1)
            v2 = nets.get(m2)
            if v1 is None or v2 is None:
                changes.append("—")
                continue
            if v1 >= 0 > v2:
                changes.append("净流入→净流出")
                signals.append("⚠️ 风险")
            elif v1 < 0 <= v2:
                changes.append("净流出→净流入")
                signals.append("↑ 反转")
            elif v1 >= 0 and v2 >= 0:
                changes.append("净流入持续")
            else:
                changes.append("净流出持续")

        if not signals:
            continue

        signal = "⚠️ 风险" if "⚠️ 风险" in signals else "↑ 反转"
        table_rows.append((sector, changes, signal))

    if not table_rows:
        return ""

    # 构建 Markdown 表格
    pair_labels = [f"{mode_labels[p1]}→{mode_labels[p2]}" for p1, p2 in pairs]
    header_cols = ["板块"] + pair_labels + ["信号"]
    sep_cols = ["------"] + ["--------"] * len(pair_labels) + ["------"]
    lines = [
        "### 跨时段异动监测",
        "",
        "| " + " | ".join(header_cols) + " |",
        "|" + "|".join(sep_cols) + "|",
    ]
    for sector, changes, signal in table_rows:
        row_cols = [sector] + changes + [signal]
        lines.append("| " + " | ".join(row_cols) + " |")

    return "\n".join(lines)


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

        # 跨时段异动检测（同日早盘→午盘→收盘对比）
        cross_session = detect_cross_session_anomalies(target_date_str)
        if anomaly_section and cross_session:
            anomaly_section = anomaly_section + "\n\n" + cross_session
        elif cross_session:
            anomaly_section = cross_session

        return table, anomaly_section, None
    except Exception as e:
        return None, None, f"板块资金流向获取失败: {e}"


