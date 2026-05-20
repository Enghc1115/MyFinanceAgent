"""
chain_reasoning.py — 产业链联动推理引擎

实现 REQUIREMENTS.md §2.3 Dimension 2: 中观产业链与确定性主线层。
当上游事件发生时（如"英伟达 GB200 供不应求"），自动推理对中下游的影响，
并识别 A 股受益标的。

纯计算模块，所有逻辑基于 knowledge_base 中的规则字典 + 文本匹配，
无外部 API 调用，无额外依赖。

供 generate_deep_report.py 调用:
    from scripts.chain_reasoning import analyze_chain
    chain_impacts, error = analyze_chain(news_items)
"""

from __future__ import annotations

import re
from typing import Optional

from scripts.knowledge_base import CHAIN_REASONING_RULES, STOCK_NAME_DICT


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _check_trigger_match(trigger: str, text: str) -> str:
    """检查单个 trigger 是否匹配 text。

    Returns:
        "exact"   — 完整匹配（大小写不敏感子串命中）
        "partial" — 部分匹配（多词 trigger 中至少一个词命中，或单词语义包含）
        ""        — 不匹配
    """
    if not text or not trigger:
        return ""

    text_lower = text.lower()
    trigger_lower = trigger.lower()

    # 1) 精确子串匹配
    if trigger_lower in text_lower:
        return "exact"

    # 2) 部分匹配
    # 2a) 多词 trigger（空格分隔）：任一长度 >= 2 的词出现在 text 中
    words = trigger_lower.split()
    if len(words) > 1:
        for word in words:
            if len(word) >= 2 and word in text_lower:
                return "partial"
    # 2b) 单词 trigger（含中文连续字符串）：检查 token 级别的包含关系
    elif len(trigger_lower) >= 2:
        text_tokens = re.findall(r"\w{2,}", text_lower)
        for token in text_tokens:
            # trigger 包含 token，或 token 包含 trigger，但不是完全相等
            if (trigger_lower in token or token in trigger_lower):
                if token != trigger_lower:
                    return "partial"

        # 2c) CJK 回退: 中文无空格，\w+ 会把整段抓成一个 token
        #     对 trigger 做 2-char 滑动窗口，检查任一窗口是否出现在 text 中
        #     例: trigger="实体清单" → 子串 "实体" 命中 → partial
        for i in range(len(trigger_lower) - 1):
            if trigger_lower[i:i + 2] in text_lower:
                return "partial"

    return ""


_SECTOR_LOGIC_TEMPLATES: dict[str, str] = {
    # 上游：最接近催化剂，率先受益
    "upstream": "上游{sector}需求随{catalyst}放量而增长，率先受益于产业链扩张",
    # 中游：产能利用率提升，订单可见度改善
    "midstream": "中游{sector}受益于{catalyst}产能扩张，订单可见度与产能利用率双升",
    # 下游：生态完善，应用场景拓展
    "downstream": "下游{sector}受益于{catalyst}生态完善，应用场景与商业模式逐步落地",
}


def _build_impact_list(
    sectors: list[str], catalyst_key: str, position: str
) -> list[dict]:
    """为一组 sector 生成 impact dict 列表。"""
    template = _SECTOR_LOGIC_TEMPLATES.get(position, _SECTOR_LOGIC_TEMPLATES["midstream"])
    severity = {"upstream": "high", "midstream": "medium", "downstream": "medium"}.get(
        position, "medium"
    )
    results: list[dict] = []
    for sector in sectors:
        logic = template.format(catalyst=catalyst_key, sector=sector)
        results.append({"sector": sector, "logic": logic, "severity": severity})
    return results


def _build_targets(
    beneficiaries: dict[str, list[str]], catalyst_key: str
) -> list[dict]:
    """将 a_share_beneficiaries 映射展开为带 code 的个股列表。

    对 STOCK_NAME_DICT 中存在的股票名，自动填入 6 位代码；
    不在字典中的（如含 _港股/_美股 后缀或未收录标的），code 留空。
    """
    targets: list[dict] = []
    for sub_sector, names in beneficiaries.items():
        for name in names:
            # 剥离港股/美股/非上市标记，尝试查找 A 股代码
            lookup_name = name
            for suffix in ("_港股", "_美股", "（非上市）", "(非上市)"):
                if suffix in lookup_name:
                    lookup_name = lookup_name.replace(suffix, "")
                    break

            stock_info = STOCK_NAME_DICT.get(lookup_name, {})
            code = stock_info.get("code", "")

            # 生成 rationale
            if code:
                rationale = f"{sub_sector}核心标的，受益于{catalyst_key}产业链趋势"
            elif "_港股" in name or "_美股" in name:
                rationale = f"{sub_sector}映射标的（非A股上市），提供方向参考"
            elif "非上市" in name:
                rationale = f"{sub_sector}关键环节（非上市公司），关注产业链替代标的"
            else:
                rationale = f"{sub_sector}相关标的，受益于{catalyst_key}产业链趋势"

            targets.append({
                "name": name,
                "code": code,
                "sub_sector": sub_sector,
                "rationale": rationale,
            })

    return targets


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_triggers(news_items: list[dict]) -> list[dict]:
    """扫描新闻条目，匹配 CHAIN_REASONING_RULES 中的触发词。

    Args:
        news_items: 新闻条目列表，每项需含 'title' 和 'content' 键。

    Returns:
        匹配事件列表。每个元素包含 rule_name / matched_trigger / news_title /
        upstream / midstream / downstream / a_share_beneficiaries / confidence。

        confidence 分级:
        - "high"   — trigger 在 title 中精确命中
        - "medium" — trigger 在 content 中精确命中（但不在 title 中）
        - "low"    — trigger 部分命中（多词中单次命中，或 token 包含关系）

        无匹配时返回空列表（非 error）。
    """
    if not news_items:
        return []

    results: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (rule_name, news_title) 去重

    for item in news_items:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        if not title and not content:
            continue

        for rule in CHAIN_REASONING_RULES:
            rule_name = rule.get("name", "")
            triggers: list[str] = rule.get("triggers", [])
            if not triggers:
                continue

            best_trigger = ""
            best_confidence = ""

            for trigger in triggers:
                # ---- 优先级: title > content; exact > partial ----
                title_match = _check_trigger_match(trigger, title)
                content_match = _check_trigger_match(trigger, content)

                if title_match == "exact":
                    if best_confidence != "high":  # 首次 high
                        best_trigger = trigger
                        best_confidence = "high"
                elif content_match == "exact" and best_confidence not in ("high",):
                    best_trigger = trigger
                    best_confidence = "medium"
                elif content_match == "partial" and best_confidence == "":
                    best_trigger = trigger
                    best_confidence = "low"

            if best_trigger and best_confidence:
                key = (rule_name, title)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "rule_name": rule_name,
                        "matched_trigger": best_trigger,
                        "news_title": title,
                        "upstream": list(rule.get("upstream", [])),
                        "midstream": list(rule.get("midstream", [])),
                        "downstream": list(rule.get("downstream", [])),
                        "a_share_beneficiaries": dict(
                            rule.get("a_share_beneficiaries", {})
                        ),
                        "confidence": best_confidence,
                    })

    return results


