"""
crowding_monitor.py — 拥挤度监测

计算 A 股板块拥挤度评分，监测科技板块集中度风险。
Howard Marks "第二层次思维"在 A 股市场的量化应用。

Pure computation module — 接收数据，不抓取数据。
"""

from scripts.knowledge_base import CROWDING_THRESHOLDS, SECTOR_CATEGORY_MAP
from scripts.config import DATA_DIR

# ---- 常量 ----

TECH_SECTORS = {"计算机", "电子", "半导体"}


# ---- 科技集中度 ----

def compute_tech_concentration(
    sector_flow_data: list[dict],
    total_market_turnover: float,
) -> dict:
    """计算科技板块成交集中度 = (计算机+电子+半导体)/全市场成交额。

    Args:
        sector_flow_data: 板块资金流向列表，每项含 '行业' 和 '净额'。
        total_market_turnover: 全市场成交额（亿元）。

    Returns:
        包含 tech_ratio, tech_turnover, total_turnover, severity, alert 的 dict。
    """
    t = CROWDING_THRESHOLDS

    # 校验
    if not sector_flow_data or total_market_turnover <= 0:
        return {
            "tech_ratio": 0.0,
            "tech_turnover": 0.0,
            "total_turnover": total_market_turnover if total_market_turnover > 0 else 0.0,
            "severity": "normal",
            "alert": None,
        }

    # 累加科技板块成交额（用 abs 净额作为代理）
    tech_turnover = 0.0
    for item in sector_flow_data:
        sector_name = item.get("行业", "")
        if sector_name in TECH_SECTORS:
            tech_turnover += abs(item.get("净额", 0.0))

    ratio = tech_turnover / total_market_turnover

    # 严重等级分类
    if ratio > t["tech_concentration_critical"]:
        severity = "critical"
    elif ratio > t["tech_concentration_warning"]:
        severity = "warning"
    elif ratio > t["tech_concentration_watch"]:
        severity = "watch"
    else:
        severity = "normal"

    # 告警文案
    severity_labels = {
        "critical": "🚨 危险",
        "warning":  "⚠️ 警戒",
        "watch":    "👀 关注",
        "normal":   "✅ 正常",
    }
    threshold_lines = {
        "critical": f"超过危险线{t['tech_concentration_critical']:.0%}",
        "warning":  f"超过警戒线{t['tech_concentration_warning']:.0%}",
        "watch":    f"超过关注线{t['tech_concentration_watch']:.0%}",
        "normal":   "",
    }

    pct = ratio * 100
    label = severity_labels[severity]
    extra = threshold_lines[severity]
    if extra:
        alert = f"{label} 科技板块成交占比达{pct:.1f}%，{extra}"
    else:
        alert = f"{label} 科技板块成交占比{pct:.1f}%，处于正常区间"

    return {
        "tech_ratio": round(ratio, 4),
        "tech_turnover": round(tech_turnover, 2),
        "total_turnover": round(total_market_turnover, 2),
        "severity": severity,
        "alert": alert,
    }


# ---- 板块拥挤度评分 ----

