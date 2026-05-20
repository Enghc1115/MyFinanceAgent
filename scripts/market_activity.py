"""
market_activity.py — 市场活跃度评估

基于涨跌比、涨停密度、成交额、涨跌强度比等指标评估市场活跃度。
"""

from scripts.core_utils import _safe_float

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

