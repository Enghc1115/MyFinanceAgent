"""
core_judgment.py — 核心判断合成 (Module 7 of deep analysis)

基于所有深度分析模块的输出，通过规则决策树合成 ≤200 字的
当日市场核心判断。纯模板填充，无 LLM 调用。

Per REQUIREMENTS.md Section 八: 核心判断（≤200字）.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# 内部辅助：市场特征提取
# ---------------------------------------------------------------------------

def _detect_market_type(panorama_text: str) -> str:
    """从指数全景输出中识别市场类型。

    Returns 普涨 / 分化 / 调整 / 震荡（默认）。
    """
    if not panorama_text:
        return "震荡"

    text = panorama_text

    # 优先级：特指 → 泛指。普涨与全面上涨优先，其次分化/结构性，再次调整/普跌
    if any(kw in text for kw in ["普涨", "全面上涨", "全线上涨", "全市场上涨"]):
        return "普涨"
    if any(kw in text for kw in ["结构性", "分化", "冰火两重天", "涨跌互现"]):
        return "分化"
    if any(kw in text for kw in ["调整", "下跌", "普跌", "全线下跌", "大跌"]):
        return "调整"
    if any(kw in text for kw in ["震荡", "横盘", "窄幅整理", "窄幅波动"]):
        return "震荡"

    return "震荡"


def _detect_sentiment_stage(sentiment_text: str) -> str:
    """从市场情绪输出中提取周期阶段。

    Returns 冰点 / 修复 / 高潮 / 分化 / "".
    """
    if not sentiment_text:
        return ""

    for stage in ["冰点", "修复", "高潮", "分化"]:
        if stage in sentiment_text:
            return stage
    return ""


def _extract_themes(theme_text: str) -> list[str]:
    """从主线分析输出中提取 1-2 个主线名称（清洗为纯净板块/主题名）。"""
    if not theme_text:
        return []

    themes: list[str] = []

    # 匹配结构化主线标题: 主线一：xxx / **主线一**：xxx / ### xxx主线
    for pattern in [
        r"主线[一二三][：:]\s*(.+?)(?:\n|$)",
        r"\*\*主线[一二三]\*\*[：:]\s*(.+?)(?:\n|$)",
        r"###\s+(.+?主线.+?)(?:\n|$)",
        r"##\s+(.+?主线.+?)(?:\n|$)",
    ]:
        for m in re.findall(pattern, theme_text):
            name = m.strip().rstrip("。，；:：")
            if name and name not in themes:
                themes.append(name)

    # 兜底：从文本中抓取高频板块关键词
    if not themes:
        sector_hits: dict[str, int] = {}
        for kw in ["半导体", "AI", "人工智能", "新能源", "消费", "医药",
                     "军工", "金融", "有色", "黄金", "机器人", "低空经济"]:
            cnt = theme_text.count(kw)
            if cnt > 0:
                sector_hits[kw] = cnt
        if sector_hits:
            top = sorted(sector_hits, key=sector_hits.get, reverse=True)
            themes = top[:2]

    # 清洗：去掉冗余后缀，避免与模板中的后缀拼接出双词
    _clean_suffixes = ["方向", "板块", "主题", "主线", "概念"]
    cleaned: list[str] = []
    for t in themes:
        for suffix in _clean_suffixes:
            if t.endswith(suffix) and len(t) > len(suffix):
                t = t[:-len(suffix)]
                break
        if t and t not in cleaned:
            cleaned.append(t)

    return cleaned[:2]


def _extract_dominant_direction(all_results: dict) -> str:
    """判断市场主导方向。

    Returns 科技成长 / 防御价值 / 周期资源 / 均衡.
    """
    theme_text = all_results.get("theme_analysis", "")
    fund_text = all_results.get("fund_flow_analysis", "")
    combined = f"{theme_text}\n{fund_text}"

    tech_kw = ["半导体", "AI", "科技", "算力", "芯片", "光模块", "消费电子", "机器人"]
    defense_kw = ["银行", "保险", "公用事业", "红利", "高股息", "防御", "黄金", "避险"]
    cycle_kw = ["能源", "有色", "煤炭", "钢铁", "化工", "石油"]

    tech_score = sum(1 for kw in tech_kw if kw in combined)
    defense_score = sum(1 for kw in defense_kw if kw in combined)
    cycle_score = sum(1 for kw in cycle_kw if kw in combined)

    if tech_score > defense_score and tech_score > cycle_score and tech_score > 0:
        return "科技成长"
    if defense_score > tech_score and defense_score > cycle_score and defense_score > 0:
        return "防御价值"
    if cycle_score > tech_score and cycle_score > defense_score and cycle_score > 0:
        return "周期资源"
    return "均衡"


def _check_crowding_risk(
    crowding_scores: dict | None,
    all_results: dict,
) -> tuple[bool, str]:
    """检查是否有拥挤度风险。

    Returns (is_high, description).
    """
    if crowding_scores:
        high_sectors = [
            name for name, info in crowding_scores.items()
            if isinstance(info, dict) and info.get("level") == "high"
        ]
        if high_sectors:
            return True, "、".join(high_sectors[:2])

    # 兜底：检查任意模块输出中是否出现拥挤/集中度告警
    for _key, text in all_results.items():
        if not isinstance(text, str):
            continue
        if "拥挤" in text or "集中度" in text:
            for kw in ["危险", "警戒", "高位", "过热"]:
                if kw in text:
                    return True, "科技板块"

    return False, ""


def _extract_key_risk(risk_text: str) -> str:
    """从机会与风险输出中提取最关键的一条风险描述。"""
    if not risk_text:
        return ""

    risk_lines: list[str] = []
    in_risk = False
    for line in risk_text.split("\n"):
        stripped = line.strip()
        if "风险" in stripped and ("#" in stripped or "**" in stripped):
            in_risk = True
            continue
        if in_risk and stripped and (stripped[0] in "-*" or stripped[:2] in ("1.", "2.", "3.")):
            item = re.sub(r'^[-*\d.]+\s*', '', stripped)
            item = re.sub(r'[⚠🚨🔴🟡🟢]', '', item).strip()
            if len(item) > 4:
                risk_lines.append(item)
        elif in_risk and stripped == "":
            if risk_lines:
                break

    return risk_lines[0] if risk_lines else ""


# ---------------------------------------------------------------------------
# 模板库：按市场类型 + 条件组合索引
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[str]] = {
    # ── 普涨 ──
    "broad_rally_normal": [
        "市场全面回暖，{theme}主线引领，赚钱效应显著。关注成交量能否持续，顺势而为。",
        "市场全面回暖，多板块共振，赚钱效应扩散。顺势而为，关注主线方向的低吸机会。",
    ],
    "broad_rally_crowded": [
        "市场普涨但{theme}拥挤度偏高，追高性价比降低。关注低位补涨方向，避免高位接力。",
    ],
    "broad_rally_peak": [
        "市场全面回暖，多主线共振，赚钱效应显著。但高潮后需警惕分化，关注成交量能否持续。",
    ],

    # ── 分化 ──
    "divergence_tech_crowded": [
        "市场结构性分化，{theme}主线延续但拥挤度已达警戒位，追高风险加大，关注低拥挤方向切换机会。",
    ],
    "divergence_defensive": [
        "市场防御性分化，资金向{theme}等避险板块集中，进攻板块承压。短期偏防御配置，等待风险偏好回升。",
    ],
    "divergence_general": [
        "市场分化轮动，{theme}方向表现活跃但持续性存疑。控制仓位灵活应对，等待主线明朗。",
    ],

    # ── 震荡 ──
    "choppy_accumulating": [
        "市场震荡蓄势，{theme}方向资金持续流入。关注突破信号和成交量配合，逢低布局核心标的。",
    ],
    "choppy_aimless": [
        "市场缩量震荡，热点快速轮动缺乏持续性，控制仓位等待方向选择。",
        "市场窄幅震荡，交投清淡。耐心等待放量突破信号，地量之后往往孕育变盘。",
    ],

    # ── 调整 ──
    "correction_fear": [
        "市场调整压力释放，恐慌情绪升温。短期观望为主，关注抗跌板块和业绩确定标的，等待情绪冰点后的修复机会。",
    ],
    "correction_normal": [
        "市场短期承压，{risk}拖累情绪。调整中关注逆势抗跌品种，为下一阶段布局做准备。",
    ],
}


# ---------------------------------------------------------------------------
# 模板选择 + 槽位填充
# ---------------------------------------------------------------------------

def _select_template(
    market_type: str,
    sentiment_stage: str,
    themes: list[str],
    is_crowded: bool,
    dominant: str,
    key_risk: str,
) -> str:
    """根据市场特征选择并填充模板。"""

    # ── 普涨 ──
    if market_type == "普涨":
        if sentiment_stage == "高潮" and is_crowded:
            return TEMPLATES["broad_rally_peak"][0]
        if is_crowded and themes:
            return TEMPLATES["broad_rally_crowded"][0].format(theme=themes[0])
        if themes:
            return TEMPLATES["broad_rally_normal"][0].format(theme=themes[0])
        return TEMPLATES["broad_rally_normal"][1]

    # ── 分化 ──
    if market_type == "分化":
        if dominant == "科技成长" and is_crowded:
            t = themes[0] if themes else "科技"
            return TEMPLATES["divergence_tech_crowded"][0].format(theme=t)
        if dominant == "防御价值":
            t = themes[0] if themes else "防御"
            return TEMPLATES["divergence_defensive"][0].format(theme=t)
        if dominant == "周期资源":
            t = themes[0] if themes else "周期"
            return TEMPLATES["divergence_general"][0].format(theme=t)
        t = themes[0] if themes else "热点"
        return TEMPLATES["divergence_general"][0].format(theme=t)

    # ── 调整 ──
    if market_type == "调整":
        if sentiment_stage == "冰点":
            return TEMPLATES["correction_fear"][0]
        r = key_risk if key_risk else "外部因素"
        return TEMPLATES["correction_normal"][0].format(risk=r)

    # ── 震荡（默认） ──
    if themes:
        return TEMPLATES["choppy_accumulating"][0].format(theme=themes[0])
    return TEMPLATES["choppy_aimless"][0]


# ---------------------------------------------------------------------------
# 截断工具
# ---------------------------------------------------------------------------

def _truncate_to_200(text: str) -> str:
    """安全截断至 200 字符，确保以句号结尾。"""
    if len(text) <= 200:
        if not text.endswith("。"):
            # 优先在最后一个逗号/顿号后补齐句号
            text = text.rstrip("，,、；;") + "。"
        return text

    # 找到前 198 字符内最后一个句号
    last_period = text[:198].rfind("。")
    if last_period > 0:
        return text[:last_period + 1]

    # 否则硬截断并加句号
    return text[:197].rstrip("，,、；;") + "。"


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def synthesize(
    all_results: dict,
    stats: dict | None = None,
    crowding_scores: dict | None = None,
) -> tuple[str | None, str | None]:
    """合成当日市场核心判断（≤200 字）。

    基于所有分析模块的 markdown 输出，通过决策树识别市场特征，
    从模板库中选择最匹配的模板并填充槽位。

    Args:
        all_results: 各模块输出 dict，key 为模块名（如 "index_panorama"），
                     value 为该模块生成的 markdown 文本。
        stats: 聚合统计 dict（可选）。预留字段，当前未使用。
        crowding_scores: 拥挤度评分 dict，来自 crowding_monitor.compute_sector_crowding()。
                         格式: {板块名: {score, level, net_flow, label}}。

    Returns:
        (judgment_markdown_or_None, error_or_None)
        - 成功: (完整的核心判断 markdown 字符串, None)
        - 失败: (None, 错误描述字符串)
    """
    try:
        if not all_results:
            return None, "all_results 为空，无法合成核心判断"

        # 1. 提取市场特征
        panorama = all_results.get("index_panorama", "")
        sentiment = all_results.get("market_sentiment", "")
        theme = all_results.get("theme_analysis", "")
        risk = all_results.get("opportunity_risk", "")

        market_type = _detect_market_type(panorama)
        sentiment_stage = _detect_sentiment_stage(sentiment)
        themes = _extract_themes(theme)
        is_crowded, _ = _check_crowding_risk(crowding_scores, all_results)
        dominant = _extract_dominant_direction(all_results)
        key_risk = _extract_key_risk(risk)

        # 2. 选模板、填槽
        judgment = _select_template(
            market_type, sentiment_stage, themes, is_crowded, dominant, key_risk
        )

        # 3. 截断至 200 字符
        judgment = _truncate_to_200(judgment)

        return judgment, None

    except Exception as exc:
        return None, f"核心判断合成失败: {exc}"
