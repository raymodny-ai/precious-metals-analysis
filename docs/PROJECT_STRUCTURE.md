# PreciousInsight - 贵金属市场分析系统

## 项目结构

```
PreciousInsight/
├── AnalysisEngine/              # 分析引擎
│   ├── InsightAgent/            # 量化分析Agent
│   │   ├── indicators/          # 技术指标库 (28指标)
│   │   ├── risk/                # 风险管理 (VaR/压力测试)
│   │   ├── ml/                  # ML预测 (XGBoost)
│   │   ├── optimization/        # 参数优化
│   │   ├── factor_engine.py     # 多因子引擎
│   │   ├── signal_generator.py  # 信号生成器
│   │   └── simple_backtester.py # 回测引擎
│   └── LLMService/              # LLM服务
│       ├── adapters/            # LLM适配器 (4提供商)
│       ├── prompts/             # Prompt模板
│       ├── llm_service.py       # 统一服务接口
│       ├── rag_system.py        # RAG检索系统
│       └── cost_tracker.py      # 成本追踪
│
├── DataCollector/               # 数据采集层
│   ├── StockDataCollector/      # 股票数据
│   │   └── adapters/            # 5个API适配器
│   ├── USNewsCrawler/           # 新闻爬虫
│   │   └── sources/             # 多源新闻
│   └── data_validator.py        # 数据验证
│
├── NotificationSystem/          # 通知系统
│   └── stock_alert_manager.py   # 股票告警
│
├── pages/                       # Streamlit页面
│   ├── 1_📊_Dashboard.py
│   ├── 2_💰_Price_Monitor.py
│   ├── 3_📈_Stock_Monitor.py
│   ├── 4_🤖_AI_Assistant.py    # AI助手(集成量化)
│   ├── 5_📊_Quantitative_Analysis.py  # 量化分析
│   └── 6_⚡_Trading_Signals.py # 信号监控
│
├── schema/                      # 数据库Schema
├── config/                      # 配置文件
├── docs/                        # 文档
│   ├── API_REFERENCE.md         # API参考
│   ├── DEPLOYMENT.md            # 部署指南
│   └── USER_MANUAL.md           # 用户手册
│
├── tests/                       # 测试
│   ├── test_phase4_indicators.py
│   ├── test_phase4_advanced.py
│   └── verify_phase4_modules.py
│
├── app.py                       # 主应用
├── requirements.txt             # 依赖列表
├── .env.example                 # 环境变量模板
└── README.md                    # 项目说明

```

## 模块说明

### Phase 1: 数据采集 (DataCollector)
- 5个股票数据API适配器
- 多源新闻聚合 (智能去重)
- 数据验证与监控

### Phase 2: LLM服务 (LLMService)
- 4大LLM提供商集成
- RAG检索增强生成
- 成本追踪与优化

### Phase 3: RAG系统
- ChromaDB向量存储
- 时间衰减+MMR检索
- 来源追踪

### Phase 4: 量化分析 ⭐
- **indicators/**: 28个技术指标
- **factor_engine.py**: 25+因子选股
- **risk/**: VaR/CVaR + 压力测试
- **signal_generator.py**: 多策略信号
- **ml/**: XGBoost预测
- **simple_backtester.py**: 回测引擎
- **optimization/**: 参数优化

### UI层 (pages/)
6个Streamlit页面:
1. 主页概览
2. 价格监控
3. 股票监控
4. AI助手 (集成量化上下文)
5. 量化分析 (5个Tab)
6. 信号监控

---

## 代码统计

- **总代码量**: ~10,000行
- **Python文件**: 60+个
- **Streamlit页面**: 6个
- **API适配器**: 9个
- **技术指标**: 28个
- **ML模型**: 1个 (XGBoost)

---

## 核心依赖

```
pandas, numpy               # 数据处理
streamlit, plotly          # UI可视化
mysql-connector-python     # 数据库
openai, anthropic          # LLM
chromadb                   # 向量存储
xgboost, scikit-learn      # 机器学习
scipy, arch                # 量化分析
```

详见 [requirements.txt](../requirements.txt)

---

## 开发规范

### 代码风格
- PEP 8
- 类型注解
- Docstring (Google风格)

### 命名规范
- 类: PascalCase
- 函数/变量: snake_case
- 常量: UPPER_CASE
- 私有: _leading_underscore

### Git提交规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
refactor: 代码重构
test: 测试相关
chore: 构建/工具相关
```

---

更多详情见 [README.md](../README.md)
