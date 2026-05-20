# MyFinanceAgent 全局需求规格文档

> 版本: v1.1
> 最后更新: 2026-05-20
> 适用范围: A 股市场分析（港股待后续扩展）

## 本次更新 (v1.1)

- TdxClaw AI 级深度分析从"待实现"升级为**必须实现**
- 美股映射重构为「个股 15-20 只 + 板块 ETF 10 个」双层结构
- 北向资金维持现状（成交额即可，不要求净买入）
- `requirements.txt` 版本锁定: `akshare==1.18.60 pandas==3.0.2 requests==2.33.1`
- 新增 CSV 归档策略: 每月 1 日自动归档上月数据至 `data/archive/YYYY-MM/`
- 附录事项全部更新，仅剩 #4（港股时间表）待定

---

## 一、项目概述

**MyFinanceAgent** 是一个自动化 A 股市场数据分析系统，每日定时抓取行情数据，生成结构化的 Markdown 日度简报，并通过 Git 同步至 GitHub 云端。

核心价值: 将分散的 A 股行情数据聚合为一份结构化的日报，覆盖大盘指数、资金流向、涨跌榜、驱动新闻、市场活跃度等维度，为个人投资者提供每日市场全景。

### 1.1 设计原则

- **数据驱动**: 所有结论必须基于可验证的量化数据，不含主观臆断
- **容错优先**: 任一数据源获取失败不阻塞整体流程，仅标记"[跳过] 原因"
- **可复现**: CSV 数据按日期归档，报告基于归档数据生成，可追溯
- **最低依赖**: 仅依赖 AkShare 开源数据 + requests，无需商业 API Key
- **纯脚本化**: 不依赖数据库、消息队列、Web 服务，纯 Python 脚本 + crontab 调度

---

## 二、目标质量等级

### 2.1 当前阶段: 基础日报（已实现）

生成包含以下章节的日度 Markdown 简报（详见第六章）。

### 2.2 TdxClaw AI 级别深度分析（必须实现）

对标专业级 A 股分析报告，以下深度分析模块为当前开发目标，必须全部实现:

| 模块 | 内容要求 |
|------|---------|
| **指数全景 + 成交额判断** | 五大指数量价配合分析，成交额与前一交易日 / 5日均量对比，判断放量/缩量方向 |
| **涨停跌停全景 + 连板梯队** | 涨停池按连板数分层（首板/2连板/3连板/4+连板），跌停原因归类（业绩暴雷/行业利空/资金出逃） |
| **主线结构分析（2-3条）** | 每条主线包含: 领涨个股 + 驱动逻辑 + 细分方向 + 持续性判断 |
| **主力资金 TOP10 + 方向归类** | 个股净流入 TOP10，按板块/行业归类，标注资金偏好方向 |
| **市场情绪** | 市场周期阶段判断（冰点→修复→高潮→分化）、赚钱效应评分、炸板率 |
| **机会与风险** | 各3条，分"短线机会"/"中线布局"级别标注 |
| **核心判断** | 200字内，一句话概括当日市场本质 |

> 此目标对应 Memory 中记录的 Claude Code 技能: `china-stock-analysis`、`sector-rotation-detector`、`munger-perspective`。当前代码中 `prep_deep_data.py` 已开始收集深度分析所需的涨停池/跌停池/个股资金流数据，为升级做数据准备。

---

## 三、系统架构

### 3.1 项目目录结构

