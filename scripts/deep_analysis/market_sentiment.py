"""
market_sentiment.py — 市场情绪综合评估 (Module 5 of deep analysis)

四维穿透框架 — 维度四：市场心理与博弈层

Calculates:
  1. Cycle stage (冰点→修复→高潮→分化)
  2. Money-making effect score (赚钱效应 0-10)
  3. Panic index (恐慌指数 0-10)
  4. Blow-up rate (炸板率) and seal success rate (封板成功率)

Pure computation: receives data, produces markdown. No external API calls.
"""

from scripts.knowledge_base import CROWDING_THRESHOLDS


def analyze(stats: dict, deep_data: dict) -> tuple[str | None, str | None]:
    """Generate market sentiment markdown section.

    Args:
        stats: Market stats dict from CSV (total, up, down, limit_up, big_up,
               big_down, limit_down, total_amount, etc.).
        deep_data: Raw deep data dict from data/deep/{date}.json. Expected keys
                   under ['sections']: limit_up_pool, limit_down_pool,
                   prev_limit_up, blow_up_and_prev_performance.

    Returns:
        (markdown_section, None) on success, or (None, error_msg) on failure.
    """
    try:
        sections = deep_data.get("sections", {}) if deep_data else {}

        # ---- extract data ----
        limit_up_pool = sections.get("limit_up_pool", []) or []
        limit_down_pool = sections.get("limit_down_pool", []) or []
        prev_limit_up = sections.get("prev_limit_up", []) or []
        blowup_info = sections.get("blow_up_and_prev_performance", {}) or {}

        total_stocks = max(stats.get("total", 1), 1)
        limit_up_count = len(limit_up_pool) if limit_up_pool else stats.get("limit_up", 0)
        limit_down_count = len(limit_down_pool) if limit_down_pool else stats.get("limit_down", 0)
        big_down = stats.get("big_down", 0)
        total_amount = stats.get("total_amount", 0)
        ratio = stats.get("ratio", 1.0)

        # ---- 1. cycle stage determination ----
        stage, stage_detail = _determine_cycle_stage(
            limit_up_pool, limit_down_pool, prev_limit_up,
            limit_up_count, total_amount, blowup_info, ratio, stats,
        )

        # ---- 2. money-making effect score (0-10) ----
        money_score, money_components = _compute_money_score(
            prev_limit_up, limit_up_count, blowup_info, limit_up_pool,
        )

        # ---- 3. panic index (0-10) ----
        panic_score = _compute_panic_index(limit_down_count, big_down, total_stocks)

        # ---- 4. blow-up rate ----
        blowup_rate, seal_rate = _extract_blowup_rate(blowup_info, limit_up_pool, stats)

        # ---- build markdown ----
        money_label = _score_label(money_score, "money")
        panic_label = _score_label(panic_score, "panic")
        blowup_label = _blowup_label(blowup_rate)

        lines = [
            "## 市场情绪",
            "",
            "| 指标 | 数值 | 判断 |",
            "|------|------|------|",
            f"| 周期阶段 | — | {stage}（{stage_detail}）|",
            f"| 赚钱效应 | {money_score:.1f}/10 | {money_label} |",
            f"| 恐慌指数 | {panic_score:.1f}/10 | {panic_label} |",
            f"| 炸板率 | {blowup_rate:.1f}% | {blowup_label} |",
            f"| 封板成功率 | {seal_rate:.1f}% | {_seal_label(seal_rate)} |",
            "",
            "### 情绪综合判断",
            "",
            _generate_summary(stage, money_score, panic_score, blowup_rate,
                              limit_up_count, limit_down_count, total_amount),
        ]

        return "\n".join(lines), None

    except Exception as e:
        return None, f"市场情绪分析失败: {e}"


# ================================================================
# 1. Cycle stage determination
# ================================================================

