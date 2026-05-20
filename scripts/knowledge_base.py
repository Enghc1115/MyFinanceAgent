"""
knowledge_base.py — 中央静态知识库

MyFinanceAgent 所有分析模块的统一数据源。
集中管理股票信息、板块分类、产业链推理规则、事件模式、
美股龙头映射、拥挤度阈值等核心元数据。

所有模块统一从此文件导入，不再在各脚本中散落硬编码字典。
纯数据常量，无函数，无外部依赖。
"""

# ============================================================
# 1. STOCK_NAME_DICT — A 股核心股票池
# ============================================================
# 每个条目: "股票名": {"code": "6位代码", "sector": "所属板块", "category": "大类"}

STOCK_NAME_DICT: dict[str, dict[str, str]] = {
    # ---- 白酒/食品 (8-10) ----
    "贵州茅台": {"code": "600519", "sector": "白酒", "category": "消费"},
    "五粮液":   {"code": "000858", "sector": "白酒", "category": "消费"},
    "泸州老窖": {"code": "000568", "sector": "白酒", "category": "消费"},
    "山西汾酒": {"code": "600809", "sector": "白酒", "category": "消费"},
    "洋河股份": {"code": "002304", "sector": "白酒", "category": "消费"},
    "古井贡酒": {"code": "000596", "sector": "白酒", "category": "消费"},
    "海天味业": {"code": "603288", "sector": "食品饮料", "category": "消费"},
    "伊利股份": {"code": "600887", "sector": "食品饮料", "category": "消费"},
    "双汇发展": {"code": "000895", "sector": "食品饮料", "category": "消费"},
    "牧原股份": {"code": "002714", "sector": "养殖业", "category": "农业"},

    # ---- 新能源/汽车 (12-15) ----
    "宁德时代": {"code": "300750", "sector": "锂电池", "category": "工业"},
    "比亚迪":   {"code": "002594", "sector": "新能源汽车", "category": "工业"},
    "阳光电源": {"code": "300274", "sector": "光伏", "category": "能源"},
    "隆基绿能": {"code": "601012", "sector": "光伏", "category": "能源"},
    "通威股份": {"code": "600438", "sector": "光伏", "category": "能源"},
    "天齐锂业": {"code": "002466", "sector": "锂电池", "category": "工业"},
    "赣锋锂业": {"code": "002460", "sector": "锂电池", "category": "工业"},
    "亿纬锂能": {"code": "300014", "sector": "锂电池", "category": "工业"},
    "国轩高科": {"code": "002074", "sector": "锂电池", "category": "工业"},
    "长城汽车": {"code": "601633", "sector": "新能源汽车", "category": "工业"},
    "长安汽车": {"code": "000625", "sector": "新能源汽车", "category": "工业"},
    "赛力斯":   {"code": "601127", "sector": "新能源汽车", "category": "工业"},
    "江淮汽车": {"code": "600418", "sector": "新能源汽车", "category": "工业"},
    "汇川技术": {"code": "300124", "sector": "工业自动化", "category": "工业"},

    # ---- 半导体/芯片 (12-15) ----
    "中芯国际": {"code": "688981", "sector": "半导体", "category": "科技"},
    "寒武纪":   {"code": "688256", "sector": "AI芯片", "category": "科技"},
    "北方华创": {"code": "002371", "sector": "半导体设备", "category": "科技"},
    "中微公司": {"code": "688012", "sector": "半导体设备", "category": "科技"},
    "韦尔股份": {"code": "603501", "sector": "半导体", "category": "科技"},
    "兆易创新": {"code": "603986", "sector": "半导体", "category": "科技"},
    "卓胜微":   {"code": "300782", "sector": "半导体", "category": "科技"},
    "紫光国微": {"code": "002049", "sector": "半导体", "category": "科技"},
    "长电科技": {"code": "600584", "sector": "先进封装", "category": "科技"},
    "通富微电": {"code": "002156", "sector": "先进封装", "category": "科技"},
    "华天科技": {"code": "002185", "sector": "先进封装", "category": "科技"},
    "海光信息": {"code": "688041", "sector": "AI芯片", "category": "科技"},
    "澜起科技": {"code": "688008", "sector": "半导体", "category": "科技"},
    "圣邦股份": {"code": "300661", "sector": "半导体", "category": "科技"},

    # ---- 消费电子 (8-10) ----
    "立讯精密": {"code": "002475", "sector": "消费电子", "category": "科技"},
    "歌尔股份": {"code": "002241", "sector": "消费电子", "category": "科技"},
    "蓝思科技": {"code": "300433", "sector": "消费电子", "category": "科技"},
    "京东方A":  {"code": "000725", "sector": "面板", "category": "科技"},
    "TCL科技":  {"code": "000100", "sector": "面板", "category": "科技"},
    "深天马A":  {"code": "000050", "sector": "面板", "category": "科技"},
    "领益智造": {"code": "002600", "sector": "消费电子", "category": "科技"},
    "东山精密": {"code": "002384", "sector": "消费电子", "category": "科技"},
    "信维通信": {"code": "300136", "sector": "消费电子", "category": "科技"},

    # ---- 医药 (10-12) ----
    "恒瑞医药": {"code": "600276", "sector": "化学制药", "category": "医药"},
    "迈瑞医疗": {"code": "300760", "sector": "医疗器械", "category": "医药"},
    "药明康德": {"code": "603259", "sector": "CXO", "category": "医药"},
    "长春高新": {"code": "000661", "sector": "生物制品", "category": "医药"},
    "片仔癀":   {"code": "600436", "sector": "中药", "category": "医药"},
    "云南白药": {"code": "000538", "sector": "中药", "category": "医药"},
    "爱尔眼科": {"code": "300015", "sector": "医疗服务", "category": "医药"},
    "泰格医药": {"code": "300347", "sector": "CXO", "category": "医药"},
    "凯莱英":   {"code": "002821", "sector": "CXO", "category": "医药"},
    "康龙化成": {"code": "300759", "sector": "CXO", "category": "医药"},
    "智飞生物": {"code": "300122", "sector": "生物制品", "category": "医药"},
    "沃森生物": {"code": "300142", "sector": "生物制品", "category": "医药"},

    # ---- 金融 (8-10) ----
    "中国平安": {"code": "601318", "sector": "保险", "category": "金融"},
    "招商银行": {"code": "600036", "sector": "银行", "category": "金融"},
    "中信证券": {"code": "600030", "sector": "券商", "category": "金融"},
    "东方财富": {"code": "300059", "sector": "券商", "category": "金融"},
    "兴业银行": {"code": "601166", "sector": "银行", "category": "金融"},
    "平安银行": {"code": "000001", "sector": "银行", "category": "金融"},
    "同花顺":   {"code": "300033", "sector": "金融科技", "category": "金融"},
    "中国人寿": {"code": "601628", "sector": "保险", "category": "金融"},
    "宁波银行": {"code": "002142", "sector": "银行", "category": "金融"},

    # ---- 地产/基建 (5-8) ----
    "万科A":    {"code": "000002", "sector": "房地产", "category": "地产"},
    "保利发展": {"code": "600048", "sector": "房地产", "category": "地产"},
    "中国建筑": {"code": "601668", "sector": "建筑", "category": "地产"},
    "三一重工": {"code": "600031", "sector": "工程机械", "category": "工业"},
    "海螺水泥": {"code": "600585", "sector": "水泥建材", "category": "地产"},
    "东方雨虹": {"code": "002271", "sector": "建材", "category": "地产"},

    # ---- 家电 (5-8) ----
    "美的集团": {"code": "000333", "sector": "家电", "category": "消费"},
    "格力电器": {"code": "000651", "sector": "家电", "category": "消费"},
    "海尔智家": {"code": "600690", "sector": "家电", "category": "消费"},
    "科沃斯":   {"code": "603486", "sector": "家电", "category": "消费"},
    "石头科技": {"code": "688169", "sector": "家电", "category": "消费"},
    "老板电器": {"code": "002508", "sector": "家电", "category": "消费"},

    # ---- 科技/AI (10-12) ----
    "科大讯飞": {"code": "002230", "sector": "AI应用", "category": "科技"},
    "中科曙光": {"code": "603019", "sector": "服务器", "category": "科技"},
    "浪潮信息": {"code": "000977", "sector": "服务器", "category": "科技"},
    "三六零":   {"code": "601360", "sector": "AI应用", "category": "科技"},
    "金山办公": {"code": "688111", "sector": "AI应用", "category": "科技"},
    "用友网络": {"code": "600588", "sector": "软件", "category": "科技"},
    "广联达":   {"code": "002410", "sector": "软件", "category": "科技"},
    "恒生电子": {"code": "600570", "sector": "金融科技", "category": "科技"},
    "中科创达": {"code": "300496", "sector": "智能驾驶", "category": "科技"},
    "德赛西威": {"code": "002920", "sector": "智能驾驶", "category": "科技"},
    "拓尔思":   {"code": "300229", "sector": "AI应用", "category": "科技"},
    "云从科技": {"code": "688327", "sector": "AI应用", "category": "科技"},

    # ---- 资源/能源 (8-10) ----
    "中国石油": {"code": "601857", "sector": "石油", "category": "能源"},
    "中国石化": {"code": "600028", "sector": "石油", "category": "能源"},
    "中国神华": {"code": "601088", "sector": "煤炭", "category": "能源"},
    "紫金矿业": {"code": "601899", "sector": "有色金属", "category": "能源"},
    "山东黄金": {"code": "600547", "sector": "黄金", "category": "能源"},
    "赤峰黄金": {"code": "600988", "sector": "黄金", "category": "能源"},
    "中金黄金": {"code": "600489", "sector": "黄金", "category": "能源"},
    "宝钢股份": {"code": "600019", "sector": "钢铁", "category": "工业"},
    "江西铜业": {"code": "600362", "sector": "有色金属", "category": "能源"},

    # ---- 军工 (10-12) ----
    "中航沈飞": {"code": "600760", "sector": "军工", "category": "军工"},
    "航发动力": {"code": "600893", "sector": "军工", "category": "军工"},
    "中航西飞": {"code": "000768", "sector": "军工", "category": "军工"},
    "中国船舶": {"code": "600150", "sector": "军工", "category": "军工"},
    "航天发展": {"code": "003547", "sector": "军工", "category": "军工"},
    "电科蓝天": {"code": "688818", "sector": "军工", "category": "军工"},
    "中国卫通": {"code": "601698", "sector": "军工", "category": "军工"},
    "航天电子": {"code": "600879", "sector": "军工", "category": "军工"},
    "航天电器": {"code": "002025", "sector": "军工", "category": "军工"},
    "中航光电": {"code": "002179", "sector": "军工", "category": "军工"},
    "航天动力": {"code": "600343", "sector": "军工", "category": "军工"},
    "中无人机": {"code": "688297", "sector": "军工", "category": "军工"},

    # ---- 通信 (5-8) ----
    "中兴通讯": {"code": "000063", "sector": "通信设备", "category": "通信"},
    "烽火通信": {"code": "600498", "sector": "通信设备", "category": "通信"},
    "通鼎互联": {"code": "002491", "sector": "通信设备", "category": "通信"},
    "光迅科技": {"code": "002281", "sector": "光模块", "category": "通信"},
    "中际旭创": {"code": "300308", "sector": "光模块", "category": "通信"},
    "天孚通信": {"code": "300394", "sector": "光模块", "category": "通信"},
    "新易盛":   {"code": "300502", "sector": "光模块", "category": "通信"},

    # ---- 其他重要 (8-10) ----
    "顺丰控股": {"code": "002352", "sector": "物流", "category": "工业"},
    "中国中免": {"code": "601888", "sector": "免税", "category": "消费"},
    "温氏股份": {"code": "300498", "sector": "养殖业", "category": "农业"},
    "分众传媒": {"code": "002027", "sector": "传媒", "category": "消费"},
    "福耀玻璃": {"code": "600660", "sector": "汽车零部件", "category": "工业"},
    "恒立液压": {"code": "601100", "sector": "工程机械", "category": "工业"},
    "华测检测": {"code": "300012", "sector": "检测服务", "category": "工业"},
    "汇顶科技": {"code": "603160", "sector": "半导体", "category": "科技"},
    "工业富联": {"code": "601138", "sector": "服务器", "category": "科技"},
}