```
MyFinanceAgent/
├── scripts/                    # 所有 Python 脚本
│   ├── __init__.py             # 包标记
│   ├── config.py               # 共享配置（路径、指数列表）
│   ├── get_market_data.py      # A 股实时行情抓取（主入口）
│   ├── generate_report.py      # 日度报告生成（主入口）
│   ├── core_utils.py           # 核心工具: CSV 读取、环比计算、报告组装
│   ├── sector_flow.py          # 板块资金流向 + 异动检测
│   ├── northbound.py           # 北向资金（东方财富数据中心）
│   ├── us_market.py            # 美股三大指数 + 龙头催化 + 海外头条
│   ├── cny_rate.py             # 人民币汇率
│   ├── headlines.py            # 多源新闻聚合 + 实体提取 + 股价联动
│   ├── top_gainers.py          # 涨跌榜 TOP10
│   ├── market_activity.py      # 市场活跃度评估
│   ├── individual_flow.py      # 个股资金流入 TOP10
│   ├── prep_deep_data.py       # 深度分析数据准备（收盘后收集涨停池等）
│   └── report_to_slides.py     # 报告转 HTML 幻灯片
├── data/                       # 数据存档
│   ├── {YYYY-MM-DD}.csv        # 日频行情快照（追加模式，可分多时段）
│   ├── sector_flow/            # 板块资金流向快照（{date}_{mode}.csv）
│   └── deep/                   # 深度分析 JSON 数据
├── reports/                    # 输出报告
│   ├── {YYYY-MM-DD}.md         # 日度简报
│   ├── deep/                   # 深度分析报告
│   └── slides/                 # HTML 幻灯片
├── logs/                       # crontab 日志
├── .venv/                      # Python 虚拟环境（Python 3.12 + 项目依赖）
├── run_daily.sh                # 定时调度入口（morning/noon/close 三时段）
├── .gitignore
├── requirements.txt            # Python 依赖
├── NOTES.md                    # 环境配置笔记（Python 路径、依赖版本）
├── DOCUMENTATION.md            # 使用文档
├── CLAUDE.md                   # 项目规范（供 Claude Code 读取）
├── REQUIREMENTS.md             # 本文件 — 全局需求规格
└── README.md
```

### 3.2 数据流

```
AkShare API ──→ get_market_data.py ──→ data/{date}.csv
                 (抓取行情)              (行情快照)

AkShare API ──→ get_market_data.py ──→ data/sector_flow/{date}_{mode}.csv
                 (--save 模式)          (板块资金流向快照)

data/{date}.csv ──→ generate_report.py ──→ reports/{date}.md
AkShare API ──→ (板块/北向/美股/汇率/新闻/涨跌榜) ──→ 同上
                 (报告各子模块实时抓取)

收盘后:
get_market_data.py ──→ prep_deep_data.py ──→ data/deep/{date}.json
```

### 3.3 模块职责矩阵

| 模块 | 职责 | 数据源 | 容错策略 |
|------|------|--------|---------|
| `get_market_data.py` | 大盘指数、涨跌家数、成交额、涨幅分布 | Sina API + AkShare `stock_zh_a_spot()` | 异常退出并报错 |
| `sector_flow.py` | 板块主力资金净流入 TOP5 + 资金方向异动 | AkShare `stock_fund_flow_industry()` | 跳过该章节 |
| `northbound.py` | 北向资金（沪股通/深股通成交额） | East Money 数据中心 REST API | 跳过，含重试3次 |
| `us_market.py` | 美股三大指数 + 核心个股映射(15-20只) + 板块映射 + 海外头条 | AkShare `stock_us_daily()` / `stock_info_global_cls()` | 跳过该章节 |
| `cny_rate.py` | 人民币兑美元汇率 | AkShare `currency_boc_safe()` | 跳过该章节 |
| `headlines.py` | 多源新闻聚合 + 实体提取 + 股价联动评分 | AkShare 财联社头条 | 跳过该章节 |
| `top_gainers.py` | A 股涨跌榜 TOP10（含板块归属） | AkShare `stock_zh_a_spot_em()` | 跳过，含缓存清除重试 |
| `market_activity.py` | 市场活跃度评估（基于已有数据计算） | 同上（纯计算） | 跳过该章节 |
| `individual_flow.py` | 全市场个股资金净流入 TOP10 | AkShare `stock_fund_flow_individual()` | 跳过该章节 |
| `prep_deep_data.py` | 收盘后收集深度分析所需数据（涨停池/跌停池/板块/个股流） | 多 AkShare 接口 | 单项失败不影响其他 |
| `report_to_slides.py` | 将 Markdown 报告转为情绪配色 HTML 幻灯片 | `reports/{date}.md` | 独立脚本，失败不影响报告 |

