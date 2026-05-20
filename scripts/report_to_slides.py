#!/usr/bin/env python3
"""report_to_slides.py — 将日度 Markdown 报告转换为 HTML 幻灯片

根据当日行情数据动态判定市场情绪，应用「A股情绪美学配色师」规范：
- 上涨(+0.5%以上) → 极光红 (Aurora Red)
- 下跌(-0.5%以下) → 深林绿 (Forest Green)
- 观望(-0.5%~+0.5%) → 禅意灰 (Zen Gray)
板块卡片根据类别叠加 Cyber Blue / Classic Gold / Teal Clean 描边。
"""

import sys
import re
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SLIDES_DIR = PROJECT_ROOT / "reports" / "slides"

# ---------------------------------------------------------------------------
# 板块关键词 → 描边色映射
# ---------------------------------------------------------------------------
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "半导体", "芯片", "AI", "人工智能", "电子", "计算机", "软件",
        "通信", "5G", "光模块", "算力", "机器人", "智能", "数据",
        "云计算", "互联网", "电池", "光伏", "面板", "航天",
    ],
    "consumer": [
        "白酒", "消费", "食品", "饮料", "家电", "汽车", "旅游",
        "零售", "免税", "化妆品", "医美",
    ],
    "medical": [
        "医药", "医疗", "生物", "基因", "疫苗", "中药", "化学制药",
        "医疗器械", "创新药",
    ],
}

SECTOR_BORDER_COLORS = {
    "tech": "rgba(0, 212, 255, 0.55)",       # Cyber Blue
    "consumer": "rgba(212, 165, 116, 0.55)",  # Classic Gold
    "medical": "rgba(94, 163, 163, 0.55)",    # Teal Clean
}


def extract_avg_change(md_text: str) -> float:
    """从报告中提取平均涨幅，返回浮点数；找不到时返回 0.0。"""
    m = re.search(r"\*\*平均涨幅\*\*[：:]\s*([+-]?[\d.]+)%", md_text)
    if not m:
        m = re.search(r"平均涨幅[：:]\s*([+-]?[\d.]+)%", md_text)
    if m:
        return float(m.group(1))
    return 0.0


def determine_mood(avg_change: float) -> str:
    """根据平均涨幅判定市场情绪。"""
    if avg_change > 0.5:
        return "bullish"
    if avg_change < -0.5:
        return "bearish"
    return "neutral"


def classify_sector(name: str) -> str:
    """根据板块名称匹配到 tech / consumer / medical / other。"""
    for category, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return category
    return "other"


def parse_markdown(text: str) -> list[tuple[str, str]]:
    """按 ## 标题拆分 sections。"""
    sections: list[tuple[str, str]] = []
    lines = text.split("\n")
    current_title = ""
    current_body: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            if current_title:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = m.group(1).strip()
            current_body = []
        else:
            current_body.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_body).strip()))
    return sections


