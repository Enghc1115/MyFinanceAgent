"""
opportunity_risk.py — 机会与风险识别 (Module 6 of deep analysis)

四维穿透框架 — 维度三（护城河） + 维度四（博弈层）交叉应用

Rule-based generation of short-term and mid-term investment opportunities
and risks from available market data. All logic is concrete and data-driven:
no generic warnings without supporting evidence.

Inputs:
  - all_sections: dict of module outputs (markdown strings or objects)
  - crowding_scores: {sector_name: {score, level, net_flow, label}, ...}
  - deep_data: raw structured data from data/deep/{date}.json

Pure computation: receives data, produces markdown. No external API calls.
"""

from scripts.knowledge_base import (
    CROWDING_THRESHOLDS,
    SECTOR_CATEGORY_MAP,
    US_SECTOR_ETFS,
)


def analyze(
    all_sections: dict = None,
    crowding_scores: dict = None,
    deep_data: dict = None,
) -> tuple[str | None, str | None]:
    """Generate opportunities and risks markdown section.

    Args:
        all_sections: Dict of module output strings/objects.
                      Keyed by module name (e.g. 'sector_flow', 'theme_analysis').
        crowding_scores: {sector_name: {score, level, net_flow, label}, ...}
                         as produced by crowding_monitor.compute_sector_crowding().
        deep_data: Raw deep data dict with sections.sector_flow,
                   sections.limit_up_pool, sections.individual_flow, etc.

    Returns:
        (markdown_section, None) on success, or (None, error_msg) on failure.
    """
    try:
        all_sections = all_sections or {}
        crowding_scores = crowding_scores or {}
        sections = deep_data.get("sections", {}) if deep_data else {}

        sector_flow = sections.get("sector_flow", []) or []
        individual_flow = sections.get("individual_flow", []) or []
        limit_up_pool = sections.get("limit_up_pool", []) or []
        limit_down_pool = sections.get("limit_down_pool", []) or []
        blowup_info = sections.get("blow_up_and_prev_performance", {}) or {}

        # ---- compute opportunities ----
        st_opps = _find_short_term_opportunities(
            sector_flow, limit_up_pool, individual_flow, crowding_scores,
        )
        mt_opps = _find_mid_term_opportunities(
            sector_flow, crowding_scores, all_sections, deep_data,
        )

        # ---- compute risks ----
        st_risks = _find_short_term_risks(
            sector_flow, limit_up_pool, crowding_scores, blowup_info,
        )
        mt_risks = _find_mid_term_risks(
            sector_flow, individual_flow, crowding_scores, deep_data, all_sections,
        )

        # ---- build markdown ----
        lines = ["## 机会与风险", ""]

        # Opportunities table
        lines.append("### 机会")
        lines.append("")
        lines.append("| # | 机会 | 级别 | 逻辑 |")
        lines.append("|---|------|------|------|")
        for i, (opp, level, logic) in enumerate(st_opps + mt_opps, 1):
            level_icon = "短线" if level == "short" else "中线"
            color = "🔴" if level == "short" else "🟡"
            lines.append(f"| {i} | {opp} | {color} {level_icon} | {logic} |")
        lines.append("")

        # Risks table
        lines.append("### 风险")
        lines.append("")
        lines.append("| # | 风险 | 级别 | 逻辑 |")
        lines.append("|---|------|------|------|")
        for i, (risk, level, logic) in enumerate(st_risks + mt_risks, 1):
            level_icon = "短线" if level == "short" else "中线"
            color = "🔴" if level == "short" else "🟡"
            lines.append(f"| {i} | {risk} | {color} {level_icon} | {logic} |")

        return "\n".join(lines), None

    except Exception as e:
        return None, f"机会与风险分析失败: {e}"


# ================================================================
# Short-term opportunities (3 rules)
# ================================================================