---

## 四、功能需求

### 4.1 行情数据抓取 (get_market_data.py)

#### 4.1.1 输入
- `--mode`: `morning` | `noon` | `close` | `default`（默认 `default`）
- `--save`: 是否保存到 CSV（默认仅打印）

#### 4.1.2 输出

**终端打印（所有模式）**:
```
A 股{时段}市场概况  {日期}  {时间}
==========================================
  上涨  {N}  下跌  {N}  平盘  {N}
  总数  {N}
  涨跌比           {N}
  总成交额         {N} 亿元

涨幅分布:
  涨停 (>=9.9%)      {N}
  大涨 (5%~9.9%)    {N}
  小涨 (0%~5%)      {N}
  小跌 (-5%~0%)     {N}
  大跌 (-5%以下)     {N}
  跌停 (<=-9.9%)    {N}

  平均涨幅          {N}%
  涨幅中位数        {N}%

指数表现:
  上证指数  {price}  {change}%
  深证成指  {price}  {change}%
  创业板指  {price}  {change}%
  科创50   {price}  {change}%
  北证50   {price}  {change}%
==========================================
```

**CSV 保存（--save 模式）**:

文件: `data/{YYYY-MM-DD}.csv`

列: `time, mode, total, up, down, flat, ratio, total_amount, limit_up, big_up, small_up, small_down, big_down, limit_down, avg_change, median_change, sh_price, sh_change, sh_change_abs, sz_price, sz_change, sz_change_abs, cyb_price, cyb_change, cyb_change_abs, kc50_price, kc50_change, kc50_change_abs, bj50_price, bj50_change, bj50_change_abs`

规则:
- 追加模式写入（同一文件可存多个时段快照）
- 若列结构变更，自动迁移旧数据并重建文件
- 编码 UTF-8

**板块资金流向快照（--save 模式）**:

文件: `data/sector_flow/{date}_{mode}.csv`

内容: AkShare `stock_fund_flow_industry("即时")` 全量导出，附加 `timestamp` 列

#### 4.1.3 数据源
- **大盘指数**: Sina Finance API (`hq.sinajs.cn/list=...`)，Referer 必须为 `https://finance.sina.com.cn`
- **全市场个股**: AkShare `stock_zh_a_spot()`（全量 A 股行情）
- **板块资金流向**: AkShare `stock_fund_flow_industry("即时")`

#### 4.1.4 错误处理
- 整体异常 → stderr 报错 + exit(1)
- 板块快照失败 → 仅打印警告，不影响主流程

### 4.2 日度简报生成 (generate_report.py)

#### 4.2.1 输入
- `--date YYYY-MM-DD`（默认今天）
- `--csv /path/to/file.csv`（默认 `data/{date}.csv`）

#### 4.2.2 输出

文件: `reports/{YYYY-MM-DD}.md`

报告章节（详见第六章 报告规格）。

#### 4.2.3 数据获取顺序

1. 读取 CSV 行情快照
2. 板块资金流向（含异动检测）
3. 北向资金
4. 美股行情
5. 人民币汇率
6. 美股板块映射
7. 多源驱动新闻
8. 涨幅榜 TOP10
9. 跌幅榜 TOP10
10. 环比前一交易日计算
11. 海外头条
12. 市场活跃度
13. 个股资金流入 TOP10
14. 美股核心个股映射
15. 生成总结 + 组装报告

### 4.3 深度数据准备 (prep_deep_data.py)

