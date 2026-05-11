# CLAUDE.md

## Project Overview

**MyFinanceAgent** — 专业的金融分析 Agent 团队，负责 A 股与港股的早盘、午盘、收盘分析。

- 每日定时抓取 A 股和港股数据
- 分析板块资金流向、异动个股及市场情绪
- 生成日度简报 + 深度复盘报告
- 本地 CSV 数据通过 Git 同步至 GitHub 云端

## Tech Stack

- 语言：Python 3.10+
- 数据源：AkShare（开源金融数据库）、新浪财经（指数 API）、东方财富数据中心（北向资金）
- 关键库：pandas, requests

## Data Sources

| 数据类型 | 接口 | 说明 |
|---------|------|------|
| 五大指数（上证/深证/创业板/科创50/北证50） | Sina API `hq.sinajs.cn` | `fetch_indices()` |
| 全 A 行情（涨跌分布、成交额） | `ak.stock_zh_a_spot()` | 含代码/名称/最新价/涨跌幅/成交额 |
| 板块资金流向 | `ak.stock_fund_flow_industry("即时")` | 含行业/净额/领涨股/领涨股-涨跌幅 |
| 个股资金流入 | `ak.stock_fund_flow_individual("即时")` | 含代码/名称/净额 |
| 北向资金成交额 | East Money `datacenter-web.eastmoney.com` | `RPT_MUTUAL_DEALAMT`，百万元转亿元 |
| 美股三大指数 | `ak.stock_us_daily("SPY" / "QQQ" / "DIA")` | SPY / QQQ / DIA |
| 人民币汇率 | `ak.currency_boc_safe()` | 中国银行牌价，美元/人民币 |
| 财联社头条 | `ak.stock_info_global_cls()` | 全球财经资讯 |

## Scripts

- 获取数据：`.venv/bin/python scripts/get_market_data.py [--mode morning|noon|close] [--save]`
- 生成简报：`.venv/bin/python scripts/generate_report.py [--date YYYY-MM-DD]`
- 定时调度：`./run_daily.sh {morning|noon|close}`（配合 crontab：工作日 10:00 / 11:30 / 15:15）

## Data Convention

- CSV 数据文件统一存放在 `data/` 目录下
- 简报统一以 Markdown 格式保存在 `reports/` 目录下
- 数据通过 `git push` 同步到 GitHub，保持本地与云端一致
- 单文件超过 50MB 需改用 Git LFS

## Report Specification

每份简报必须包含以下内容：

- 涨跌家数比
- 成交量变化（环比前一交易日）
- 主力资金流入前五板块（含龙头个股及涨跌幅）
- 资金流向分析须区分**北向资金**与**主力净流入**
- **海外市场消息**：美股三大指数走势 + 海外龙头催化事件（英伟达/AMD/OpenAI/特斯拉/苹果等）及 A 股映射方向
- **市场活跃度**：涨停密度、上涨占比、涨跌强度比等综合指标，判定活跃度等级

## Feature Modules

### 资金监控

- 在主力净流入前五板块中，展示该板块的**龙头个股**（资金流入最多且涨幅最高）
- 数据来源：`ak.stock_fund_flow_industry("即时")`

### 个股资金流入监测

- 获取全市场个股资金净流入 TOP10
- 提取板块龙头个股（领涨股）的个股资金流入情况
- 数据来源：`ak.stock_fund_flow_individual("即时")`，字段含 `"净额"`（格式如 `"19.43亿"`，需转为数值排序）

### 资金延续性监测

- 对比板块主力净流入 vs 板块内龙头个股的资金净流入，检测**资金背离**
  - 板块净流入大但龙头个股净流入小 → 资金分散，无明确龙头
  - 板块净流入大且龙头个股净流入大 → 资金集中，龙头确立
- 数据来源：板块级 `ak.stock_fund_flow_industry("即时")` + 个股级 `ak.stock_fund_flow_individual("即时")`

### 异动分析

监测时间点与触发模式：

| 时段 | 时间 | 对应 mode |
|------|------|-----------|
| 早盘 | 10:00 | `morning` |
| 午盘 | 11:30 | `noon` |
| 收盘 | 15:15 | `close` |

监测内容：
- 对比前后两个时间点的主力资金方向变化
- **⚠️ 由净流入转为净流出** — 重点标记
- **↑ 由净流出转为净流入** — 可能为向上拐点，重点标记
- 板块级别和个股级别均需覆盖

数据存储：每次抓取时保存板块资金流向快照至 `data/sector_flow/{date}_{mode}.csv`

## Available Subagents

### deep-analysis

**职责**：收盘后，基于已有数据 + 互联网搜索，独立产出整篇深度复盘报告。