def md_table_to_html(md_text: str) -> str:
    """Markdown 表格 → HTML 表格。"""
    if not md_text or "|" not in md_text:
        return md_text or ""
    lines = md_text.strip().split("\n")
    html = "<table>"
    for line in lines:
        line = line.strip()
        if not line or re.match(r"^\|[-:\s|]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        tag = "th" if html == "<table>" else "td"
        html += "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
    html += "</table>"
    return html


def replace_special(text: str) -> str:
    """列表项 & 加粗替换。"""
    text = re.sub(r"^- (.+)", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(<li>.*</li>\n?)+", r"<ul>\g<0></ul>", text)
    return text


def build_slide(title: str, body: str, mood: str) -> str:
    """生成一张幻灯片 HTML。板块标题自动加行业描边 class。"""
    cls = ""
    if any(k in title for k in ["涨幅", "上涨", "多头", "流入", "TOP"]):
        cls = " up"
    elif any(k in title for k in ["跌幅", "下跌", "空头", "流出"]):
        cls = " down"

    body_html = md_table_to_html(body)
    body_html = replace_special(body_html)
    if not body_html.startswith("<table") and not body_html.startswith("<ul>"):
        body_html = f'<div class="summary{cls}">{body_html.replace(chr(10), "<br>")}</div>'

    # 板块资金流向：为每个板块行加描边 class
    if "板块资金流向" in title:
        body_html = _inject_sector_borders(body_html)

    return f'<div class="slide section-enter"><h2>{title}</h2>{body_html}</div>'


def _inject_sector_borders(html: str) -> str:
    """在板块表格中，为 <tr> 注入对应行业描边 class。"""
    # 匹配 <tr><td>板块名</td>... 的行
    def _replace_tr(m: re.Match) -> str:
        row = m.group(0)
        # 提取第一个 td 内容
        td_m = re.search(r"<td>(.+?)</td>", row)
        if not td_m:
            return row
        sector_name = td_m.group(1)
        cat = classify_sector(sector_name)
        if cat == "other":
            return row
        # 替换 <tr> 为 <tr class="sector-xxx">
        return row.replace("<tr>", f'<tr class="sector-{cat}">', 1)

    # 匹配每个表格行（跳过表头行 <th>）
    html = re.sub(r"<tr><td>.+?</td>.+?</tr>", _replace_tr, html)
    return html


# ---------------------------------------------------------------------------
# 动态 CSS 生成
# ---------------------------------------------------------------------------
MOOD_PALETTES = {
    "bullish": {
        "main_color": "#e74c3c",
        "accent": "#c0392b",
        "bg_gradient": "linear-gradient(160deg, #1c0d0d 0%, #2a1518 45%, #1c0d0d 100%)",
        "slide_bg": "#fefaf9",
        "slide_border": "rgba(231, 76, 60, 0.12)",
        "h2_border": "#e74c3c",
        "up_color": "#e74c3c",
        "tag_up_bg": "#fde8e8",
        "tag_up_text": "#c0392b",
        "glass": "rgba(255, 245, 245, 0.72)",
        "table_header_bg": "#fef5f5",
    },
    "bearish": {
        "main_color": "#27ae60",
        "accent": "#1e8449",
        "bg_gradient": "linear-gradient(160deg, #0d1c0d 0%, #152a18 45%, #0d1c0d 100%)",
        "slide_bg": "#f9fefa",
        "slide_border": "rgba(39, 174, 96, 0.12)",
        "h2_border": "#27ae60",
        "up_color": "#e74c3c",
        "tag_up_bg": "#d4edda",
        "tag_up_text": "#155724",
        "glass": "rgba(245, 255, 245, 0.72)",
        "table_header_bg": "#f5fef5",
    },
    "neutral": {
        "main_color": "#8e8e93",
        "accent": "#636366",
        "bg_gradient": "linear-gradient(160deg, #1c1c1e 0%, #2c2c2e 45%, #1c1c1e 100%)",
        "slide_bg": "#fafafa",
        "slide_border": "rgba(142, 142, 147, 0.12)",
        "h2_border": "#8e8e93",
        "up_color": "#e74c3c",
        "tag_up_bg": "#f0f0f0",
        "tag_up_text": "#636366",
        "glass": "rgba(250, 250, 250, 0.72)",
        "table_header_bg": "#f8f8f8",
    },
}


def build_css(mood: str) -> str:
    """根据市场情绪动态生成 CSS。"""
    p = MOOD_PALETTES[mood]

    return f"""    :root {{
      --market-main-color: {p["main_color"]};
      --market-accent: {p["accent"]};
      --market-bg-gradient: {p["bg_gradient"]};
      --slide-bg: {p["slide_bg"]};
      --slide-border: {p["slide_border"]};
      --h2-border: {p["h2_border"]};
      --up-color: {p["up_color"]};
      --tag-up-bg: {p["tag_up_bg"]};
      --tag-up-text: {p["tag_up_text"]};

      --apple-glass: {p["glass"]};
      --apple-radius: 28px;
      --apple-font: -apple-system, "PingFang SC", "SF Pro Display", sans-serif;
      --page-transition: 0.8s cubic-bezier(0.25, 1, 0.5, 1);

      --sector-tech: rgba(0, 212, 255, 0.55);
      --sector-consumer: rgba(212, 165, 116, 0.55);
      --sector-medical: rgba(94, 163, 163, 0.55);

      --table-header-bg: {p["table_header_bg"]};
    }}"""


# ---------------------------------------------------------------------------
# HTML 模板
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

{css_variables}

  body {{
    font-family: var(--apple-font);
    background: var(--market-bg-gradient);
    color: #1c1c1e;
    min-height: 100vh;
    letter-spacing: 0.02em;
    -webkit-font-smoothing: antialiased;
  }}

  .container {{
    max-width: 1000px;
    margin: 0 auto;
    padding: 60px 24px 80px;
  }}

  /* ---- 幻灯片卡片 ---- */
  .slide {{
    background: var(--apple-glass);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--apple-radius);
    border: 1px solid var(--slide-border);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.06),
                0 2px 8px rgba(0, 0, 0, 0.04);
    padding: 40px 44px;
    margin-bottom: 32px;
    transition: box-shadow 0.3s ease;
  }}

  .slide:hover {{
    box-shadow: 0 14px 48px rgba(0, 0, 0, 0.09),
                0 4px 12px rgba(0, 0, 0, 0.05);
  }}

  .slide h2 {{
    font-size: 1.4em;
    font-weight: 650;
    color: #1c1c1e;
    border-bottom: 2px solid var(--h2-border);
    padding-bottom: 10px;
    margin-bottom: 24px;
    letter-spacing: 0.03em;
  }}

  /* ---- 板块卡片描边 ---- */
  tr.sector-tech td:first-child {{
    border-left: 3px solid var(--sector-tech);
    padding-left: 14px;
  }}
  tr.sector-consumer td:first-child {{
    border-left: 3px solid var(--sector-consumer);
    padding-left: 14px;
  }}
  tr.sector-medical td:first-child {{
    border-left: 3px solid var(--sector-medical);
    padding-left: 14px;
  }}

  /* ---- 通用表格 ---- */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px;
    font-size: 0.95em;
  }}

  th, td {{
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }}

  th {{
    background: var(--table-header-bg);
    font-weight: 600;
    color: #555;
    font-size: 0.88em;
    text-transform: none;
    letter-spacing: 0.03em;
  }}

  tr:hover td {{
    background: rgba(0, 0, 0, 0.025);
  }}

  /* ---- 涨跌色（A 股文化：红涨绿跌） ---- */
  .up {{ color: var(--up-color); }}
  .down {{ color: #27ae60; }}

  .tag-up {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 14px;
    font-size: 0.85em;
    font-weight: 500;
    background: var(--tag-up-bg);
    color: var(--tag-up-text);
  }}

  .tag-down {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 14px;
    font-size: 0.85em;
    font-weight: 500;
    background: #e8f5e9;
    color: #2e7d32;
  }}

  /* ---- 摘要文本 ---- */
  .summary {{
    line-height: 1.9;
    font-size: 1.02em;
    color: #333;
  }}

  .summary li {{
    margin: 4px 0 4px 20px;
  }}

  .summary ul {{
    margin: 8px 0;
  }}

  .summary strong {{
    color: #1c1c1e;
  }}

  /* ---- 引用块 ---- */
  blockquote {{
    border-left: 3px solid var(--market-main-color);
    padding: 10px 18px;
    margin: 12px 0;
    background: var(--table-header-bg);
    border-radius: 0 12px 12px 0;
    color: #666;
    font-size: 0.92em;
    line-height: 1.7;
  }}

  /* ---- 进入动画 ---- */
  .section-enter {{
    opacity: 0;
    transform: translateY(36px);
    transition: opacity var(--page-transition),
                transform var(--page-transition);
  }}

  .section-enter.visible {{
    opacity: 1;
    transform: translateY(0);
  }}

  /* ---- 情绪标签 ---- */
  .mood-badge {{
    display: inline-block;
    padding: 6px 18px;
    border-radius: 20px;
    font-size: 0.82em;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-bottom: 32px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #fff;
    background: var(--market-main-color);
  }}

  /* ---- 响应式 ---- */
  @media (max-width: 768px) {{
    .container {{ padding: 32px 12px 48px; }}
    .slide {{ padding: 28px 20px; border-radius: 22px; }}
    table {{ font-size: 0.8em; }}
    th, td {{ padding: 6px 8px; }}
  }}
