"""
us_market.py — 美股行情数据获取

提供:
  - fetch_us_market: 美股三大指数 (SPY, QQQ, DIA)
  - fetch_us_leader_stocks: 美股龙头催化 (NVDA, AMD, AAPL, TSLA, TSM)
  - fetch_overseas_headlines: 海外相关头条筛选
"""

import akshare as ak


def fetch_us_market(target_date_str: str) -> tuple:
    """获取美股三大指数行情（SPY、QQQ、DIA），含隔夜涨跌方向和 A 股映射提示。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        symbols = {"SPY": "S&P 500(SPY)", "QQQ": "Nasdaq(QQQ)", "DIA": "Dow(DIA)"}
        lines = [
            "| 指数 | 收盘价 | 涨跌幅 | 方向 |",
            "|------|--------|--------|------|",
        ]
        directions = []
        for symbol, name in symbols.items():
            df = ak.stock_us_daily(symbol)
            # A 股收盘时美股未开盘，date 过滤会命中空行
            # DataFrame 按日期升序排列，取最后一行即最近交易日
            if df is None or df.empty:
                lines.append(f"| {name} | - | - | - |")
                continue
            r = df.iloc[-1]
            close = float(r["close"])
            open_ = float(r["open"])
            change = (close - open_) / open_ * 100
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            direction = (
                "🟢 上涨" if change > 0 else ("🔴 下跌" if change < 0 else "⚪ 平盘")
            )
            directions.append(direction)
            lines.append(f"| {name} | {close:.2f} | {change_str} | {direction} |")

        table = "\n".join(lines)

        # A 股映射提示
        mapping_notes = []
        if "S&P" in table:
            mapping_notes.append("美股走势影响次日北向资金方向和 A 股开盘情绪")
        if "Nasdaq" in table:
            mapping_notes.append("纳指走势映射 A 股科技/半导体/AI 算力板块")
        if "Dow" in table:
            mapping_notes.append("道指走势映射 A 股金融/消费/周期板块")

        result = table + "\n\n**A 股映射**：" + "；".join(mapping_notes)
        return result, None
    except Exception as e:
        return None, f"美股行情获取失败: {e}"


def fetch_us_leader_stocks(target_date_str: str) -> tuple:
    """获取美股龙头股（NVDA/AMD/AAPL/TSLA/TSM）当日行情及 A 股映射方向。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        leaders = {
            "NVDA": "英伟达",
            "AMD": "AMD",
            "AAPL": "苹果",
            "TSLA": "特斯拉",
            "TSM": "台积电",
        }
        mapping = {
            "NVDA": "AI 算力/光模块/液冷",
            "AMD": "CPU 链/服务器",
            "AAPL": "消费电子/果链",
            "TSLA": "智能驾驶/机器人",
            "TSM": "半导体/芯片",
        }
        lines = [
            "| 个股 | 收盘价 | 涨跌幅 | A 股映射 |",
            "|------|--------|--------|----------|",
        ]
        for symbol, name in leaders.items():
            df = ak.stock_us_daily(symbol)
            # DataFrame 按日期升序排列，取最后一行即最近交易日
            if df is None or df.empty:
                lines.append(f"| {name} | - | - | {mapping.get(symbol, '')} |")
                continue
            r = df.iloc[-1]
            close = float(r["close"])
            change = (close - float(r["open"])) / float(r["open"]) * 100
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(
                f"| {name} | {close:.2f} | {change_str} | {mapping.get(symbol, '')} |"
            )
        return "\n".join(lines), None
    except Exception as e:
        return None, f"美股龙头行情获取失败: {e}"


def fetch_overseas_headlines() -> tuple:
    """从财联社头条中筛选海外相关新闻，补充海外市场动态。

    Returns:
        (markdown_list_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_info_global_cls()
        overseas_kw = [
            "美股", "美元", "美联储", "原油", "黄金", "英伟达", "NVIDIA",
            "AMD", "英特尔", "美光", "特斯拉", "苹果", "OpenAI",
            "欧洲", "日本", "韩国", "台积电", "安森美", "美伊",
            "伊朗", "战争", "原油", "北约", "API", "全球",
        ]
        matches = []
        for _, r in df.iterrows():
            text = str(r.get("标题", "")) + str(r.get("内容", ""))
            if any(kw in text for kw in overseas_kw):
                title = r.get("标题", "")
                if title and title not in matches:
                    matches.append(f"- 🌍 {title}")
        if matches:
            return "\n".join(matches[:8]), None  # 最多8条
        return "*当日财联社头条中未发现海外相关新闻*", None
    except Exception as e:
        return None, f"海外头条筛选失败: {e}"