# ---- 便捷派生：按分类/code 反向索引（供其他模块按需使用） ----
STOCK_CODE_TO_NAME: dict[str, str] = {
    v["code"]: k for k, v in STOCK_NAME_DICT.items()
}

STOCK_NAME_TO_CATEGORY: dict[str, str] = {
    k: v["category"] for k, v in STOCK_NAME_DICT.items()
}

STOCK_NAME_TO_SECTOR: dict[str, str] = {
    k: v["sector"] for k, v in STOCK_NAME_DICT.items()
}

# 从 STOCK_NAME_DICT 提取的公司关键词列表（供 headlines.py 实体提取使用）
COMPANY_KEYWORDS: list[str] = sorted(STOCK_NAME_DICT.keys(), key=len, reverse=True)


# ============================================================
# 2. SECTOR_CATEGORY_MAP — 板块 → 大类映射
# ============================================================

SECTOR_CATEGORY_MAP: dict[str, str] = {
    # ---- 科技 ----
    "半导体":       "科技",
    "半导体设备":   "科技",
    "AI芯片":       "科技",
    "先进封装":     "科技",
    "芯片":         "科技",
    "集成电路":     "科技",
    "AI应用":       "科技",
    "人工智能":     "科技",
    "软件":         "科技",
    "服务器":       "科技",
    "消费电子":     "科技",
    "面板":         "科技",
    "金融科技":     "科技",
    "智能驾驶":     "科技",
    "信创":         "科技",
    "数据要素":     "科技",
    "算力":         "科技",
    "东数西算":     "科技",
    "机器人":       "科技",
    "人形机器人":   "科技",

    # ---- 消费 ----
    "白酒":         "消费",
    "食品饮料":     "消费",
    "家电":         "消费",
    "免税":         "消费",
    "传媒":         "消费",
    "医美":         "消费",
    "预制菜":       "消费",
    "跨境电商":     "消费",
    "教育":         "消费",
    "游戏":         "消费",

    # ---- 医药 ----
    "化学制药":     "医药",
    "医疗器械":     "医药",
    "CXO":          "医药",
    "生物制品":     "医药",
    "中药":         "医药",
    "医疗服务":     "医药",

    # ---- 金融 ----
    "保险":         "金融",
    "银行":         "金融",
    "券商":         "金融",

    # ---- 工业 ----
    "锂电池":       "工业",
    "新能源汽车":   "工业",
    "工业自动化":   "工业",
    "工程机械":     "工业",
    "汽车零部件":   "工业",
    "物流":         "工业",
    "检测服务":     "工业",
    "钢铁":         "工业",
    "化工":         "工业",
    "工业母机":     "工业",
    "高端装备":     "工业",

    # ---- 能源 ----
    "光伏":         "能源",
    "石油":         "能源",
    "煤炭":         "能源",
    "有色金属":     "能源",
    "黄金":         "能源",
    "稀土":         "能源",
    "氢能":         "能源",
    "核电":         "能源",
    "风电":         "能源",
    "储能":         "能源",
    "充电桩":       "能源",
    "智能电网":     "能源",

    # ---- 军工 ----
    "军工":         "军工",
    "商业航天":     "军工",
    "低空经济":     "军工",

    # ---- 通信 ----
    "通信设备":     "通信",
    "光模块":       "通信",
    "5G":           "通信",
    "CPO":          "通信",

    # ---- 地产 ----
    "房地产":       "地产",
    "建筑":         "地产",
    "水泥建材":     "地产",
    "建材":         "地产",

    # ---- 农业 ----
    "养殖业":       "农业",
    "农业":         "农业",

    # ---- 其他 ----
    "新材料":       "工业",
    "碳纤维":       "工业",
    "数字经济":     "科技",
}


