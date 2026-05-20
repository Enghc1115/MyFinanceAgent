"""
theme_analysis.py — 主线结构分析 (Module 3 of deep analysis)

Groups limit-up stocks by sector, identifies 2-3 main themes,
and evaluates sustainability with multi-factor scoring.

Implements REQUIREMENTS.md 6.2 Section 四: 主线结构分析.

Input:
    - deep_data dict (from data/deep/{date}.json)
    - chain_impacts list (from chain_reasoning.analyze_chain())
    - crowding_scores dict (from crowding_monitor.compute_sector_crowding())

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

# Possible column names for stock code in limit-up pool
_CODE_CANDIDATES = ("代码", "股票代码")
_NAME_CANDIDATES = ("名称", "股票名称", "股票简称")
_SECTOR_CANDIDATES = ("所属行业", "行业", "板块")
_BOARD_COUNT_CANDIDATES = ("连板数", "连板", "连续涨停天数")
_PRICE_CANDIDATES = ("最新价", "最新价格")
_CHANGE_CANDIDATES = ("涨跌幅", "涨幅")


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


def _safe_int(row: dict, candidates: tuple[str, ...], default: int = 1) -> int:
    col = _find_col(row, candidates)
    if col is None:
        return default
    try:
        return int(float(row[col]))
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
# Sector classification
# ---------------------------------------------------------------------------

def _classify_stock_sector(stock: dict) -> str:
    """Determine the sector/industry of a limit-up stock.

    Priority:
      1. 所属行业 column in the data itself
      2. Look up stock code → name → sector in knowledge base
      3. Code prefix inference as fallback

    Returns a normalized sector name string.
    """
    # 1) Direct from data
    raw_sector = _safe_str(stock, _SECTOR_CANDIDATES, "").strip()
    if raw_sector:
        # Try to standardize through SECTOR_CATEGORY_MAP
        if raw_sector in SECTOR_CATEGORY_MAP:
            return raw_sector
        # Fuzzy: check if any known sector is a substring
        for known in SECTOR_CATEGORY_MAP:
            if known in raw_sector or raw_sector in known:
                return known
        return raw_sector

    # 2) Knowledge base lookup
    code = _safe_str(stock, _CODE_CANDIDATES, "").strip()
    if code and code in STOCK_CODE_TO_NAME:
        name = STOCK_CODE_TO_NAME[code]
        if name in STOCK_NAME_TO_SECTOR:
            return STOCK_NAME_TO_SECTOR[name]

    # 3) Code prefix inference only for board-level labeling
    if code:
        prefix = code[:3]
        if prefix in ("600", "601", "603", "605"):
            return "沪主板"
        if prefix in ("000", "001", "002", "003"):
            return "深主板"
        if prefix in ("300", "301"):
            return "创业板"
        if prefix in ("688", "689"):
            return "科创板"

    return "其他"


# ---------------------------------------------------------------------------
# Theme ranking
# ---------------------------------------------------------------------------

def _build_sector_net_flow_map(sector_flow_data: list) -> dict[str, float]:
    """Build {sector_name: net_flow_amount} from sector_flow data.

    Net flow values are expected to be numeric (in 亿).
    """
    flow_map: dict[str, float] = {}
    name_col = _find_col(sector_flow_data[0], ("行业", "板块名称", "名称")) if sector_flow_data else None
    net_col = _find_col(sector_flow_data[0], ("净额", "主力净流入", "净流入")) if sector_flow_data else None

    if not name_col or not net_col:
        return flow_map

    for item in sector_flow_data:
        name = str(item.get(name_col, "")).strip()
        if not name:
            continue
        try:
            flow_map[name] = float(item.get(net_col, 0))
        except (ValueError, TypeError):
            flow_map[name] = 0.0

    return flow_map


def _rank_themes(
    sector_groups: dict[str, list[dict]],
    sector_flow_map: dict[str, float],
    max_themes: int = 3,
) -> list[dict]:
    """Rank themes by composite score and return top themes.

    Score = limit_up_count * 2 + inverted_sector_flow_rank

    The inverted rank gives highest score to the sector with largest net inflow.
    """
    # Sort sectors by net inflow descending
    sorted_by_flow = sorted(
        sector_flow_map.items(), key=lambda kv: kv[1], reverse=True
    )
    # Build rank map: sector → rank (1 = highest inflow)
    flow_rank: dict[str, int] = {}
    for rank, (sector_name, _) in enumerate(sorted_by_flow, 1):
        flow_rank[sector_name] = rank

    max_rank = len(flow_rank) or 1

    scored: list[dict] = []
    for sector, stocks in sector_groups.items():
        count = len(stocks)
        # Invert rank: rank 1 → max_rank points, rank N → 1 point
        rank_pos = flow_rank.get(sector, max_rank)
        inverted_rank_score = max_rank - rank_pos + 1
        composite = count * 2 + inverted_rank_score

        scored.append({
            "sector": sector,
            "stocks": stocks,
            "count": count,
            "net_flow": sector_flow_map.get(sector, 0),
            "composite_score": composite,
            "flow_rank": rank_pos,
        })

    scored.sort(key=lambda t: t["composite_score"], reverse=True)
    return scored[:max_themes]


# ---------------------------------------------------------------------------
# Leader / follow classification
# ---------------------------------------------------------------------------

def _classify_leader_follow(
    stocks: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Sort stocks by board count and change%, classify leader vs follow.

    Returns (leaders, follows).
    Leader = top 1-2 by board count; Follow = next 2-3.
    """
    scored_stocks = []
    for s in stocks:
        board_count = _safe_int(s, _BOARD_COUNT_CANDIDATES, 1)
        change_pct = abs(_safe_float(s, _CHANGE_CANDIDATES, 0))
        scored_stocks.append({
            "stock": s,
            "board_count": board_count,
            "change_pct": change_pct,
        })

    # Sort: board_count desc, then change_pct desc
    scored_stocks.sort(key=lambda x: (x["board_count"], x["change_pct"]), reverse=True)

    leaders = [item["stock"] for item in scored_stocks[:2]]
    follows = [item["stock"] for item in scored_stocks[2:5]]
    return leaders, follows


