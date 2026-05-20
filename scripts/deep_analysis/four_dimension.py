"""
four_dimension.py — 四维穿透分析框架 (Module 8 of deep analysis)

将当日所有分析模块的输出映射到强制性的四维分析模板，
从宏观（Dalio）→ 中观（Fisher）→ 微观（Buffett/Munger）→ 博弈（Marks）
逐层穿透，产出完整的结构化分析。

Per REQUIREMENTS.md §2.3: 四维穿透 + 三大技能.
纯字典驱动 + 模板填充，无 LLM 调用。
"""

from __future__ import annotations

from typing import Optional

from scripts.knowledge_base import (
    EVENT_PATTERNS,
    STOCK_NAME_DICT,
    SECTOR_CATEGORY_MAP,
    CROWDING_THRESHOLDS,
)

# ---------------------------------------------------------------------------
# 事件匹配触发器：每个 EVENT_PATTERNS 条目 → 在新闻中搜索的关键词
# 因为新闻文本包含的是"出口管制""降准"等具体表述，而非 EVENTS 的抽象名称
# ---------------------------------------------------------------------------

EVENT_TRIGGERS: dict[str, list[str]] = {
    "地缘冲突升级":     ["冲突", "地缘", "战争", "制裁", "实体清单", "出口管制",
                          "芯片法案", "科技脱钩", "贸易战", "加征关税", "关税",
                          "制裁名单", "技术封锁", "断供", "脱钩"],
    "产业政策发布":     ["政策", "印发", "出台", "发布", "规划", "方案", "通知",
                          "行动计划", "指导意见", "白皮书", "发改委", "工信部"],
    "货币政策宽松":     ["降准", "降息", "LPR", "MLF", "宽松", "逆回购",
                          "流动性释放", "下调利率", "下调", "存款准备金", "SLF",
                          "扩表", "放水", "结构性工具"],
    "货币政策收紧":     ["加息", "上调利率", "缩表", "收紧", "回笼", "上调",
                          "公开市场回笼", "流动性紧"],
    "外贸数据超预期":   ["外贸", "出口", "进口", "贸易顺差", "贸易数据",
                          "进出口", "海关", "贸易额"],
    "美股科技大跌":     ["美股大跌", "美股暴跌", "纳斯达克大跌", "科技股大跌",
                          "美股重挫", "美科技股", "Nasdaq下跌", "道指下跌"],
    "美股科技大涨":     ["美股大涨", "美股暴涨", "纳斯达克大涨", "科技股大涨",
                          "美股创新高", "美科技股", "Nasdaq上涨", "道指上涨"],
    "原油价格大涨":     ["原油", "OPEC", "布伦特", "WTI", "油价", "石油价格",
                          "俄油", "增产", "减产", "能源危机"],
    "人民币汇率波动":   ["人民币", "汇率", "CNY", "CNH", "离岸", "在岸",
                          "中间价", "贬值", "升值", "外汇", "汇率波动"],
    "行业监管收紧":     ["监管", "约谈", "处罚", "整改", "反垄断", "调查",
                          "停业整顿", "罚款", "合规", "问询函", "关注函"],
    "技术突破/创新":    ["技术突破", "创新药", "新品发布", "量产", "首发",
                          "重大进展", "突破性", "里程碑", "获批上市", "突破"],
    "财报季/业绩披露":   ["财报", "业绩", "季报", "年报", "预告", "快报",
                          "披露", "营收", "净利润", "盈利"],
    "房地产政策调整":    ["房地产", "楼市", "房贷", "购房", "限购", "限贷",
                          "首付", "公积金", "保交楼", "住房", "契税", "增值税",
                          "城中村", "保障房", "收储", "白名单"],
    "疫情/公共卫生事件": ["疫情", "病毒", "变种", "感染", "疫苗", "新冠",
                          "公共卫生", "隔离", "管控"],
}

# 按风险等级排序的事件名（用于取最高优先级匹配）
_EVENT_PRIORITY_ORDER: list[str] = []
for _level in ["high", "medium", "low"]:
    for _name, _pat in EVENT_PATTERNS.items():
        if _pat.get("risk_level") == _level and _name not in _EVENT_PRIORITY_ORDER:
            _EVENT_PRIORITY_ORDER.append(_name)


