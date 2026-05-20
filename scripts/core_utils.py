"""
core_utils.py — 核心工具函数

提供 CSV 读取、环比计算、报告组装等可复用基础能力。
"""

import json
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

from scripts.config import DATA_DIR, REPORTS_DIR, INDICES_CONFIG

# 指数前缀 → 显示名
INDICES_MAP = [(p, n) for p, _, n in INDICES_CONFIG]

def read_csv_data(csv_path: str) -> dict:
    """从 CSV 末行解析行情统计数据，返回 dict。"""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV 文件为空: {csv_path}")
    row = df.iloc[-1]  # 最后一行 = 最新快照

    stats = {
        "time":       str(row.get("time", "")),
        "total":      int(row.get("total", 0)),
        "up":         int(row.get("up", 0)),
        "down":       int(row.get("down", 0)),
        "flat":       int(row.get("flat", 0)),
        "ratio":      _safe_float(row.get("ratio", 0)),
        "total_amount": _safe_float(row.get("total_amount", 0)),
        "limit_up":   int(row.get("limit_up", 0)),
        "big_up":     int(row.get("big_up", 0)),
        "small_up":   int(row.get("small_up", 0)),
        "small_down": int(row.get("small_down", 0)),
        "big_down":   int(row.get("big_down", 0)),
        "limit_down": int(row.get("limit_down", 0)),
        "avg_change":    _safe_float(row.get("avg_change", 0)),
        "median_change": _safe_float(row.get("median_change", 0)),
    }

    # 指数行情
    indices = {}
    for prefix, name in INDICES_MAP:
        price = _safe_float(row.get(f"{prefix}_price", None))
        change = _safe_float(row.get(f"{prefix}_change", None))
        if price is not None and change is not None:
            indices[prefix] = {"name": name, "price": price, "change": change}
    stats["indices"] = indices

    return stats