def reason_chain_impact(matched_event: dict) -> dict:
    """对单条匹配事件进行完整的产业链影响推理。

    Args:
        matched_event: match_triggers 返回的单个匹配事件 dict。

    Returns:
        结构化产业链分析 dict，包含:
        - catalyst: 催化事件描述
        - upstream_impact / midstream_impact / downstream_impact
        - a_share_targets: 含 name / code / sub_sector / rationale 的个股列表
    """
    rule_name = matched_event.get("rule_name", "")
    news_title = matched_event.get("news_title", "")
    matched_trigger = matched_event.get("matched_trigger", "")

    upstream: list[str] = matched_event.get("upstream", [])
    midstream: list[str] = matched_event.get("midstream", [])
    downstream: list[str] = matched_event.get("downstream", [])
    beneficiaries: dict[str, list[str]] = matched_event.get(
        "a_share_beneficiaries", {}
    )

    # 催化剂描述：优先用新闻标题，其次用规则名 + 触发词
    catalyst = news_title or f"{rule_name} 触发: {matched_trigger}"

    # 从规则名提取短关键词，用于生成模板文本
    catalyst_key = rule_name.split("/")[0].strip() if rule_name else "产业链"

    return {
        "catalyst": catalyst,
        "upstream_impact": _build_impact_list(upstream, catalyst_key, "upstream"),
        "midstream_impact": _build_impact_list(midstream, catalyst_key, "midstream"),
        "downstream_impact": _build_impact_list(downstream, catalyst_key, "downstream"),
        "a_share_targets": _build_targets(beneficiaries, catalyst_key),
    }


def enrich_theme_with_chain(theme: dict, chain_impacts: list[dict]) -> dict:
    """将产业链推理结果合并到主线分析 dict 中。

    Args:
        theme: 主线分析 dict，含 'name' / 'leaders' / 'driver' / 'sub_directions' 等键。
        chain_impacts: reason_chain_impact 返回的影响分析列表。

    Returns:
        在 theme 基础上新增 'chain_reasoning' 键的 dict。
        若 chain_impacts 为空，chain_reasoning 设为 None 并附带说明。
    """
    enriched = dict(theme)  # 浅拷贝，避免修改原始 dict

    if not chain_impacts:
        enriched["chain_reasoning"] = {
            "status": "no_match",
            "message": "当前新闻未命中产业链推理规则，无联动分析。",
            "impacts": [],
        }
        return enriched

    # 汇总所有 impact 中的受益标的，去重
    all_targets: list[dict] = []
    seen_codes: set[str] = set()
    for impact in chain_impacts:
        for t in impact.get("a_share_targets", []):
            code = t.get("code", "")
            name = t.get("name", "")
            dedup_key = code or name
            if dedup_key and dedup_key not in seen_codes:
                seen_codes.add(dedup_key)
                all_targets.append(t)

    enriched["chain_reasoning"] = {
        "status": "matched",
        "match_count": len(chain_impacts),
        "impacts": chain_impacts,
        "aggregated_targets": all_targets,
    }
    return enriched


def analyze_chain(news_items: list[dict]) -> tuple[list[dict], Optional[str]]:
    """产业链推理主入口 —— 供 generate_deep_report.py 调用。

    完整管线: match_triggers → reason_chain_impact。

    Args:
        news_items: 新闻条目列表，每项含 'title' 和 'content'。

    Returns:
        (chain_impacts, error_or_None)
        - chain_impacts: 产业链影响分析列表（无匹配时为空列表 []）
        - error: 异常时为错误描述字符串，正常时为 None

        该函数不抛异常，所有异常转为 error 字符串返回。
    """
    try:
        matched = match_triggers(news_items)
    except Exception as exc:
        return [], f"match_triggers 异常: {exc}"

    if not matched:
        return [], None

    chain_impacts: list[dict] = []
    for event in matched:
        try:
            impact = reason_chain_impact(event)
            chain_impacts.append(impact)
        except Exception as exc:
            # 单条推理失败不阻塞整体，继续处理下一条
            chain_impacts.append({
                "catalyst": event.get("news_title", "未知事件"),
                "error": f"reason_chain_impact 异常: {exc}",
                "upstream_impact": [],
                "midstream_impact": [],
                "downstream_impact": [],
                "a_share_targets": [],
            })

    return chain_impacts, None
