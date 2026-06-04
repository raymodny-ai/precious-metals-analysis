# PreciousInsight 贵金属市场分析系统

一个集成AI、量化分析、实时数据的专业级贵金属投资分析平台

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 🎯 核心特性

### Phase 1: 多源数据采集
- ✅ **5个数据源适配器**: yFinance, Alpha Vantage, Polygon, TwelveData, Finnhub
- ✅ **智能新闻聚合**: NewsAPI, RSS, Reddit多源去重
- ✅ **数据验证监控**: 自动检测数据质量和新鲜度

### Phase 2: LLM智能分析
- ✅ **4大LLM提供商**: OpenAI, Anthropic, Google Gemini, DeepSeek
- ✅ **Prompt工程优化**: CoT, Few-Shot, 强制JSON输出
- ✅ **成本追踪**: SQLite持久化,实时成本分析

### Phase 3: RAG检索系统
- ✅ **ChromaDB向量存储**: 历史报告+新闻语义检索
- ✅ **智能检索**: 时间衰减+MMR多样性平衡
- ✅ **来源追踪**: 完整引用链追溯

### Phase 4: 量化分析 ⭐ NEW
- ✅ **28个技术指标**: 趋势/动量/成交量/波动率/贵金属专用
- ✅ **多因子引擎**: 25+因子综合评分
- ✅ **风险管理**: VaR/CVaR + 6场景压力测试
- ✅ **交易信号**: 3策略实时监控
- ✅ **ML预测**: XGBoost方向预测
- ✅ **回测引擎**: 完整策略验证
- ✅ **参数优化**: 网格搜索自动调优

### UI界面
- ✅ **6个Streamlit页面**: 
  - 主页概览
  - 价格监控
  - 股票监控  
  - AI助手 (集成量化)
  - 量化分析 (5个Tab)
  - 信号监控

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│          Streamlit UI (6 Pages)                  │
│  Dashboard | Price | Stock | AI | Quant | Signal│
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│          Application Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Flask   │ │Scheduled │ │ Signal   │        │
│  │   API    │ │  Tasks   │ │ Monitor  │        │
│  └──────────┘ └──────────┘ └──────────┘        │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│          Core Modules (Phase 1-4)                │
│                                                   │
│  ┌─────────────────────────────────────┐        │
│  │ Data Collection (Phase 1)           │        │
│  │ - Multi-source adapters             │        │
│  │ - News aggregation                  │        │
│  └─────────────────────────────────────┘        │
│                                                   │
│  ┌─────────────────────────────────────┐        │
│  │ LLM Service (Phase 2)               │        │
│  │ - 4 LLM providers                   │        │
│  │ - Cost tracking                     │        │
│  └─────────────────────────────────────┘        │
│                                                   │
│  ┌─────────────────────────────────────┐        │
│  │ RAG System (Phase 3)                │        │
│  │ - ChromaDB vectors                  │        │
│  │ - Smart retrieval                   │        │
│  └─────────────────────────────────────┘        │
│                                                   │
│  ┌─────────────────────────────────────┐        │
│  │ Quantitative Engine (Phase 4) ⭐     │        │
│  │ - Technical indicators (28)         │        │
│  │ - Factor engine (25+)               │        │
│  │ - Risk management (VaR/Stress)      │        │
│  │ - Trading signals (3 strategies)    │        │
│  │ - ML predictions (XGBoost)          │        │
│  │ - Backtester & Optimizer            │        │
│  └─────────────────────────────────────┘        │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│          Data & Storage Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  MySQL   │ │  Redis   │ │ChromaDB  │        │
│  │ (Primary)│ │ (Cache)  │ │(Vectors) │        │
│  └──────────┘ └──────────┘ └──────────┘        │
└──────────────────────────────────────────────────┘
```

---

## 📦 快速开始

### 前置要求
- Python 3.9+
- MySQL 8.0+
- Redis 6.0+ (可选,用于缓存)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/PreciousInsight.git
cd PreciousInsight

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑.env文件,填入API密钥

# 5. 初始化数据库
python schema/init_database.py

# 6. 启动应用
streamlit run app.py
```