# ---------------------------------------------------------------------------
# Chain impact matching
# ---------------------------------------------------------------------------

def _match_chain_impacts(
    theme_sector: str, chain_impacts: list[dict]
) -> list[dict]:
    """Find chain impacts whose sectors overlap with the theme's sector."""
    if not chain_impacts:
        return []

    matches: list[dict] = []
    for impact in chain_impacts:
        all_sectors: list[str] = []
        for pos_key in ("upstream_impact", "midstream_impact", "downstream_impact"):
            for item in impact.get(pos_key, []):
                sector = item.get("sector", "")
                if sector:
                    all_sectors.append(sector)

        # Check overlap: any known sector map entry appears
        theme_category = SECTOR_CATEGORY_MAP.get(theme_sector, theme_sector)
        for s in all_sectors:
            s_category = SECTOR_CATEGORY_MAP.get(s, s)
            if theme_sector in s or s in theme_sector or theme_category == s_category:
                matches.append(impact)
                break

    return matches


# ---------------------------------------------------------------------------
# Sub-directions inference
# ---------------------------------------------------------------------------

_SECTOR_SUB_DIRECTIONS: dict[str, list[str]] = {
    "半导体":     ["半导体设备", "AI芯片", "先进封装", "存储芯片"],
    "AI芯片":     ["算力芯片", "推理芯片", "存算一体"],
    "先进封装":   ["CoWoS", "3D封装", "Chiplet"],
    "消费电子":   ["AI手机", "智能穿戴", "AR/VR"],
    "光模块":     ["800G光模块", "硅光技术", "CPO"],
    "通信设备":   ["5G基站", "卫星通信", "6G研发"],
    "军工":       ["军机产业链", "导弹/弹药", "军工电子", "船舶"],
    "商业航天":   ["卫星制造", "火箭发射", "地面设备"],
    "低空经济":   ["eVTOL", "无人机", "低空基建"],
    "新能源汽车": ["整车", "锂电池", "智能驾驶", "充电桩"],
    "光伏":       ["硅料/硅片", "电池/组件", "逆变器", "辅材"],
    "锂电池":     ["正极材料", "负极材料", "电解液", "隔膜"],
    "AI应用":     ["大模型", "AI Agent", "AI+教育", "AI+医疗"],
    "服务器":     ["AI服务器", "液冷散热", "算力租赁"],
    "机器人":     ["人形机器人", "工业机器人", "核心零部件"],
    "白酒":       ["高端白酒", "次高端", "区域名酒"],
    "医药":       ["创新药", "CXO", "医疗器械", "中药"],
    "CXO":        ["CDMO", "CRO", "临床前"],
    "银行":       ["国有大行", "股份行", "城商行"],
    "券商":       ["头部券商", "互联网券商", "中小券商"],
    "房地产":     ["央企地产", "地方国企", "优质民企"],
    "面板":       ["OLED", "MiniLED", "MicroLED"],
    "金融科技":   ["数字人民币", "证券IT", "银行IT"],
    "智能驾驶":   ["激光雷达", "域控制器", "高精地图"],
    "石油":       ["勘探开发", "炼化", "油服"],
    "黄金":       ["黄金矿企", "黄金珠宝零售"],
    "煤炭":       ["动力煤", "焦煤", "煤化工"],
}