收盘后运行，收集用于深度分析的完整数据集。

#### 4.3.1 收集内容
1. 板块资金流向（全量）
2. 个股资金流入（全量）
3. 涨停池（`stock_zt_pool_em`）
4. 跌停池（`stock_zt_pool_dtgc_em`）
5. 全 A 行情快照（`stock_zh_a_spot_em`）

#### 4.3.2 输出
文件: `data/deep/{date}.json`

结构:
```json
{
  "date": "YYYY-MM-DD",
  "collected_at": "ISO timestamp",
  "sections": {
    "sector_flow": [...],
    "individual_flow": [...],
    "limit_up_pool": [...],
    "limit_down_pool": [...],
    "a_spot": [...]
  }
}
```

### 4.4 报告转幻灯片 (report_to_slides.py)

将日度 Markdown 报告转为情绪配色的 HTML 幻灯片。

#### 4.4.1 情绪配色规则
- 上证涨幅 > +0.5% → 极光红 (Aurora Red)
- 上证涨幅 < -0.5% → 深林绿 (Forest Green)
- -0.5% ≤ 涨幅 ≤ +0.5% → 禅意灰 (Zen Gray)

#### 4.4.2 板块卡片描边
- 科技类（半导体/芯片/AI/电子/5G/光模块/机器人 → Cyber Blue）
- 消费类（白酒/消费/食品/汽车/旅游 → Classic Gold）
- 医药类（医药/医疗/生物/基因 → Teal Clean）

### 4.5 定时调度 (run_daily.sh)

三时段自动执行，仅交易日触发。

| 时段 | 时间 | 操作 |
|------|------|------|
| morning | 10:00 | 仅打印行情（不保存） |
| noon | 11:30 | 打印 + 保存 CSV + 板块快照 |
| close | 15:15 | 打印 + 保存 CSV + 板块快照 + 生成日度简报 |

#### 4.5.1 交易日检测
1. 检查是否周末（`date +%u >= 6`）→ 跳过
2. 通过 Sina API (`sh000001`) 获取市场日期，与今日对比
3. API 失败时放行（让后续抓取自行报错）

#### 4.5.2 Cron 配置
```cron
# 早盘
0 10 * * 1-5 cd /path/to/MyFinanceAgent && ./run_daily.sh morning >> logs/morning.log 2>&1
# 午盘
30 11 * * 1-5 cd /path/to/MyFinanceAgent && ./run_daily.sh noon >> logs/noon.log 2>&1
# 收盘
15 15 * * 1-5 cd /path/to/MyFinanceAgent && ./run_daily.sh close >> logs/close.log 2>&1
```

---

## 五、子模块功能详述

### 5.1 板块资金流向 (sector_flow.py)

#### fetch_industry_flow_with_anomalies(target_date_str)
- 获取当日板块资金净流入 TOP5
- 每行含: 板块名称、净额(亿)、龙头个股、龙头涨跌幅
- 对比当日历史快照检测资金方向异动:
  - ⚠️ 净流入→净流出: 标记为风险信号
  - ↑ 净流出→净流入: 标记为反转信号
- 对比基准: 取当日已保存的最新时段快照（morning < noon < close）

### 5.2 北向资金 (northbound.py)

#### fetch_northbound_deal_amt(target_date_str)
- 数据源: East Money 数据中心 REST API
- 获取: 沪股通成交额、深股通成交额、北向合计成交额
- 单位转换: 百万元 → 亿元（除以 100）
- 全 0 数据视为"当日数据暂未更新"
- 重试策略: 最多3次，间隔2秒

### 5.3 美股市场 (us_market.py)

**设计原则**: 采用「个股 + 板块」双层映射结构，既追踪核心美股对 A 股的个股级别传导，也通过板块 ETF 把握行业级联动。

