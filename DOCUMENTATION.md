# MyFinanceAgent 使用文档

## 项目结构

```
MyFinanceAgent/
├── scripts/
│   ├── __init__.py           # 包标记
│   ├── config.py             # 共享配置（DATA_DIR / REPORTS_DIR / INDICES_CONFIG）
│   ├── get_market_data.py    # A 股实时行情抓取 → CSV + sector 快照
│   └── generate_report.py    # 日度报告生成 → Markdown
├── data/
│   ├── {date}.csv            # 行情快照（按日期）
│   └── sector_flow/          # 板块资金流向快照（异动分析用）
├── reports/                  # 日度简报输出目录（{date}.md）
├── logs/                     # crontab 日志
├── CLAUDE.md                 # 项目规范与功能模块说明
├── DOCUMENTATION.md          # 本文件
├── NOTES.md                  # 环境配置注意事项
├── README.md                 # 项目简介
├── requirements.txt          # Python 依赖
├── run_daily.sh              # 定时调度脚本（早晚收盘三时段）
└── .gitignore                # Git 忽略规则
```

## 环境要求

- Python 3.12（通过 Homebrew 安装，路径见 NOTES.md）
- 虚拟环境 `.venv/`（已配置好所有依赖）

## 运行脚本

### 抓取实时行情

```bash
# 仅打印
.venv/bin/python scripts/get_market_data.py

# 收盘 + 保存 CSV + 板块快照
.venv/bin/python scripts/get_market_data.py --mode close --save
```

输出内容：
- **五大指数**：上证/深证/创业板/科创50/北证50
- **涨跌家数比**：上涨 / 下跌 / 平盘
- **总成交额**：沪深京全市场成交总额（亿元）
- **涨幅分布**：涨停/大涨/小涨/小跌/大跌/跌停
- **平均涨幅 & 涨幅中位数**

### 生成日度简报

```bash
.venv/bin/python scripts/generate_report.py --date 2026-05-08
.venv/bin/python scripts/generate_report.py   # 默认今天
```

报告包含以下章节：
- **大盘指数** — 五大指数收盘价及涨跌幅
- **宏观市场** — 美股三大指数（SPY/QQQ/DIA）+ USD/CNY 汇率——仅限于早盘报告
- **市场概况** — 涨跌家数、成交额、涨幅分布、环比前一交易日
- **板块资金流向** — TOP5 板块 + 龙头个股及涨跌幅
- **异动监测** — 对比历史快照，检测主力资金方向变化（⚠️ 净流入→净流出 / ↑ 净流出→净流入）
- **北向资金** — 沪股通/深股通日度成交额（East Money 数据中心）
- **涨幅榜** — A 股涨幅 TOP10
- **今日头条** — 财联社早间头条
- **总结** — 基于数据的自动解读——调用金融分析相关的skill

### 定时调度（crontab）

三个时段，仅工作日执行：

```bash
./run_daily.sh morning   # 早盘 10:00，仅打印
./run_daily.sh noon      # 午盘 11:30，打印 + 保存 CSV + 板块快照
./run_daily.sh close     # 收盘 15:15，打印 + 保存 + 生成日度简报
```

`run_daily.sh` 自动检测周末和节假日（非交易日自动跳过）。

## 数据存储规范

| 项目 | 规范 |
|------|------|
| 行情快照 | `data/{date}.csv`（CSV, UTF-8，追加模式） |
| 板块快照 | `data/sector_flow/{date}_{mode}.csv`（mode: morning/noon/close） |
| 日度简报 | `reports/{date}.md`（Markdown） |
| 同步方式 | `git push` 至 GitHub |
| 大文件 | 单文件超过 50MB 需改用 Git LFS |

## 功能模块

详见 `CLAUDE.md` → `## Feature Modules`，包含：

- **资金监控** — 板块主力净流入 TOP5 + 龙头个股
- **个股资金流入监测** — 全市场个股净流入 TOP10 + 板块龙头个股资金追踪
- **资金延续性监测** — 板块净流入 vs 龙头个股净流入的背离检测
- **异动分析** — 对比早盘/午盘/收盘板块快照，标记资金方向反转

## 获取帮助

如遇到 Python 环境或依赖问题，先查阅 `NOTES.md`；如为 AkShare 接口报错，优先清除缓存重试：

```bash
rm -rf /tmp/.akshare/
```