# ============================================================
# 3. CHAIN_REASONING_RULES — 产业链联动推理规则
# ============================================================
# 每个规则定义：触发关键词 → 上下游 → A 股受益标的

CHAIN_REASONING_RULES: list[dict] = [
    {
        "name": "英伟达Blackwell / 算力产业链",
        "triggers": [
            "英伟达", "NVIDIA", "Blackwell", "GB200", "GB300",
            "B200", "B300", "算力芯片", "GPU", "HBM",
        ],
        "upstream":   ["光模块", "服务器", "先进封装", "PCB", "铜缆连接器", "散热"],
        "midstream":  ["算力租赁", "数据中心", "AI服务器"],
        "downstream": ["AI应用", "大模型", "智能驾驶"],
        "a_share_beneficiaries": {
            "光模块/光通信": ["中际旭创", "天孚通信", "新易盛", "光迅科技"],
            "服务器/算力":   ["工业富联", "浪潮信息", "中科曙光", "紫光股份"],
            "先进封装":       ["长电科技", "通富微电", "华天科技"],
            "PCB":            ["沪电股份", "深南电路", "鹏鼎控股", "东山精密"],
            "铜缆连接器":     ["立讯精密", "兆龙互连", "博威合金"],
            "散热":           ["英维克", "高澜股份", "佳力图"],
            "算力租赁":       ["光环新网", "数据港", "奥飞数据"],
            "AI应用":         ["科大讯飞", "金山办公", "拓尔思", "云从科技"],
        },
    },
    {
        "name": "台积电 / 先进制程映射",
        "triggers": [
            "台积电", "TSMC", "先进制程", "3nm", "2nm", "N3", "N2",
            "CoWoS", "晶圆代工", "SoIC",
        ],
        "upstream":   ["半导体设备", "硅片", "光刻胶", "电子气体"],
        "midstream":  ["晶圆制造", "先进封装"],
        "downstream": ["芯片设计", "AI芯片", "消费电子"],
        "a_share_beneficiaries": {
            "半导体设备": ["北方华创", "中微公司", "拓荆科技", "盛美上海"],
            "晶圆制造":   ["中芯国际", "华虹半导体"],
            "先进封装":   ["长电科技", "通富微电", "华天科技", "晶方科技"],
            "半导体材料": ["沪硅产业", "立昂微", "安集科技", "鼎龙股份"],
        },
    },
    {
        "name": "ASML / 半导体设备出口管制",
        "triggers": [
            "ASML", "光刻机", "出口管制", "DUV", "EUV",
            "荷兰", "美国制裁", "实体清单", "半导体出口",
        ],
        "upstream":   ["半导体设备", "光刻胶", "电子特气"],
        "midstream":  ["晶圆制造", "半导体零部件"],
        "downstream": ["芯片", "AI", "通信"],
        "a_share_beneficiaries": {
            "国产光刻机":   ["上海微电子（非上市）"],
            "半导体设备":   ["北方华创", "中微公司", "盛美上海", "拓荆科技"],
            "半导体材料":   ["安集科技", "沪硅产业", "鼎龙股份", "容大感光"],
            "EDA/设计工具": ["华大九天", "概伦电子", "广立微"],
        },
    },
    {
        "name": "苹果供应链 / iPhone 新品周期",
        "triggers": [
            "苹果", "Apple", "iPhone", "iPad", "MacBook",
            "Vision Pro", "AirPods", "Apple Watch", "果链",
        ],
        "upstream":   ["面板", "摄像头", "声学组件", "精密结构件", "PCB"],
        "midstream":  ["整机组装", "电池模组", "天线模组"],
        "downstream": ["授权经销商", "配件", "维修服务"],
        "a_share_beneficiaries": {
            "整机组装":   ["立讯精密", "歌尔股份", "工业富联"],
            "面板":       ["京东方A", "TCL科技"],
            "精密结构件": ["蓝思科技", "领益智造", "长盈精密"],
            "PCB/天线":   ["东山精密", "信维通信", "鹏鼎控股"],
        },
    },
    {
        "name": "特斯拉 / Optimus人形机器人",
        "triggers": [
            "特斯拉", "Tesla", "Optimus", "人形机器人",
            "擎天柱", "马斯克", "Cybercab", "FSD",
        ],
        "upstream":   ["电机", "减速器", "传感器", "丝杠", "轴承"],
        "midstream":  ["机器人整机", "运动控制器"],
        "downstream": ["智能制造", "物流自动化"],
        "a_share_beneficiaries": {
            "执行器/电机": ["汇川技术", "鸣志电器", "步科股份"],
            "减速器":       ["绿的谐波", "双环传动", "中大力德"],
            "传感器":       ["奥普特", "汉威科技", "柯力传感"],
            "丝杠/轴承":   ["恒立液压", "秦川机床", "五洲新春"],
            "机器人整机":   ["埃斯顿", "拓斯达", "机器人"],
        },
    },
    {
        "name": "新能源 / 光伏产业链",
        "triggers": [
            "光伏", "硅料", "硅片", "PERC", "TOPCon", "HJT",
            "钙钛矿", "组件", "逆变器", "光伏装机", "风光大基地",
        ],
        "upstream":   ["硅料", "硅片", "银浆", "光伏玻璃"],
        "midstream":  ["电池片", "组件", "逆变器"],
        "downstream": ["电站运营", "储能", "特高压"],
        "a_share_beneficiaries": {
            "硅料/硅片":   ["通威股份", "隆基绿能", "TCL中环", "大全能源"],
            "电池/组件":   ["晶澳科技", "天合光能", "晶科能源", "东方日升"],
            "逆变器":       ["阳光电源", "锦浪科技", "固德威", "禾迈股份"],
            "光伏辅材":     ["福斯特", "福莱特", "帝科股份"],
            "下游运营":     ["三峡能源", "正泰电器", "林洋能源"],
        },
    },
    {
        "name": "中美关系 / 国产替代",
        "triggers": [
            "中美", "关税", "制裁", "贸易战", "实体清单",
            "科技脱钩", "出口管制", "芯片法案", "国产替代", "自主可控",
        ],
        "upstream":   ["半导体设备", "EDA软件", "材料"],
        "midstream":  ["芯片制造", "操作系统", "数据库"],
        "downstream": ["信创", "网络安全", "数据要素"],
        "a_share_beneficiaries": {
            "半导体设备":   ["北方华创", "中微公司", "拓荆科技"],
            "芯片/CPU":     ["海光信息", "龙芯中科", "寒武纪"],
            "操作系统":     ["中国软件", "诚迈科技", "麒麟信安"],
            "信创/软件":    ["金山办公", "用友网络", "东方通"],
            "网络安全":     ["奇安信", "深信服", "启明星辰"],
            "军工":         ["中航沈飞", "航发动力", "中国船舶"],
        },
    },
    {
        "name": "央行政策 / 流动性",
        "triggers": [
            "降准", "降息", "LPR", "MLF", "逆回购",
            "央行", "货币政策", "流动性", "美联储", "利率决议",
            "缩表", "扩表", "存款准备金", "SLF", "PSL",
        ],
        "upstream":   ["银行间利率", "国债收益率", "存款成本"],
        "midstream":  ["银行信贷", "社融规模", "M2增速"],
        "downstream": ["地产销售", "企业投资", "消费贷款"],
        "a_share_beneficiaries": {
            "银行":     ["招商银行", "平安银行", "宁波银行", "工商银行"],
            "地产":     ["万科A", "保利发展", "华润置地_港股"],
            "券商":     ["中信证券", "东方财富", "华泰证券"],
            "保险":     ["中国平安", "中国人寿", "中国太保"],
            "消费/家电": ["美的集团", "格力电器", "海尔智家"],
        },
    },
    {
        "name": "原油 / 大宗商品",
        "triggers": [
            "原油", "OPEC", "布伦特", "WTI", "能源",
            "大宗商品", "铜", "铝", "铁矿石", "金价", "LME",
        ],
        "upstream":   ["原油勘探", "采矿", "冶炼"],
        "midstream":  ["炼化", "运输", "贸易"],
        "downstream": ["化工", "航空", "制造"],
        "a_share_beneficiaries": {
            "石油":       ["中国石油", "中国石化", "中海油服"],
            "黄金":       ["山东黄金", "赤峰黄金", "中金黄金", "紫金矿业"],
            "铜/有色":    ["紫金矿业", "江西铜业", "洛阳钼业"],
            "煤炭":       ["中国神华", "陕西煤业", "广汇能源"],
            "化工（受损）": ["万华化学", "恒力石化", "荣盛石化"],
            "航空（受损）": ["中国国航", "南方航空", "中国东航"],
        },
    },
    {
        "name": "商业航天 / 低空经济",
        "triggers": [
            "商业航天", "低空经济", "eVTOL", "无人机",
            "SpaceX", "卫星互联网", "火箭回收", "空天",
            "通航", "eVTOL适航", "低空航线",
        ],
        "upstream":   ["卫星制造", "火箭发动机", "航空材料"],
        "midstream":  ["卫星发射", "卫星运营", "地面设备"],
        "downstream": ["通信服务", "遥感应用", "低空物流"],
        "a_share_beneficiaries": {
            "卫星制造":     ["中国卫星", "中国卫通", "航天电子"],
            "火箭/发射":    ["航天动力", "航天电器", "中航光电"],
            "无人机/eVTOL": ["中无人机", "纵横股份", "亿航智能_美股"],
            "地面/通信":    ["华力创通", "上海瀚讯", "信科移动"],
            "低空基建":     ["莱斯信息", "深城交", "四维图新"],
        },
    },
]