def _match_event_patterns(text: str) -> list[tuple[str, dict, int]]:
    """在文本中匹配 EVENT_PATTERNS，返回 (事件名, 模式dict, 命中关键词数)。"""
    results: list[tuple[str, dict, int]] = []
    for event_name, triggers in EVENT_TRIGGERS.items():
        if event_name not in EVENT_PATTERNS:
            continue
        hit_count = sum(1 for t in triggers if t in text)
        if hit_count > 0:
            results.append((event_name, EVENT_PATTERNS[event_name], hit_count))
    # 按命中数降序排列
    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 常量：第二层次思维洞察模板
# ---------------------------------------------------------------------------

# key = (crowding_level_or_position, sentiment_stage)
SECOND_LEVEL_INSIGHTS: dict[tuple[str, str], str] = {
    ("高位", "高潮"): (
        "第一层思维认为主线将延续、应该追涨；"
        "第二层思维看到的是散户蜂拥而入、机构已在高位派发筹码"
    ),
    ("高位", "分化"): (
        "第一层思维追逐强势板块；"
        "第二层思维警惕拥挤度风险并寻找低位切换机会"
    ),
    ("低位", "冰点"): (
        "第一层思维被恐慌情绪裹挟、急于离场；"
        "第二层思维看到的是情绪冰点后的逆向布局机会"
    ),
    ("低位", "修复"): (
        "第一层思维还在犹豫观望、等待更多确认信号；"
        "第二层思维已经注意到资金在低位悄悄吸筹"
    ),
    ("中位", "震荡"): (
        "第一层思维因市场震荡而观望；"
        "第二层思维关注资金在震荡中悄悄布局的方向"
    ),
    ("中位", "分化"): (
        "第一层思维只看到板块间的强弱分化；"
        "第二层思维思考的是分化背后的资金迁徙逻辑和持续性"
    ),
}

# 兜底洞察
_DEFAULT_SECOND_LEVEL = (
    "第一层思维关注今日涨跌；"
    "第二层思维关注涨跌背后的资金逻辑与持续性"
)

# 护城河类型 → 行业归类映射
MOAT_CLASSIFICATION: dict[str, str] = {
    "科技":  "技术壁垒 / 研发投入",
    "消费":  "品牌壁垒 / 渠道锁定",
    "医药":  "专利壁垒 / 临床管线",
    "金融":  "牌照壁垒 / 规模效应",
    "能源":  "资源壁垒 / 成本优势",
    "工业":  "制造壁垒 / 供应链深度",
    "军工":  "资质壁垒 / 供应关系锁定",
    "通信":  "技术壁垒 / 客户粘性",
    "地产":  "土地储备 / 融资成本优势",
    "农业":  "规模效应 / 养殖技术壁垒",
}


# ---------------------------------------------------------------------------
# 内部辅助：文本解析
# ---------------------------------------------------------------------------

def _extract_sentiment_stage(all_results: dict) -> str:
    """从 market_sentiment 模块输出中提取周期阶段。"""
    text = all_results.get("market_sentiment", "")
    if not isinstance(text, str) or not text:
        return ""
    for stage in ["冰点", "修复", "高潮", "分化"]:
        if stage in text:
            return stage
    return ""


def _extract_theme_leaders(all_results: dict) -> list[dict]:
    """从 theme_analysis 输出中提取领涨个股。

    Returns [{name, sector, category, moat_type}, ...].
    """
    theme_text = all_results.get("theme_analysis", "")
    fund_text = all_results.get("fund_flow_analysis", "")

    leaders: list[dict] = []
    seen: set[str] = set()

    combined = f"{theme_text}\n{fund_text}"
    for name, info in STOCK_NAME_DICT.items():
        if name in combined and name not in seen:
            seen.add(name)
            category = info.get("category", "")
            sector = info.get("sector", "")
            leaders.append({
                "name": name,
                "sector": sector,
                "category": category,
                "moat_type": MOAT_CLASSIFICATION.get(category, "综合壁垒"),
            })

    return leaders[:6]