**定位**：一个聚合 agent，覆盖情绪分析、主线识别、资金深度、机会风险、明日观察等全部模块。不拆成多个小 agent。

**输入**：
- `data/{date}.csv` — 全 A 行情快照
- `data/sector_flow/{date}_close.csv` — 板块资金流向
- `ak.stock_fund_flow_individual("即时")` — 个股资金净流入 TOP
- `ak.stock_fund_flow_industry("即时")` — 板块资金流向
- `ak.stock_zt_pool_em(date='YYYYMMDD')` — 涨停股池（含连板数、炸板次数、封板时间）
- `ak.stock_zt_pool_dtgc_em(date='YYYYMMDD')` — 跌停股池
- `ak.stock_zt_pool_previous_em(date='YYYYMMDD')` — 昨日涨停股
- `ak.stock_zh_a_spot()` — 全 A 实时行情（当日涨停/跌停/涨幅分布）
- WebSearch — 补充催化事件、外盘、新闻解读

**输出**：`reports/deep/{date}.md` + `reports/slides/deep-{date}.html`

**后处理**：
1. Markdown 报告生成后，调用 `frontend-slides` 技能转换为 HTML 演示文稿，保存在 `reports/slides/deep-{date}.html`
2. 读取行情数据中的涨跌幅、板块信息、波动率，调用 `a-share-color-psychologist` 技能对 HTML 进行情绪驱动配色：
   - 根据指数涨跌幅判定市场状态（亢奋/温和上涨/观望/温和下跌/恐惧）
   - 按板块归属叠加对应配色描边（科技蓝、消费金、医药青等）
   - 根据波动率调整毛玻璃模糊度
   - 重写 `frontend-slides` 的 CSS 变量层，不修改 HTML 结构和 JS 逻辑

**产出结构（8 模块）**：

| 模块 | 说明 |
|------|------|
| 新闻解读 | 事件 + 强度 + 影响分析，关联盘面。**必须包含海外龙头催化事件**（英伟达/AMD/OpenAI/特斯拉/苹果等）及其对 A 股映射方向 |
| 指数全景 | 量价/支撑压力/YTD/资金流向/外盘关联 |
| 主线分析 | 识别 2-5 条主线，催化→板块→个股链条 |
| 重点个股 | 市场地位/资金面/技术面/行业逻辑 |
| 资金深度 | 净流入 TOP10 + 主线归属 + 量价配合判断 |
| 情绪分析 | 涨停/跌停/连板/炸板率/情绪周期 |
| 机会与风险 | 各 3 条，带评级 + 逻辑 |
| 明日观察 | 优先级表 + 关键观察指标 |

**行为要求**：
1. 每条判断标注数据来源或逻辑链，不凭空断言
2. 主线分析必须回答"今天市场在炒什么"
3. 机会与风险必须包含可验证的观察指标
4. 专业、简洁、有判断的输出风格
5. **情绪分析必须提取连板/炸板数据**：调用 `ak.stock_zt_pool_em(date)` 获取涨停池 → 统计连板数分布、最高连板、炸板次数、行业分布。计算指标包括：炸板率（炸板次数/涨停家数）、连板晋级率（2连板+/涨停家数）、连板高度
6. **海外催化事件必须搜索**：对每个疑似受外盘驱动的板块，必须通过 WebSearch 搜索对应的海外龙头动态。搜索关键词模板：
   - 算力/AI 板块 → 搜索 "NVIDIA AI factory deal May 2026" "AMD earnings data center" "OpenAI Anthropic funding"
   - 消费电子 → 搜索 "Apple supply chain May 2026" "TSMC AI chip orders"
   - 商业航天 → 搜索 "SpaceX launch May 2026" "Rocket Lab earnings"
   - 半导体 → 搜索 "Micron TSMC semiconductor May 2026" "US chip export control"
   要求：每个海外催化事件必须附带可点击的超链接来源

**分析框架 — 双重逻辑链交叉验证**

分析时须同时运用两条逻辑链，并在报告中呈现两者的交集与背离：

**逻辑链 A（自下而上 — 资金驱动）**
```
主力资金建仓 → 形成强势板块 → 强势板块中筛选强势个股 → 
事件催化放大关注度 → 市场共识形成 → 资金持续流入 → 主线确立
```
- 数据源：板块资金流向 + 个股资金流入 + 量价关系
- 适用场景：识别当前正在发生的行情，判断主线性价比和延续性

**逻辑链 B（自上而下 — 政策/产业驱动）**
```
十五五规划 → 国产替代/自主可控 → 对美科技映射/跟随 → 
AI革命下的新经济逻辑 → 产业政策落地 → 业绩验证 → 板块轮动
```
- 数据源：政策文件 (NDRC/工信部)、产业新闻、全球科技趋势
- 适用场景：判断中长期产业趋势，识别处于早期阶段的潜力主线

