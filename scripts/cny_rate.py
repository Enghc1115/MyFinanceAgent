"""
cny_rate.py — 人民币汇率

获取在岸/离岸人民币兑美元汇率。
"""

import akshare as ak

def fetch_cny_rate(target_date_str: str) -> tuple:
    """获取 USD/CNY 人民币汇率。

    Returns:
        (info_str_or_None, error_str_or_None)
    """
    try:
        from datetime import date
        target = date.fromisoformat(target_date_str)
        df = ak.currency_boc_safe()
        row = df[df["日期"] == target]
        if row.empty:
            latest = df["日期"].iloc[-1]
            return None, f"未找到 {target_date_str} 汇率数据，最新可用: {latest}"
        rate = float(row["美元"].iloc[0]) / 100
        return f"USD/CNY: {rate:.4f}", None
    except Exception as e:
        return None, f"汇率获取失败: {e}"