def _extract_risks(all_results: dict, top_n: int = 2) -> list[str]:
    """从 opportunity_risk 输出中提取风险描述。"""
    risk_text = all_results.get("opportunity_risk", "")
    if not isinstance(risk_text, str) or not risk_text:
        return []

    risks: list[str] = []
    in_section = False
    for line in risk_text.split("\n"):
        stripped = line.strip()
        if "风险" in stripped and ("##" in stripped or "**" in stripped):
            in_section = True
            continue
        if "机会" in stripped and ("##" in stripped or "**" in stripped):
            in_section = False
            continue
        if in_section and stripped and (stripped[0] in "-*" or stripped[:2] in ("1.", "2.", "3.")):
            import re
            item = re.sub(r'^[-*\d.]+\s*', '', stripped)
            item = re.sub(r'[⚠🚨🔴🟡🟢]', '', item).strip()
            if len(item) > 4:
                risks.append(item)
                if len(risks) >= top_n:
                    break

    return risks


def _get_crowding_position(crowding_scores: dict | None) -> str:
    """从拥挤度评分中判断整体拥挤度位置。

    Returns 高位 / 中位 / 低位 / 未知.
    """
    if not crowding_scores:
        return "未知"

    high_count = 0
    low_count = 0
    total = 0
    for _name, info in crowding_scores.items():
        if not isinstance(info, dict):
            continue
        total += 1
        level = info.get("level", "")
        if level == "high":
            high_count += 1
        elif level == "low":
            low_count += 1

    if total == 0:
        return "未知"
    if high_count / total > 0.3:
        return "高位"
    if low_count / total > 0.5:
        return "低位"
    return "中位"


# ---------------------------------------------------------------------------
# Section builders（五段，每段返回 markdown 字符串）
# ---------------------------------------------------------------------------

def _build_catalyst(news_items: list | None) -> str:
    """Section 1: 今日核心催化剂（Catalyst）。"""
    if not news_items:
        return "今日无显著外部催化，市场由内生资金驱动"

    # 1) 扫描所有新闻，用 EVENT_TRIGGERS 匹配
    #    优先级：risk_level (high > medium > low)，同级别内比命中数
    best_event: str = ""
    best_news: dict | None = None
    best_hits = 0
    best_risk_rank = 99  # 越小越优先

    risk_rank_map = {"high": 0, "medium": 1, "low": 2}

    for item in news_items:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        combined = f"{title} {content}"

        matches = _match_event_patterns(combined)
        if matches:
            event_name, pattern, hits = matches[0]
            rank = risk_rank_map.get(pattern.get("risk_level", "medium"), 1)
            # 更优：风险级别更高，或同级别下命中更多
            if rank < best_risk_rank or (rank == best_risk_rank and hits > best_hits):
                best_risk_rank = rank
                best_hits = hits
                best_event = event_name
                best_news = item

    if best_news and best_event:
        title = best_news.get("title", "")
        ev = EVENT_PATTERNS.get(best_event, {})
        direction = ev.get("directional", "")
        affected = ev.get("affected_sectors", [])
        return (
            f"**{title}**\n\n- 事件类型: {best_event}\n- 方向判断: {direction}\n- 影响板块: {'、'.join(affected[:5]) if affected else '待观察'}"
        )

    # 2) 兜底：选实体命中数最多的新闻
    max_hits = 0
    fallback: dict | None = None
    for item in news_items:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        combined = f"{title} {content}"
        hits = sum(1 for name in STOCK_NAME_DICT if name in combined)
        if hits > max_hits:
            max_hits = hits
            fallback = item

    if fallback and max_hits > 0:
        return f"**{fallback.get('title', '')}**\n\n该消息涉及 {max_hits} 个核心标的，为当日最受关注的事件"

    return "今日无显著外部催化，市场由内生资金驱动"


