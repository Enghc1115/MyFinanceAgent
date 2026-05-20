"""
fund_flow_analysis.py — 主力资金 TOP10 + 方向归类 (Module 4 of deep analysis)

Ranks individual stocks by net fund inflow, groups by industry direction,
and identifies capital preference themes.

Implements REQUIREMENTS.md 6.2 Section 五: 主力资金 TOP10 + 方向归类.

Input:
    - deep_data dict (from data/deep/{date}.json, contains individual_flow
      and sector_flow sections)

Output: tuple[str | None, str | None] — (markdown_section, error_msg)

Pure computation module — no API calls, no side effects.
"""

from __future__ import annotations

from typing import Optional

from scripts.knowledge_base import (
    STOCK_CODE_TO_NAME,
    STOCK_NAME_TO_SECTOR,
    SECTOR_CATEGORY_MAP,
)


# ---------------------------------------------------------------------------
# Column name helpers — handle akshare version variance
# ---------------------------------------------------------------------------

_CODE_CANDIDATES = ("股票代码", "代码")
_NAME_CANDIDATES = ("股票简称", "股票名称", "名称")
_PRICE_CANDIDATES = ("最新价", "最新价格")
_CHANGE_CANDIDATES = ("涨跌幅", "涨幅")
_NET_FLOW_CANDIDATES = ("净额", "净流入", "主力净流入", "资金净流入")
_SECTOR_CANDIDATES = ("所属行业", "行业", "板块")


def _find_col(row: dict, candidates: tuple[str, ...]) -> str | None:
    """Find which candidate column name exists in the row dict."""
    for c in candidates:
        if c in row:
            return c
    return None


def _safe_str(row: dict, candidates: tuple[str, ...], default: str = "") -> str:
    col = _find_col(row, candidates)
    return str(row.get(col, default)) if col else default


def _safe_float(row: dict, candidates: tuple[str, ...], default: float = 0.0) -> float:
    col = _find_col(row, candidates)
    if col is None:
        return default
    try:
        return float(row[col])
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def _extract_section(deep_data: dict, section_key: str) -> list:
    """Extract a section list from deep_data, handling both
    {"sections": {key: [...]}} and direct {key: [...]} formats.
    """
    if "sections" in deep_data and isinstance(deep_data["sections"], dict):
        return deep_data["sections"].get(section_key, []) or []
    return deep_data.get(section_key, []) or []


# ---------------------------------------------------------------------------
# Net inflow parsing
# ---------------------------------------------------------------------------

