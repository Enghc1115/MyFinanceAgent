"""
top_gainers.py — 涨跌榜

获取 A 股全市场涨幅 TOP 10 和跌幅 TOP 10。
数据源使用东方财富 stock_zh_a_spot_em()，稳定性优于 stock_zh_a_spot()。
"""

import akshare as ak
import time
import os
import glob


def _clear_akshare_cache():
    """清除 akshare 缓存目录，解决 API 返回 HTML 而非 JSON 的问题。"""
    cache_dir = "/tmp/.akshare/"
    if os.path.exists(cache_dir):
        for f in glob.glob(os.path.join(cache_dir, "*")):
            try:
                os.remove(f)
            except Exception:
                pass


def _map_sector(code: str) -> str:
    """根据股票代码前缀映射板块归属（简单规则）。"""
    if not code:
        return "未知"
    prefix = str(code)[:3]
    if prefix in ("600", "601", "603", "605"):
        return "上海主板"
    elif prefix in ("000", "001", "002", "003"):
        return "深圳主板"
    elif prefix in ("300", "301"):
        return "创业板"
    elif prefix == "688":
        return "科创板"
    elif prefix in ("430", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839",
                    "870", "871", "872", "873"):
        return "北交所"
    else:
        return "其他"


def _build_table(df, top_n: int = 10) -> str:
    """从 DataFrame 构建 Markdown 表格。

    Args:
        df: 已排序的个股数据 DataFrame
        top_n: 取前 N 条

    Returns:
        Markdown 表格字符串
    """
    df = df.head(top_n)
    lines = [
        "| 代码 | 名称 | 最新价 | 涨跌幅 | 板块 |",
        "|------|------|--------|--------|------|",
    ]
    for _, r in df.iterrows():
        code = r.get("代码", "")
        name = r.get("名称", "")
        price = r.get("最新价", 0)
        change = r.get("涨跌幅", 0)
        sector = _map_sector(str(code))
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        lines.append(f"| {code} | {name} | {price:.2f} | {change_str} | {sector} |")
    return "\n".join(lines)


def _fetch_spot_df() -> tuple:
    """获取全市场个股行情 DataFrame。

    主数据源：stock_zh_a_spot_em()（东方财富）。
    重试策略：首次尝试 → 清缓存重试一次（共 2 次）。

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
            if df is None or len(df) == 0:
                raise ValueError("API 返回空数据")
            return df, None
        except Exception as e:
            last_error = e
    return None, f"涨跌榜数据获取失败: {last_error}"


def fetch_top_gainers() -> tuple:
    """获取 A 股涨幅榜 Top 10。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    df, error = _fetch_spot_df()
    if error:
        return None, error

    try:
        df = df.sort_values("涨跌幅", ascending=False, na_position="last")
        return _build_table(df, top_n=10), None
    except Exception as e:
        return None, f"涨幅榜构建失败: {e}"


def fetch_top_losers() -> tuple:
    """获取 A 股跌幅榜 Top 10。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    df, error = _fetch_spot_df()
    if error:
        return None, error

    try:
        df = df.sort_values("涨跌幅", ascending=True, na_position="last")
        return _build_table(df, top_n=10), None
    except Exception as e:
        return None, f"跌幅榜构建失败: {e}"