#### fetch_us_market(target_date_str)
- 获取美股三大指数 SPY/QQQ/DIA 最新交易日行情
- 计算隔夜涨跌幅 + 方向标记（🟢/🔴/⚪）
- 附带 A 股整体映射提示

#### fetch_us_sector_map()
按美股板块涨跌映射到对应 A 股板块，使用板块 ETF 作为代理:

| 美股板块 ETF | 映射 A 股方向 | 关系 |
|-------------|-------------|------|
| SMH (半导体) | 半导体/芯片/光刻机 | 全球半导体产业链联动 |
| QQQ (科技) | AI/软件/云计算/互联网 | 科技风险偏好传导 |
| XLE (能源) | 石油/煤炭/天然气 | 全球能源价格联动 |
| XLV (医疗) | 医药/医疗/生物 | 创新药/器械估值锚定 |
| XLY (消费) | 白酒/消费/汽车/家电 | 消费信心传导 |
| XLF (金融) | 银行/保险/券商 | 利率预期传导 |
| TAN (新能源) | 光伏/锂电/储能/风电 | 全球新能源景气度 |
| XBI (生物科技) | CXO/创新药/基因 | 生物科技投融资风向 |
| GDX (黄金矿业) | 贵金属/有色/黄金 | 避险情绪 + 金价联动 |
| KWEB (中概互联) | 港股科技/A 股映射 | 中概股估值锚定 |

每行输出: 板块名称、ETF 涨跌幅、方向标记、A 股映射判断（利好/利空/中性 + 一句话逻辑）

#### fetch_us_core_stocks(target_date_str)
获取核心美股行情，每只个股标注对应 A 股映射方向。覆盖范围 15-20 只，分三类:

**科技半导体链**:
| 美股 | A 股映射方向 |
|------|------------|
| NVDA (英伟达) | AI 算力/光模块/液冷/PCB |
| AMD | CPU 链/服务器/封测 |
| AVGO (博通) | 网络芯片/ASIC/交换机 |
| TSM (台积电) | 晶圆代工/先进封装 |
| ASML | 光刻机/设备/材料 |
| MU (美光) | 存储/HBM |

**消费科技链**:
| 美股 | A 股映射方向 |
|------|------------|
| AAPL (苹果) | 消费电子/果链/精密制造 |
| TSLA (特斯拉) | 智能驾驶/机器人/汽零 |
| AMZN (亚马逊) | 云计算/跨境电商/物流 |

**中概 & 映射敏感**:
| 美股 | A 股映射方向 |
|------|------------|
| BABA (阿里巴巴) | 互联网平台/云计算/港股情绪 |
| PDD (拼多多) | 电商/消费降级/出海 |
| JD (京东) | 物流/供应链/消费 |
| BIDU (百度) | AI/自动驾驶/大模型 |
| NIO (蔚来) | 新能源车/锂电池/汽零 |
| LI (理想) | 增程/豪华车/新势力 |

#### fetch_overseas_headlines()
- 从财联社全球头条中筛选海外相关新闻
- 关键词匹配: 美股/美元/美联储/CPI/非农/原油/黄金/英伟达/AMD/特斯拉/台积电/中概/欧洲/日本/地缘等
- 最多返回 8 条

### 5.4 涨跌榜 (top_gainers.py)

#### fetch_top_gainers()
- 获取 A 股涨幅 TOP10
- 每行含: 代码、名称、最新价、涨跌幅、板块归属
- 板块归属根据代码前缀推断: 600→上海主板 / 000→深圳主板 / 300→创业板 / 688→科创板 / 43/83/87→北交所

#### fetch_top_losers()
- 获取 A 股跌幅 TOP10
- 结构同上

### 5.5 市场活跃度 (market_activity.py)

#### fetch_market_activity(stats)
基于已有行情数据计算:

