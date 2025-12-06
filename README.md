# 🥇 Precious Metals Market Analysis System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**贵金属市场情绪分析与预测系统** - 基于NLP和机器学习的黄金/白银ETF资金流向分析平台

## ✨ Features

- 📈 **Real-time Data Collection** - 价格、新闻、ETF资金流向
- 🧠 **NLP Sentiment Analysis** - FinBERT + DeepSeek 混合情绪分析
- 🤖 **ML Price Prediction** - LSTM, CNN-LSTM-Attention, TabNet, XGBoost 集成模型
- 📊 **Backtesting System** - 完整策略回测框架
- ⚡ **Real-time Pipeline** - Kafka 实时数据流处理
- 📅 **Task Scheduling** - Airflow DAG 定时任务
- 📉 **Monitoring** - Prometheus + Grafana 监控
- 🔐 **Authentication** - JWT 用户认证

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (with TimescaleDB)
- Redis 7+
- Node.js 18+ (for frontend)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/precious-metals-analysis.git
cd precious-metals-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
psql -U postgres -f scripts/init_database.sql

# Run API server
uvicorn src.api.main:app --reload
```

### Docker Deployment

```bash
# Build and run all services
docker-compose up -d

# Check status
docker-compose ps
```

### Kubernetes Deployment

```bash
kubectl apply -f k8s/
```

## 📁 Project Structure

```
precious_metals/
├── src/
│   ├── api/                 # FastAPI application
│   ├── data_collection/     # Data fetchers
│   ├── nlp/                 # NLP & sentiment analysis
│   ├── ml/                  # Machine learning models
│   ├── etf/                 # ETF analysis & alerts
│   ├── backtest/            # Backtesting framework
│   └── utils/               # Utilities & helpers
├── frontend/                # React dashboard
├── tests/                   # Test suites
├── k8s/                     # Kubernetes configs
├── scripts/                 # Database & utility scripts
├── configs/                 # Configuration files
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prices/{symbol}` | GET | Historical price data |
| `/api/v1/prices/latest` | GET | Latest prices |
| `/api/v1/etf/flows/{symbol}` | GET | ETF fund flows |
| `/api/v1/news` | GET | News with sentiment |
| `/api/v1/sentiment/dashboard/{symbol}` | GET | Sentiment metrics |
| `/api/v1/predictions/{symbol}` | GET | Price predictions |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/register` | POST | User registration |
| `/ws/prices` | WebSocket | Real-time prices |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/test_integration.py -v
```

## 📊 Supported Symbols

**Gold ETFs**: GLD, IAU, GLDM, SGOL, PHYS

**Silver ETFs**: SLV, SIVR, PSLV, AGQ

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API key | Optional |
| `FRED_API_KEY` | FRED API key | Optional |
| `NEWS_API_KEY` | News API key | Optional |
| `JWT_SECRET_KEY` | JWT signing key | ✅ |

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [FinBERT](https://github.com/ProsusAI/finBERT) for financial sentiment analysis
- [yfinance](https://github.com/ranaroussi/yfinance) for market data
- [FastAPI](https://fastapi.tiangolo.com) for the API framework