def _determine_cycle_stage(
    limit_up_pool: list[dict],
    limit_down_pool: list[dict],
    prev_limit_up: list[dict],
    limit_up_count: int,
    total_amount: float,
    blowup_info: dict,
    ratio: float,
    stats: dict,
) -> tuple[str, str]:
    """Determine the market cycle stage based on multiple indicators.

    Returns (stage_name, detail_description).
    """
    # -- count multi-board stocks (4+) --
    multi_board_4plus = 0
    multi_board_3plus = 0
    for item in limit_up_pool:
        lb = item.get("连板数", 0)
        if isinstance(lb, str):
            # "10/6" format: split and take first part
            parts = lb.split("/")
            try:
                lb = int(parts[0])
            except (ValueError, IndexError):
                lb = 1
        if lb >= 4:
            multi_board_4plus += 1
        if lb >= 3:
            multi_board_3plus += 1

    # -- prev limit-up stock performance --
    prev_up_pct = 50.0  # neutral default
    if prev_limit_up:
        changes = []
        for item in prev_limit_up:
            chg = float(item.get("涨跌幅", 0))
            changes.append(chg)
        if changes:
            prev_up_pct = sum(1 for c in changes if c > 0) / len(changes) * 100

    # -- blow-up rate --
    blowup_rate, _ = _extract_blowup_rate(blowup_info, limit_up_pool, stats)

    # -- turnover assessment (万亿 scale) --
    turnover_level = "正常"
    if total_amount >= 18000:
        turnover_level = "天量"
    elif total_amount >= 13000:
        turnover_level = "放量"
    elif total_amount >= 9000:
        turnover_level = "正常"
    elif total_amount >= 6000:
        turnover_level = "缩量"
    else:
        turnover_level = "地量"

    # -- stage logic (priority: frozen > climax > divergence > repair > default) --
    frozen_signals = 0
    climax_signals = 0
    divergence_signals = 0
    repair_signals = 0

    # 冰点 signals
    if limit_up_count < 30:
        frozen_signals += 2
    if total_amount < 8000:
        frozen_signals += 1
    if ratio < 0.8:
        frozen_signals += 1

    # 高潮 signals
    if limit_up_count >= 80:
        climax_signals += 2
    if multi_board_4plus >= 3:
        climax_signals += 1
    if total_amount >= 13000:
        climax_signals += 1
    if ratio >= 3:
        climax_signals += 1

    # 分化 signals
    if limit_up_count >= 50 and blowup_rate > 30:
        divergence_signals += 2
    if limit_up_count >= 50 and ratio < 1.5:
        divergence_signals += 1
    if blowup_rate > 35:
        divergence_signals += 1

    # 修复 signals
    if 30 <= limit_up_count <= 80 and prev_up_pct >= 50:
        repair_signals += 1
    if 30 <= limit_up_count and prev_up_pct >= 60:
        repair_signals += 1

    # Determine stage
    if frozen_signals >= 3 and limit_up_count < 30:
        stage = "冰点"
        detail = f"涨停{limit_up_count}只，成交{total_amount:.0f}亿（{turnover_level}），市场情绪极度低迷"
    elif climax_signals >= 3:
        stage = "高潮"
        if multi_board_4plus > 0:
            detail = f"涨停{limit_up_count}只，{multi_board_4plus}只4+连板，成交{total_amount:.0f}亿（{turnover_level}）"
        else:
            detail = f"涨停{limit_up_count}只，成交{total_amount:.0f}亿（{turnover_level}），做多情绪高涨"
    elif divergence_signals >= 2:
        stage = "分化"
        detail = f"涨停{limit_up_count}只但炸板率{blowup_rate:.1f}%，板块间分化明显"
    elif repair_signals >= 1:
        stage = "修复"
        detail = f"涨停{limit_up_count}只，昨日涨停今日上涨{prev_up_pct:.0f}%，情绪回暖"
    elif limit_up_count < 30:
        stage = "冰点"
        detail = f"涨停仅{limit_up_count}只，市场情绪冰点"
    elif limit_up_count > 80:
        if blowup_rate > 30:
            stage = "分化"
            detail = f"涨停{limit_up_count}只但炸板率{blowup_rate:.1f}%，高位分歧加剧"
        else:
            stage = "高潮"
            detail = f"涨停{limit_up_count}只，市场热度较高"
    else:
        # Default: determine based on ratio
        if ratio >= 2:
            stage = "修复"
            detail = f"涨跌比{ratio}，涨停{limit_up_count}只，市场偏暖"
        elif ratio >= 1:
            stage = "修复"
            detail = f"涨跌比{ratio}，涨停{limit_up_count}只，市场中性偏稳"
        else:
            stage = "冰点"
            detail = f"涨跌比{ratio}，涨停{limit_up_count}只，市场偏弱"

    return stage, detail


# ================================================================
# 2. Money-making effect score (0-10)
# ================================================================