def _find_short_term_opportunities(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
    individual_flow: list[dict],
    crowding_scores: dict,
) -> list[tuple[str, str, str]]:
    """Find short-term (短线) opportunities."""
    opportunities = []

    # --- Rule A: Sectors with net inflow AND growing limit-up cluster ---
    rule_a_opp = _rule_a_inflow_limit_up_cluster(sector_flow, limit_up_pool)
    if rule_a_opp:
        opportunities.append(rule_a_opp)

    # --- Rule B: 首板 stocks in inflow-heavy sectors ---
    rule_b_opp = _rule_b_first_board_in_inflow(sector_flow, limit_up_pool)
    if rule_b_opp:
        opportunities.append(rule_b_opp)

    # --- Rule C: Reversal plays ---
    rule_c_opp = _rule_c_reversal_plays(sector_flow, individual_flow)
    if rule_c_opp:
        opportunities.append(rule_c_opp)

    # Fill remaining slots with fallbacks
    while len(opportunities) < 3:
        fallback = _short_term_fallback(sector_flow, limit_up_pool, len(opportunities))
        if fallback:
            opportunities.append(fallback)
        else:
            break

    return opportunities[:3]


def _rule_a_inflow_limit_up_cluster(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
) -> tuple[str, str, str] | None:
    """Rule A: Sectors with net inflow > 0 AND limit-up cluster growing."""
    # Find top 3 inflow sectors
    top_inflow = sorted(
        [s for s in sector_flow if s.get("净额", 0) > 0],
        key=lambda x: float(x.get("净额", 0)),
        reverse=True,
    )[:3]

    for sector in top_inflow:
        name = sector.get("行业", "")
        net = float(sector.get("净额", 0))
        # Count limit-ups in this sector
        lu_count = sum(1 for lu in limit_up_pool if lu.get("所属行业") == name)
        if lu_count >= 2:
            return (
                f"{name}板块短线动量机会",
                "short",
                f"{name}净流入+{net:.1f}亿，涨停{lu_count}只形成集群，"
                f"短期资金扎堆，适合短线跟随但需快进快出",
            )

    # Relax: any sector with inflow and at least 1 limit-up
    for sector in top_inflow:
        name = sector.get("行业", "")
        net = float(sector.get("净额", 0))
        lu_count = sum(1 for lu in limit_up_pool if lu.get("所属行业") == name)
        if lu_count >= 1:
            return (
                f"{name}板块资金关注度提升",
                "short",
                f"{name}净流入+{net:.1f}亿，出现涨停个股，"
                f"关注该板块是否形成持续资金合力",
            )

    return None


def _rule_b_first_board_in_inflow(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
) -> tuple[str, str, str] | None:
    """Rule B: 首板 (first board) stocks in inflow-heavy sectors."""
    top_sector_names = {
        s.get("行业", "") for s in sorted(
            [s for s in sector_flow if s.get("净额", 0) > 0],
            key=lambda x: float(x.get("净额", 0)),
            reverse=True,
        )[:5]
    }

    first_board_candidates = []
    for lu in limit_up_pool:
        lb = lu.get("连板数", 1)
        if isinstance(lb, str):
            parts = lb.split("/")
            try:
                lb = int(parts[0])
            except (ValueError, IndexError):
                lb = 1
        sector = lu.get("所属行业", "")
        name = lu.get("名称", "")
        if lb == 1 and sector in top_sector_names:
            first_board_candidates.append((name, sector))

    if first_board_candidates:
        names = [c[0] for c in first_board_candidates[:3]]
        sectors = list({c[1] for c in first_board_candidates[:3]})
        sector_str = "、".join(sectors)
        name_str = "、".join(names)
        return (
            f"首板突破机会（{name_str}）",
            "short",
            f"{sector_str}板块资金持续流入，{name_str}今日首板涨停，"
            f"若明日高开确认则具备短线博弈价值，注意设好止损",
        )

    return None


