"""
index_panorama.py — 指数全景分析（量价配合 + 行情类型判断）
Deep Analysis Module 1 of 8

读取五大指数的价格/涨跌幅，结合全市场成交额环比变化，
对每个指数进行量价配合归类，并判断当日行情类型。
"""

from scripts.config import INDICES_CONFIG

# 指数前缀 → 显示名
INDEX_MAP: list[tuple[str, str]] = [(p, n) for p, _, n in INDICES_CONFIG]


def analyze(stats: dict, deep_data: dict = None, prev_stats: dict = None) -> tuple[str | None, str | None]:
    """
    分析指数全景，输出量价配合表格与行情类型判断。

    Args:
        stats: 当日行情 dict，来自 core_utils.read_csv_data()
        deep_data: 深度数据 dict（可选，本模块暂未使用）
        prev_stats: 前一交易日行情 dict（可选，用于计算成交额环比）

    Returns:
        (markdown_section, error_str_or_None)
    """
    try:
        indices = stats.get("indices", {})
        if not indices:
            return (None, "stats 中无 indices 数据")

        total_amount = stats.get("total_amount", 0)

        # ---- 1. 成交额环比变化 ----
        turnover_change_str = _calc_turnover_change(total_amount, prev_stats)

        # ---- 2. 判断整体放量/缩量方向 ----
        volume_direction = _volume_direction(total_amount, prev_stats)

        # ---- 3. 为每个指数做量价配合归类 ----
        index_rows: list[dict] = []
        for prefix, name in INDEX_MAP:
            if prefix not in indices:
                continue
            idx = indices[prefix]
            price = idx["price"]
            change = idx["change"]
            coordination = _classify_coordination(change, volume_direction)
            index_rows.append({
                "name": name,
                "price": price,
                "change": change,
                "coordination": coordination,
            })

        if not index_rows:
            return (None, "无有效指数数据")

        # ---- 4. 领涨/领跌指数 ----
        best = max(index_rows, key=lambda r: r["change"])
        worst = min(index_rows, key=lambda r: r["change"])
        spread = best["change"] - worst["change"]

        # ---- 5. 行情类型判断 ----
        market_type, type_rationale = _classify_market(index_rows, spread)

        # ---- 6. 组装 Markdown ----
        lines = ["## 二、指数全景", "", "### 五大指数表现", ""]
        lines.append("| 指数 | 收盘价 | 涨跌幅 | 量价配合 |")
        lines.append("|------|--------|--------|---------|")

        for r in index_rows:
            sign = "+" if r["change"] > 0 else ""
            chg_str = f"{sign}{r['change']:.2f}%"
            lines.append(
                f"| {r['name']} | {r['price']:.2f} | {chg_str} | {r['coordination']} |"
            )

        lines.append("")
        lines.append(f"- **全市场成交额**: {total_amount:.2f} 亿元")
        if turnover_change_str:
            lines.append(f"- **环比前一交易日**: {turnover_change_str}")
        if volume_direction == "放量":
            lines.append("- 整体量能方向: **放量**（成交额环比增加）")
        elif volume_direction == "缩量":
            lines.append("- 整体量能方向: **缩量**（成交额环比减少）")
        elif volume_direction == "持平":
            lines.append("- 整体量能方向: **平量**（成交额环比基本不变）")
        else:
            lines.append("- 整体量能方向: 无对比数据（需前一交易日 CSV）")

        lines.append("")
        lines.append("### 指数结构分析")
        lines.append("")

        if spread > 0.01:
            lines.append(f"- **领涨**: {best['name']}（{best['change']:+.2f}%）")
            lines.append(f"- **承压**: {worst['name']}（{worst['change']:+.2f}%）")
            lines.append(f"- **极差**: {spread:.2f}%")
        else:
            lines.append("- 五大指数涨跌幅基本一致，无明显分化")

        lines.append("")
        lines.append("### 行情类型判断")
        lines.append("")
        lines.append(f"**{market_type}**：{type_rationale}")

        return ("\n".join(lines), None)

    except Exception as e:
        return (None, f"指数全景分析失败: {e}")