# ============================================================
# 4. EVENT_PATTERNS — 事件驱动的四维分析语义
# ============================================================

EVENT_PATTERNS: dict[str, dict] = {
    "地缘冲突升级": {
        "directional":       "加速国产替代/自主可控进程，避险情绪推升黄金/军工",
        "affected_sectors":  ["军工", "半导体", "稀土", "能源", "黄金"],
        "dalio_macro":       "逆全球化加剧，国防与科技自主是长期确定性",
        "risk_level":        "high",
    },
    "产业政策发布": {
        "directional":       "政策驱动行业景气度提升，结构性机会凸显",
        "affected_sectors":  [],  # 动态填入
        "dalio_macro":       "财政/产业政策发力，结构性机会凸显",
        "risk_level":        "medium",
    },
    "货币政策宽松": {
        "directional":       "流动性改善，利好成长/科技板块与地产链",
        "affected_sectors":  ["银行", "券商", "地产", "消费"],
        "dalio_macro":       "宽松周期中信贷扩张，资产价格获得支撑",
        "risk_level":        "low",
    },
    "货币政策收紧": {
        "directional":       "流动性收缩，高估值板块承压，防御性板块相对占优",
        "affected_sectors":  ["银行", "保险", "公用事业"],
        "dalio_macro":       "紧缩周期中风险偏好下降，价值股优于成长股",
        "risk_level":        "high",
    },
    "外贸数据超预期": {
        "directional":       "出口链利好，但需区分是量增还是价涨",
        "affected_sectors":  ["消费电子", "光伏", "新能源", "家电", "纺织"],
        "dalio_macro":       "外需韧性支撑制造业，但关税风险仍存",
        "risk_level":        "medium",
    },
    "美股科技大跌": {
        "directional":       "风险偏好传导，A 股科技/AI 板块次日承压",
        "affected_sectors":  ["半导体", "AI", "消费电子", "通信"],
        "dalio_macro":       "全球风险偏好联动，科技估值重定价",
        "risk_level":        "high",
    },
    "美股科技大涨": {
        "directional":       "利好 A 股科技/AI 方向，北向资金流入预期增强",
        "affected_sectors":  ["半导体", "AI", "消费电子", "光模块"],
        "dalio_macro":       "全球风险偏好提升，科技股估值扩张",
        "risk_level":        "medium",
    },
    "原油价格大涨": {
        "directional":       "利好能源板块，但压制航空/化工/制造毛利率",
        "affected_sectors":  ["石油", "煤炭", "化工（受损）", "航空（受损）"],
        "dalio_macro":       "输入性通胀压力上升，央行政策空间收窄",
        "risk_level":        "high",
    },
    "人民币汇率波动": {
        "directional":       "升值有利进口/消费/航空；贬值有利出口/制造",
        "affected_sectors":  ["航空", "造纸", "消费电子", "出口制造"],
        "dalio_macro":       "汇率是内外经济力量博弈的最终定价",
        "risk_level":        "medium",
    },
    "行业监管收紧": {
        "directional":       "短期估值承压，长期利好合规龙头集中度提升",
        "affected_sectors":  [],  # 动态填入
        "dalio_macro":       "监管重塑行业格局，头部企业相对受益",
        "risk_level":        "high",
    },
    "技术突破/创新": {
        "directional":       "开辟新成长赛道，催化板块情绪与估值提升",
        "affected_sectors":  [],  # 动态填入
        "dalio_macro":       "技术创新是长期生产力提升的核心驱动力",
        "risk_level":        "low",
    },
    "财报季/业绩披露": {
        "directional":       "业绩验证期，赛道逻辑让位于基本面",
        "affected_sectors":  [],  # 动态填入
        "dalio_macro":       "微观数据验证宏观趋势，企业盈利是市场的终极锚",
        "risk_level":        "medium",
    },
    "房地产政策调整": {
        "directional":       "政策托底信号，短期提振地产链情绪但需基本面验证",
        "affected_sectors":  ["房地产", "银行", "建材", "家电", "建筑"],
        "dalio_macro":       "地产仍是中国经济与信用的核心支柱，政策底线清晰",
        "risk_level":        "medium",
    },
    "疫情/公共卫生事件": {
        "directional":       "冲击线下消费/出行板块，利好医药/线上服务",
        "affected_sectors":  ["医药", "医疗器械", "线上服务"],
        "dalio_macro":       "扰动短期经济活动，政策应对决定复苏节奏",
        "risk_level":        "high",
    },
}