def compute_sector_crowding(current_sector_flow: list[dict]) -> dict[str, dict]:
    """计算每个板块的拥挤度评分（0-10）。

    评分由三个加权分量构成：
      - 资金流向强度（权重 0.4）：基于绝对净额大小
      - 资金集中度（权重 0.3）：头部板块占比
      - 绝对规模比重（权重 0.3）：abs(净额)/总和

    Args:
        current_sector_flow: 板块资金流向列表，每项含 '行业' 和 '净额'。

    Returns:
        {板块名: {score, level, net_flow, label}, ...}
    """
    t = CROWDING_THRESHOLDS

    # 过滤有效数据
    valid = [
        item for item in current_sector_flow
        if "行业" in item and "净额" in item and item.get("行业")
    ]
    if not valid:
        return {}

    total_abs = sum(abs(item["净额"]) for item in valid)
    total_positive = sum(item["净额"] for item in valid if item["净额"] > 0)

    # 找出最大绝对净额（用于集中度分量）
    max_abs_flow = max(abs(item["净额"]) for item in valid)

    result: dict[str, dict] = {}

    for item in valid:
        name = item["行业"]
        net_flow = item["净额"]
        abs_flow = abs(net_flow)

        # 分量 1：资金流向强度（权重 0.4），基于绝对规模
        if abs_flow >= 100:
            c1 = 10
        elif abs_flow >= 50:
            c1 = 8
        elif abs_flow >= 20:
            c1 = 5
        elif abs_flow > 0:
            c1 = 3
        else:
            c1 = 0

        # 分量 2：资金集中度（权重 0.3），头部板块占比
        concentration = abs_flow / total_abs if total_abs > 0 else 0
        if concentration > 0.30:
            c2 = 10
        elif concentration > 0.20:
            c2 = 7
        elif concentration > 0.10:
            c2 = 4
        elif concentration > 0.05:
            c2 = 2
        else:
            c2 = 1

        # 分量 3：绝对规模比重（权重 0.3），线性缩放至 0-10
        c3_raw = concentration  # abs(net_flow) / total_abs
        c3 = round(c3_raw * 10, 1)

        # 加权总分
        score = round(c1 * 0.4 + c2 * 0.3 + c3 * 0.3, 1)

        # 等级与标签
        if score >= t["crowding_score_high"]:
            level = "high"
            if net_flow < 0:
                label = "🔴 高位（资金出逃）"
            else:
                label = "🔴 高位"
        elif score > t["crowding_score_low"]:
            level = "medium"
            label = "🟡 中等"
        else:
            level = "low"
            label = "🟢 低位"

        result[name] = {
            "score": score,
            "level": level,
            "net_flow": round(net_flow, 2),
            "label": label,
        }

    return result


# ---- 公开 API：生成 Markdown 报告 ----

def compute_crowding_table(
    sector_flow_data: list[dict],
    total_market_turnover: float,
) -> tuple[str | None, str | None]:
    """主公开 API。综合科技集中度 + 板块拥挤度，生成 Markdown 报告。

    Args:
        sector_flow_data: 板块资金流向列表，每项含 '行业' 和 '净额'。
        total_market_turnover: 全市场成交额（亿元）。

    Returns:
        (markdown_section_or_None, error_or_None)
    """
    try:
        # 1. 科技集中度
        tech = compute_tech_concentration(sector_flow_data, total_market_turnover)

        # 2. 板块拥挤度
        crowding = compute_sector_crowding(sector_flow_data)

        # 3. 组装 Markdown
        lines = ["### 拥挤度监测", ""]

        # --- 科技集中度表 ---
        lines.append("| 指标 | 数值 | 状态 |")
        lines.append("|------|------|------|")
        pct_str = f"{tech['tech_ratio'] * 100:.1f}%"
        alert_str = tech["alert"].split(" ", 1)[1] if tech["alert"] and " " in tech["alert"] else tech.get("alert", "—")
        severity_icon = tech["alert"].split(" ")[0] if tech["alert"] and " " in tech["alert"] else ""
        status_str = f"{severity_icon} {alert_str}" if severity_icon else alert_str
        lines.append(
            f"| (计算机+电子+半导体)/全市场成交 | {pct_str} | {status_str} |"
        )
        lines.append("")

        # --- 板块拥挤度表 ---
        if not crowding:
            lines.append("_暂无板块拥挤度数据_")
            return "\n".join(lines), None

        lines.append("| 板块 | 拥挤度 | 净流入(亿) | 状态 |")
        lines.append("|------|--------|-----------|------|")

        # 按拥挤度降序排列
        sorted_sectors = sorted(
            crowding.items(),
            key=lambda kv: kv[1]["score"],
            reverse=True,
        )
        for sector_name, info in sorted_sectors:
            nf = info["net_flow"]
            nf_str = f"+{nf:.2f}" if nf >= 0 else f"{nf:.2f}"
            lines.append(
                f"| {sector_name} | {info['score']}/10 | {nf_str} | {info['label']} |"
            )

        return "\n".join(lines), None

    except Exception as e:
        return None, f"拥挤度监测计算失败: {e}"
