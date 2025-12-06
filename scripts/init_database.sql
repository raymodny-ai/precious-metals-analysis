-- ============================================================================
-- 贵金属市场分析系统 - 数据库Schema
-- Precious Metals Market Analysis System - Database Schema
-- PostgreSQL + TimescaleDB
-- ============================================================================

-- 启用 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 资产维度表 (Assets Dimension Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,  -- 'gold_etf', 'silver_etf', 'futures', 'index'
    exchange VARCHAR(20),
    currency VARCHAR(10) DEFAULT 'USD',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入基础资产数据
INSERT INTO assets (symbol, name, asset_type, exchange) VALUES
    -- 黄金 ETF
    ('GLD', 'SPDR Gold Shares', 'gold_etf', 'NYSE'),
    ('IAU', 'iShares Gold Trust', 'gold_etf', 'NYSE'),
    ('GLDM', 'SPDR Gold MiniShares Trust', 'gold_etf', 'NYSE'),
    ('SGOL', 'Aberdeen Standard Physical Swiss Gold Shares', 'gold_etf', 'NYSE'),
    -- 白银 ETF
    ('SLV', 'iShares Silver Trust', 'silver_etf', 'NYSE'),
    ('SIVR', 'Aberdeen Standard Physical Silver Shares', 'silver_etf', 'NYSE'),
    ('AGQ', 'ProShares Ultra Silver', 'silver_etf', 'NYSE'),
    -- 宏观指标
    ('DXY', 'US Dollar Index', 'index', 'ICE'),
    ('VIX', 'CBOE Volatility Index', 'index', 'CBOE'),
    ('TNX', '10-Year Treasury Yield', 'index', 'CBOE')
ON CONFLICT (symbol) DO NOTHING;

-- ============================================================================
-- 2. 价格数据超表 (Price Data Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open FLOAT8,
    high FLOAT8,
    low FLOAT8,
    close FLOAT8 NOT NULL,
    volume FLOAT8,
    adj_close FLOAT8,
    source VARCHAR(20) DEFAULT 'yfinance',
    PRIMARY KEY (symbol, time)
);

-- 转换为超表
SELECT create_hypertable('price_data', 'time', 
    partitioning_column => 'symbol',
    number_partitions => 4,
    if_not_exists => TRUE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_price_time_symbol ON price_data (time DESC, symbol);
CREATE INDEX IF NOT EXISTS idx_price_symbol_time ON price_data (symbol, time DESC);

-- ============================================================================
-- 3. 新闻文章超表 (News Articles Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_articles (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20),
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    url TEXT,
    author VARCHAR(100),
    -- 情绪分析结果
    sentiment_positive FLOAT8,
    sentiment_negative FLOAT8,
    sentiment_neutral FLOAT8,
    sentiment_score FLOAT8,  -- 综合得分 (-1 to +1)
    sentiment_label VARCHAR(20),  -- 'positive', 'negative', 'neutral'
    -- 元数据
    keywords TEXT[],
    language VARCHAR(10) DEFAULT 'en',
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, time)
);

-- 转换为超表
SELECT create_hypertable('news_articles', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_news_symbol_time ON news_articles (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles (sentiment_score DESC);
CREATE INDEX IF NOT EXISTS idx_news_processed ON news_articles (processed) WHERE processed = FALSE;

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_news_title_search ON news_articles 
    USING GIN (to_tsvector('english', title));

-- ============================================================================
-- 4. ETF资金流超表 (ETF Flows Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS etf_flows (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- 资金流数据
    net_flow FLOAT8,  -- 净流入(正)/流出(负) 美元
    shares_outstanding FLOAT8,  -- 流通份额
    aum FLOAT8,  -- 管理资产规模
    -- 变化率
    flow_change_1d FLOAT8,
    flow_change_5d FLOAT8,
    flow_change_20d FLOAT8,
    -- 元数据
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, time)
);

-- 转换为超表
SELECT create_hypertable('etf_flows', 'time',
    partitioning_column => 'symbol',
    number_partitions => 4,
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_etf_flows_time ON etf_flows (time DESC);
CREATE INDEX IF NOT EXISTS idx_etf_flows_symbol_time ON etf_flows (symbol, time DESC);

-- ============================================================================
-- 5. ETF持有者表 (ETF Holders Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS etf_holders (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    holder_name VARCHAR(200) NOT NULL,
    shares FLOAT8,
    value_usd FLOAT8,
    percent_of_fund FLOAT8,
    report_date DATE,
    holder_type VARCHAR(50),  -- 'institutional', 'mutual_fund', 'etf'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, holder_name, report_date)
);

CREATE INDEX IF NOT EXISTS idx_holders_symbol ON etf_holders (symbol);

-- ============================================================================
-- 6. 情绪指标超表 (Sentiment Metrics Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sentiment_metrics (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    interval_type VARCHAR(10) NOT NULL,  -- 'hourly', 'daily'
    -- 汇总指标
    sentiment_index FLOAT8,  -- 综合情绪指数 (0-100)
    bullish_ratio FLOAT8,  -- 看涨比例
    bearish_ratio FLOAT8,  -- 看跌比例
    news_volume INT,  -- 新闻数量
    avg_sentiment FLOAT8,  -- 平均情绪得分
    sentiment_std FLOAT8,  -- 情绪波动
    -- 变化率
    sentiment_change_1d FLOAT8,
    sentiment_change_5d FLOAT8,
    -- 热度指标
    heat_index FLOAT8,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, interval_type, time)
);

-- 转换为超表
SELECT create_hypertable('sentiment_metrics', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_metrics (symbol, time DESC);

-- ============================================================================
-- 7. 相关性分析表 (Correlation Analysis Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS correlation_analysis (
    id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    symbol1 VARCHAR(20) NOT NULL,
    symbol2 VARCHAR(20) NOT NULL,
    correlation_type VARCHAR(50) NOT NULL,  -- 'price', 'sentiment', 'flow'
    lookback_days INT NOT NULL,
    correlation_value FLOAT8 NOT NULL,
    p_value FLOAT8,
    is_significant BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (analysis_date, symbol1, symbol2, correlation_type, lookback_days)
);

CREATE INDEX IF NOT EXISTS idx_correlation_date ON correlation_analysis (analysis_date DESC);

-- ============================================================================
-- 8. 交易信号表 (Trading Signals Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- 信号信息
    signal_type VARCHAR(20) NOT NULL,  -- 'BUY', 'SELL', 'HOLD'
    signal_strength VARCHAR(20),  -- 'STRONG', 'MODERATE', 'WEAK'
    confidence FLOAT8,  -- 置信度 (0-1)
    -- 预测信息
    predicted_price FLOAT8,
    predicted_return FLOAT8,
    prediction_horizon INT,  -- 预测天数
    -- 模型信息
    model_name VARCHAR(50),
    model_version VARCHAR(20),
    -- 特征重要性
    feature_importance JSONB,
    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON trading_signals (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_type ON trading_signals (signal_type);

-- ============================================================================
-- 9. 连续聚合视图 (Continuous Aggregates)
-- ============================================================================

-- 小时级价格聚合
CREATE MATERIALIZED VIEW IF NOT EXISTS price_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket(INTERVAL '1 hour', time) AS hour,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM price_data
GROUP BY hour, symbol
WITH NO DATA;

-- 日级价格聚合
CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket(INTERVAL '1 day', time) AS day,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume,
    -- 技术指标基础
    AVG(close) AS avg_close,
    STDDEV(close) AS std_close
FROM price_data
GROUP BY day, symbol
WITH NO DATA;

-- 日情绪汇总
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_sentiment_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', time) AS day,
    symbol,
    COUNT(*) AS news_count,
    AVG(sentiment_score) AS avg_sentiment,
    STDDEV(sentiment_score) AS sentiment_volatility,
    SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
    SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
    SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral_count
FROM news_articles
WHERE symbol IS NOT NULL
GROUP BY day, symbol
WITH NO DATA;

-- 添加刷新策略
SELECT add_continuous_aggregate_policy('price_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('price_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('daily_sentiment_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- 10. 数据压缩策略 (Compression Policies)
-- ============================================================================

-- 价格数据压缩
ALTER TABLE price_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('price_data', INTERVAL '7 days', if_not_exists => TRUE);

-- 新闻数据压缩
ALTER TABLE news_articles SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('news_articles', INTERVAL '7 days', if_not_exists => TRUE);

-- ETF流量数据压缩
ALTER TABLE etf_flows SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('etf_flows', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================================
-- 11. 数据保留策略 (Retention Policies)
-- ============================================================================

SELECT add_retention_policy('price_data', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('news_articles', INTERVAL '3 years', if_not_exists => TRUE);
SELECT add_retention_policy('etf_flows', INTERVAL '10 years', if_not_exists => TRUE);
SELECT add_retention_policy('sentiment_metrics', INTERVAL '2 years', if_not_exists => TRUE);

-- ============================================================================
-- 完成提示
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Database schema created successfully!';
    RAISE NOTICE 'Tables: assets, price_data, news_articles, etf_flows, etf_holders, sentiment_metrics, correlation_analysis, trading_signals';
    RAISE NOTICE 'Continuous Aggregates: price_hourly, price_daily, daily_sentiment_summary';
    RAISE NOTICE 'Compression and retention policies configured.';
END $$;