</style>
</head>
<body>
<div class="container">
<div class="mood-badge">{mood_label}</div>
{slides}
</div>
<script>
(function() {{
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        entry.target.classList.add('visible');
      }}
    }});
  }}, {{ threshold: 0.15, rootMargin: '0px 0px -40px 0px' }});

  document.querySelectorAll('.section-enter').forEach(el => observer.observe(el));
}})();
</script>
</body>
</html>"""


def generate_html(md_text: str, target_date: str, avg_change: float, mood: str) -> str:
    """组装完整 HTML 页面。"""
    sections = parse_markdown(md_text)
    title = f"A 股市场日报 — {target_date}"

    # 情绪标签
    mood_labels = {
        "bullish": f"行情偏强  +{avg_change:.2f}%",
        "bearish": f"行情偏弱  {avg_change:.2f}%",
        "neutral": f"窄幅波动  {avg_change:+.2f}%",
    }
    mood_label = mood_labels[mood]

    # CSS 变量
    css_vars = build_css(mood)

    # 幻灯片
    slides = "".join(build_slide(t, b, mood) for t, b in sections if b.strip())

    return HTML_TEMPLATE.format(
        title=title,
        css_variables=css_vars,
        mood_label=mood_label,
        slides=slides,
    )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main() -> None:
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    md_path = REPORTS_DIR / f"{target_date}.md"

    if not md_path.exists():
        print(f"[错误] 未找到报告: {md_path}")
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")

    avg_change = extract_avg_change(md_text)
    mood = determine_mood(avg_change)

    html = generate_html(md_text, target_date, avg_change, mood)

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SLIDES_DIR / f"{target_date}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"幻灯片已保存: {out_path}")
    print(f"  市场情绪: {mood} (平均涨幅 {avg_change:+.2f}%)")


if __name__ == "__main__":
    main()