def _compute_money_score(
    prev_limit_up: list[dict],
    limit_up_count: int,
    blowup_info: dict,
    limit_up_pool: list[dict],
) -> tuple[float, list[str]]:
    """Compute the money-making effect score with component breakdown.

    Returns (score, [component_labels]).
    """
    components = []

    # Component 1: previous limit-up performance (weight 0.4)
    w1 = 0.4
    c1 = 0.0
    if prev_limit_up:
        changes = []
        for item in prev_limit_up:
            try:
                chg = float(item.get("涨跌幅", 0))
                changes.append(chg)
            except (ValueError, TypeError):
                pass
        if changes:
            up_pct = sum(1 for c in changes if c > 0) / len(changes) * 100
            c1 = min(up_pct / 10, 10)  # normalize: 100% up → score 10
            components.append(f"昨日涨停今日上涨{up_pct:.0f}%（权重{w1:.1f}）")
        else:
            w2_adj = 0.3 + w1 / 2
            w3_adj = 0.3 + w1 / 2
            components.append(f"昨日涨停数据异常，权重转移至其他分量")
    else:
        # No prev data: redistribute weight to components 2 and 3
        w2_adj = 0.3 + w1 / 2
        w3_adj = 0.3 + w1 / 2
        components.append("昨日涨停数据不可用，权重转移")

    if not prev_limit_up or not any("权重转移" in c for c in components):
        w2_adj = 0.3
        w3_adj = 0.3

    # Component 2: current limit_up count normalized (weight 0.3, or adjusted)
    if limit_up_count >= 150:
        c2 = 10
    elif limit_up_count >= 100:
        c2 = 8
    elif limit_up_count >= 80:
        c2 = 7
    elif limit_up_count >= 50:
        c2 = 5
    elif limit_up_count >= 30:
        c2 = 3
    elif limit_up_count > 0:
        c2 = 1.5
    else:
        c2 = 0
    components.append(f"当日涨停{limit_up_count}只→得分{c2:.0f}（权重{w2_adj:.1f}）")

    # Component 3: inverse of blow-up rate (weight 0.3, or adjusted)
    blowup_rate, _ = _extract_blowup_rate(blowup_info, limit_up_pool, {"limit_up": limit_up_count, "big_up": 0})
    if blowup_rate <= 10:
        c3 = 10
    elif blowup_rate <= 20:
        c3 = 8
    elif blowup_rate <= 30:
        c3 = 5
    elif blowup_rate <= 40:
        c3 = 3
    else:
        c3 = max(0, 10 - blowup_rate / 5)  # linear decay after 40%
    components.append(f"炸板率{blowup_rate:.1f}%→得分{c3:.0f}（权重{w3_adj:.1f}）")

    score = round(w1 * c1 + w2_adj * c2 + w3_adj * c3, 1)

    return min(score, 10), components


# ================================================================
# 3. Panic index (0-10)
# ================================================================

def _compute_panic_index(
    limit_down_count: int,
    big_down: int,
    total_stocks: int,
) -> float:
    """Compute panic index (0-10) from limit-down and big-down ratios.

    Primary: limit_down / total * 100, capped at 10.
    Secondary: big_down / total * 100 * 0.3, added as supplement.
    """
    primary = (limit_down_count / total_stocks * 100) if total_stocks > 0 else 0
    secondary = (big_down / total_stocks * 100 * 0.3) if total_stocks > 0 else 0

    score = min(min(primary, 10) + secondary, 10)
    return round(score, 1)


# ================================================================
# 4. Blow-up rate extraction
# ================================================================

def _extract_blowup_rate(
    blowup_info: dict,
    limit_up_pool: list[dict],
    stats: dict,
) -> tuple[float, float]:
    """Extract blow-up rate and seal success rate.

    Priority:
      1. From blowup_info (pre-computed by prep_deep_data)
      2. Estimated from limit_up_pool data (炸板次数)
      3. Estimated from stats (big_up vs limit_up)
    """
    rate = 0.0
    seal_rate = 100.0

    # Priority 1: pre-computed data
    if blowup_info:
        rate = float(blowup_info.get("炸板率", 0))
        seal_rate = float(blowup_info.get("封板成功率", 100))
        if rate > 0 or seal_rate < 100:
            return rate, seal_rate

    # Priority 2: from limit_up_pool 炸板次数
    if limit_up_pool:
        total = len(limit_up_pool)
        blown = 0
        for item in limit_up_pool:
            try:
                bc = int(item.get("炸板次数", 0))
                if bc > 0:
                    blown += 1
            except (ValueError, TypeError):
                pass
        if total > 0:
            rate = blown / total * 100
            seal_rate = 100 - rate
            return round(rate, 1), round(seal_rate, 1)

    # Priority 3: estimate from stats
    limit_up = stats.get("limit_up", 0)
    big_up = stats.get("big_up", 0)
    # Rough estimate: stocks that are "big up" but not "limit up" are potential 炸板
    # This is a noisy approximation
    if limit_up > 0:
        estimated_blown = max(0, big_up * 0.1)  # ~10% of big_up might be 炸板
        estimated_total = limit_up + estimated_blown
        if estimated_total > 0:
            rate = estimated_blown / estimated_total * 100
            seal_rate = 100 - rate

    return round(rate, 1), round(seal_rate, 1)