def _safe_float(val, default=None):
    """安全转 float，不可转时返回 default。"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def find_prev_csv_date(target_date: date) -> str | None:
    """在 DATA_DIR 中查找 target_date 之前的最新 CSV 日期。

    Returns:
        date_str (YYYY-MM-DD) 或 None
    """
    if not DATA_DIR.exists():
        return None
    candidates = []
    for f in DATA_DIR.iterdir():
        if f.suffix == ".csv" and f.stem.count("-") == 2:
            try:
                d = datetime.strptime(f.stem, "%Y-%m-%d").date()
                if d < target_date:
                    candidates.append((d, f.stem))
            except ValueError:
                continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]  # YYYY-MM-DD


def calc_change_vs_prev(current_amount: float, prev_csv_date: str) -> str:
    """计算总成交额环比前一交易日的变化率。"""
    prev_path = DATA_DIR / f"{prev_csv_date}.csv"
    if not prev_path.exists():
        return "暂无历史数据"
    try:
        prev_df = pd.read_csv(prev_path)
        if prev_df.empty:
            return "暂无历史数据"
        prev_amount = _safe_float(prev_df.iloc[-1].get("total_amount", None))
        if prev_amount is None or prev_amount == 0:
            return "暂无历史数据"
        pct = (current_amount - prev_amount) / prev_amount * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.2f}%"
    except Exception:
        return "暂无历史数据"


def generate_summary(stats: dict,
                     industry_error: str | None,
                     northbound_error: str | None,
                     us_error: str | None = None,
                     cny_error: str | None = None,
                     driven_news_error: str | None = None,
                     gainers_error: str | None = None,
                     losers_error: str | None = None) -> str:
    """生成 2-3 句市场概况总结。"""
    parts = []
    ratio = stats["ratio"]
    avg = stats["avg_change"]
    up = stats["up"]
    down = stats["down"]

    # 1. 大盘强弱
    if ratio > 2:
        parts.append(f"市场表现强势，上涨家数{up}家远超下跌{down}家，涨跌比{ratio}，平均涨幅{avg:.2f}%。")
    elif ratio > 1:
        parts.append(f"市场整体偏强，上涨{up}家 vs 下跌{down}家（涨跌比{ratio}），平均涨幅{avg:.2f}%。")
    elif ratio == 1:
        parts.append(f"市场涨跌均衡（涨跌比{ratio}），平均涨幅{avg:.2f}%。")
    else:
        parts.append(f"市场表现偏弱，下跌{down}家多于上涨{up}家（涨跌比{ratio}），平均涨幅{avg:.2f}%。")

    # 2. 指数分化
    indices = stats.get("indices", {})
    changes = {p: idx["change"] for p, idx in indices.items()}
    if changes:
        max_prefix = max(changes, key=changes.get)
        min_prefix = min(changes, key=changes.get)
        spread = changes[max_prefix] - changes[min_prefix]
        if spread > 1.5:
            name_max = indices[max_prefix]["name"]
            name_min = indices[min_prefix]["name"]
            parts.append(f"指数分化明显，{name_max}领涨（{changes[max_prefix]:.2f}%），{name_min}承压（{changes[min_prefix]:.2f}%）。")

    # 3. 备注错误
    if industry_error:
        parts.append(f"（板块数据: {industry_error}）")
    if northbound_error:
        parts.append(f"（北向数据: {northbound_error}）")
    if us_error:
        parts.append(f"（美股数据: {us_error}）")
    if cny_error:
        parts.append(f"（汇率数据: {cny_error}）")
    if driven_news_error:
        parts.append(f"（驱动新闻数据: {driven_news_error}）")
    if gainers_error:
        parts.append(f"（涨幅榜数据: {gainers_error}）")
    if losers_error:
        parts.append(f"（跌幅榜数据: {losers_error}）")

    return " ".join(parts)


def generate_report(stats: dict, date_str: str,
                    change_vs_prev: str,
                    industry_table: str | None,
                    northbound_table: str | None,
                    summary: str,
                    anomaly_section: str | None = None,
                    us_table: str | None = None,
                    cny_info: str | None = None,
                    gainers_table: str | None = None,
                    losers_table: str | None = None,
                    driven_news_table: str | None = None,
                    overseas_section: str | None = None,
                    activity_section: str | None = None,
                    individual_flow_table: str | None = None,
                    us_leader_table: str | None = None,
                    us_etf_table: str | None = None,
                    entity_price_table: str | None = None) -> str:
    """组装完整 Markdown 报告。"""
    idx = stats["indices"]

    # 大盘指数表
    idx_lines = ["| 指数 | 收盘价 | 涨跌幅 |", "|------|--------|--------|"]
    for prefix, name in INDICES_MAP:
        if prefix in idx:
            i = idx[prefix]
            change_str = f"+{i['change']:.2f}%" if i["change"] > 0 else f"{i['change']:.2f}%"
            idx_lines.append(f"| {name} | {i['price']:.2f} | {change_str} |")
        else:
            idx_lines.append(f"| {name} | - | - |")
    index_table = "\n".join(idx_lines)

    # 环比说明
    change_desc = f"环比前一交易日: {change_vs_prev}" if change_vs_prev != "暂无历史数据" else "暂无历史数据"

    # 涨幅分布表
    dist_lines = [
        "| 区间 | 家数 |",
        "|------|------|",
        f"| 涨停 (>=9.9%) | {stats['limit_up']} |",
        f"| 大涨 (5%~9.9%) | {stats['big_up']} |",
        f"| 小涨 (0%~5%) | {stats['small_up']} |",
        f"| 小跌 (-5%~0%) | {stats['small_down']} |",
        f"| 大跌 (-5%以下) | {stats['big_down']} |",
        f"| 跌停 (<=-9.9%) | {stats['limit_down']} |",
    ]
    dist_table = "\n".join(dist_lines)

    # 板块
    industry_section = industry_table or "*数据获取失败*"
    # 异动监测
    anomaly_display = f"\n{anomaly_section}\n" if anomaly_section else ""
    # 北向
    northbound_section = northbound_table or "*数据获取失败*"
    # 宏观
    us_section = us_table or "*数据获取失败*"
    cny_section = cny_info or "*数据获取失败*"
    # 海外头条
    overseas_display = f"\n{overseas_section}\n" if overseas_section else ""
    # 美股龙头催化
    us_leader_display = f"\n{us_leader_table}\n" if us_leader_table else ""
    # 美股板块ETF映射
    us_etf_display = f"\n### 美股板块映射\n\n{us_etf_table}\n" if us_etf_table else ""
    # 新闻-个股联动
    entity_price_display = f"\n### 新闻-个股联动\n\n{entity_price_table}\n" if entity_price_table else ""
    # 市场活跃度
    activity_display = f"\n{activity_section}\n" if activity_section else ""
    # 涨幅榜
    gainers_section = gainers_table or "*数据获取失败*"
    # 跌幅榜
    losers_section = losers_table or "*数据获取失败*"
    # 个股资金流入
    individual_flow_display = f"\n{individual_flow_table}\n" if individual_flow_table else ""
    # 驱动新闻
    driven_news_section = driven_news_table or "*数据获取失败*"

    report = f"""# A 股市场日报 — {date_str}