# ============================================================
# 5. US_LEADER_STOCKS — 美股龙头 → A 股映射
# ============================================================

US_LEADER_STOCKS: dict[str, dict[str, str]] = {
    # ---- 科技半导体链 ----
    "NVDA": {"name_cn": "英伟达",   "category": "科技半导体", "a_share_mapping": "AI算力/光模块",  "weight": "high"},
    "AMD":  {"name_cn": "AMD",      "category": "科技半导体", "a_share_mapping": "CPU/GPU芯片",    "weight": "medium"},
    "AVGO": {"name_cn": "博通",     "category": "科技半导体", "a_share_mapping": "网络芯片/ASIC",  "weight": "medium"},
    "TSM":  {"name_cn": "台积电",   "category": "科技半导体", "a_share_mapping": "晶圆代工/封测",  "weight": "high"},
    "ASML": {"name_cn": "阿斯麦",   "category": "科技半导体", "a_share_mapping": "半导体设备/材料", "weight": "medium"},
    "MU":   {"name_cn": "美光科技", "category": "科技半导体", "a_share_mapping": "存储芯片",        "weight": "medium"},
    "INTC": {"name_cn": "英特尔",   "category": "科技半导体", "a_share_mapping": "CPU/服务器",      "weight": "medium"},

    # ---- 消费科技链 ----
    "AAPL":  {"name_cn": "苹果",   "category": "消费科技", "a_share_mapping": "消费电子/果链",    "weight": "high"},
    "TSLA":  {"name_cn": "特斯拉", "category": "消费科技", "a_share_mapping": "新能源车/机器人",   "weight": "high"},
    "AMZN":  {"name_cn": "亚马逊", "category": "消费科技", "a_share_mapping": "云计算/跨境电商",   "weight": "medium"},
    "MSFT":  {"name_cn": "微软",   "category": "消费科技", "a_share_mapping": "AI应用/云计算",     "weight": "high"},
    "GOOGL": {"name_cn": "谷歌",   "category": "消费科技", "a_share_mapping": "AI/云计算/广告",    "weight": "medium"},
    "META":  {"name_cn": "Meta",   "category": "消费科技", "a_share_mapping": "元宇宙/AI/广告",    "weight": "medium"},

    # ---- 中概 / 映射敏感 ----
    "BABA": {"name_cn": "阿里巴巴", "category": "中概映射", "a_share_mapping": "电商/云计算",     "weight": "high"},
    "PDD":  {"name_cn": "拼多多",   "category": "中概映射", "a_share_mapping": "下沉消费/跨境电商", "weight": "medium"},
    "JD":   {"name_cn": "京东",     "category": "中概映射", "a_share_mapping": "零售/物流",        "weight": "medium"},
    "BIDU": {"name_cn": "百度",     "category": "中概映射", "a_share_mapping": "AI/自动驾驶",      "weight": "medium"},
    "NIO":  {"name_cn": "蔚来",     "category": "中概映射", "a_share_mapping": "新能源车",          "weight": "medium"},
    "LI":   {"name_cn": "理想汽车", "category": "中概映射", "a_share_mapping": "新能源车",          "weight": "medium"},
    "XPEV": {"name_cn": "小鹏汽车", "category": "中概映射", "a_share_mapping": "新能源车/智驾",    "weight": "medium"},
}