def _build_dalio(news_items: list | None) -> str:
    """Section 2: 地缘与宏观映射（Dalio 视角）。"""
    if not news_items:
        return (
            "- 判断: 市场由内生资金驱动，无显著外部地缘催化\n"
            "- 大周期定位: 逆全球化持续深化，科技自主与国防安全为长期主线"
        )

    # 扫描所有新闻，用 EVENT_TRIGGERS 匹配（过滤弱匹配：至少 2 个关键词命中）
    matched_events: list[tuple[str, dict, int]] = []
    seen: set[str] = set()

    for item in news_items:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        combined = f"{title} {content}"

        for event_name, pattern, hits in _match_event_patterns(combined):
            if event_name not in seen and hits >= 2:
                seen.add(event_name)
                matched_events.append((event_name, pattern, hits))


    if not matched_events:
        return (
            "- 判断: 当日新闻未命中已知地缘事件模式，市场由内生资金驱动\n"
            "- 大周期定位: 逆全球化持续深化，科技自主与国防安全为长期主线"
        )

    lines: list[str] = []
    for event_name, pattern, hits in matched_events:
        affected = pattern.get("affected_sectors", [])
        directional = pattern.get("directional", "")
        dalio_macro = pattern.get("dalio_macro", "")

        # 判断: 对"国产替代/自主可控"是加速还是脉冲
        if any(kw in directional for kw in ["国产替代", "自主可控", "科技自主"]):
            judgment = "该事件对国产替代/自主可控进程构成**加速**推动"
        elif any(kw in " ".join(affected) for kw in ["半导体", "军工", "稀土"]):
            judgment = "该事件对国产替代/自主可控进程形成**脉冲式**催化，关注持续性"
        else:
            judgment = "该事件对国产替代的直接推动有限，主要影响相关行业的短期情绪"

        lines.append(
            f"- **{event_name}**: {judgment}\n  - 方向: {directional}\n  - 影响板块: {'、'.join(affected[:5]) if affected else '待观察'}"
        )

    # 大周期定位：取第一个匹配事件的 dalio_macro
    primary_macro = matched_events[0][1].get("dalio_macro", "")
    if primary_macro:
        lines.append(f"\n- **大周期定位**: {primary_macro}")

    return "\n".join(lines)


def _build_fisher(
    all_results: dict,
    chain_impacts: list | None,
) -> str:
    """Section 3: 产业链定位（Fisher 视角）。"""
    lines: list[str] = []

    # 从 chain_impacts 提取产业链信息
    if chain_impacts:
        for impact in chain_impacts[:2]:  # 最多取 2 条
            catalyst = impact.get("catalyst", "")

            # 受益板块（从 upstream/midstream/downstream 汇总）
            all_sectors: list[str] = []
            for pos in ["upstream_impact", "midstream_impact", "downstream_impact"]:
                for item in impact.get(pos, []):
                    sector = item.get("sector", "")
                    if sector and sector not in all_sectors:
                        all_sectors.append(sector)

            lines.append(f"- **催化事件**: {catalyst}")
            if all_sectors:
                lines.append(f"- **受益板块**: {'、'.join(all_sectors[:6])}")

            # 产业链位置判断
            has_upstream = bool(impact.get("upstream_impact"))
            has_midstream = bool(impact.get("midstream_impact"))
            has_downstream = bool(impact.get("downstream_impact"))

            if has_upstream and not has_midstream:
                position = "上游（率先受益于催化事件）"
            elif has_upstream and has_midstream and has_downstream:
                position = "全产业链（上中下游均有映射）"
            elif has_midstream:
                position = "中游（产能扩张与订单可见度提升）"
            elif has_downstream:
                position = "下游（应用场景与商业模式落地）"
            else:
                position = "待进一步确认"

            lines.append(f"- **产业链位置**: {position}")

            # 核心逻辑：从 chain_impacts 中提取 severity 最高的项
            high_severity_items = []
            for pos in ["upstream_impact", "midstream_impact", "downstream_impact"]:
                for item in impact.get(pos, []):
                    if item.get("severity") == "high":
                        high_severity_items.append(item.get("logic", ""))

            if high_severity_items:
                lines.append(f"- **核心逻辑**: {high_severity_items[0]}")
            lines.append("")

    # 兜底：从 theme_analysis 推断
    if not chain_impacts or not any(
        impact.get("upstream_impact") or impact.get("midstream_impact")
        for impact in chain_impacts
    ):
        theme_text = all_results.get("theme_analysis", "")
        if isinstance(theme_text, str) and theme_text:
            # 尝试提取板块/行业关键词
            sector_hits: dict[str, int] = {}
            for sector in SECTOR_CATEGORY_MAP:
                cnt = theme_text.count(sector)
                if cnt > 0:
                    sector_hits[sector] = cnt
            if sector_hits:
                top_sectors = sorted(sector_hits, key=sector_hits.get, reverse=True)[:5]
                lines.append(f"- **受益板块**（基于主题分析）: {'、'.join(top_sectors)}")

                # 判断产业链位置
                upstream_kw = ["设备", "材料", "上游", "硅片", "光刻", "EDA"]
                midstream_kw = ["制造", "封装", "组装", "模组"]
                downstream_kw = ["应用", "运营", "服务", "终端"]

                has_u = any(kw in theme_text for kw in upstream_kw)
                has_m = any(kw in theme_text for kw in midstream_kw)
                has_d = any(kw in theme_text for kw in downstream_kw)

                if has_u:
                    position = "上游（设备/材料先行）"
                elif has_m:
                    position = "中游（制造/封装）"
                elif has_d:
                    position = "下游（应用落地）"
                else:
                    position = "全产业链（上中下游均有映射）"
                lines.append(f"- **产业链位置**: {position}")

    return "\n".join(lines) if lines else "暂无产业链定位数据"


