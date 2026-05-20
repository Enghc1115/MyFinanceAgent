"""
northbound.py — 北向资金数据

通过 East Money 数据中心获取北向资金日度成交额。
"""

import time as _time


def fetch_northbound_deal_amt(target_date_str: str) -> tuple:
    """通过 East Money 数据中心获取北向资金日度成交额。

    包含重试逻辑（最多 3 次），对字段访问做 .get() 容错保护，
    全部字段为 0 时返回"数据暂未更新"提示。

    Returns:
        (markdown_table_or_None, error_str_or_None)
    """
    last_error = None
    for attempt in range(3):
        try:
            import requests as _req
            if attempt > 0:
                _time.sleep(2)

            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_MUTUAL_DEALAMT",
                "columns": "TRADE_DATE,NF_DEAL_AMT,SSC_DEAL_AMT,ST_DEAL_AMT",
                "filter": f"(TRADE_DATE='{target_date_str}')",
                "pageNumber": "1",
                "pageSize": "5",
                "source": "WEB",
                "client": "WEB",
            }
            r = _req.get(
                url,
                params=params,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            data = r.json()
            rows = (data.get("result") or {}).get("data", [])
            if not rows:
                return None, f"未找到 {target_date_str} 北向资金数据"

            rec = rows[0]
            # 字段访问保护：.get() 默认 0，再用 or 0 防 None
            nf_raw = rec.get("NF_DEAL_AMT", 0) or 0
            ssc_raw = rec.get("SSC_DEAL_AMT", 0) or 0
            st_raw = rec.get("ST_DEAL_AMT", 0) or 0
            # 单位: 百万元 → 亿元 (/100)
            nf = nf_raw / 100
            ssc = ssc_raw / 100
            st = st_raw / 100

            # 全部为 0 说明数据未更新
            if nf == 0 and ssc == 0 and st == 0:
                return None, "北向资金当日数据暂未更新"

            lines = [
                "| 通道 | 成交额(亿) |",
                "|------|-----------|",
                f"| 沪股通 | {ssc:.2f} |",
                f"| 深股通 | {st:.2f} |",
                f"| 北向合计 | {nf:.2f} |",
            ]
            return "\n".join(lines), None
        except Exception as e:
            last_error = e

    return None, f"北向资金获取失败: {last_error}"