| 指标 | 计算方式 | 说明 |
|------|---------|------|
| 总成交额 | 直接读取 | 资金参与规模 |
| 涨跌比 | up/down | 多头/空头力量对比 |
| 上涨占比 | up/total × 100% | 市场宽度 |
| 涨停密度 | limit_up/total × 100% | 追涨意愿 |
| 涨跌强度比 | (up+limit_up)/(down+limit_down) | 多空极端值对比 |

综合判定:
- ratio ≥ 2 且涨停密度 ≥ 2% → 🔥🔥 非常活跃
- ratio ≥ 1.5 且涨停密度 ≥ 1% → 🔥 活跃
- ratio ≥ 1 → ⚪ 一般
- ratio < 0.8 → ❄️ 低迷

### 5.6 个股资金流入 (individual_flow.py)

#### fetch_individual_flow()
- 获取全市场个股资金净流入 TOP10
- 每行含: 排名、代码、名称、最新价、涨跌幅、净流入
- 金额解析: 支持"亿"/"万"单位自动转换

### 5.7 驱动新闻 (headlines.py)

#### fetch_driven_news()
- 从多源财经数据聚合新闻
- 实体提取: 从新闻文本中识别 A 股公司简称（内置 100+ 常见龙头/热门股关键词）
- 股价联动评分: 将识别到的公司与其当日涨跌幅关联
- 输出: 驱动新闻表格（新闻标题 + 关联个股 + 涨跌幅）

### 5.8 总结生成 (core_utils.py)

#### generate_summary(stats, ...)
基于行情数据自动生成 2-3 句市场概括:
1. 大盘强弱判断（基于涨跌比 + 平均涨幅）
2. 指数分化判断（基于五大指数涨跌幅极差 > 1.5%）
3. 数据异常备注（各数据源失败原因附后）

---

## 六、报告规格

### 6.1 当前日度简报（已实现）

```markdown
# A 股市场日报 — YYYY-MM-DD

## 大盘指数
| 指数 | 收盘价 | 涨跌幅 |
|------|--------|--------|
| 上证指数 | {price} | {change}% |
| ...（共五大指数）

## 宏观市场
|| 指数 | 收盘价 | 涨跌幅 | 方向 |
||------|--------|--------|------|
|| S&P 500(SPY) | ... | ... | 🟢/🔴 |
|| Dow Jones(DIA) | ... | ... | 🟢/🔴 |
|| Nasdaq(QQQ) | ... | ... | 🟢/🔴 |

> A 股整体映射提示

USD/CNY: {rate}

### 美股板块映射
|| 板块 ETF | 涨跌幅 | 方向 | A 股映射判断 |
||---------|--------|------|-------------|
|| SMH 半导体 | ... | 🟢 | 利好芯片/光刻机: 理由 |
|| ...（共10个板块 ETF） |

### 核心个股映射（15-20只）
|| 类别 | 美股 | 涨跌幅 | 方向 | A 股映射 |
||------|------|--------|------|----------|
|| 科技半导体 | NVDA | ... | 🟢 | AI 算力/光模块/液冷 |
|| ... | ... | ... | ... | ... |
|| 消费科技 | AAPL | ... | 🔴 | 消费电子/果链 |
|| ... | ... | ... | ... | ... |
|| 中概 | BABA | ... | ... | 互联网平台/港股情绪 |
|| ... | ... | ... | ... | ... |

## 海外头条
- 🌍 {海外新闻标题列表}

## 市场活跃度
| 指标 | 数值 | 说明 |
|------|------|------|
| 总成交额 | ... | 资金参与规模 |
| ...（共6项指标含综合判定）

## 市场概况
- 上涨家数 / 下跌家数 / 平盘
- 涨跌比
- 总成交额（亿元）
- 环比前一交易日变化

### 涨幅分布
| 区间 | 家数 |
|------|------|
| 涨停 | {n} |
| ...（共6个区间）

- 平均涨幅 / 涨幅中位数

## 板块资金流向
| 板块 | 净额(亿) | 龙头个股 | 龙头涨跌幅 |
|------|----------|----------|------------|
| ...（TOP5）

### 异动监测（有异常时显示）
| 板块 | 方向变化 | 前净额 | 现净额 |

## 个股资金流入 TOP10
| 排名 | 代码 | 名称 | 最新价 | 涨跌幅 | 净流入 |

## 北向资金
| 通道 | 成交额(亿) |
|------|-----------|
| 沪股通 | ... |
| 深股通 | ... |
| 北向合计 | ... |

## 涨幅榜
| 代码 | 名称 | 最新价 | 涨跌幅 | 板块 |
| ...（TOP10）

## 跌幅榜
| 代码 | 名称 | 最新价 | 涨跌幅 | 板块 |
| ...（TOP10）

## 今日驱动新闻
| 新闻标题 | 关联个股 | 涨跌幅 |

## 总结
{2-3句自动总结 + 数据异常备注}
```