def _infer_sub_directions(sector: str) -> list[str]:
    """Infer sub-directions for a given sector."""
    # Exact match
    if sector in _SECTOR_SUB_DIRECTIONS:
        return list(_SECTOR_SUB_DIRECTIONS[sector])
    # Partial match
    for known, subs in _SECTOR_SUB_DIRECTIONS.items():
        if known in sector or sector in known:
            return list(subs)
    # Category-level
    category = SECTOR_CATEGORY_MAP.get(sector, "")
    for known, subs in _SECTOR_SUB_DIRECTIONS.items():
        if SECTOR_CATEGORY_MAP.get(known, "") == category:
            return list(subs)
    return []


# ---------------------------------------------------------------------------
# Sustainability scoring
# ---------------------------------------------------------------------------

def _compute_sustainability(
    theme: dict,
    crowding_scores: dict[str, dict] | None = None,
) -> tuple[float, str]:
    """Compute sustainability score (0-10) for a theme.

    Four weighted components:
      1. Consecutive board depth (0.25): 4+连板=10, 3=7, 2=4, 首板=1
      2. Fund flow direction (0.30): >50亿=10, >20亿=7, >0=4, net outflow=1
      3. Turnover trend (0.25): from crowding_scores if available, else 5
      4. Theme breadth (0.20): >10 stocks=10, >5=7, >3=4, else 1

    Returns (score, rationale_string).
    """
    sector = theme.get("sector", "")
    stocks: list = theme.get("stocks", [])
    net_flow = theme.get("net_flow", 0)

    # Component 1: Consecutive board depth
    max_board = 1
    for s in stocks:
        bc = _safe_int(s, _BOARD_COUNT_CANDIDATES, 1)
        if bc > max_board:
            max_board = bc

    if max_board >= 4:
        c1, r1 = 10, f"最高{max_board}连板"
    elif max_board == 3:
        c1, r1 = 7, f"最高{max_board}连板"
    elif max_board == 2:
        c1, r1 = 4, f"最高{max_board}连板"
    else:
        c1, r1 = 1, "均为首板"

    # Component 2: Fund flow direction
    if net_flow > 50:
        c2, r2 = 10, f"板块净流入{net_flow:.1f}亿（>50亿）"
    elif net_flow > 20:
        c2, r2 = 7, f"板块净流入{net_flow:.1f}亿（20-50亿）"
    elif net_flow > 0:
        c2, r2 = 4, f"板块净流入{net_flow:.1f}亿（<20亿）"
    else:
        c2, r2 = 1, f"板块净流出{abs(net_flow):.1f}亿"

    # Component 3: Turnover trend (from crowding_scores)
    c3 = 5
    r3 = "无拥挤度参考数据"
    if crowding_scores and sector in crowding_scores:
        cs = crowding_scores[sector].get("score", 5)
        # Invert: high crowding = lower sustainability
        if cs >= 7:
            c3, r3 = 3, f"拥挤度偏高（{cs}/10），高位风险"
        elif cs >= 4:
            c3, r3 = 5, f"拥挤度中等（{cs}/10）"
        else:
            c3, r3 = 7, f"拥挤度偏低（{cs}/10），低位关注"

    # Component 4: Theme breadth
    count = len(stocks)
    if count > 10:
        c4, r4 = 10, f"{count}只涨停，板块效应强"
    elif count > 5:
        c4, r4 = 7, f"{count}只涨停，板块效应中等"
    elif count > 3:
        c4, r4 = 4, f"{count}只涨停，板块联动偏弱"
    else:
        c4, r4 = 1, f"仅{count}只涨停"

    score = round(c1 * 0.25 + c2 * 0.30 + c3 * 0.25 + c4 * 0.20, 1)

    rationale_parts = [
        f"连板深度({c1}/10·权重0.25): {r1}",
        f"资金流向({c2}/10·权重0.30): {r2}",
        f"换手趋势({c3}/10·权重0.25): {r3}",
        f"板块广度({c4}/10·权重0.20): {r4}",
    ]
    rationale = "; ".join(rationale_parts)

    return score, rationale