**交叉验证规则**：
- 链 A 和链 B 指向同一方向 → 主线确定性强，可重点分析
- 链 A 强但链 B 弱 → 短期资金炒作，警惕快速退潮
- 链 B 强但链 A 弱 → 政策/产业已布局但资金未确认，可能处于布局窗口期
- 两者方向相反 → 存在认知偏差，需更高确定性才参与

**催化信息要求**：
- 每个催化事件必须附带可点击的超链接（来源 URL）
- 优先采用权威来源：官方政策文件、交易所公告、头部财经媒体
- 标注信息来源（如：国家航天局官网 / 工信部 / 21世纪经济报道 / 证券时报）

## Available Skills

### frontend-slides

创建动画丰富的 HTML 演示文稿，适用于投屏汇报或展示分析结果。

- 触发方式：`/frontend-slides` 或描述需要制作演示文稿的需求
- 来源：`zarazhangrui/frontend-slides@frontend-slides`
- 安装位置：`.agents/skills/frontend-slides/`

#### 自动触发规则

每次运行项目生成日度简报（`generate_report.py`）后，**自动调用此 skill** 将当日 Markdown 报告转换为 HTML 演示文稿，保存在 `reports/slides/{date}.html`。

> **回退规则**：若当天（`date.today()`）无数据或为非交易日，自动回退到 `data/` 目录下最新的 CSV 文件对应的日期，为该最近交易日生成报告和 slides。

转换要求：
- 读取 `reports/{date}.md` 作为演示内容
- 一页 slide 对应一个主要章节（大盘指数、宏观市场、市场概况、板块资金流向、异动监测、北向资金、涨幅榜、总结）

### china-stock-analysis

A 股价值投资分析工具，提供股票筛选、财务深度分析、行业对比、估值建模四大模块。

- 触发方式：描述需要分析某只个股的基本面或估值时自动触发
- 来源：`sugarforever/01coder-agent-skills@china-stock-analysis`（12.3K 安装）
- 安装位置：`.agents/skills/china-stock-analysis/`
- 参考用途：deep-analysis 中个股深度分析时，调用此 skill 获取基本面数据

### sector-rotation-detector

板块轮动检测，基于宏观指标研判 A 股行业轮动机会（6-12 个月维度）。

- 触发方式：需要分析宏观周期与板块配置时自动触发
- 来源：`yuping322/finskills@sector-rotation-detector`（20 安装）
- 安装位置：`.agents/skills/sector-rotation-detector/`
- 核心框架：五大宏观支柱（货币/通胀/增长/就业/政策）→ 周期定位 → 行业信号
- 参考用途：deep-analysis 中逻辑链 B（政策/产业驱动）的分析依据

### a-share-color-psychologist

A股情绪美学配色师。根据行情数据自动生成符合"红涨绿跌"直觉且具备 Apple 级高级感的 HTML 皮肤。

- 触发方式：被 `deep-analysis` agent 在后处理阶段调用，为 HTML 演示文稿注入情绪驱动配色
- 覆盖机制：重写 `frontend-slides` 的 CSS 变量层，不修改 HTML 结构和 JS 逻辑
- 安装位置：`.agents/skills/a-share-color-psychologist/`
- 参考用途：与 `frontend-slides` 配合使用，前端展示 + 情绪配色
- 调用方：`deep-analysis`（后处理第 2 步）

### munger-perspective

查理·芒格的思维框架与表达方式。基于《穷查理宝典》、伯克希尔股东会等 50+ 来源蒸馏。
提炼 5 个核心心智模型、8 条决策启发式，用于审视投资决策中的认知偏误和逆向思考。

- 触发方式：需要逆向思考、认知偏误检查、跨学科分析时自动触发
- 来源：`alchaincyf/munger-skill`（GitHub）
- 安装位置：`.agents/skills/munger-perspective/`
- 参考用途：deep-analysis 中机会/风险评估时，调用此 skill 审视逻辑是否有认知偏误
- 数据表格保留，关键数据（涨跌幅、资金净额）用色阶标注
- 设计风格偏向专业金融简报（深色或白底简洁风）

## Rules

- 遇到 AkShare API 报错时，优先尝试清除缓存并重试：`rm -rf /tmp/.akshare/`
- East Money API 被网络层拦截（`push2.eastmoney.com` 域名 blocked）时，改用新浪 Sina API 或 East Money datacenter-web 作为回退

## Output Convention

任何 agent 生成的笔记/报告类内容，必须：
1. 同时输出 `.md` 和 `.html` 两种格式
2. `.html` 文件用 Chrome 打开
