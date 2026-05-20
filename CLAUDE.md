# CLAUDE.md

## Project Overview

**MyFinanceAgent** — 专业的金融分析 Agent 团队，负责 A 股与港股的早盘、午盘、收盘分析。

- 每日定时抓取 A 股和港股数据
- 分析板块资金流向、异动个股及市场情绪
- 生成周度/阶段性行情回顾报告
- 本地 CSV 数据通过 Git 同步至 GitHub 云端

## Tech Stack

- 语言：Python 3.10+
- 数据源：AkShare（开源金融数据库）
- 关键库：pandas, matplotlib, requests

## Scripts

- 获取数据：`python scripts/get_market_data.py`
- 生成简报：`python scripts/generate_report.py`

## Data Convention

- CSV 数据文件统一存放在 `data/` 目录下
- 简报统一以 Markdown 格式保存在 `reports/` 目录下
- 数据通过 `git push` 同步到 GitHub，保持本地与云端一致
- 单文件超过 50MB 需改用 Git LFS

## Report Specification

每份简报必须包含以下内容：

- 涨跌家数比
- 成交量变化（环比前一交易日）
- 主力资金流入前五板块
- 资金流向分析须区分**北向资金**与**主力净流入**

## Rules

- 遇到 API 报错时，优先尝试清除缓存并重试