# ============================================================
# 6. US_SECTOR_ETFS — 美股行业 ETF → A 股映射
# ============================================================

US_SECTOR_ETFS: dict[str, dict] = {
    "SMH": {
        "name": "半导体ETF",
        "description": "美国半导体行业（英伟达/博通/AMD等）",
        "a_share_mapped_sectors": ["半导体", "芯片", "集成电路", "光模块"],
        "direction_logic": "SMH涨→A股半导体/芯片方向利好，AI算力需求传导；SMH跌→避险情绪压制科技板块",
    },
    "QQQ": {
        "name": "纳斯达克100 ETF",
        "description": "美国科技龙头（苹果/微软/英伟达等）",
        "a_share_mapped_sectors": ["科技", "AI", "消费电子", "软件"],
        "direction_logic": "QQQ涨→A股科技/AI方向利好，全球风险偏好提升，北向资金流入预期增强",
    },
    "XLE": {
        "name": "能源ETF",
        "description": "美国能源行业（埃克森美孚/雪佛龙等）",
        "a_share_mapped_sectors": ["石油", "煤炭", "化工"],
        "direction_logic": "XLE涨→A股能源/资源方向利好，但高油价压制制造业成本端",
    },
    "XLV": {
        "name": "医疗保健ETF",
        "description": "美国医疗保健行业",
        "a_share_mapped_sectors": ["医药", "医疗器械", "CXO", "生物制品"],
        "direction_logic": "XLV涨→A股医药方向情绪提振，尤其创新药/CXO对外资敏感性高",
    },
    "XLY": {
        "name": "可选消费ETF",
        "description": "美国可选消费行业（亚马逊/特斯拉/星巴克等）",
        "a_share_mapped_sectors": ["家电", "汽车", "免税", "零售"],
        "direction_logic": "XLY涨→全球消费信心回升，利好A股消费/出口链",
    },
    "XLF": {
        "name": "金融ETF",
        "description": "美国金融行业（摩根大通/高盛等）",
        "a_share_mapped_sectors": ["银行", "保险", "券商"],
        "direction_logic": "XLF涨→全球金融条件改善信号，利好A股金融板块估值修复",
    },
    "TAN": {
        "name": "太阳能ETF",
        "description": "全球太阳能/清洁能源行业",
        "a_share_mapped_sectors": ["光伏", "储能", "风电", "新能源"],
        "direction_logic": "TAN涨→A股光伏/新能源方向利好，全球绿色投资情绪共振",
    },
    "XBI": {
        "name": "生物科技ETF",
        "description": "美国生物科技/创新药行业",
        "a_share_mapped_sectors": ["CXO", "生物制品", "创新药"],
        "direction_logic": "XBI涨→A股CXO/创新药方向利好，外资对医药板块风险偏好上升",
    },
    "GDX": {
        "name": "黄金矿业ETF",
        "description": "全球黄金矿业公司",
        "a_share_mapped_sectors": ["黄金", "有色金属", "贵金属"],
        "direction_logic": "GDX涨→A股黄金/贵金属方向利好，避险需求上升或宽松预期升温",
    },
    "KWEB": {
        "name": "中概互联网ETF",
        "description": "海外上市中国互联网公司（阿里/腾讯/拼多多等）",
        "a_share_mapped_sectors": ["互联网", "传媒", "金融科技", "电商"],
        "direction_logic": "KWEB涨→中概股情绪回暖，利好A股互联网/传媒方向，外资对中国资产信心增强",
    },
}


# ============================================================
# 7. CROWDING_THRESHOLDS — 拥挤度阈值
# ============================================================

CROWDING_THRESHOLDS: dict[str, float] = {
    "tech_concentration_critical": 0.15,   # 科技成交占比 > 15% = 高度拥挤
    "tech_concentration_warning":  0.12,   # > 12% = 警戒
    "tech_concentration_watch":    0.10,   # > 10% = 关注
    "sector_turnover_spike":       2.0,    # 板块换手率 > 5日均值的2倍 = 异动
    "crowding_score_high":         7.0,    # 拥挤度评分 > 7 = 高位（减仓信号）
    "crowding_score_low":          3.0,    # < 3 = 低位（关注信号）
    "volume_ratio_extreme":        2.5,    # 成交额/20日均值 > 2.5 = 极端放量
    "sentiment_divergence":        0.30,    # 涨跌比与成交额的背离阈值（相关系数 < 0.3）
    "northbound_surge":            100.0,   # 北向单日净流入 > 100亿 = 显著流入信号
}