# ---------------------------------------------------------------------------
# Driver logic inference
# ---------------------------------------------------------------------------

def _infer_driver_logic(
    theme: dict, chain_matches: list[dict]
) -> str:
    """Infer the driver logic for a theme.

    If chain_impacts match, use them as the primary driver.
    Otherwise, infer from fund flow direction and sector characteristics.
    """
    sector = theme.get("sector", "")

    if chain_matches:
        catalysts = []
        for impact in chain_matches:
            catalyst = impact.get("catalyst", "")
            if catalyst and catalyst not in catalysts:
                catalysts.append(catalyst)
        if catalysts:
            return "政策/事件催化: " + "；".join(catalysts[:3])

    # Fallback: infer from sector flow direction
    net_flow = theme.get("net_flow", 0)
    if net_flow > 0:
        return f"主力资金净流入{net_flow:.1f}亿，资金主动加仓{_sector_label(sector)}方向"
    else:
        return f"{_sector_label(sector)}板块结构性活跃，但资金整体呈流出态势"


def _sector_label(sector: str) -> str:
    """Return a display label for a sector."""
    category = SECTOR_CATEGORY_MAP.get(sector, "")
    if category:
        return f"{sector}（{category}）"
    return sector


# ---------------------------------------------------------------------------
# Chain reasoning text generation
# ---------------------------------------------------------------------------

