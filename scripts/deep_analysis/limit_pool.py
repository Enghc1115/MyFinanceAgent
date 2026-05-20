"""
limit_pool.py — 涨停跌停全景 + 连板梯队分析
Deep Analysis Module 2 of 8

读取涨停池/跌停池数据，按连板数分层展示涨停梯队，
并对跌停个股做原因归类（业绩暴雷/行业利空/资金出逃/其他）。
"""

from collections import Counter

from scripts.knowledge_base import SECTOR_CATEGORY_MAP, STOCK_NAME_DICT, STOCK_CODE_TO_NAME


# ---- 对外主入口 ----


def analyze(deep_data: dict, prev_deep_data: dict = None) -> tuple[str | None, str | None]:
    """
    涨停跌停全景分析主入口。合并涨停梯队 + 跌停分析为一个 Markdown 段落。

    Args:
        deep_data: 当日深度数据 dict（含 limit_up_pool / limit_down_pool 等 section）
        prev_deep_data: 前一交易日深度数据 dict（可选，用于连板交叉验证）

    Returns:
        (markdown_section, error_str_or_None)
    """
    if deep_data is None:
        return (None, "deep_data 为 None，无涨停/跌停数据")

    up_md, up_err = analyze_limit_up(deep_data, prev_deep_data)
    down_md, down_err = analyze_limit_down(deep_data)

    errors = [e for e in (up_err, down_err) if e]
    if errors and not up_md and not down_md:
        return (None, "; ".join(errors))

    parts = []
    if up_md:
        parts.append(up_md)
    if down_md:
        parts.append(down_md)
    if errors:
        parts.append(f"> 数据异常: {'; '.join(errors)}")

    return ("\n\n".join(parts), None)


def analyze_limit_up(deep_data: dict, prev_deep_data: dict = None) -> tuple[str | None, str | None]:
    """
    涨停池分析：按连板数分层展示，识别主线主题。

    Args:
        deep_data: 当日深度数据
        prev_deep_data: 前日深度数据（可选）

    Returns:
        (markdown_section, error_str_or_None)
    """
    try:
        sections = (deep_data or {}).get("sections", {})
        pool = sections.get("limit_up_pool", [])

        if not pool:
            return ("### 涨停梯队\n\n- 今日无涨停个股", None)

        # ---- 1. 构建昨日涨停代码集合（供连板交叉验证） ----
        yesterday_codes: set[str] = set()
        if prev_deep_data:
            prev_sections = prev_deep_data.get("sections", {})
            prev_pool = prev_sections.get("limit_up_pool", [])
            yesterday_codes = {_norm_code(r.get("代码", "")) for r in prev_pool}

        # ---- 2. 计算每只个股的连板数与归类 ----
        stocks: list[dict] = []
        for r in pool:
            code = _norm_code(r.get("代码", ""))
            name = r.get("名称", "")
            sector = r.get("所属行业", "")
            consecutive = _resolve_consecutive(r, yesterday_codes)

            # 确定主线（从 sector → category 映射，再按板块聚类）
            category = SECTOR_CATEGORY_MAP.get(sector, _infer_category_from_code(code))
            theme = category if category else "其他"

            stocks.append({
                "code": code,
                "name": name,
                "sector": sector,
                "theme": theme,
                "consecutive": consecutive,
            })

        # ---- 3. 按连板数分层 ----
        tier_4plus = [s for s in stocks if s["consecutive"] >= 4]
        tier_3 = [s for s in stocks if s["consecutive"] == 3]
        tier_2 = [s for s in stocks if s["consecutive"] == 2]
        tier_1 = [s for s in stocks if s["consecutive"] <= 1]

        # ---- 4. 组装 Markdown ----
        lines = ["### 涨停梯队", ""]
        lines.append("| 连板层级 | 个股列表 | 所属主线 |")
        lines.append("|---------|---------|---------|")

        _render_tier(lines, "4+连板", tier_4plus)
        _render_tier(lines, "3连板", tier_3)
        _render_tier(lines, "2连板", tier_2)
        _render_tier(lines, "首板", tier_1)

        lines.append("")

        # 统计行
        total = len(pool)
        lines.append(f"- **涨停总计**: {total} 家")

        # 炸板率
        blow_rate = _extract_blow_rate(deep_data, pool)
        if blow_rate is not None:
            lines.append(f"- **炸板率**: {blow_rate:.1f}%")

        # 昨日涨停今日表现
        prev_perf = _extract_prev_performance(deep_data)
        if prev_perf:
            lines.append(
                f"- **昨日涨停今日表现**: "
                f"上涨 {prev_perf.get('上涨数','?')} / "
                f"下跌 {prev_perf.get('下跌数','?')} / "
                f"平盘 {prev_perf.get('平盘数','?')} "
                f"（上涨比例 {prev_perf.get('上涨比例','?')}%）"
            )

        return ("\n".join(lines), None)

    except Exception as e:
        return (None, f"涨停分析失败: {e}")


