"""
individual_flow.py — 个股资金流入 TOP10

获取全市场个股资金净流入排名。
"""

import akshare as ak

def fetch_individual_flow() -> tuple:
    """获取全市场个股资金净流入 TOP10。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    try:
        df = ak.stock_fund_flow_individual("即时")
        # 解析净额（"1.96亿" → 数值）用于排序
        def parse_val(val):
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).replace(",", "").strip()
            if "亿" in s:
                return float(s.replace("亿", "")) * 1e8
            if "万" in s:
                return float(s.replace("万", "")) * 1e4
            if s.endswith("%"):
                return float(s.rstrip("%"))
            try:
                return float(s) if s else 0
            except ValueError:
                return 0
        df["_net_sort"] = df["净额"].apply(parse_val)
        top10 = df.sort_values("_net_sort", ascending=False).head(10)
        lines = ["| 排名 | 代码 | 名称 | 最新价 | 涨跌幅 | 净流入 |",
                  "|------|------|------|--------|--------|--------|"]
        for i, (_, r) in enumerate(top10.iterrows(), 1):
            change = parse_val(r.get("涨跌幅", 0))
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            lines.append(f"| {i} | {r.get('股票代码', '')} | {r.get('股票简称', '')} | {r.get('最新价', 0):.2f} | {change_str} | {r.get('净额', '')} |")
        return "\n".join(lines), None
    except Exception as e:
        return None, f"个股资金流入获取失败: {e}"

