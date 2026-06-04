-- PreciousInsight Stock Monitoring Schema

-- 1. 贵金属价格表
CREATE TABLE IF NOT EXISTS metal_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    metal_type VARCHAR(50) NOT NULL COMMENT 'gold, silver, platinum, palladium',
    price DECIMAL(12, 4) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    source VARCHAR(50) DEFAULT 'unknown',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metal_time (metal_type, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 股票基本信息表
CREATE TABLE IF NOT EXISTS stock_info (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    description TEXT,
    currency VARCHAR(10) DEFAULT 'USD',
    market_cap BIGINT,
    pe_ratio DECIMAL(10, 2),
    dividend_yield DECIMAL(10, 4),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 股票价格历史表
CREATE TABLE IF NOT EXISTS stock_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    adj_close DECIMAL(12, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY idx_symbol_date (symbol, date),
    FOREIGN KEY (symbol) REFERENCES stock_info(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 股票新闻表
CREATE TABLE IF NOT EXISTS stock_news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    source VARCHAR(100),
    published_at TIMESTAMP,
    summary TEXT,
    sentiment_score DECIMAL(5, 4) COMMENT '-1 to 1',
    sentiment_label VARCHAR(20) COMMENT 'positive, negative, neutral',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_pub (symbol, published_at),
    FOREIGN KEY (symbol) REFERENCES stock_info(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 股票预警记录表
CREATE TABLE IF NOT EXISTS stock_alerts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL COMMENT 'PRICE_BREAKOUT, PERCENT_CHANGE, etc.',
    severity VARCHAR(20) DEFAULT 'MEDIUM' COMMENT 'LOW, MEDIUM, HIGH',
    message TEXT,
    trigger_data JSON COMMENT 'Snapshot of data that triggered alert',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_created (symbol, created_at),
    FOREIGN KEY (symbol) REFERENCES stock_info(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 股票与黄金相关性表
CREATE TABLE IF NOT EXISTS stock_metal_correlation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    metal_type VARCHAR(50) DEFAULT 'gold',
    period VARCHAR(20) DEFAULT '3mo' COMMENT '1mo, 3mo, 6mo, 1y',
    correlation_coefficient DECIMAL(6, 4) NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_metal (symbol, metal_type),
    FOREIGN KEY (symbol) REFERENCES stock_info(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