def _format_chain_reasoning(chain_matches: list[dict]) -> str | None:
    """Generate chain reasoning text from matched impacts."""
    if not chain_matches:
        return None

    lines: list[str] = []
    for impact in chain_matches[:2]:  # At most 2 chain impacts
        catalyst = impact.get("catalyst", "")
        lines.append(f"催化事件: {catalyst}")

        for pos_key, pos_label in [
            ("upstream_impact", "上游"),
            ("midstream_impact", "中游"),
            ("downstream_impact", "下游"),
        ]:
            items = impact.get(pos_key, [])
            if items:
                sectors_text = "、".join(
                    item.get("sector", "") for item in items[:3]
                )
                lines.append(f"  → {pos_label}: {sectors_text}")

        # Relevant A-share targets
        targets = impact.get("a_share_targets", [])
        if targets:
            target_names = [
                t.get("name", "") for t in targets[:5] if t.get("code")
            ]
            if target_names:
                lines.append(f"  → 相关标的: {'、'.join(target_names)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Star rating
# ---------------------------------------------------------------------------

def _sustainability_stars(score: float) -> str:
    """Convert sustainability score to star rating."""
    if score >= 7:
        return "★★★"  # ★★★
    elif score >= 4:
        return "★★☆"  # ★★☆
    else:
        return "★☆☆"  # ★☆☆


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(
    deep_data: dict,
    chain_impacts: list | None = None,
    crowding_scores: dict | None = None,
) -> tuple[str | None, str | None]:
    """Main entry point — analyze main themes from limit-up pool.

    Args:
        deep_data: Deep data dict loaded from data/deep/{date}.json.
        chain_impacts: Chain impact analysis from chain_reasoning.analyze_chain().
        crowding_scores: Sector crowding scores from crowding_monitor.compute_sector_crowding().

    Returns:
        (markdown_section, error_msg).  One is always None.
    """
    try:
        # ---- Load data ----
        limit_up_pool = _extract_section(deep_data, "limit_up_pool")
        sector_flow_data = _extract_section(deep_data, "sector_flow")

        chain_impacts = chain_impacts or []
        crowding_scores = crowding_scores or {}

        # ---- Edge case: insufficient data ----
        if not limit_up_pool:
            # Check if data exists but is empty vs. truly missing
            return (
                "### 主线结构分析\n\n_今日涨停数据暂未获取，无法进行主线结构分析。_",
                None,
            )

        if len(limit_up_pool) < 10:
            return (
                "### 主线结构分析\n\n今日无明显主线，市场热点分散（涨停家数不足10家）。",
                None,
            )

        # ---- Group stocks by sector ----
        sector_groups: dict[str, list[dict]] = {}
        for stock in limit_up_pool:
            sector = _classify_stock_sector(stock)
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(stock)

        if not sector_groups:
            return (
                "### 主线结构分析\n\n无法识别板块归属，主线结构分析暂缺。",
                None,
            )

        # ---- Build flow map and rank themes ----
        sector_flow_map = _build_sector_net_flow_map(sector_flow_data)
        ranked_themes = _rank_themes(sector_groups, sector_flow_map, max_themes=3)

        if not ranked_themes:
            return (
                "### 主线结构分析\n\n今日无明显主线，市场热点分散。",
                None,
            )

        # ---- Generate markdown for each theme ----
        lines = ["### 主线结构分析", ""]

        for idx, theme in enumerate(ranked_themes, 1):
            sector = theme["sector"]
            stocks = theme["stocks"]
            count = theme["count"]
            net_flow = theme["net_flow"]

            leaders, follows = _classify_leader_follow(stocks)

            # Match chain impacts
            chain_matches = _match_chain_impacts(sector, chain_impacts)

            # Driver logic
            driver = _infer_driver_logic(theme, chain_matches)

            # Sub-directions
            sub_dirs = _infer_sub_directions(sector)

            # Sustainability
            sustain_score, sustain_rationale = _compute_sustainability(
                theme, crowding_scores
            )
            stars = _sustainability_stars(sustain_score)

            # ---- Build leader string ----
            leader_parts: list[str] = []
            for stock in leaders:
                name = _safe_str(stock, _NAME_CANDIDATES, "?")
                board = _safe_int(stock, _BOARD_COUNT_CANDIDATES, 1)
                code = _safe_str(stock, _CODE_CANDIDATES, "")
                if board >= 2:
                    leader_parts.append(f"{name}({code}, {board}连板)")
                else:
                    leader_parts.append(f"{name}({code})")
            # Add follows
            follow_names = [
                _safe_str(s, _NAME_CANDIDATES, "?") for s in follows
            ]
            leader_text = "、".join(leader_parts)
            if follow_names:
                leader_text += "；跟风：" + "、".join(follow_names)

            # ---- Format theme block ----
            lines.append(f"#### 主线{idx}: {sector} {stars}")
            lines.append(f"- **涨停家数**: {count}只")
            if net_flow != 0:
                flow_dir = "净流入" if net_flow > 0 else "净流出"
                lines.append(f"- **板块资金**: {flow_dir}{abs(net_flow):.1f}亿")
            lines.append(f"- **领涨个股**: {leader_text}")
            lines.append(f"- **驱动逻辑**: {driver}")
            if sub_dirs:
                lines.append(f"- **细分方向**: {'、'.join(sub_dirs[:4])}")
            chain_text = _format_chain_reasoning(chain_matches)
            if chain_text:
                lines.append(f"- **产业链推理**:")
                for cl in chain_text.split("\n"):
                    lines.append(f"  {cl}")
            lines.append(
                f"- **持续性判断**: {sustain_score}/10 {stars} — {sustain_rationale}"
            )
            lines.append("")

        return "\n".join(lines), None

    except Exception as exc:
        return None, f"主线结构分析失败: {exc}"