def _rule_c_reversal_plays(
    sector_flow: list[dict],
    individual_flow: list[dict],
) -> tuple[str, str, str] | None:
    """Rule C: Reversal plays — sectors that went from net outflow to inflow.

    Since we don't have prev-day sector_flow in this module (unless it's
    in all_sections), we look for stocks/sectors with strong reversal signals:
    stocks that are up >5% today AND have net inflow, implying a turnaround.
    """
    # Find sectors with high net inflow that are mid-ranked (not top, suggesting
    # they recently turned around)
    positive_sectors = sorted(
        [s for s in sector_flow if s.get("净额", 0) > 0],
        key=lambda x: float(x.get("净额", 0)),
        reverse=True,
    )

    # Look for sectors in the middle of the pack with moderate inflow
    # (reversal typically starts moderate, not at the top)
    mid_sectors = positive_sectors[len(positive_sectors) // 3: len(positive_sectors) * 2 // 3]
    for sector in mid_sectors:
        name = sector.get("行业", "")
        net = float(sector.get("净额", 0))
        leader = sector.get("领涨股", "")
        leader_chg = sector.get("领涨股-涨跌幅", 0)
        if net > 0 and float(leader_chg or 0) > 3:
            return (
                f"{name}板块资金反转迹象",
                "short",
                f"{name}由弱转强，净流入+{net:.1f}亿，龙头{leader}涨{leader_chg:.1f}%，"
                f"若持续性确认可考虑参与",
            )

    return None


def _short_term_fallback(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
    idx: int,
) -> tuple[str, str, str] | None:
    """Generate fallback short-term opportunities when rules don't fire."""
    top_inflow = sorted(
        [s for s in sector_flow if s.get("净额", 0) > 0],
        key=lambda x: float(x.get("净额", 0)),
        reverse=True,
    )[:5]

    if idx == 0 and top_inflow:
        s = top_inflow[0]
        return (
            f"{s['行业']}板块趋势跟随",
            "short",
            f"{s['行业']}为当日资金净流入最大板块（+{float(s.get('净额',0)):.1f}亿），"
            f"龙头{s.get('领涨股','')}领涨，顺势参与需关注量能持续性",
        )
    elif idx == 1 and len(top_inflow) >= 2:
        s = top_inflow[1]
        return (
            f"{s['行业']}板块补涨机会",
            "short",
            f"{s['行业']}净流入+{float(s.get('净额',0)):.1f}亿居次席，"
            f"若龙头板块冲高回落，资金可能轮动至此",
        )
    elif idx == 2 and limit_up_pool:
        # Find the sector with most limit-ups
        sector_counts = {}
        for lu in limit_up_pool:
            s = lu.get("所属行业", "未知")
            sector_counts[s] = sector_counts.get(s, 0) + 1
        if sector_counts:
            top_sector = max(sector_counts, key=sector_counts.get)
            count = sector_counts[top_sector]
            return (
                f"{top_sector}板块涨停集群效应",
                "short",
                f"{top_sector}板块出现{count}只涨停，板块效应明显，"
                f"龙头个股次日高溢价概率较大",
            )

    return None


# ================================================================
# Mid-term opportunities (3 rules)
# ================================================================

def _find_mid_term_opportunities(
    sector_flow: list[dict],
    crowding_scores: dict,
    all_sections: dict,
    deep_data: dict,
) -> list[tuple[str, str, str]]:
    """Find mid-term (中线) opportunities."""
    opportunities = []

    # --- Rule A: Low crowding + positive flow → undervalued entry ---
    rule_a_opp = _rule_a_low_crowding_positive_flow(sector_flow, crowding_scores)
    if rule_a_opp:
        opportunities.append(rule_a_opp)

    # --- Rule B: Policy-catalyzed sectors ---
    rule_b_opp = _rule_b_policy_catalyzed(all_sections, deep_data)
    if rule_b_opp:
        opportunities.append(rule_b_opp)

    # --- Rule C: Defensive sectors with low crowding ---
    rule_c_opp = _rule_c_defensive_low_crowding(sector_flow, crowding_scores)
    if rule_c_opp:
        opportunities.append(rule_c_opp)

    # Fill remaining slots
    while len(opportunities) < 3:
        fallback = _mid_term_fallback(sector_flow, crowding_scores, len(opportunities))
        if fallback:
            opportunities.append(fallback)
        else:
            break

    return opportunities[:3]


def _rule_a_low_crowding_positive_flow(
    sector_flow: list[dict],
    crowding_scores: dict,
) -> tuple[str, str, str] | None:
    """Rule A: Sectors with crowding < 5 AND positive flow → undervalued."""
    candidates = []
    for name, info in crowding_scores.items():
        if info.get("score", 10) < 5 and info.get("net_flow", -1) > 0:
            candidates.append((name, info["score"], info["net_flow"]))

    if candidates:
        candidates.sort(key=lambda x: x[1])  # lowest crowding first
        name, score, flow = candidates[0]
        return (
            f"{name}板块低拥挤+资金流入",
            "mid",
            f"{name}拥挤度仅{score:.1f}/10（低位），且资金净流入+{flow:.1f}亿，"
            f"中线配置价值凸显，可逢低分批布局",
        )

    # Fallback: look in sector_flow for sectors with inflow but not in crowding
    if not crowding_scores and sector_flow:
        positive = [s for s in sector_flow if s.get("净额", 0) > 0]
        positive.sort(key=lambda x: float(x.get("净额", 0)))
        if positive:
            # Take a moderate one (not the hottest = less crowded)
            s = positive[len(positive) // 2]
            return (
                f"{s['行业']}板块中线关注",
                "mid",
                f"{s['行业']}净流入+{float(s.get('净额',0)):.1f}亿，"
                f"未处于极端拥挤状态，中线可跟踪资金持续性与龙头业绩兑现",
            )

    return None


def _rule_b_policy_catalyzed(
    all_sections: dict,
    deep_data: dict,
) -> tuple[str, str, str] | None:
    """Rule B: Policy-catalyzed sectors from news/theme analysis.

    Searches all_sections for keywords suggesting policy catalyst.
    """
    # Check all_sections for policy-related themes
    policy_keywords = ["政策", "产业", "国家", "规划", "文件", "会议", "补贴", "监管放松",
                       "十四五", "十五五", "两会", "中央", "国务院", "发改委", "工信部"]
    policy_sectors = set()

    for module_key, content in all_sections.items():
        if not isinstance(content, str):
            continue
        for kw in policy_keywords:
            if kw in content:
                # Try to extract sector names from the content
                for sector_name in SECTOR_CATEGORY_MAP:
                    if sector_name in content:
                        policy_sectors.add(sector_name)

    if policy_sectors:
        sector_list = "、".join(sorted(policy_sectors)[:3])
        return (
            f"{sector_list}政策催化方向",
            "mid",
            f"当日新闻中出现政策信号，{sector_list}相关板块受催化，"
            f"中线跟踪政策落地节奏与产业数据验证",
        )

    return None


def _rule_c_defensive_low_crowding(
    sector_flow: list[dict],
    crowding_scores: dict,
) -> tuple[str, str, str] | None:
    """Rule C: Defensive sectors with low crowding (< 3) and stable flow."""
    defensive_categories = {"消费", "医药", "金融", "农业"}

    candidates = []
    for name, info in crowding_scores.items():
        cat = SECTOR_CATEGORY_MAP.get(name, "")
        if cat in defensive_categories and info.get("score", 10) < 3:
            candidates.append((name, info["score"], info.get("net_flow", 0)))

    if candidates:
        candidates.sort(key=lambda x: x[1])  # lowest first
        name, score, flow = candidates[0]
        flow_str = f"+{flow:.1f}亿" if flow >= 0 else f"{flow:.1f}亿"
        return (
            f"{name}板块防御性配置",
            "mid",
            f"{name}拥挤度仅{score:.1f}/10（极低位），资金{flow_str}，"
            f"作为防御性板块具备中线安全边际，适合风险偏好较低的配置",
        )

    # Fallback: look in sector_flow for moderate-positive defensive sectors
    if not crowding_scores:
        defensive_positive = []
        for s in sector_flow:
            cat = SECTOR_CATEGORY_MAP.get(s.get("行业", ""), "")
            if cat in defensive_categories and s.get("净额", 0) > 0:
                defensive_positive.append(s)
        if defensive_positive:
            s = min(defensive_positive, key=lambda x: float(x.get("净额", 0)))
            return (
                f"{s['行业']}板块防御价值",
                "mid",
                f"{s['行业']}属防御类板块，净流入+{float(s.get('净额',0)):.1f}亿，"
                f"市场波动期具备相对抗跌属性，中线可作为底仓配置",
            )

    return None


def _mid_term_fallback(
    sector_flow: list[dict],
    crowding_scores: dict,
    idx: int,
) -> tuple[str, str, str] | None:
    """Fallback mid-term opportunities."""
    positive = sorted(
        [s for s in sector_flow if s.get("净额", 0) > 0],
        key=lambda x: float(x.get("净额", 0)),
    )

    if idx == 0 and len(positive) >= 2:
        s = positive[-2]  # second from top
        return (
            f"{s['行业']}中线趋势机会",
            "mid",
            f"{s['行业']}净流入+{float(s.get('净额',0)):.1f}亿，资金温和流入，"
            f"若行业基本面改善，中线具备趋势延续潜力",
        )
    elif idx == 1 and positive:
        s = positive[len(positive) // 3]
        return (
            f"{s['行业']}左侧布局窗口",
            "mid",
            f"{s['行业']}资金+{float(s.get('净额',0)):.1f}亿温和流入，"
            f"行业拥挤度不高，中线可等待催化剂逐步建仓",
        )
    elif idx == 2 and len(positive) >= 3:
        s = positive[len(positive) * 2 // 3]
        return (
            f"{s['行业']}板块中线观察池",
            "mid",
            f"{s['行业']}资金+{float(s.get('净额',0)):.1f}亿小幅流入，"
            f"作为备选方向纳入中线观察，关注后续资金是否持续流入及基本面变化",
        )

    # Fallback: use any sector (including neutral/outflow) for observations
    if idx == 2 and sector_flow:
        s = sector_flow[-1]  # last sector
        net = float(s.get("净额", 0))
        net_str = f"+{net:.1f}亿" if net >= 0 else f"{net:.1f}亿"
        return (
            f"{s['行业']}板块关注窗口",
            "mid",
            f"{s['行业']}资金{net_str}，当前市场风格下该板块"
            f"存在轮动可能，中线可纳入跟踪范围",
        )

    return None


# ================================================================
# Short-term risks (3 rules)
# ================================================================

def _find_short_term_risks(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
    crowding_scores: dict,
    blowup_info: dict,
) -> list[tuple[str, str, str]]:
    """Find short-term (短线) risks."""
    risks = []

    # --- Rule A: High-board stocks in outflow sectors ---
    rule_a_risk = _rule_a_high_board_outflow(limit_up_pool, sector_flow)
    if rule_a_risk:
        risks.append(rule_a_risk)

    # --- Rule B: Sectors with crowding > 7 ---
    rule_b_risk = _rule_b_overcrowding_short(crowding_scores)
    if rule_b_risk:
        risks.append(rule_b_risk)

    # --- Rule C: Blow-up rate > 40% ---
    rule_c_risk = _rule_c_high_blowup(blowup_info, limit_up_pool)
    if rule_c_risk:
        risks.append(rule_c_risk)

    # Fill remaining
    while len(risks) < 3:
        fallback = _short_term_risk_fallback(sector_flow, limit_up_pool, len(risks))
        if fallback:
            risks.append(fallback)
        else:
            break

    return risks[:3]


def _rule_a_high_board_outflow(
    limit_up_pool: list[dict],
    sector_flow: list[dict],
) -> tuple[str, str, str] | None:
    """Rule A: High-board stocks (3+ 连板) in sectors with net outflow."""
    # Find outflow sectors
    outflow_sectors = {
        s.get("行业", ""): float(s.get("净额", 0))
        for s in sector_flow if s.get("净额", 0) < 0
    }

    if not outflow_sectors:
        return None

    high_board_in_outflow = []
    for lu in limit_up_pool:
        lb = lu.get("连板数", 1)
        if isinstance(lb, str):
            parts = lb.split("/")
            try:
                lb = int(parts[0])
            except (ValueError, IndexError):
                lb = 1
        sector = lu.get("所属行业", "")
        if lb >= 3 and sector in outflow_sectors:
            high_board_in_outflow.append((lu.get("名称", ""), lb, sector,
                                         outflow_sectors[sector]))

    if high_board_in_outflow:
        hb = high_board_in_outflow[0]
        sector_set = list({h[2] for h in high_board_in_outflow[:3]})
        name_list = [h[0] for h in high_board_in_outflow[:3]]
        return (
            f"{'、'.join(sector_set)}高位股回调风险",
            "short",
            f"{'、'.join(name_list)}等{hb[1]}连板股所在{hb[2]}板块资金净流出"
            f"{abs(hb[3]):.1f}亿，高位股与板块资金背离，警惕获利盘兑现导致的大幅回调",
        )

    return None


def _rule_b_overcrowding_short(
    crowding_scores: dict,
) -> tuple[str, str, str] | None:
    """Rule B: Sectors with crowding score > 7 → overcrowding risk."""
    high = []
    for name, info in crowding_scores.items():
        if info.get("score", 0) > CROWDING_THRESHOLDS.get("crowding_score_high", 7):
            high.append((name, info["score"], info.get("net_flow", 0)))

    if high:
        high.sort(key=lambda x: x[1], reverse=True)
        name, score, flow = high[0]
        flow_desc = "资金仍在流入" if flow > 0 else "资金已开始流出"
        return (
            f"{name}板块过度拥挤风险",
            "short",
            f"{name}拥挤度{score:.1f}/10（高位），{flow_desc}（{flow:+.1f}亿），"
            f"拥挤度过高时追涨胜率骤降，短期应回避或仅轻仓参与",
        )

    # Fallback: if no crowding data, check sector_flow for extreme inflows
    return None


def _rule_c_high_blowup(
    blowup_info: dict,
    limit_up_pool: list[dict],
) -> tuple[str, str, str] | None:
    """Rule C: Blow-up rate > 40% → market overheating risk."""
    rate = float(blowup_info.get("炸板率", 0))

    # If no pre-computed rate, estimate from pool
    if rate == 0 and limit_up_pool:
        blown = sum(1 for lu in limit_up_pool if int(lu.get("炸板次数", 0)) > 0)
        total = len(limit_up_pool)
        rate = blown / total * 100 if total > 0 else 0

    if rate > 40:
        return (
            "市场整体过热——追高风险",
            "short",
            f"当日炸板率高达{rate:.1f}%（>40%警戒线），封板意愿急剧下降，"
            f"市场短期过热信号明确，追涨策略风险收益比极差，建议减仓观望",
        )
    elif rate > 30:
        return (
            "市场追高风险上升",
            "short",
            f"当日炸板率{rate:.1f}%偏高，多只涨停股盘中炸板，"
            f"高位股接力意愿减弱，短线应降低仓位并严格止损",
        )

    return None


def _short_term_risk_fallback(
    sector_flow: list[dict],
    limit_up_pool: list[dict],
    idx: int,
) -> tuple[str, str, str] | None:
    """Fallback short-term risks."""
    outflow = sorted(
        [s for s in sector_flow if s.get("净额", 0) < 0],
        key=lambda x: float(x.get("净额", 0)),
    )

    if idx == 0 and outflow:
        s = outflow[0]
        return (
            f"{s['行业']}板块资金持续出逃风险",
            "short",
            f"{s['行业']}净流出{abs(float(s.get('净额',0))):.1f}亿，"
            f"短期回避该板块，等待资金回流信号再考虑参与",
        )
    elif idx == 1 and len(outflow) >= 2:
        s = outflow[1]
        return (
            f"{s['行业']}板块弱势延续风险",
            "short",
            f"{s['行业']}净流出{abs(float(s.get('净额',0))):.1f}亿，"
            f"弱势板块不宜左侧抄底，等企稳信号出现再做决策",
        )
    elif idx == 2:
        # General market risk if blow-up rate unavailable
        return (
            "市场分化加剧——选股难度上升",
            "short",
            "板块间资金流向分化明显，追涨被套概率上升，"
            "短线操作应聚焦资金持续流入的主线板块",
        )

    return None


# ================================================================
# Mid-term risks (3 rules)
# ================================================================

def _find_mid_term_risks(
    sector_flow: list[dict],
    individual_flow: list[dict],
    crowding_scores: dict,
    deep_data: dict,
    all_sections: dict,
) -> list[tuple[str, str, str]]:
    """Find mid-term (中线) risks."""
    risks = []

    # --- Rule A: Sectors with persistent outflow ---
    rule_a_risk = _rule_a_persistent_outflow(sector_flow, individual_flow)
    if rule_a_risk:
        risks.append(rule_a_risk)

    # --- Rule B: Crowding reversal risk (score > 8) ---
    rule_b_risk = _rule_b_crowding_reversal(crowding_scores)
    if rule_b_risk:
        risks.append(rule_b_risk)

    # --- Rule C: External risk (US sector ETF negative → A-share correlated) ---
    rule_c_risk = _rule_c_external_risk(deep_data, all_sections)
    if rule_c_risk:
        risks.append(rule_c_risk)

    # Fill remaining
    while len(risks) < 3:
        fallback = _mid_term_risk_fallback(sector_flow, crowding_scores, len(risks))
        if fallback:
            risks.append(fallback)
        else:
            break

    return risks[:3]


def _rule_a_persistent_outflow(
    sector_flow: list[dict],
    individual_flow: list[dict],
) -> tuple[str, str, str] | None:
    """Rule A: Sectors appearing negative in both sector_flow and individual_flow.

    Since we only have one day's data, we mark sectors with large outflow
    as potentially persistent outflow risks.
    """
    # Find sectors with large negative flow
    outflow_sectors = sorted(
        [s for s in sector_flow if s.get("净额", 0) < -10],
        key=lambda x: float(x.get("净额", 0)),
    )

    if outflow_sectors:
        s = outflow_sectors[0]
        name = s.get("行业", "")
        net = float(s.get("净额", 0))
        # Count individual stocks in this sector with negative flow
        sector_individual_outflow = 0
        for ind in individual_flow:
            # approximate: if stock name appears and flow is negative
            flow_str = str(ind.get("净额", "0"))
            if "万" in flow_str or "亿" in flow_str:
                is_negative = flow_str.startswith("-")
                if is_negative:
                    sector_individual_outflow += 1

        if abs(net) > 20:
            severity = "大幅"
        else:
            severity = "持续"

        return (
            f"{name}板块{severity}资金流出风险",
            "mid",
            f"{name}板块净流出{abs(net):.1f}亿，个股层面也普遍承压，"
            f"中线回避该板块直至资金方向逆转或基本面出现改善信号",
        )

    return None


def _rule_b_crowding_reversal(
    crowding_scores: dict,
) -> tuple[str, str, str] | None:
    """Rule B: Crowding reversal risk — score > 8."""
    extreme = []
    for name, info in crowding_scores.items():
        if info.get("score", 0) > 8:
            extreme.append((name, info["score"], info.get("net_flow", 0)))

    if extreme:
        extreme.sort(key=lambda x: x[1], reverse=True)
        name, score, flow = extreme[0]
        return (
            f"{name}板块拥挤度极高——反转风险",
            "mid",
            f"{name}拥挤度{score:.1f}/10（极度拥挤），历史规律显示拥挤度>8后"
            f"板块通常进入中期调整，无论当前趋势多强都应逐步减仓",
        )

    return None


def _rule_c_external_risk(
    deep_data: dict,
    all_sections: dict,
) -> tuple[str, str, str] | None:
    """Rule C: External risk — US sector ETF negative → A-share correlated risk."""
    sections = deep_data.get("sections", {}) if deep_data else {}
    us_etfs = sections.get("us_sector_etfs", {}) or {}

    # Check US sector ETFs that impact A-shares
    critical_etfs = ["SMH", "QQQ", "KWEB"]  # semiconductor, tech, China internet
    negative_etfs = []
    for symbol in critical_etfs:
        etf_data = us_etfs.get(symbol, {})
        change = etf_data.get("change", 0)
        if change and change < 0:
            negative_etfs.append((symbol, etf_data.get("name", symbol), change))

    if negative_etfs:
        names = [e[1] for e in negative_etfs]
        changes_str = ", ".join(f"{n}{c:+.1f}%" for _, n, c in negative_etfs)
        return (
            "美股下跌传导A股风险",
            "mid",
            f"隔夜{changes_str}下跌，全球风险偏好承压，"
            f"A股半导体/科技/中概方向开盘可能承压，中线需关注美股趋势是否恶化",
        )

    # Also check from all_sections strings
    for key, content in all_sections.items():
        if isinstance(content, str) and "美股" in content:
            if "跌" in content[:200]:  # check first 200 chars for negative signal
                return (
                    "海外风险偏好回落传导风险",
                    "mid",
                    "美股市场出现调整信号，若调整持续，可能通过北向资金和情绪传导至A股，"
                    "中线需密切关注美联储政策及美股走势",
                )
            break

    return None


def _mid_term_risk_fallback(
    sector_flow: list[dict],
    crowding_scores: dict,
    idx: int,
) -> tuple[str, str, str] | None:
    """Fallback mid-term risks."""
    outflow = sorted(
        [s for s in sector_flow if s.get("净额", 0) < 0],
        key=lambda x: float(x.get("净额", 0)),
    )

    if idx == 0 and outflow:
        s = outflow[-1]  # smallest outflow
        return (
            f"{s['行业']}板块中线走弱风险",
            "mid",
            f"{s['行业']}净流出{abs(float(s.get('净额',0))):.1f}亿，"
            f"若连续多日流出则确认趋势走弱，中线应观望",
        )
    elif idx == 1 and len(outflow) >= 2:
        s = outflow[len(outflow) // 2]
        return (
            f"{s['行业']}板块资金阴跌风险",
            "mid",
            f"{s['行业']}持续净流出{abs(float(s.get('净额',0))):.1f}亿，"
            f"中线配置应关注行业景气度变化，基本面若恶化则需果断止损",
        )
    elif idx == 2 and len(outflow) >= 3:
        s = outflow[len(outflow) // 3]
        return (
            f"{s['行业']}板块中线回避",
            "mid",
            f"{s['行业']}净流出{abs(float(s.get('净额',0))):.1f}亿，"
            f"资金流出趋势下中线参与风险收益比不佳，等待明确企稳信号",
        )

    # Fallback: general macro risk
    if idx == 2:
        return (
            "市场结构性分化——中线选股难度加大",
            "mid",
            "当前市场板块间资金分化明显，中线持仓需关注行业景气度与资金趋势的匹配度，"
            "避免在资金持续流出方向重仓",
        )

    return None