def _build_buffett(
    all_results: dict,
    chain_impacts: list | None,
) -> str:
    """Section 4: Alpha 标的筛选（Buffett/Munger 视角）。"""
    lines: list[str] = []

    # 1) "卖铲人" — 卡位龙头
    shovel_sellers: list[str] = []

    # 从 chain_impacts 的上游受益标的中找
    if chain_impacts:
        for impact in chain_impacts:
            for target in impact.get("a_share_targets", []):
                name = target.get("name", "")
                sub_sector = target.get("sub_sector", "")
                # 上游 + 有 A 股代码 → 卖铲人
                if (any(kw in sub_sector for kw in ["设备", "材料", "上游", "零部件"])
                        and target.get("code")):
                    if name not in shovel_sellers:
                        shovel_sellers.append(name)

    # 从 theme leaders 补
    if not shovel_sellers:
        leaders = _extract_theme_leaders(all_results)
        for ldr in leaders:
            sector = ldr.get("sector", "")
            if any(kw in sector for kw in ["设备", "材料", "零部件", "半导体设备"]):
                shovel_sellers.append(ldr["name"])

    lines.append(
        f"1. **谁是\"卖铲人\"（卡位龙头）？**\n   {'、'.join(shovel_sellers[:4]) if shovel_sellers else '当前主题的卡位龙头待进一步确认'}"
    )

    # 2) 高利润率 / 研发转化率
    leaders = _extract_theme_leaders(all_results)
    moat_types: set[str] = set()
    for ldr in leaders:
        mt = ldr.get("moat_type", "")
        if mt:
            moat_types.add(mt)

    moat_desc = "、".join(sorted(moat_types)[:3]) if moat_types else "综合壁垒"
    lines.append(
        f"2. **谁拥有极高毛利率和研发转化率？**\n   护城河类型: {moat_desc}\n   科技方向关注研发壁垒（高研发投入 + 高毛利率），消费方向关注品牌壁垒（高复购 + 渠道锁定），医药方向关注专利壁垒（临床管线 + 独家品种）"
    )

    # 3) 订单粘性
    sticky_names: list[str] = []
    if chain_impacts:
        for impact in chain_impacts:
            for target in impact.get("a_share_targets", []):
                name = target.get("name", "")
                sub_sector = target.get("sub_sector", "")
                # 卡位 + 有代码 → 高粘性
                if (any(kw in sub_sector for kw in ["整机", "组装", "设备", "核心"])
                        and target.get("code") and name not in sticky_names):
                    sticky_names.append(name)

    if not sticky_names and leaders:
        sticky_names = [ldr["name"] for ldr in leaders[:3]]

    if sticky_names:
        sticky_desc = '、'.join(sticky_names[:4])
    else:
        sticky_desc = '当前数据不足以判断订单粘性，关注产业链核心供应商和独家供应关系的标的'
    lines.append(
        f"3. **谁的订单最具有粘性？**\n   {sticky_desc}"
    )

    return "\n".join(lines)