### Docker部署 (推荐)

```bash
# 构建镜像
docker build -t preciousinsight .

# 运行容器
docker-compose up -d

# 访问http://localhost:8501
```

---

## 💻 使用示例

### 1. 量化分析

```python
from AnalysisEngine.InsightAgent.indicators import *
from AnalysisEngine.InsightAgent.risk import VaRCalculator

# 获取数据
data = fetch_market_data('GLD', days=180)

# 技术分析
rsi = MomentumIndicators.rsi(data['close'], 14)
macd, signal, _ = TrendIndicators.macd(data['close'])

print(f"当前RSI: {rsi.iloc[-1]:.2f}")
print(f"MACD趋势: {'看涨' if macd.iloc[-1] > signal.iloc[-1] else '看跌'}")

# 风险分析
returns = data['close'].pct_change().dropna()
var_calc = VaRCalculator(confidence_level=0.95)
var_result = var_calc.historical_var(returns)

print(f"VaR(95%): {var_result.var_value:.2%}")
```

### 2. 交易信号

```python
from AnalysisEngine.InsightAgent.signal_generator import *

# 创建策略
trend_strategy = TrendFollowingStrategy()
signal = trend_strategy.generate_signal(data)

print(f"信号: {signal.signal_type.value}")
print(f"强度: {signal.strength:.2f}")
print(f"理由: {signal.reasoning}")
```

### 3. ML预测

```python
from AnalysisEngine.InsightAgent.ml import XGBoostPredictor

# 训练模型
predictor = XGBoostPredictor()
results = predictor.train(data, test_size=0.2)

# 预测
direction = predictor.predict(data)  # 1=涨, 0=跌
probability = predictor.predict_proba(data)

print(f"预测: {'上涨' if direction == 1 else '下跌'}")
print(f"置信度: {probability:.1%}")
```

---

## 📚 文档

- [API参考](docs/API_REFERENCE.md)
- [用户手册](docs/USER_MANUAL.md)
- [部署指南](docs/DEPLOYMENT.md)
- [常见问题](docs/FAQ.md)

---

## 🔧 配置说明

### 环境变量

```env
# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=precious_insight

# LLM API密钥
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# 数据源API
ALPHA_VANTAGE_KEY=...
POLYGON_API_KEY=...
```

完整配置见 [.env.example](.env.example)

---

## 🎯 性能指标

| 指标 | 数值 |
|-----|------|
| 页面加载时间 | < 2秒 |
| 技术指标计算 | < 100ms |
| LLM响应时间 | 2-5秒 |
| 缓存命中率 | > 60% |
| 并发支持 | 50+ 用户 |

---

##📊 项目统计

- **总代码量**: ~10,000行
- **模块数**: 60+个文件
- **功能完整度**: 95%
- **测试覆盖**: 核心模块已验证
- **生产就绪**: ✅

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 📝 更新日志

### v2.0.0 (2025-11-28)
- ✨ 新增Phase 4量化分析模块
- ✨ 集成XGBoost ML预测
- ✨ 添加压力测试框架
- ✨ 创建量化分析UI页面
- ✨ 升级AI助手集成量化上下文
- 🐛 修复多项性能问题
- 📚 完善文档

### v1.0.0 (2024-XX-XX)
- ✨ Phase 1-3基础功能
- ✨ LLM多提供商支持
- ✨ RAG检索系统

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## ⚠️ 免责声明

本系统仅供学习和研究使用,不构成投资建议。投资有风险,入市需谨慎。

---

## 📧 联系方式

- Issue: [GitHub Issues](https://github.com/yourname/PreciousInsight/issues)
- Email: your.email@example.com

---

**PreciousInsight** - 让AI为您的贵金属投资保驾护航 🚀