def analyze_limit_down(deep_data: dict) -> tuple[str | None, str | None]:
    """
    跌停池分析：按原因归类（业绩暴雷/行业利空/资金出逃/其他）。

    Args:
        deep_data: 当日深度数据

    Returns:
        (markdown_section, error_str_or_None)
    """
    try:
        sections = (deep_data or {}).get("sections", {})
        pool = sections.get("limit_down_pool", [])

        if not pool:
            return ("### 跌停分析\n\n- 今日无跌停个股", None)

        # ---- 1. 收集所有跌停股信息 ----
        records: list[dict] = []
        for r in pool:
            records.append({
                "code": _norm_code(r.get("代码", "")),
                "name": r.get("名称", ""),
                "sector": r.get("所属行业", ""),
            })

        # ---- 2. 行业聚类，判断是否存在行业利空 ----
        sector_counter = Counter(r["sector"] for r in records)

        # ---- 3. 逐股判定原因 ----
        classified: list[dict] = []
        for r in records:
            reason = _classify_limit_down_reason(r, sector_counter)
            classified.append({**r, "reason": reason})

        # ---- 4. 组装 Markdown ----
        lines = ["### 跌停分析", ""]
        lines.append("| 个股 | 代码 | 跌停原因 |")
        lines.append("|------|------|---------|")

        for r in classified:
            lines.append(f"| {r['name']} | {r['code']} | {r['reason']} |")

        lines.append("")
        lines.append(f"- **跌停总计**: {len(pool)} 家")

        return ("\n".join(lines), None)

    except Exception as e:
        return (None, f"跌停分析失败: {e}")


# ---- 内部辅助函数 ----


def _norm_code(raw) -> str:
    """标准化股票代码为 6 位字符串。"""
    return str(raw).strip().zfill(6)


def _resolve_consecutive(record: dict, yesterday_codes: set[str]) -> int:
    """确定个股连板数。

    优先使用数据自带的 '连板数' 字段，其次通过昨日涨停池交叉验证。
    """
    try:
        raw = record.get("连板数")
        if raw is not None and str(raw).strip() != "":
            return int(raw)
    except (ValueError, TypeError):
        pass

    # 回退：与昨日涨停池对比
    code = _norm_code(record.get("代码", ""))
    if code in yesterday_codes:
        return 2  # 至少 2 连板（无法确定更高连板数）
    return 1


def _infer_category_from_code(code: str) -> str | None:
    """通过代码反查 STOCK_NAME_DICT 获取 category。"""
    for name, info in STOCK_NAME_DICT.items():
        if info["code"] == code:
            return info.get("category")
    return None


def _classify_limit_down_reason(record: dict, sector_counter: Counter) -> str:
    """判断一只跌停股的原因类别。"""
    name = record.get("name", "")
    sector = record.get("sector", "")
    code = record.get("code", "")

    # 1. 业绩暴雷：ST / *ST 股票
    if "ST" in name.upper() or name.startswith("*"):
        return f"业绩暴雷（{name} 存在退市/财务风险）"

    # 2. 行业利空：同行业 >= 3 只跌停
    if sector and sector_counter.get(sector, 0) >= 3:
        return f"行业利空（{sector}板块集体回调，共 {sector_counter[sector]} 家跌停）"

    # 3. 资金出逃：检测是否为前期热门股（在 STOCK_NAME_DICT 中）
    if code in STOCK_CODE_TO_NAME:
        return "资金出逃（前期热门股遭遇集中抛售）"

    # 4. 兜底
    return "其他（市场情绪或个股因素）"


def _extract_blow_rate(deep_data: dict, pool: list) -> float | None:
    """提取炸板率。优先从 blow_up_and_prev_performance section 获取，
    其次从涨停池记录中的 炸板次数 字段计算。"""
    sections = deep_data.get("sections", {})
    blow_info = sections.get("blow_up_and_prev_performance", {})

    if blow_info and "炸板率" in blow_info:
        return float(blow_info["炸板率"])

    # 从涨停池自行计算
    if not pool:
        return None
    total = len(pool)
    blown = 0
    for r in pool:
        try:
            if int(r.get("炸板次数", 0)) > 0:
                blown += 1
        except (ValueError, TypeError):
            pass
    return round(blown / total * 100, 1)


def _extract_prev_performance(deep_data: dict) -> dict | None:
    """提取昨日涨停今日表现数据。"""
    sections = deep_data.get("sections", {})
    blow_info = sections.get("blow_up_and_prev_performance", {})
    if blow_info and "prev_limit_up_performance" in blow_info:
        perf = blow_info["prev_limit_up_performance"]
        if perf:
            return perf
    return None


def _render_tier(lines: list[str], label: str, stocks: list[dict]) -> None:
    """渲染一个连板层级到 Markdown 表格行。"""
    if not stocks:
        return

    name_list = "、".join(f"{s['name']}{_consecutive_suffix(s)}" for s in stocks)
    themes = "、".join(sorted(set(s["theme"] for s in stocks)))
    lines.append(f"| {label} | {name_list} | {themes} |")


def _consecutive_suffix(stock: dict) -> str:
    """连板后缀，如 '(12天10板)' 仅 3+ 连板显示。"""
    c = stock["consecutive"]
    if c >= 4:
        return f"({c}连板)"
    if c >= 3:
        return f"({c}连板)"
    return ""
