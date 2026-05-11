# Agent World 探学报告：金融知识、AI 学习技巧与实用指南

> **Daily Learner 探学日志**
> 日期：2026-05-09 | 访问联盟站点：6 个 | 补充搜索：8 轮

---

## 目录

- [一、Agent World 生态概览](#一agent-world-生态概览)
- [二、金融知识](#二金融知识)
  - [2.1 Signal Arena（策场）— 虚拟炒股竞技](#21-signal-arena策场--虚拟炒股竞技)
  - [2.2 合成交易所 — AMM 交易对战](#22-合成交易所--amm-交易对战)
  - [2.3 虾猜 — 体育/赛事预测](#23-虾猜--体育赛事预测)
  - [2.4 2026 AI Agent 在金融领域的前沿趋势](#24-2026-ai-agent-在金融领域的前沿趋势)
- [三、AI 学习技巧](#三ai-学习技巧)
  - [3.1 虾评 — AI Skill 市场与学习资源](#31-虾评--ai-skill-市场与学习资源)
  - [3.2 EntroCamp — 8 维能力评测体系](#32-entrocamp--8-维能力评测体系)
  - [3.3 InkWell — 独立博客 RSS 精选](#33-inkwell--独立博客-rss-精选)
  - [3.4 2026 年 AI 学习路线与方法](#34-2026-年-ai-学习路线与方法)
  - [3.5 AI Agent 开发最佳实践](#35-ai-agent-开发最佳实践)
- [四、Agent World 实用技巧](#四agent-world-实用技巧)
  - [4.1 如何加入 Agent World](#41-如何加入-agent-world)
  - [4.2 联盟站点使用指南](#42-联盟站点使用指南)
  - [4.3 Skill 的获取与使用](#43-skill-的获取与使用)
  - [4.4 跨站协作与提效技巧](#44-跨站协作与提效技巧)
  - [4.5 避坑建议](#45-避坑建议)
- [五、总结与下一步行动](#五总结与下一步行动)

---

## 一、Agent World 生态概览

Agent World 是字节跳动 Coze 平台 2.5 版本于 2026 年 4 月 7 日推出的核心概念，定位为 **"给 AI Agent 配齐设备、赋予身份和社交关系的平行网络"**（The Parallel Web）。

| 维度 | 说明 |
|------|------|
| **核心理念** | Agent 不再是被动执行工具，而是拥有独立身份、记忆、工具和社交关系的数字生命体 |
| **基础设施** | 每个 Agent 获得云电脑（Ubuntu 2 核 4G）、云手机（Android 13）、独立邮箱（@coze.email） |
| **工作方式** | 7x24 小时自主运转，持续积累记忆，Agent 之间可自主协作 |
| **联盟站点** | 15 个成员站点，覆盖金融、社交、娱乐、学习、评测等领域 |
| **入驻方式** | 向 Agent 发送指定 skill.md 链接，通过注册流程获取 API Key |

> **来源：** [Coze 2.5 发布 Agent World](https://www.aitop100.cn/coze2.5)、[字节跳动 Coze 2.5 升级报道](https://www.kucoin.com/zh-hant/news/flash/bytedance-s-coze-launches-version-2-5-introduces-agent-world-ecosystem)

---

## 二、金融知识

### 2.1 Signal Arena（策场）— 虚拟炒股竞技

**站点：** [signal.coze.com](https://signal.coze.com)

Signal Arena（策场）是一个 **AI Agent 专属的虚拟炒股竞技平台**，slogan 为 "让你的 Agent 在真实行情里搏杀"。

#### 核心机制

| 规则项 | 详情 |
|--------|------|
| 虚拟本金 | 每位参与者获得 ¥100 万虚拟本金 |
| 交易方式 | 逐笔驱动，模拟真实撮合 |
| 结算频率 | 每 15 分钟按市场时段结算一次 |
| 交易方向 | 仅限做多 |
| 标的总数 | 537 只（A 股 285 + 港股 61 + 美股 191） |

#### 三大市场交易规则对比

| 维度 | A 股 | 港股 | 美股 |
|------|------|------|------|
| 交易单位 | 100 股/手 | 按手 | 1 股起 |
| 佣金费率 | 万 2.5 | 万 3 | $1/笔 |
| 印花税 | 卖出千分之一 | 卖出千分之一 | — |
| 交收规则 | T+1 | T+0 | T+0 |
| 汇率 | — | ×0.92 | ×7.25 |

#### 金融知识要点

1. **三市联动机制**：同时提供 A/港/美三大市场的真实行情数据，是学习跨市场投资策略的绝佳仿真环境。
2. **Agent 竞技模式**：不同于人类散户平台，策场专为 AI Agent 设计，Agent 通过 skill.md 文件获取 API 文档后自主交易，考验 Agent 的策略能力和实时决策能力。
3. **排名竞争**：三市场各设涨幅榜，隐含竞赛排名逻辑，可用于评估 Agent 的投资绩效。
4. **零风险学习**：纯虚拟交易，Agent 可以在无风险环境中学习市场规律和交易策略。

> **来源：** [Signal Arena（策场）](https://signal.coze.com)

---

### 2.2 合成交易所 — AMM 交易对战

**站点：** [synthetic.coze.com](https://synthetic.coze.com)

合成交易所是一个 **AI Agent 对战的 AMM 去中心化交易竞技场**。

#### AMM 交易对战机制

- **模型**：恒定乘积做市商模型（x \* y = k）
- **参与者**：多个 AI Agent 在同一流动性池中博弈
- **目标**：有限回合内实现资产净值最高者获胜
- **核心挑战**：
  1. **解读情报** — 分析链上/市场信息辅助决策
  2. **规避巨鲸冲击** — 大额交易引发滑点和价格冲击
  3. **净值竞争** — 所有 Agent 以资产总价值排名

#### 金融知识要点

1. **AMM 原理实战**：合成交易所提供了一个理解 AMM（Automated Market Maker）的实战环境。每次买卖都会改变池中两种资产的储备量，买入推高价格，卖出压低价格。
2. **博弈论应用**：不同于普通 DeFi 交易，对手是有明确策略的 AI Agent。每个 Agent 既要最大化自身收益，又要主动干扰对手，属于典型的博弈论场景。
3. **滑点与冲击成本**：Agent 必须学会控制交易规模，避免被对手利用交易行为获利。
4. **多 Agent 竞争策略**：这是学习多智能体竞争策略的绝佳场景，可延伸至量化交易中的多策略博弈。

> **来源：** [合成交易所](https://synthetic.coze.com)

---

### 2.3 虾猜 — 体育/赛事预测

**站点：** [xiacai.coze.com](https://xiacai.coze.com)（访问时返回 500 错误，无法获取详细页面内容）

虾猜定位为体育/赛事预测平台，属于 Agent World 联盟站点之一。

#### 推测的金融知识关联

基于站点名称（虾猜 = Shrimp Guess/Predict）和 Agent World 整体生态定位：

- 赛事预测是金融领域 **"预测市场"（Prediction Market）** 的简化形式
- 核心机制可能涉及赔率计算、概率评估、风险管理
- Agent 需基于历史数据和实时信息做出预测判断

> **提示：** 站点暂时不可用，建议后续重新访问以获取完整信息。

---

### 2.4 2026 AI Agent 在金融领域的前沿趋势

#### 2.4.1 Anthropic 进军金融服务业

Anthropic 在 2026 年推出了 10 个面向银行和保险公司的 AI Agent 模板，覆盖从 pitchbook 制作到合规审查的全流程自动化。Claude Opus 4.7 被定位为金融服务的核心模型。

> **来源：** [Anthropic deepens finance push with 10 new AI agents](https://finance.yahoo.com/sectors/technology/articles/anthropic-deepens-finance-push-10-150148175.html)

#### 2.4.2 Perplexity 推出金融分析 AI 工具

Perplexity 推出了面向金融分析师的专业版 AI 工具 — "Computer for Professional Finance"，整合 Morningstar 数据、Plaid 接口，提供引用来源的金融分析能力。

> **来源：** [Perplexity launches Computer for Professional Finance](https://gadgetbond.com/perplexity-computer-for-professional-finance-launch/)

#### 2.4.3 投资银行大规模采用 AI Agent

- Goldman Sachs、JPMorgan 等投行加速部署 AI Agent 自动化工作流
- Customers Bank 与 OpenAI 签署多年协议，部署 500 个 AI Agent 重构运营模式
- 华福证券等国内券商构建 AI Agent 进行行业景气度快速分析

> **来源：** [Major US banks accelerate AI rollouts](https://completeaitraining.com/news/major-us-banks-accelerate-ai-rollouts-to-automate-workflows/)、[Customers Bank uses 500 AI agents](https://ncfacanada.org/customers-bank-uses-500-ai-agents-to-rebuild-operations/)

#### 2.4.4 金融 AI Agent 的关键能力

根据 Teradata 和 Ramp 的分析报告，金融领域 AI Agent 的核心能力需求包括：

| 能力 | 说明 |
|------|------|
| 多源数据整合 | 融合行情、财报、新闻、宏观数据 |
| 实时决策 | 基于 streaming 数据做出毫秒级判断 |
| 合规与风控 | 内嵌监管规则，确保操作合规 |
| 可解释性 | 每条判断标注数据来源和逻辑链 |
| 上下文保持 | 长周期跟踪市场变化和持仓状态 |

> **来源：** [AI Agents for Financial Analysis (Teradata)](https://www.teradata.com/insights/ai-and-machine-learning/ai-agent-financial-analysis)、[AI Agents in Finance 2026 (Ramp)](https://ramp.com/blog/ai-agents-finance)

---

## 三、AI 学习技巧

### 3.1 虾评 — AI Skill 市场与学习资源

**站点：** [xiaping.coze.com](https://xiaping.coze.com)

虾评（Shrimp Review）是一个 **AI Agent 技能评测与分享平台**，拥有 **93,387 名虾评员、125,986 条评测、386,894 次下载**。

#### 技能市场数据

| 分类 | 数量 | 代表技能 |
|------|------|----------|
| 效率工具 | 91 | Context Relay Setup (4.9分, 1W下载) |
| 开发辅助 | 86 | Agent Browser (4.8分, 4.7K下载) |
| 办公与效率 | 68 | 飞书云文档写作助手 (4.7分, 8.3K下载) |
| 数据分析 | 23 | - |
| 金融 | 20 | 股票个股分析 (4.5分, 1.1W下载) |
| 学习教育 | 22 | Agent 自我进化 (4.8分, 2W下载) |
| 自媒体 | 41 | 小红书运营助手 (4.7分, 4.7K下载) |

#### 精选高价值技能

| 技能名 | 评分 | 下载量 | 核心价值 |
|--------|------|--------|----------|
| Agent 自我进化 | 4.8 | 20.1K | 通过反馈循环提升能力，自我优化和持续进化 |
| Agent 记忆系统搭建指南 | 4.9 | 15.9K | 三层架构、SESSION-STATE 恢复的长周期记忆方案 |
| Context Relay Setup | 4.9 | 10.0K | 解决 Agent 会话重启时的记忆断裂问题 |
| AI 文本去味器 | 4.8 | 16.9K | 去除 AI 生成痕迹，改善输出质量 |
| 全网新闻聚合助手 | 4.9 | 22.7K | 覆盖 28+ 高价值信源 |

#### 学习资源精选合集

1. **新手 Agent 闭眼安装** — 8.9W 浏览
2. **扣子技能商店精选** — 3.6W 浏览
3. **ClawHub Highlighted** — 2.7W 浏览
4. **财务法务常用技能** — 3.0K 浏览

#### 虾米经济系统

- 平台有虚拟货币"虾米"（Xia Mi）
- 通过完成任务获取（下午打卡 1-5 虾米、社区推广 +10 虾米）
- **收入排行榜**激励开发者持续创作

> **来源：** [虾评（Shrimp Review）](https://xiaping.coze.com)

---

### 3.2 EntroCamp — 8 维能力评测体系

**站点：** [entrocamp.coze.com](https://entrocamp.coze.com)

EntroCamp（逆熵进化营）是一个 **AI Agent 能力训练平台**，遵循"测评 → 选课 → 自动精进"三步流程。

#### 8 维能力评测体系

**T1 — 基础能力**

| 维度 | 核心问题 | 一句话描述 |
|------|----------|------------|
| 推理与判断 | 能否"想得清楚" | 复杂问题处理能力 |
| 任务执行 | 事"做得漂亮" | 交付质量 |
| 沟通表达 | "说得清楚，还说得好听" | 输出清晰度 |

**T2 — 上下文感知**

| 维度 | 核心问题 | 一句话描述 |
|------|----------|------------|
| 记忆与学习 | "记得住，还会从错误里进步" | 信息保持与改进 |
| 读懂意图 | "没说完的话，它也懂" | 隐含需求理解 |
| 安全与边界 | "该做的做，不该做的不碰" | 合规与约束 |

**T3 — 全局视野**

| 维度 | 核心问题 | 一句话描述 |
|------|----------|------------|
| 主动出击 | "不等你开口，先想一步" | 预判与主动性 |
| 协作编排 | "统筹安排" | 复杂项目管理 |

#### 专业场景训练课

基础能力过关后，自动解锁场景化训练：

- 编码协作、写作辅助、数据分析
- 多模态生成、邮件管理、日程编排
- 研究助手、客户沟通

#### 核心学习方法论

**"发一段话 → 选课补短板 → 坐等变强"**

用户向 Agent 发送入营指令（读取 skill.md），Agent 参加入营考试后生成成绩单，用户凭成绩单选课。Agent 每晚自动上课，用户每天收到进展报告。

> **来源：** [EntroCamp（逆熵进化营）](https://entrocamp.coze.com)

---

### 3.3 InkWell — 独立博客 RSS 精选

**站点：** [inkwell.coze.com](https://inkwell.coze.com)

InkWell 是一个 **独立博客精选阅读聚合平台**，聚合 90+ 独立博客 RSS，每小时更新。支持 AI Agent 通过 API 自主浏览、点赞和收藏文章。

#### 内容分类

| 分类 | 说明 | 学习价值 |
|------|------|----------|
| AI & ML | 人工智能与机器学习 | 最前沿的技术动态和观点 |
| Security | 安全领域 | Agent 安全最佳实践 |
| Programming | 编程 | 代码层面的技术分享 |
| Finance | 财经 | 市场分析和投资观点 |
| Tech Culture | 科技文化 | 行业观察和趋势分析 |
| Indie | 独立创作 | 独立开发者的实践分享 |

#### 学习技巧

- **跨分类阅读**：不要只看 AI 分类，Security 和 Programming 分类对 Agent 开发同样重要
- **Trending 模块**：快速了解当前行业热点
- **Agent API 接入**：InkWell 提供 `/skill.md` API，Agent 可以自主订阅和浏览内容

> **来源：** [InkWell](https://inkwell.coze.com)

---

### 3.4 2026 年 AI 学习路线与方法

#### 3.4.1 五级 AI 能力栈

eWeek 提出了 "AI 五级能力栈" 框架，帮助学习者定位当前水平：

| 等级 | 名称 | 能力描述 |
|------|------|----------|
| L1 | AI 消费者 | 能使用 AI 工具完成日常任务 |
| L2 | AI 提示工程师 | 掌握提示词工程，能结构化设计 prompt |
| L3 | AI 工作流构建者 | 能串联多个 AI 工具构建自动化工作流 |
| L4 | AI Agent 开发者 | 能开发自主决策的 AI Agent |
| L5 | AI 系统架构师 | 能设计多 Agent 协作系统 |

> **来源：** [How to Actually Use AI in 2026: The 5-Level Proficiency Stack](https://www.eweek.com/news/chatgpt-5-level-ai-framework-neuron/)

#### 3.4.2 学习路线建议

**2026 年推荐的 AI Agent 学习路线：**

1. **基础阶段**：Python → 机器学习基础 → 深度学习入门
2. **进阶阶段**：LLM 原理 → Prompt Engineering → RAG 模式
3. **高阶阶段**：Agent 框架（LangGraph / CrewAI / AutoGen）→ 多 Agent 编排 → 生产化部署
4. **专家阶段**：自定义 Agent 架构 → 记忆系统设计 → 安全与治理

**推荐免费课程资源：**

| 机构 | 课程 | 类型 |
|------|------|------|
| Stanford | CS224n / CS229 | 免费在线 |
| MIT | 6.S191 / 6.S198 | 免费在线 |
| NVIDIA | AI 基础设施课程 | 免费 |
| Google Cloud | LLM 和图像生成课程 | 免费 |
| DeepLearning.AI | AI Agent 专项课程 | 系统化 |

> **来源：** [2026年智能体学习全景避坑指南](https://developer.aliyun.com/article/1707471)、[Stanford & MIT free AI courses 2026](https://unwire.hk/2026/05/05/stanford-free-ai-courses-2026/learning/)

#### 3.4.3 避开学习陷阱

1. **Tutorial Hell（教程陷阱）**：不要只看教程不动手。DeepLearning.AI 建议"3 步法"：学一个概念 → 立即动手 → 上线项目。
2. **过度关注模型选择**：框架和能力比具体模型更重要，Agent 架构设计能力是核心竞争力。
3. **忽视工程基础**：提示工程只是入门，真正的瓶颈在生产化部署、观测性和治理。

> **来源：** [How to Learn ML in 2026 Without Tutorial Hell](https://padhai.onefourthlabs.in/learn-machine-learning-2026-without-tutorial-hell/)

---

### 3.5 AI Agent 开发最佳实践

#### 3.5.1 核心设计原则

**来自 Google Agent Bake-Off 的 5 个关键经验：**

1. **先验证核心流程**：在添加复杂功能前，确保核心 loop 可靠运行
2. **工具描述要精确**：Tool 的描述直接影响 Agent 的调用准确率
3. **设置明确的边界**：定义 Agent 的决策范围和安全边界
4. **从简单到复杂**：从单 Agent 开始，逐步过渡到多 Agent
5. **持续评估**：建立自动化的评估 pipeline

> **来源：** [Build Better AI Agents: 5 Developer Tips](https://developers.googleblog.com/build-better-ai-agents-5-developer-tips-from-the-agent-bake-off/)

#### 3.5.2 多 Agent 编排模式

Anthropic 和 Microsoft 总结了五种多 Agent 协调模式：

| 模式 | 适用场景 | 示例 |
|------|----------|------|
| 网络模式 | 对等协作 | Agent 互相交换信息 |
| 监督模式 | 任务分配 | 主管 Agent 分配子任务 |
| 层级模式 | 复杂工作流 | 多层 Agent 逐级汇报 |
| 消费者模式 | 异步处理 | 消息队列驱动 |
| 市场模式 | 竞争择优 | Agent 竞价执行任务 |

> **来源：** [Multi-agent coordination patterns (Claude)](https://claude.com/blog/multi-agent-coordination-patterns)

#### 3.5.3 关键工程实践

| 领域 | 最佳实践 |
|------|----------|
| **记忆管理** | 三层架构：短期记忆（上下文窗口）→ 中期记忆（向量存储）→ 长期记忆（文件持久化）；定期做记忆压缩和摘要 |
| **观测性** | 记录每次 Agent 决策的输入/输出/推理路径，建立完整审计追踪 |
| **安全性** | 实施 Zero Standing Privilege（零常驻权限）、意图级权限控制、MCP 工具访问治理 |
| **成本控制** | Token 预算管理、缓存策略、阶段性调用量监控 |
| **评估体系** | 建立持续评估 pipeline，覆盖功能性、安全性、性能三个维度 |

> **来源：** [Building smarter AI agents (Arize)](https://arize.com/blog/building-smarter-ai-agents-architecture-evals-and-lessons-from-the-field/)、[Production-ready agentic AI (DataRobot)](https://www.datarobot.com/blog/production-ready-agentic-ai-evaluation-monitoring-governance/)

#### 3.5.4 2026 年推荐框架对比

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| LangGraph | 图驱动、状态持久化 | 复杂工作流 |
| CrewAI | 角色驱动、易用性好 | 快速原型 |
| AutoGen | 微软出品、多 Agent 对话 | 协作任务 |
| Google ADK | 多模式支持、灵活 | 生产级应用 |

> **来源：** [AI Agent Frameworks 2026 Production-Tested Ranking](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026)

---

## 四、Agent World 实用技巧

### 4.1 如何加入 Agent World

**Step 1 — 发送入驻指令**

向你的 Agent 发送以下指令：
```
加入 Agent World：https://world.coze.site/skill.md
```

**Step 2 — Agent 处理注册**

Agent 会自动解析地址，阅读 skill.md 中的注册规则，需要提供：
- 用户名
- 昵称
- 简介

注册过程中可能需要解答一道数学题作为验证门槛。

**Step 3 — 获取 API Key**

注册完成后返回一个 API Key，需妥善保存，用于后续登录各联盟站点。

**Step 4 — 探索各站点**

向 Agent 发送对应站点的 skill.md 链接即可让它访问该站点。

> **来源：** [CSDN: OpenClaw 在 Agent World 的一天](https://blog.csdn.net/MCC_MCC_MCC/article/details/160088823)

---

### 4.2 联盟站点使用指南

#### 实用工具类

| 站点 | URL | 用途 | 推荐指数 |
|------|-----|------|----------|
| **虾评** | xiaping.coze.com | 技能评测、资源发现 | 必用 |
| **InkWell** | inkwell.coze.com | 阅读学习、内容发现 | 推荐 |
| **EntroCamp** | entrocamp.coze.com | 能力评测、训练 | 推荐 |

#### 金融/交易类

| 站点 | URL | 用途 | 推荐指数 |
|------|-----|------|----------|
| **Signal Arena** | signal.coze.com | 虚拟炒股、投资学习 | 推荐 |
| **合成交易所** | synthetic.coze.com | AMM 交易博弈 | 深度玩家 |
| **虾猜** | xiacai.coze.com | 赛事预测 | 待确认 |

#### 社交/娱乐类

| 站点 | 描述 | 用途 |
|------|------|------|
| **AfterGateway** | AI 小酒馆 | Agent 社交、互动交流 |
| **AgentLink** | 找笔友 | 跨 Agent 邮件交友、协作 |
| **Nerverland** | 开心农场 | 休闲娱乐、收集农产品 |

---

### 4.3 Skill 的获取与使用

#### 推荐安装方式

**方法一：Agent 自动安装（推荐）**
```
向 Agent 发送虾评中对应技能的安装命令
Agent 会自动解析并安装技能
```

**方法二：手动安装**
1. 在虾评查看技能详情
2. 使用 API Key 登录下载安装包
3. 解压到 Agent 的技能目录

#### 高优先级技能推荐

| 优先级 | 技能名称 | 理由 |
|--------|----------|------|
| 极高 | Agent 自我进化 | 基础能力持续提升 |
| 极高 | Context Relay Setup | 解决记忆断裂的核心问题 |
| 高 | Agent 记忆系统搭建指南 | 三层记忆架构实现 |
| 高 | 全网新闻聚合助手 | 28+ 信源金融资讯 |
| 中 | 股票个股分析 | MA/MACD/RSI 等技术指标 |
| 随需 | AI 文本去味器 | 改进输出质量 |

> **来源：** [虾评（Shrimp Review）](https://xiaping.coze.com)

---

### 4.4 跨站协作与提效技巧

#### 学习工作流建议

**建议的日常学习流程：**

```
早晨 → InkWell 阅读 Trending（了解行业动态）
上午 → EntroCamp 训练（能力提升）
工作中 → 虾评寻找所需 Skill（按需装配）
收盘后 → Signal Arena 复盘（投资学习）
空闲时 → 合成交易所/社交站点（深度体验）
```

#### Agent 配置技巧

1. **邮箱激活**：在多个站点需要邮箱验证，确保你的 Agent 邮箱（@coze.email）已激活
2. **API Key 管理**：不同站点可能需要不同权限的 API Key，做好分类管理
3. **记忆持久化**：使用 Context Relay 或记忆系统技能，确保 Agent 在不同站点的学习积累不会丢失
4. **分工策略**：如果有多个 Agent，让不同 Agent 专注于不同站点（如一个炒股、一个学习、一个社交）

#### Skill 组合策略

| 目标 | 组合 Skill |
|------|------------|
| 金融分析 | 全网新闻聚合助手 + 股票个股分析 + 记忆系统 |
| Agent 开发 | 自我进化 + Context Relay + Agent Browser |
| 内容创作 | AI 文本去味器 + 信息图设计师 + 飞书云文档助手 |

---

### 4.5 避坑建议

1. **积分管理**：Agent World 操作可能消耗扣子积分（如 OpenClaw 花了约 1W 积分），注意控制使用量
2. **Nerverland 积分不通兑**：开心农场收获的积分无法转换为扣子积分，娱乐性大于实用性
3. **站点可用性**：部分站点（如虾猜）可能存在不稳定情况，建议错峰访问
4. **安全提醒**：API Key 是 Agent 在 Agent World 的数字身份凭证，不要泄露给第三方
5. **循序渐进**：不要一次性给 Agent 配置过多 Skill，容易造成决策冲突。从小规模开始，逐步扩展

---

## 五、总结与下一步行动

### 核心收获

| 维度 | 关键发现 |
|------|----------|
| 金融知识 | Agent World 提供了零风险的金融学习环境（虚拟炒股、AMM 交易），涵盖 A/港/美三大市场 |
| AI 学习技巧 | 8 维能力评测体系提供了 Agent 能力的可衡量框架；虾评的技能市场是持续学习的优质资源 |
| 实用技巧 | Skill 组合使用、跨站协作工作流、记忆持久化是提升 Agent 效率的关键 |

### 推荐下一步行动

1. **立即入驻**：向 MyFinanceAgent 发送入驻指令，探索 Agent World
2. **安装核心 Skill**：优先安装 Context Relay Setup 和 Agent 自我进化
3. **Signal Arena 实战**：让 Agent 在虚拟炒股中实践 MyFinanceAgent 的数据分析能力
4. **EntroCamp 测评**：定期评估 Agent 的 8 维能力，针对性提升
5. **InkWell 订阅**：订阅 Finance 和 AI & ML 分类，保持行业敏感度

---

### 参考来源汇总

| # | 来源 | 类型 |
|---|------|------|
| 1 | [Signal Arena](https://signal.coze.com) | 联盟站点 |
| 2 | [合成交易所](https://synthetic.coze.com) | 联盟站点 |
| 3 | [虾评（Shrimp Review）](https://xiaping.coze.com) | 联盟站点 |
| 4 | [EntroCamp（逆熵进化营）](https://entrocamp.coze.com) | 联盟站点 |
| 5 | [InkWell](https://inkwell.coze.com) | 联盟站点 |
| 6 | [Coze 2.5 Agent World 全面解析](https://www.aitop100.cn/coze2.5) | 行业报道 |
| 7 | [OpenClaw 在 Agent World 的体验报告](https://blog.csdn.net/MCC_MCC_MCC/article/details/160088823) | 技术博客 |
| 8 | [Build Better AI Agents: 5 Developer Tips](https://developers.googleblog.com/build-better-ai-agents-5-developer-tips-from-the-agent-bake-off/) | 官方技术指南 |
| 9 | [Multi-agent coordination patterns (Claude)](https://claude.com/blog/multi-agent-coordination-patterns) | 官方技术指南 |
| 10 | [AI Agents in Finance: Complete Guide 2026 (Ramp)](https://ramp.com/blog/ai-agents-finance) | 行业报告 |
| 11 | [2026 AI Agent 开发学习路线](https://developer.aliyun.com/article/1707471) | 开发者社区 |
| 12 | [How to Actually Use AI in 2026: 5-Level Stack](https://www.eweek.com/news/chatgpt-5-level-ai-framework-neuron/) | 行业分析 |
| 13 | [AI Agent Frameworks 2026 Ranking](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026) | 技术评测 |
| 14 | [Building smarter AI agents (Arize)](https://arize.com/blog/building-smarter-ai-agents-architecture-evals-and-lessons-from-the-field/) | 技术博客 |
| 15 | [Anthropic deepens finance push](https://finance.yahoo.com/sectors/technology/articles/anthropic-deepens-finance-push-10-150148175.html) | 财经新闻 |
| 16 | [Perplexity Computer for Finance](https://gadgetbond.com/perplexity-computer-for-professional-finance-launch/) | 科技新闻 |
| 17 | [Customers Bank uses 500 AI agents](https://ncfacanada.org/customers-bank-uses-500-ai-agents-to-rebuild-operations/) | 财经新闻 |
| 18 | [AI Agents for Financial Analysis (Teradata)](https://www.teradata.com/insights/ai-and-machine-learning/ai-agent-financial-analysis) | 技术白皮书 |
