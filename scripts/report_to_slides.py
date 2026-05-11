#!/usr/bin/env python3
"""report_to_slides.py — 将日度 Markdown 报告转换为 HTML 幻灯片"""

import sys
import re
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SLIDES_DIR = PROJECT_ROOT / "reports" / "slides"

HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #1a1a2e; }}
  .slide {{ max-width: 1000px; margin: 20px auto; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
  .slide h2 {{ font-size: 1.5em; color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 8px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f9fa; font-weight: 600; }}
  tr:hover {{ background: #f0f0f0; }}
  .up {{ color: #e74c3c; }}
  .down {{ color: #27ae60; }}
  .summary {{ line-height: 1.8; font-size: 1.05em; }}
  .tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: .85em; }}
  .tag-up {{ background: #ffe0e0; color: #c0392b; }}
  .tag-down {{ background: #d4edda; color: #155724; }}
</style>
</head>
<body>
<div class="container">
"""

FOOTER = """</div></body></html>"""


def parse_markdown(text: str):
    """Split markdown into sections by ## headings."""
    sections = []
    lines = text.split("\n")
    current_title = ""
    current_body = []
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
    """Convert markdown table to HTML table."""
    if not md_text or "|" not in md_text:
        return md_text or ""
    lines = md_text.strip().split("\n")
    html = "<table>"
    for line in lines:
        line = line.strip()
        if not line or line.startswith("|--"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        tag = "th" if html == "<table>" else "td"
        html += "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
    html += "</table>"
    return html


def replace_special(text: str) -> str:
    """Replace markdown list items and highlight numbers."""
    text = re.sub(r"^- (.+)", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Wrap list items in ul
    text = re.sub(r"(<li>.*</li>\n?)+", r"<ul>\g<0></ul>", text)
    return text


def build_slide(title: str, body: str) -> str:
    """Build a single slide HTML."""
    # Determine color class from title
    cls = ""
    if any(k in title for k in ["涨幅", "上涨", "多头", "流入"]):
        cls = " up"
    elif any(k in title for k in ["跌幅", "下跌", "空头", "流出"]):
        cls = " down"

    body_html = md_table_to_html(body)
    body_html = replace_special(body_html)
    # Wrap non-table/list content in paragraph
    if not body_html.startswith("<table") and not body_html.startswith("<ul>"):
        body_html = f'<div class="summary{cls}">{body_html.replace(chr(10), "<br>")}</div>'

    return f'<div class="slide"><h2>{title}</h2>{body_html}</div>'


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    md_path = REPORTS_DIR / f"{target_date}.md"
    if not md_path.exists():
        print(f"[错误] 未找到报告: {md_path}")
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    sections = parse_markdown(md_text)

    title = f"A 股市场日报 — {target_date}"
    slides = "".join(build_slide(t, b) for t, b in sections if b)

    html = HEADER.format(title=title) + slides + FOOTER

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SLIDES_DIR / f"{target_date}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"幻灯片已保存: {out_path}")


if __name__ == "__main__":
    main()