# ---- 内部辅助函数 ----

def _calc_turnover_change(current_amount: float, prev_stats: dict | None) -> str:
    """计算成交额环比变化描述。"""
    if prev_stats is None:
        return ""
    prev_amount = prev_stats.get("total_amount", 0)
    if not prev_amount or prev_amount == 0:
        return ""
    pct = (current_amount - prev_amount) / prev_amount * 100
    sign = "+" if pct >= 0 else ""
    direction = "放量" if pct > 0 else ("缩量" if pct < 0 else "持平")
    return f"{sign}{pct:.1f}%（{direction}）"


def _volume_direction(current_amount: float, prev_stats: dict | None) -> str:
    """判断整体成交额方向: '放量' / '缩量' / '持平' / '未知'。"""
    if prev_stats is None:
        return "未知"
    prev_amount = prev_stats.get("total_amount", 0)
    if not prev_amount or prev_amount == 0:
        return "未知"
    pct = (current_amount - prev_amount) / prev_amount * 100
    if pct > 1:
        return "放量"
    elif pct < -1:
        return "缩量"
    else:
        return "持平"


def _classify_coordination(change: float, volume_direction: str) -> str:
    """根据价格方向与量能方向，归类量价配合。"""
    if change > 0.05:
        price_dir = "上涨"
    elif change < -0.05:
        price_dir = "下跌"
    else:
        price_dir = "平盘"

    if volume_direction == "放量":
        if price_dir == "上涨":
            return "放量上涨"
        elif price_dir == "下跌":
            return "放量下跌"
        else:
            return "放量平盘"
    elif volume_direction == "缩量":
        if price_dir == "上涨":
            return "缩量上涨"
        elif price_dir == "下跌":
            return "缩量下跌"
        else:
            return "缩量平盘"
    elif volume_direction == "持平":
        if price_dir == "上涨":
            return "平量上涨"
        elif price_dir == "下跌":
            return "平量下跌"
        else:
            return "平量平盘"
    else:
        # volume_direction == "未知"：无对比数据
        return f"{price_dir}（量能无对比）"


def _classify_market(index_rows: list[dict], spread: float) -> tuple[str, str]:
    """判断行情类型并给出理由。"""
    up_count = sum(1 for r in index_rows if r["change"] > 0.05)
    down_count = sum(1 for r in index_rows if r["change"] < -0.05)
    total = len(index_rows)

    # 普涨：全部上涨，极差 < 1.5%
    if up_count == total and spread < 1.5:
        return (
            "普涨",
            f"五大指数全面上涨，涨幅极差仅 {spread:.2f}%，"
            f"市场呈现普涨格局，赚钱效应广泛。",
        )

    # 分化：极差 > 1.5%
    if spread > 1.5:
        best = max(index_rows, key=lambda r: r["change"])
        worst = min(index_rows, key=lambda r: r["change"])
        return (
            "分化",
            f"指数间分化显著（极差 {spread:.2f}%），"
            f"{best['name']}领涨（{best['change']:+.2f}%），"
            f"{worst['name']}承压（{worst['change']:+.2f}%）。"
            f"资金在不同板块间轮动明显，结构性行情特征突出。",
        )

    # 震荡：方向混杂，极差 < 1%
    if up_count > 0 and down_count > 0 and spread < 1:
        return (
            "震荡",
            f"五大指数涨跌互现（上涨 {up_count} 个，下跌 {down_count} 个），"
            f"极差仅 {spread:.2f}%，市场处于窄幅震荡状态，方向不明。",
        )

    # 调整：3+ 指数下跌
    if down_count >= 3:
        return (
            "调整",
            f"{down_count}/{total} 个指数下跌，"
            f"极差 {spread:.2f}%，市场整体处于调整态势，风险偏好下降。",
        )

    # 兜底
    return (
        "震荡",
        f"五大指数涨跌互现（上涨 {up_count} 个，下跌 {down_count} 个），"
        f"极差 {spread:.2f}%，市场方向不明。",
    )