### 6.2 深度报告（必须实现）

> 基于 `prep_deep_data.py` 收集的全量数据进行深度分析，达到 TdxClaw AI 级别报告标准:

```markdown
# A 股深度分析 — YYYY-MM-DD（周X）

## 一、新闻解读
| 事件 | 强度 | 影响分析 |
（每条新闻标注 🔴强/🟢一般/🟡弱 影响级别 + 判断依据）

## 二、指数全景
### 五大指数表现（含成交额环比）
### 指数结构分析（领涨/领跌指数原因）
### 外盘影响（美股隔夜 + A股映射判断）
### 行情类型判断（普涨/分化/震荡/调整）

## 三、涨停跌停全景
### 涨停梯队
| 连板数 | 个股列表 | 所属主线 |
### 跌停分析
| 个股 | 跌停原因归类 |

## 四、主线结构分析（2-3条）
每条主线:
- 领涨个股（龙头 + 跟风）
- 驱动逻辑（政策/事件/资金/业绩）
- 细分方向
- 持续性判断

## 五、主力资金 TOP10 + 方向归类
| 排名 | 代码 | 名称 | 净流入(亿) | 所属方向 |

## 六、市场情绪
- 周期阶段: 冰点/修复/高潮/分化
- 赚钱效应: 涨停家数 / 炸板率 / 昨日涨停今日表现
- 恐慌指数: 跌停家数 / 跌幅>5%家数

## 七、机会与风险
### 机会（分短线/中线级别，各3条）
### 风险（分短线/中线级别，各3条）

## 八、核心判断（≤200字）
```

---

## 七、环境与依赖

### 7.1 运行环境

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS（已验证 15.x） |
| Python | 3.12（通过 Homebrew 安装，路径 `/usr/local/opt/python@3.12/bin/python3.12`） |
| 虚拟环境 | `.venv/`（基于 Python 3.12 创建） |
| 系统 Python | 3.9（macOS 自带，不可升级/替换） |

### 7.2 Python 依赖

| 库 | 版本（2026-05-09） | 用途 |
|----|-------------------|------|
| akshare | 1.18.60 | A 股/美股/汇率等金融数据获取 |
| pandas | 3.0.2 | CSV 数据处理与分析 |
| requests | 2.33.1 | HTTP API 调用（Sina / East Money） |

完整 `requirements.txt`（版本锁定）:
```
akshare==1.18.60
pandas==3.0.2
requests==2.33.1
```

### 7.3 API 报错处理

AkShare 缓存问题优先处理:
```bash
rm -rf /tmp/.akshare/
```

---

## 八、数据规范

### 8.1 数据存储

| 数据类型 | 路径 | 格式 | 编码 | 写入模式 |
|---------|------|------|------|---------|
| 行情快照 | `data/{YYYY-MM-DD}.csv` | CSV | UTF-8 | 追加 |
| 板块快照 | `data/sector_flow/{date}_{mode}.csv` | CSV | UTF-8-SIG | 覆写 |
| 深度数据 | `data/deep/{date}.json` | JSON | UTF-8 | 覆写 |
| 日度简报 | `reports/{YYYY-MM-DD}.md` | Markdown | UTF-8 | 覆写 |
| 深度报告 | `reports/deep/{YYYY-MM-DD}.md` | Markdown | UTF-8 | 覆写 |