def _parse_net_inflow_float(value) -> float:
    """Parse net inflow value to a numeric float (in yuan).

    Handles:
      - Raw float/int (in yuan)
      - "X亿" → X * 1e8
      - "X万" → X * 1e4
      - "-X亿", "-X万"
      - Empty / None → 0
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).replace(",", "").strip()
    if not s:
        return 0.0

    negative = s.startswith("-")
    if negative:
        s = s[1:]

    multiplier = 1.0
    if "亿" in s:
        s = s.replace("亿", "")
        multiplier = 1e8
    elif "万" in s:
        s = s.replace("万", "")
        multiplier = 1e4

    try:
        num = float(s)
    except ValueError:
        return 0.0

    result = num * multiplier
    return -result if negative else result


def parse_net_inflow_yi(value) -> float:
    """Parse net inflow value to float in 亿 (display unit).

    Returns the value in 亿, rounded to 2 decimal places.
    """
    raw = _parse_net_inflow_float(value)
    return round(raw / 1e8, 2)


# ---------------------------------------------------------------------------
# Stock sector / direction classification
# ---------------------------------------------------------------------------

def _get_stock_direction(stock: dict) -> tuple[str, str]:
    """Determine the sector and broad direction for a stock.

    Priority:
      1. Look up stock code in knowledge base
      2. Use sector info from the stock data itself

    Returns (sector, direction_category).
    """
    code = _safe_str(stock, _CODE_CANDIDATES, "").strip()

    # 1) Knowledge base lookup: code → name → sector → category
    if code and code in STOCK_CODE_TO_NAME:
        name = STOCK_CODE_TO_NAME[code]
        if name in STOCK_NAME_TO_SECTOR:
            sector = STOCK_NAME_TO_SECTOR[name]
            category = SECTOR_CATEGORY_MAP.get(sector, sector)
            return sector, category

    # 2) Direct sector info in the stock data
    raw_sector = _safe_str(stock, _SECTOR_CANDIDATES, "").strip()
    if raw_sector:
        # Normalize through SECTOR_CATEGORY_MAP
        if raw_sector in SECTOR_CATEGORY_MAP:
            category = SECTOR_CATEGORY_MAP[raw_sector]
            return raw_sector, category
        # Fuzzy match
        for known in SECTOR_CATEGORY_MAP:
            if known in raw_sector or raw_sector in known:
                return raw_sector, SECTOR_CATEGORY_MAP[known]
        return raw_sector, raw_sector

    # 3) Code prefix fallback
    if code:
        prefix = code[:3]
        if prefix in ("600", "601", "603", "605"):
            return "沪主板", "沪主板"
        if prefix in ("000", "001", "002", "003"):
            return "深主板", "深主板"
        if prefix in ("300", "301"):
            return "创业板", "创业板"
        if prefix in ("688", "689"):
            return "科创板", "科创板"

    return "其他", "其他"


# ---------------------------------------------------------------------------
# Direction group analysis
# ---------------------------------------------------------------------------

def _analyze_direction_groups(
    top_stocks: list[dict],
) -> list[dict]:
    """Group top stocks by direction and compute category-level totals.

    Returns sorted list of direction group dicts:
      {direction, total_flow, stocks: [...], flow_direction: "in"/"out"}
    """
    groups: dict[str, dict] = {}

    for item in top_stocks:
        direction = item.get("direction", "其他")
        flow_yi = item.get("net_inflow_yi", 0)

        if direction not in groups:
            groups[direction] = {
                "direction": direction,
                "total_flow": 0.0,
                "stocks": [],
            }
        groups[direction]["total_flow"] += flow_yi
        groups[direction]["stocks"].append(item)

    # Sort by absolute total flow descending
    result = sorted(
        groups.values(),
        key=lambda g: abs(g["total_flow"]),
        reverse=True,
    )
    return result


# ---------------------------------------------------------------------------
# Direction insight text
# ---------------------------------------------------------------------------

_DIRECTION_INSIGHTS: dict[str, str] = {
    "军工":   "军工装备—地缘紧张与装备现代化双轮驱动",
    "半导体": "半导体—国产替代加速，AI算力需求传导",
    "通信":   "通信设备—5G/卫星互联网建设推进",
    "科技":   "科技方向—AI产业链持续活跃",
    "消费":   "消费方向—内需复苏预期升温",
    "医药":   "医药方向—创新药/CXO景气度修复",
    "金融":   "金融方向—政策宽松预期，估值修复",
    "工业":   "工业方向—高端制造与新质生产力",
    "能源":   "能源方向—资源品价格上行/新能源景气",
    "地产":   "地产方向—政策托底信号明确",
    "农业":   "农业方向—养殖周期反转预期",
}


def _get_direction_insight(direction: str, total_flow: float) -> str:
    """Generate a human-readable insight for a capital preference direction."""
    flow_dir = "净流入" if total_flow > 0 else "净流出"
    abs_flow = abs(total_flow)

    base = _DIRECTION_INSIGHTS.get(direction)
    if base:
        return f"{base}，{flow_dir}合计{abs_flow:.1f}亿"
    return f"{direction}方向，{flow_dir}合计{abs_flow:.1f}亿"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(deep_data: dict) -> tuple[str | None, str | None]:
    """Main entry point — analyze top 10 individual fund flow + direction grouping.

    Args:
        deep_data: Deep data dict loaded from data/deep/{date}.json.
                   Expected to contain "individual_flow" section.

    Returns:
        (markdown_section, error_msg).  One is always None.
    """
    try:
        # ---- Load data ----
        individual_flow = _extract_section(deep_data, "individual_flow")

        if not individual_flow:
            return (
                "## 主力资金 TOP10 + 方向归类\n\n"
                "_个股资金流数据暂未获取，无法进行分析。_",
                None,
            )

        # ---- Parse and score every stock ----
        scored: list[dict] = []
        for stock in individual_flow:
            raw_flow = _safe_str(stock, _NET_FLOW_CANDIDATES, "0")
            flow_float = _parse_net_inflow_float(raw_flow)
            flow_yi = round(flow_float / 1e8, 2)
            sector, direction = _get_stock_direction(stock)

            scored.append({
                "code": _safe_str(stock, _CODE_CANDIDATES, ""),
                "name": _safe_str(stock, _NAME_CANDIDATES, ""),
                "price": _safe_float(stock, _PRICE_CANDIDATES, 0),
                "change_pct": _safe_float(stock, _CHANGE_CANDIDATES, 0),
                "net_inflow_raw": raw_flow,
                "net_inflow_float": flow_float,
                "net_inflow_yi": flow_yi,
                "sector": sector,
                "direction": direction,
            })

        if not scored:
            return (
                "## 主力资金 TOP10 + 方向归类\n\n_无法解析个股资金流数据。_",
                None,
            )

        # ---- Sort by net inflow descending, take top 10 ----
        scored.sort(key=lambda x: x["net_inflow_float"], reverse=True)
        top10 = scored[:10]

        # ---- Build TOP10 table ----
        lines = [
            "## 主力资金 TOP10 + 方向归类",
            "",
            "| 排名 | 代码 | 名称 | 净流入(亿) | 所属方向 |",
            "|------|------|------|-----------|---------|",
        ]

        for rank, item in enumerate(top10, 1):
            flow_str = f"+{item['net_inflow_yi']:.2f}" if item["net_inflow_yi"] >= 0 else f"{item['net_inflow_yi']:.2f}"
            lines.append(
                f"| {rank} | {item['code']} | {item['name']} "
                f"| {flow_str} | {item['direction']} |"
            )
        lines.append("")

        # ---- Direction group analysis ----
        groups = _analyze_direction_groups(top10)

        if groups:
            lines.append("### 资金偏好方向")
            lines.append("")

            for group in groups[:3]:  # Top 2-3 direction groups
                direction = group["direction"]
                total = group["total_flow"]
                stocks = group["stocks"]

                # Representative stocks (top 2-3 in group)
                rep_names = [s["name"] for s in stocks[:3] if s["name"]]

                insight = _get_direction_insight(direction, total)

                if rep_names:
                    lines.append(
                        f"- **{direction}**: {insight}，"
                        f"代表个股: {'、'.join(rep_names)}"
                    )
                else:
                    lines.append(f"- **{direction}**: {insight}")

        return "\n".join(lines), None

    except Exception as exc:
        return None, f"主力资金方向分析失败: {exc}"
