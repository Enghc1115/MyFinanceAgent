"""
headlines.py — 多源新闻聚合 + 实体提取 + 股价联动评分

从多个财经数据源聚合新闻，提取实体（公司、板块、股票代码），
结合实时行情计算股价联动评分，输出驱动新闻表格。
"""

import re
import time
import os
import glob
import akshare as ak
import pandas as pd
from scripts.knowledge_base import STOCK_NAME_DICT, COMPANY_KEYWORDS


def _clear_akshare_cache():
    """清除 akshare 缓存目录，解决 API 返回异常的问题。"""
    cache_dir = "/tmp/.akshare/"
    if os.path.exists(cache_dir):
        for f in glob.glob(os.path.join(cache_dir, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

# ============================================================
# Entity Extraction Keywords
# ============================================================

# COMPANY_KEYWORDS 从 scripts.knowledge_base 导入（基于 STOCK_NAME_DICT 的 129 只核心股票）
# SECTOR_KEYWORDS 保留硬编码（板块/概念关键词，用于新闻文本匹配）

# 板块/概念关键词
SECTOR_KEYWORDS: list[str] = [
    "半导体", "芯片", "AI", "人工智能", "光伏", "新能源", "锂电池", "储能",
    "消费", "医药", "白酒", "银行", "券商", "保险", "地产", "汽车",
    "军工", "5G", "数字经济", "机器人", "自动驾驶", "算力", "数据要素",
    "电力", "煤炭", "石油", "黄金", "稀土", "钢铁", "化工", "有色",
    "通信", "信创", "东数西算", "元宇宙", "VR", "AR", "量子计算",
    "预制菜", "医美", "免税", "跨境电商", "物流", "教育", "游戏",
    "氢能", "核电", "风电", "充电桩", "智能电网",
    "工业母机", "高端装备", "新材料", "碳纤维",
    "低空经济", "商业航天", "脑机接口", "人形机器人", "固态电池",
    "钠离子电池", "钙钛矿", "HBM", "CPO", "先进封装",
]

# 股票代码正则：6 位数字
_STOCK_CODE_RE = re.compile(r"\b(\d{6})\b")


# ============================================================
# Internal: Multi-source fetching
# ============================================================

def _normalize_title(t: str) -> str:
    """去空白、截短，用于去重比对。"""
    return re.sub(r"\s+", "", str(t))[:35]


def _get_col(row, candidates: list[str]) -> str:
    """从行中尝试多个候选列名，返回第一个非空值。"""
    for c in candidates:
        val = row.get(c)
        if val is not None and not pd.isna(val) and str(val).strip():
            return str(val).strip()
    return ""


def _fetch_cls_source() -> tuple[list[dict], str | None]:
    """财联社 7x24 全球快讯。"""
    try:
        df = ak.stock_info_global_cls()
        if df is None or df.empty:
            return [], "财联社返回空数据"
        items = []
        for _, r in df.iterrows():
            title = _get_col(r, ["标题", "title", "新闻标题"])
            if not title:
                continue
            content = _get_col(r, ["内容", "content", "新闻内容", "summary"])
            items.append({
                "title": title,
                "content": content,
                "source": "财联社",
            })
        return items, None
    except Exception as e:
        return [], f"财联社获取失败: {e}"


def _fetch_eastmoney_source() -> tuple[list[dict], str | None]:
    """东方财富新闻。"""
    try:
        df = ak.stock_news_em()
        if df is None or df.empty:
            return [], "东方财富返回空数据"
        items = []
        for _, r in df.iterrows():
            title = _get_col(r, ["新闻标题", "标题", "title"])
            if not title:
                continue
            content = _get_col(r, ["新闻内容", "内容", "content"])
            items.append({
                "title": title,
                "content": content,
                "source": "东方财富",
            })
        return items, None
    except Exception as e:
        return [], f"东方财富获取失败: {e}"


def _fetch_sina_source() -> tuple[list[dict], str | None]:
    """新浪财经 24 小时滚动新闻。"""
    try:
        for func_name in ["stock_info_sina_finance", "stock_info_sina"]:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            try:
                df = func()
                if df is None or df.empty:
                    continue
                items = []
                for _, r in df.iterrows():
                    title = _get_col(r, ["标题", "title", "新闻标题"])
                    if not title:
                        continue
                    items.append({
                        "title": title,
                        "content": "",
                        "source": "新浪财经",
                    })
                return items, None
            except Exception:
                continue
        return [], "新浪财经无可用 API"
    except Exception as e:
        return [], f"新浪财经获取失败: {e}"


def _fetch_wallstreetcn_source() -> tuple[list[dict], str | None]:
    """华尔街见闻。"""
    try:
        for func_name in ["stock_info_wallstreetcn", "stock_info_wsj_cn"]:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            try:
                df = func()
                if df is None or df.empty:
                    continue
                items = []
                for _, r in df.iterrows():
                    title = _get_col(r, ["标题", "title", "新闻标题"])
                    if not title:
                        continue
                    items.append({
                        "title": title,
                        "content": "",
                        "source": "华尔街见闻",
                    })
                return items, None
            except Exception:
                continue
        return [], "华尔街见闻无可用 API"
    except Exception as e:
        return [], f"华尔街见闻获取失败: {e}"


def _fetch_all_news() -> tuple[list[dict], list[str]]:
    """从所有数据源聚合新闻。单个源失败不影响其他源。

    Returns:
        (news_items, error_messages)
    """
    sources = [
        ("财联社", _fetch_cls_source),
        ("东方财富", _fetch_eastmoney_source),
        ("新浪财经", _fetch_sina_source),
        ("华尔街见闻", _fetch_wallstreetcn_source),
    ]

    all_news: list[dict] = []
    errors: list[str] = []

    for name, func in sources:
        items, err = func()
        if err:
            errors.append(err)
        else:
            all_news.extend(items)

    return all_news, errors


def _deduplicate(news_items: list[dict]) -> list[dict]:
    """按标题去重（归一化后前 N 个字符完全一致视为重复）。"""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in news_items:
        norm = _normalize_title(item["title"])
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(item)
    return unique


# ============================================================
# Internal: Entity Extraction
# ============================================================

def _extract_entities(text: str) -> dict[str, list[str]]:
    """从文本中提取实体，并通过 STOCK_NAME_DICT 补充代码与板块信息。

    Returns:
        {"companies": [...], "sectors": [...], "codes": [...]}
    """
    result: dict[str, list[str]] = {
        "companies": [],
        "sectors": [],
        "codes": [],
    }

    t = str(text)

    # 公司名匹配（COMPANY_KEYWORDS 已从 knowledge_base 按长度降序排列）
    for kw in COMPANY_KEYWORDS:
        if kw in t:
            result["companies"].append(kw)
            # 从知识库补充代码和板块信息
            info = STOCK_NAME_DICT.get(kw)
            if info:
                code = info.get("code", "")
                sector = info.get("sector", "")
                if code and code not in result["codes"]:
                    result["codes"].append(code)
                if sector and sector not in result["sectors"]:
                    result["sectors"].append(sector)

    # 板块/概念匹配（从长到短排序，减少子串误匹配）
    sorted_sectors = sorted(SECTOR_KEYWORDS, key=len, reverse=True)
    for kw in sorted_sectors:
        if kw in t and kw not in result["sectors"]:
            result["sectors"].append(kw)

    # 股票代码匹配
    codes = _STOCK_CODE_RE.findall(t)
    for code in codes:
        if code not in result["codes"]:
            result["codes"].append(code)

    return result


# ============================================================
# Internal: Real-time Quotes & Linkage Scoring
# ============================================================

def _get_realtime_quotes() -> tuple[pd.DataFrame | None, str | None]:
    """获取 A 股全市场实时行情（含缓存清理重试）。

    Returns:
        (DataFrame_or_None, error_str_or_None)
    """
    last_error = None
    for attempt in range(2):
        try:
            if attempt > 0:
                _clear_akshare_cache()
                time.sleep(1)
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                raise ValueError("API 返回空数据")
            return df, None
        except Exception as e:
            last_error = e
    return None, f"实时行情获取失败: {last_error}"


def _build_name_lookup(quotes_df: pd.DataFrame) -> dict[str, pd.Series]:
    """构建股票名称 → 行数据的查找表，含简称变体。

    自动生成简称：去除常见后缀（股份、集团、科技、电子、控股等）。
    """
    lookup: dict[str, pd.Series] = {}

    if "名称" not in quotes_df.columns:
        return lookup

    for _, row in quotes_df.iterrows():
        name = str(row["名称"]).strip()
        if not name or name == "nan":
            continue
        # 全名
        lookup[name] = row
        # 简称变体：去后缀
        short = name
        for suffix in ["股份", "集团", "科技", "电子", "控股", "有限", "实业",
                        "产业", "发展", "能源", "医药", "医疗", "信息",
                        "技术", "材料", "电气", "智能", "数字", "网络",
                        "光电", "精密", "环保", "食品", "饮料", "传媒"]:
            short = short.replace(suffix, "")
        if short != name and len(short) >= 2:
            lookup[short] = row

    return lookup


def _build_code_lookup(quotes_df: pd.DataFrame) -> dict[str, pd.Series]:
    """构建股票代码 → 行数据的查找表。"""
    lookup: dict[str, pd.Series] = {}
    if "代码" not in quotes_df.columns:
        return lookup
    for _, row in quotes_df.iterrows():
        code = str(row["代码"]).strip()
        if code and code != "nan":
            lookup[code] = row
    return lookup


def _score_news(
    news_items: list[dict],
    quotes_df: pd.DataFrame,
    name_lookup: dict[str, pd.Series],
    code_lookup: dict[str, pd.Series],
) -> list[dict]:
    """计算每条新闻的股价联动评分。

    评分 = min(|涨跌幅|, 10)，仅 |涨跌幅| > 2% 纳入驱动新闻。
    """
    scored: list[dict] = []

    for item in news_items:
        text = item["title"] + " " + item.get("content", "")
        entities = _extract_entities(text)

        # 收集所有匹配到的股票行
        matched_stocks: dict[str, dict] = {}  # code -> {name, change}

        # 公司名匹配
        for comp in entities["companies"]:
            row = name_lookup.get(comp)
            if row is not None:
                code = str(row.get("代码", "")).strip()
                if code:
                    matched_stocks[code] = {
                        "name": str(row.get("名称", comp)).strip(),
                        "change": float(row.get("涨跌幅", 0) or 0),
                    }

        # 股票代码匹配
        for code in entities["codes"]:
            if code not in matched_stocks:
                row = code_lookup.get(code)
                if row is not None:
                    matched_stocks[code] = {
                        "name": str(row.get("名称", "")).strip(),
                        "change": float(row.get("涨跌幅", 0) or 0),
                    }

        if not matched_stocks:
            continue

        # 取涨跌幅绝对值最大的股票作为联动标的
        best_code = max(matched_stocks, key=lambda c: abs(matched_stocks[c]["change"]))
        best = matched_stocks[best_code]
        change = best["change"]

        # 阈值：|涨跌幅| > 2%
        if abs(change) <= 2.0:
            continue

        # 联动评分 = |涨跌幅| 归一化到 0-10
        score = min(abs(change), 10.0)

        # 影响标的：股票名 + 匹配到的板块
        matched_names = [best["name"]]
        # 去重（避免股票名和板块名重复）
        matched_names.extend([s for s in entities["sectors"] if s not in matched_names])
        # 限制数量
        entities_str = "/".join(matched_names[:3])

        scored.append({
            "title": item["title"],
            "source": item["source"],
            "entities_str": entities_str,
            "score": round(score, 1),
            "change": change,
        })

    # 按联动评分降序
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# ============================================================
# Public API
# ============================================================

def fetch_driven_news() -> tuple[str | None, str | None]:
    """多源聚合 + 实体提取 + 股价联动评分。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    # 1. 多源聚合
    all_news, errors = _fetch_all_news()

    if not all_news:
        err_msg = "; ".join(errors) if errors else "所有数据源均无数据"
        return None, err_msg

    # 2. 去重
    all_news = _deduplicate(all_news)

    # 3. 获取实时行情
    quotes_df, quote_err = _get_realtime_quotes()
    if quote_err:
        # 取不到行情时，降级为无评分的普通新闻列表
        lines = ["| 新闻标题 | 来源 |",
                  "|----------|------|"]
        for item in all_news[:15]:
            title = item["title"][:60] + "..." if len(item["title"]) > 60 else item["title"]
            lines.append(f"| {title} | {item['source']} |")
        return "\n".join(lines), None

    # 4. 构建查找表
    name_lookup = _build_name_lookup(quotes_df)
    code_lookup = _build_code_lookup(quotes_df)

    # 5. 评分
    scored = _score_news(all_news, quotes_df, name_lookup, code_lookup)

    # 6. 格式化输出
    if not scored:
        return "_今日暂无显著驱动新闻（无股价涨跌幅 > 2% 的关联标的）_", None

    top_n = min(len(scored), 15)
    scored = scored[:top_n]

    lines = [
        "| 新闻标题 | 来源 | 影响标的 | 联动评分 | 涨跌幅 |",
        "|----------|------|----------|----------|--------|",
    ]
    for n in scored:
        title = n["title"][:55] + "..." if len(n["title"]) > 55 else n["title"]
        pct = n["change"]
        pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        lines.append(
            f"| {title} | {n['source']} | {n['entities_str']} "
            f"| {n['score']:.1f} | {pct_str} |"
        )

    return "\n".join(lines), None


def build_entity_price_table(date_str: str = None) -> tuple[str | None, str | None]:
    """构建「新闻 → 关联个股 → 涨跌幅」映射表。

    与 fetch_driven_news() 的区别：
    - fetch_driven_news() 按股价联动评分排序，仅展示 |涨跌幅| > 2% 的驱动新闻
    - build_entity_price_table() 不设阈值，纯粹展示「哪些个股上了新闻、涨跌如何」

    用途：为深度分析报告提供「新闻-个股」事实映射，不做评分筛选。

    Args:
        date_str: 日期字符串（保留参数，当前使用实时数据）

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    # 1. 多源聚合
    all_news, errors = _fetch_all_news()

    if not all_news:
        err_msg = "; ".join(errors) if errors else "所有数据源均无数据"
        return None, err_msg

    # 2. 去重
    all_news = _deduplicate(all_news)

    # 3. 获取实时行情
    quotes_df, quote_err = _get_realtime_quotes()
    if quote_err:
        return None, f"无法获取实时行情: {quote_err}"

    # 4. 构建查找表
    name_lookup = _build_name_lookup(quotes_df)
    code_lookup = _build_code_lookup(quotes_df)

    # 5. 逐条新闻匹配个股涨跌
    rows: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()  # (title_prefix, stock_name) 去重

    for item in all_news:
        text = item["title"] + " " + item.get("content", "")
        entities = _extract_entities(text)

        matched_stocks: dict[str, dict] = {}  # code -> {name, change}

        # 公司名匹配
        for comp in entities["companies"]:
            row = name_lookup.get(comp)
            if row is not None:
                code = str(row.get("代码", "")).strip()
                if code:
                    matched_stocks[code] = {
                        "name": str(row.get("名称", comp)).strip(),
                        "change": float(row.get("涨跌幅", 0) or 0),
                    }

        # 股票代码匹配
        for code in entities["codes"]:
            if code not in matched_stocks:
                row = code_lookup.get(code)
                if row is not None:
                    matched_stocks[code] = {
                        "name": str(row.get("名称", "")).strip(),
                        "change": float(row.get("涨跌幅", 0) or 0),
                    }

        # 为每对 (新闻, 个股) 生成一行
        title = item["title"]
        for code, stock in matched_stocks.items():
            pair = (title[:40], stock["name"])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            change = stock["change"]
            rows.append({
                "title": title,
                "stock_name": stock["name"],
                "change": change,
            })

    # 6. 格式化输出
    if not rows:
        return "_今日新闻中未匹配到关联个股_", None

    # 按涨跌幅绝对值降序排列
    rows.sort(key=lambda x: abs(x["change"]), reverse=True)

    lines = [
        "| 新闻标题 | 关联个股 | 涨跌幅 |",
        "|----------|----------|--------|",
    ]
    for r in rows[:30]:  # 最多展示 30 条
        short_title = r["title"][:55] + "..." if len(r["title"]) > 55 else r["title"]
        pct = r["change"]
        pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        lines.append(f"| {short_title} | {r['stock_name']} | {pct_str} |")

    return "\n".join(lines), None