## 大盘指数

{index_table}

## 宏观市场

{us_section}

{cny_section}

## 海外市场

{overseas_display}

### 海外龙头催化

{us_leader_display}

{us_etf_display}
{entity_price_display}
## 市场活跃度

{activity_display}

## 市场概况

- **上涨家数**: {stats["up"]}  **下跌家数**: {stats["down"]}  **平盘**: {stats["flat"]}
- **涨跌比**: {stats["ratio"]}
- **总成交额**: {stats["total_amount"]:.2f} 亿元
- **{change_desc}**

### 涨幅分布

{dist_table}

- **平均涨幅**: {stats["avg_change"]:.2f}%
- **涨幅中位数**: {stats["median_change"]:.2f}%

## 板块资金流向

{industry_section}
{anomaly_display}
## 个股资金流入 TOP10

{individual_flow_display}
## 北向资金

> 注：北向净额数据暂不可用，以下为成交额数据。

{northbound_section}

## 涨幅榜

{gainers_section}

## 跌幅榜

{losers_section}

## 今日驱动新闻

{driven_news_section}

## 总结

{summary}
"""
    return report


# ---------------------------------------------------------------------------
# 深度报告（deep report）工具
# ---------------------------------------------------------------------------

DEEP_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "deep"

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

SECTION_ORDER = [
    ("news_interpretation", "一、新闻解读"),
    ("index_panorama", "二、指数全景"),
    ("limit_pool", "三、涨停跌停全景"),
    ("theme_analysis", "四、主线结构分析"),
    ("fund_flow_analysis", "五、主力资金 TOP10"),
    ("market_sentiment", "六、市场情绪"),
    ("opportunity_risk", "七、机会与风险"),
    ("core_judgment", "八、核心判断"),
    ("four_dimension", "九、四维穿透分析"),
]


def read_deep_json(date_str: str) -> dict | None:
    """从 data/deep/{date_str}.json 读取深度数据。

    Returns:
        解析后的 dict；文件不存在或 JSON 无效时返回 None。
    """
    deep_path = DEEP_DATA_DIR / f"{date_str}.json"
    if not deep_path.exists():
        return None
    try:
        with open(deep_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def assemble_deep_report(date_str: str, sections: dict, errors: list[str]) -> str:
    """将各分析模块的输出组装为深度报告 Markdown。

    Args:
        date_str: 日期字符串 YYYY-MM-DD。
        sections: {section_key: markdown_text}，键名参见 SECTION_ORDER。
        errors: 数据异常描述列表。

    Returns:
        完整 Markdown 字符串。
    """
    # 星期几
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        wday = WEEKDAY_CN[dt.weekday()]
    except (ValueError, IndexError):
        wday = ""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 按顺序拼接章节
    section_blocks: list[str] = []
    for key, heading in SECTION_ORDER:
        content = sections.get(key)
        if content and content.strip():
            section_blocks.append(content.strip())
        else:
            # 缺失时用占位
            section_blocks.append(f"{heading}\n\n*数据获取失败，该章节跳过*")

    body = "\n\n".join(section_blocks)

    # 错误备注
    if errors:
        error_lines = "\n".join(f"- {e}" for e in errors)
        error_section = f"## 数据异常备注\n\n{error_lines}\n"
    else:
        error_section = "## 数据异常备注\n\n无\n"

    report = f"""# A 股深度分析 — {date_str}（{wday}）

> 生成时间: {now_str}
> 数据来源: CSV 收盘快照 / AkShare 板块资金流 / 个股资金流 / 美股映射

{body}

---

{error_section}

---

## 免责声明
本报告基于公开数据自动生成，仅供参考，不构成投资建议。市场有风险，投资需谨慎。历史数据不代表未来表现。
"""
    return report


