#!/usr/bin/env python3
"""
generate_deep_report.py — TdxClaw AI 级深度分析报告生成器

主入口：加载数据 → 调用全部深度分析子模块 → 组装报告 → 保存。
所有模块调用由 try/except 包裹，单个模块失败不影响整体流程。

用法:
    python scripts/generate_deep_report.py --date 2026-05-20
    python scripts/generate_deep_report.py                # 默认当天
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# 确保项目根目录在导入路径中（使 from scripts.xxx import ... 生效）
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _resolve_news_intensity(risk_level: str) -> str:
    """将 EVENT_PATTERNS 的 risk_level 映射为视觉强度指示符。"""
    if risk_level == "high":
        return "🔴 强"
    elif risk_level == "medium":
        return "🟡 中"
    elif risk_level == "low":
        return "🟢 弱"
    return "⚪ —"


def _normalize_title_for_dedup(title: str) -> str:
    """去空白、截短，用于展示层面的去重比对。"""
    return "".join(str(title).split())[:40]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="生成 A 股深度分析报告")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="日期 YYYY-MM-DD（默认当天）",
    )
    args = parser.parse_args()
    date_str: str = args.date

    # 校验日期格式
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"错误: 日期格式无效 '{date_str}'（需要 YYYY-MM-DD）")
        sys.exit(1)

    # ---- 依赖导入（从 scripts 包统一导入） ----
    try:
        from scripts.core_utils import (
            read_csv_data,
            read_deep_json,
            find_prev_csv_date,
            assemble_deep_report,
        )
        from scripts.config import DATA_DIR, DEEP_REPORTS_DIR
    except ImportError as e:
        print(f"错误: 核心依赖导入失败: {e}")
        sys.exit(1)

    print(f"[generate_deep_report] 开始生成 {date_str} 深度分析报告 ...")

    # ========================================================================
    # Step 1: 加载 CSV 行情快照
    # ========================================================================
    csv_path = DATA_DIR / f"{date_str}.csv"
    if not csv_path.exists():
        print(f"错误: CSV 文件不存在: {csv_path}")
        sys.exit(1)

    stats = read_csv_data(str(csv_path))
    print(f"  [加载] CSV 数据: {csv_path}")

    # ========================================================================
    # Step 2: 加载深度 JSON（由 prep_deep_data.py 准备）
    # ========================================================================
    deep_data = read_deep_json(date_str)
    if deep_data is None:
        print(f"  警告: 深度 JSON 不存在 (data/deep/{date_str}.json)，"
              f"部分分析模块将降级运行")

    # ========================================================================
    # Step 3: 加载前一交易日数据（用于环比 & 连板检测）
    # ========================================================================
    prev_date_str = (parsed_date - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_deep_data = read_deep_json(prev_date_str)

    prev_csv_date = find_prev_csv_date(parsed_date.date())
    prev_stats: Optional[dict] = None
    if prev_csv_date:
        prev_csv_path = DATA_DIR / f"{prev_csv_date}.csv"
        if prev_csv_path.exists():
            try:
                prev_stats = read_csv_data(str(prev_csv_path))
            except Exception:
                prev_stats = None

    print(f"  [加载] 前一日 CSV: {prev_csv_date or '无'}, "
          f"前一日 deep JSON: {'有' if prev_deep_data else '无'}")

    # ========================================================================
    # Step 4: 调用分析模块（每个模块独立 try/except，失败不阻塞）
    # ========================================================================
    errors: list[str] = []
    sections: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 4a. 产业链推理 & 新闻聚合（供后续模块使用）
    # ------------------------------------------------------------------
    chain_impacts: list[dict] = []
    all_news: list[dict] = []
    try:
        from scripts.headlines import _fetch_all_news, _deduplicate
        from scripts.chain_reasoning import analyze_chain

        raw_news, news_errors = _fetch_all_news()
        if raw_news:
            all_news = _deduplicate(raw_news)
        if news_errors:
            errors.append(f"新闻获取: {'; '.join(news_errors[:3])}")

        if all_news:
            chain_impacts, chain_err = analyze_chain(all_news)
            if chain_err:
                errors.append(f"产业链推理: {chain_err}")
        print(f"  [产业链推理] {len(all_news)} 条新闻 → "
              f"{len(chain_impacts)} 条产业链匹配")
    except Exception as e:
        errors.append(f"产业链推理异常: {e}")
        print(f"  警告: 产业链推理异常: {e}")

    # ------------------------------------------------------------------
    # 4b. 拥挤度监测
    # ------------------------------------------------------------------
    crowding_scores: dict[str, dict] = {}
    try:
        from scripts.crowding_monitor import (
            compute_crowding_table,
            compute_sector_crowding,
        )

        sector_flow_raw = (
            deep_data.get("sections", {}).get("sector_flow", [])
            if deep_data else []
        )
        total_amount = stats.get("total_amount", 0)

        crowding_table, crowd_err = compute_crowding_table(
            sector_flow_raw, total_amount
        )
        if crowding_table:
            sections["crowding_monitor"] = crowding_table
        if crowd_err:
            errors.append(f"拥挤度: {crowd_err}")

        crowding_scores = (
            compute_sector_crowding(sector_flow_raw) if sector_flow_raw else {}
        )
        print(f"  [拥挤度监测] {len(crowding_scores)} 个板块评估完成")
    except Exception as e:
        errors.append(f"拥挤度异常: {e}")
        print(f"  警告: 拥挤度异常: {e}")

    # ------------------------------------------------------------------
    # 4c. 模块一: 指数全景
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.index_panorama import analyze as analyze_index
        idx_section, idx_err = analyze_index(stats, deep_data, prev_stats)
        if idx_section:
            sections["index_panorama"] = idx_section
        if idx_err:
            errors.append(f"指数全景: {idx_err}")
        print(f"  [指数全景] {'完成' if idx_section else '跳过'}")
    except Exception as e:
        errors.append(f"指数全景异常: {e}")
        print(f"  警告: 指数全景异常: {e}")

    # ------------------------------------------------------------------
    # 4d. 模块二: 涨停跌停全景
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.limit_pool import analyze as analyze_limits
        limit_section, limit_err = analyze_limits(
            deep_data or {}, prev_deep_data
        )
        if limit_section:
            sections["limit_pool"] = limit_section
        if limit_err:
            errors.append(f"涨停跌停: {limit_err}")
        print(f"  [涨停跌停] {'完成' if limit_section else '跳过'}")
    except Exception as e:
        errors.append(f"涨停跌停异常: {e}")
        print(f"  警告: 涨停跌停异常: {e}")

    # ------------------------------------------------------------------
    # 4e. 模块三: 主线结构分析
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.theme_analysis import analyze as analyze_themes
        theme_section, theme_err = analyze_themes(
            deep_data or {}, chain_impacts, crowding_scores
        )
        if theme_section:
            sections["theme_analysis"] = theme_section
        if theme_err:
            errors.append(f"主线分析: {theme_err}")
        print(f"  [主线分析] {'完成' if theme_section else '跳过'}")
    except Exception as e:
        errors.append(f"主线分析异常: {e}")
        print(f"  警告: 主线分析异常: {e}")

    # ------------------------------------------------------------------
    # 4f. 模块四: 主力资金方向归类
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.fund_flow_analysis import (
            analyze as analyze_flow,
        )
        flow_section, flow_err = analyze_flow(deep_data or {})
        if flow_section:
            sections["fund_flow_analysis"] = flow_section
        if flow_err:
            errors.append(f"资金流向: {flow_err}")
        print(f"  [资金流向] {'完成' if flow_section else '跳过'}")
    except Exception as e:
        errors.append(f"资金流向异常: {e}")
        print(f"  警告: 资金流向异常: {e}")

    # ------------------------------------------------------------------
    # 4g. 模块五: 市场情绪综合评估
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.market_sentiment import (
            analyze as analyze_sentiment,
        )
        sent_section, sent_err = analyze_sentiment(stats, deep_data or {})
        if sent_section:
            sections["market_sentiment"] = sent_section
        if sent_err:
            errors.append(f"市场情绪: {sent_err}")
        print(f"  [市场情绪] {'完成' if sent_section else '跳过'}")
    except Exception as e:
        errors.append(f"市场情绪异常: {e}")
        print(f"  警告: 市场情绪异常: {e}")

    # ------------------------------------------------------------------
    # 4h. 模块六: 机会与风险识别
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.opportunity_risk import (
            analyze as analyze_opprisk,
        )
        opp_section, opp_err = analyze_opprisk(
            sections, crowding_scores, deep_data
        )
        if opp_section:
            sections["opportunity_risk"] = opp_section
        if opp_err:
            errors.append(f"机会风险: {opp_err}")
        print(f"  [机会风险] {'完成' if opp_section else '跳过'}")
    except Exception as e:
        errors.append(f"机会风险异常: {e}")
        print(f"  警告: 机会风险异常: {e}")

    # ------------------------------------------------------------------
    # 4i. 模块七: 核心判断
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.core_judgment import synthesize
        core_section, core_err = synthesize(sections, stats, crowding_scores)
        if core_section:
            sections["core_judgment"] = core_section
        if core_err:
            errors.append(f"核心判断: {core_err}")
        print(f"  [核心判断] {'完成' if core_section else '跳过'}")
    except Exception as e:
        errors.append(f"核心判断异常: {e}")
        print(f"  警告: 核心判断异常: {e}")

    # ------------------------------------------------------------------
    # 4j. 模块八: 四维穿透分析框架
    # ------------------------------------------------------------------
    try:
        from scripts.deep_analysis.four_dimension import apply as apply_four_dim
        fd_section, fd_err = apply_four_dim(
            sections,
            all_news if all_news else [],
            chain_impacts,
            crowding_scores,
            stats,
        )
        if fd_section:
            sections["four_dimension"] = fd_section
        if fd_err:
            errors.append(f"四维分析: {fd_err}")
        print(f"  [四维分析] {'完成' if fd_section else '跳过'}")
    except Exception as e:
        errors.append(f"四维分析异常: {e}")
        print(f"  警告: 四维分析异常: {e}")

    # ------------------------------------------------------------------
    # 4k. 新闻解读（基于 EVENT_PATTERNS 的事件匹配）
    # ------------------------------------------------------------------
    try:
        if all_news:
            from scripts.knowledge_base import EVENT_PATTERNS

            news_lines = [
                "## 一、新闻解读",
                "",
                "| 事件 | 强度 | 影响分析 |",
                "|------|------|----------|",
            ]
            seen_titles: set[str] = set()
            for item in all_news[:20]:
                title = item.get("title", "")
                content = item.get("content", "")
                text = f"{title} {content}"
                if not title.strip():
                    continue

                norm = _normalize_title_for_dedup(title)
                if norm in seen_titles:
                    continue

                for pattern_name, pattern_info in EVENT_PATTERNS.items():
                    keywords = pattern_info.get("keywords", [])
                    if not keywords:
                        # 无显式 keywords 时，用 pattern_name 作为隐式匹配词
                        keywords = [pattern_name]

                    if any(kw in text for kw in keywords):
                        intensity = _resolve_news_intensity(
                            pattern_info.get("risk_level", "")
                        )
                        impact = pattern_info.get("directional", "")
                        # 截断过长标题
                        display_title = title[:55]
                        news_lines.append(
                            f"| {display_title} | {intensity} | {impact} |"
                        )
                        seen_titles.add(norm)
                        break

            if len(news_lines) > 4:  # 超过表头行数: heading + blank + header + separator
                sections["news_interpretation"] = "\n".join(news_lines)
                print(f"  [新闻解读] {len(news_lines) - 4} 条事件匹配")
            else:
                print("  [新闻解读] 无事件匹配，该章节跳过")
    except Exception as e:
        errors.append(f"新闻解读: {e}")
        print(f"  警告: 新闻解读异常: {e}")

    # ========================================================================
    # Step 5: 组装 & 保存报告
    # ========================================================================
    DEEP_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        report = assemble_deep_report(date_str, sections, errors)
    except Exception as e:
        print(f"错误: 报告组装失败: {e}")
        # 回退：直接拼接 sections
        fallback_body = "\n\n---\n\n".join(
            content for content in sections.values() if content
        )
        report = (
            f"# A 股深度分析 — {date_str}\n\n"
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{fallback_body}\n\n"
            f"## 数据异常备注\n\n"
            + "\n".join(f"- {e}" for e in errors)
            + "\n"
        )

    output_path = DEEP_REPORTS_DIR / f"{date_str}.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"\n深度报告已保存: {output_path}")

    # ========================================================================
    # Step 6: 结果总结
    # ========================================================================
    if errors:
        print(f"\n警告: {len(errors)} 个环节存在异常:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("所有模块执行正常，无异常。")

    section_count = len(sections)
    print(f"完成: 报告共输出 {section_count} 个章节。")


if __name__ == "__main__":
    main()