def _build_marks(
    all_results: dict,
    crowding_scores: dict | None,
) -> str:
    """Section 5: 博弈与风险提示（Howard Marks 视角）。"""
    lines: list[str] = []

    # 拥挤度位置
    position = _get_crowding_position(crowding_scores)
    position_labels = {
        "高位": "高位滞涨 — 注意获利了结压力",
        "中位": "中位运行 — 结构性机会为主",
        "低位": "低位潜伏 — 关注逆向布局机会",
        "未知": "无法判断（缺乏拥挤度数据）",
    }
    lines.append(f"- **当前板块位置**: {position_labels.get(position, position)}")

    # 拥挤度详情
    if crowding_scores:
        high_items = [
            (name, info.get("score", 0))
            for name, info in crowding_scores.items()
            if isinstance(info, dict) and info.get("level") == "high"
        ]
        low_items = [
            (name, info.get("score", 0))
            for name, info in crowding_scores.items()
            if isinstance(info, dict) and info.get("level") == "low"
        ]
        if high_items:
            top_high = sorted(high_items, key=lambda x: x[1], reverse=True)[:3]
            lines.append(f"- **拥挤度**: 高位板块 — {'、'.join(f'{n}({s})' for n, s in top_high)}")
        if low_items:
            top_low = sorted(low_items, key=lambda x: x[1])[:3]
            lines.append(f"  低位板块 — {'、'.join(f'{n}({s})' for n, s in top_low)}")

    # 第二层次思维
    sentiment_stage = _extract_sentiment_stage(all_results)
    insight = SECOND_LEVEL_INSIGHTS.get(
        (position, sentiment_stage),
        SECOND_LEVEL_INSIGHTS.get((position, "震荡"), _DEFAULT_SECOND_LEVEL),
    )
    lines.append(f"\n- **第二层思维**: {insight}")

    # 警惕风险（top 2）
    risks = _extract_risks(all_results, top_n=2)
    if risks:
        lines.append(f"\n- **警惕风险**:")
        for r in risks:
            lines.append(f"  1. {r}" if risks.index(r) == 0 else f"  2. {r}")
    else:
        lines.append("\n- **警惕风险**: 当前数据不足以提取具体风险，关注市场整体波动与流动性变化")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def apply(
    all_results: dict,
    news_items: list | None = None,
    chain_impacts: list | None = None,
    crowding_scores: dict | None = None,
    stats: dict | None = None,
) -> tuple[str | None, str | None]:
    """应用四维穿透分析框架，产出完整结构化分析报告。

    将所有分析模块的输出映射到强制性的四维分析模板：
    - 维度一: 宏观地缘（Dalio 大周期）
    - 维度二: 中观产业链（Fisher 成长股）
    - 维度三: 微观护城河（Buffett/Munger）
    - 维度四: 市场博弈（Howard Marks 第二层思维）

    Args:
        all_results: 各模块输出 dict，key 为模块名，value 为 markdown 文本。
        news_items: 新闻条目列表，每项含 'title' 和 'content'。
        chain_impacts: 产业链影响分析列表，来自 chain_reasoning.analyze_chain()。
        crowding_scores: 拥挤度评分 dict，来自 crowding_monitor.compute_sector_crowding()。
        stats: 聚合统计 dict（可选）。预留字段。

    Returns:
        (markdown_report_or_None, error_or_None)
    """
    try:
        if not all_results:
            return None, "all_results 为空，无法应用四维穿透框架"

        sections: list[str] = []

        # ── 标题 ──
        sections.append("## 四维穿透分析")
        sections.append("")

        # ── Catalyst ──
        sections.append("### 今日核心催化剂 (Catalyst)")
        sections.append("")
        sections.append(_build_catalyst(news_items))
        sections.append("")

        # ── Dalio ──
        sections.append("### 地缘与宏观映射 (达利欧 Dalio 视角)")
        sections.append("")
        sections.append(_build_dalio(news_items))
        sections.append("")

        # ── Fisher ──
        sections.append("### 产业链定位 (费雪 Fisher 视角)")
        sections.append("")
        sections.append(_build_fisher(all_results, chain_impacts))
        sections.append("")

        # ── Buffett/Munger ──
        sections.append("### Alpha 标的筛选 (巴菲特/芒格 视角)")
        sections.append("")
        sections.append(_build_buffett(all_results, chain_impacts))
        sections.append("")

        # ── Howard Marks ──
        sections.append("### 博弈与风险提示 (霍华德·马克斯 Howard Marks 视角)")
        sections.append("")
        sections.append(_build_marks(all_results, crowding_scores))
        sections.append("")

        return "\n".join(sections), None

    except Exception as exc:
        return None, f"四维穿透分析生成失败: {exc}"