### 8.2 CSV 定期归档

**规则**: 每月 1 日自动将上月的 CSV 行情快照和板块快照迁移到归档目录。

- 源路径: `data/{上月}-*.csv`、`data/sector_flow/{上月}-*.csv`
- 目标路径: `data/archive/{YYYY-MM}/`（按月分目录）
- 归档后原位置文件删除
- 当月数据保留在 `data/` 根目录供快速访问
- 归档为本地操作，不影响 Git 仓库（`data/archive/` 加入 `.gitignore`）

**实现方式**: 在 `run_daily.sh` close 时段末尾、或独立 cron 任务（每月 1 日 00:05）中执行。

### 8.3 Git 同步
- 通过 `git push` 同步至 GitHub: `https://github.com/Enghc1115/MyFinanceAgent.git`
- 单文件超过 50MB 需改用 Git LFS

### 8.3 日期格式
- 统一使用 `YYYY-MM-DD`（ISO 8601 日期格式）
- CSV 文件名与日期严格对应

---

## 九、代码规范

### 9.1 Python 脚本执行
- 必须使用虚拟环境: `.venv/bin/python {script}.py`
- 禁止使用系统 Python 3.9（缺少 akshare 依赖）
- 项目根目录需在 `sys.path` 中以保证模块导入正常

### 9.2 错误处理约定
- 数据源获取失败 → 返回 `(None, "错误描述")` tuple
- 报告生成时 → 用 `*数据获取失败*` 替代缺失章节
- 整体异常 → stderr 输出 + `sys.exit(1)`

### 9.3 编码约定
- 所有文件 UTF-8 编码
- 中文内容不做转义
- Markdown 表格使用标准 GFM 格式

---

## 十、扩展规划

### 10.1 港股支持（待定）
- 需新增港股数据源（AkShare 港股接口）
- 需新增恒生指数/恒生科技指数监控
- 需新增南向资金数据
- 需考虑港股与 A 股的联动分析

### 10.2 Agent 协作工作流（当前）
- **Claude Code**: 执行具体任务（修复数据源、生成报告、质检）
- **Hermes Agent**: 监督验收（决定发送/删除报告、管理 crontab 定时任务）
- 质量门禁: gaps ≤ 2 → 发送, gaps > 2 → 删除

### 10.3 已安装的 Claude Code 技能
- `china-stock-analysis` — A 股深度分析
- `frontend-slides` — 前端幻灯片生成
- `munger-perspective` — 芒格视角分析
- `sector-rotation-detector` — 板块轮动检测

---

## 附录 A: 待确认/待补充事项

| # | 事项 | 状态 |
|---|------|------|
| 1 | `requirements.txt` 版本锁定 — 已锁定为 `akshare==1.18.60 pandas==3.0.2 requests==2.33.1` | ✅ 已确认 |
| 2 | 报告中北向资金仅有成交额、无净买入额 — 维持现状，成交额即可 | ✅ 已确认 |
| 3 | CLAUDE.md 提到 matplotlib 但代码未使用 — 确认为历史遗留，已移除 | ✅ |
| 4 | 港股支持时间表 | 待定 |
| 5 | 深度报告自动生成（基于 prep_deep_data.py 输出） | 必须实现 |
| 6 | CSV 归档策略 — 每月 1 日自动归档上月数据至 `data/archive/YYYY-MM/`，详见 8.2 节 | ✅ 已确认 |
| 7 | 美股映射从个股5只扩展为「个股15-20只 + 板块ETF 10个」双层结构 | ✅ 已确认 |