# ================================================================
# Label helpers
# ================================================================

def _score_label(score: float, score_type: str) -> str:
    """Convert numeric score to descriptive label."""
    if score_type == "money":
        if score >= 8:
            return "极强——市场赚钱效应显著"
        elif score >= 6:
            return "中等偏强——有一定赚钱效应"
        elif score >= 4:
            return "中等——结构性机会为主"
        elif score >= 2:
            return "偏弱——赚钱难度较大"
        else:
            return "极弱——市场缺乏赚钱效应"
    elif score_type == "panic":
        if score >= 8:
            return "极高——恐慌情绪蔓延"
        elif score >= 5:
            return "较高——市场出现恐慌苗头"
        elif score >= 3:
            return "中等——局部恐慌"
        elif score >= 1:
            return "较低——市场情绪稳定"
        else:
            return "极低——市场毫无恐慌"


def _blowup_label(rate: float) -> str:
    if rate >= 40:
        return "高——封板意愿弱，追高风险大"
    elif rate >= 30:
        return "偏高——炸板较多，需谨慎追涨"
    elif rate >= 20:
        return "正常偏高"
    else:
        return "正常——封板意愿强"


def _seal_label(rate: float) -> str:
    if rate >= 80:
        return "强——封板成功率较高"
    elif rate >= 70:
        return "正常"
    elif rate >= 60:
        return "偏弱——炸板风险较大"
    else:
        return "弱——追涨需格外谨慎"


# ================================================================
# Sentiment summary generation
# ================================================================

def _generate_summary(
    stage: str,
    money_score: float,
    panic_score: float,
    blowup_rate: float,
    limit_up_count: int,
    limit_down_count: int,
    total_amount: float,
) -> str:
    """Generate 2-3 sentence sentiment summary based on indicators."""
    parts = []

    # Sentence 1: cycle stage + core condition
    if stage == "高潮":
        parts.append(
            f"当前市场处于{stage}阶段，涨停{limit_up_count}家，成交{total_amount:.0f}亿，"
            f"做多情绪充分释放，但需关注高位分化的风险。"
        )
    elif stage == "分化":
        parts.append(
            f"市场进入{stage}阶段，涨停家数仍较多但炸板率升至{blowup_rate:.1f}%，"
            f"资金分歧加大，追高风险上升。"
        )
    elif stage == "修复":
        parts.append(
            f"市场处于{stage}阶段，赚钱效应{_level_cn(money_score)}，"
            f"情绪从冰点回暖，可适度参与结构性机会。"
        )
    else:  # 冰点
        parts.append(
            f"市场处于{stage}阶段，赚钱效应{_level_cn(money_score)}，恐慌指数{panic_score:.1f}，"
            f"资金参与意愿低迷，宜保持谨慎或逢低左侧布局。"
        )

    # Sentence 2: money effect + panic summary
    if money_score >= 6:
        parts.append(f"赚钱效应{_level_cn(money_score)}（{money_score:.1f}/10），短线资金活跃度较高。")
    elif money_score >= 4:
        parts.append(f"赚钱效应中等（{money_score:.1f}/10），以结构性机会为主，需精选方向。")
    else:
        parts.append(f"赚钱效应{_level_cn(money_score)}（{money_score:.1f}/10），追涨策略风险收益比不佳。")

    # Sentence 3: risk note
    if panic_score >= 5:
        parts.append(f"恐慌指数偏高（{panic_score:.1f}/10），跌停{limit_down_count}家，注意风险控制。")
    elif blowup_rate >= 30:
        parts.append(f"炸板率{blowup_rate:.1f}%偏高，封板意愿减弱，警惕情绪退潮。")
    elif stage == "高潮":
        parts.append(f"连续高潮后需警惕情绪退潮和获利盘兑现压力。")
    else:
        parts.append(f"整体市场情绪处于可控区间，关注量能变化与主线持续性。")

    return "".join(parts)


def _level_cn(score: float) -> str:
    if score >= 8:
        return "极强"
    elif score >= 6:
        return "偏强"
    elif score >= 4:
        return "中等"
    elif score >= 2:
        return "偏弱"
    else:
        return "极弱"
