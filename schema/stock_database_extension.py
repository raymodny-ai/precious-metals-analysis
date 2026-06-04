"""
股票数据数据库扩展
为美股监察功能添加新表
"""
import mysql.connector
import os
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': os.getenv('DB_PASSWORD', 'your_password'),
    'database': 'precious_insight'
}

def create_stock_tables():
    """创建股票相关数据表"""
    
    # 连接数据库
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("创建股票数据库表...")
    
    # 1. 股票价格表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_prices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        price DECIMAL(10, 2),
        previous_close DECIMAL(10, 2),
        change_amount DECIMAL(10, 2),
        change_percent DECIMAL(8, 4),
        volume BIGINT,
        market_cap BIGINT,
        pe_ratio DECIMAL(8, 2),
        timestamp DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol_timestamp (symbol, timestamp),
        INDEX idx_timestamp (timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✓ 创建 stock_prices 表")
    
    # 2. 股票元数据表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_metadata (
        symbol VARCHAR(20) PRIMARY KEY,
        company_name VARCHAR(200),
        sector VARCHAR(100),
        industry VARCHAR(100),
        category VARCHAR(50) COMMENT 'ETF, Mining, Index等',
        market_cap BIGINT,
        pe_ratio DECIMAL(8, 2),
        forward_pe DECIMAL(8, 2),
        price_to_book DECIMAL(8, 2),
        dividend_yield DECIMAL(6, 4),
        eps DECIMAL(10, 2),
        revenue BIGINT,
        week_52_high DECIMAL(10, 2),
        week_52_low DECIMAL(10, 2),
        avg_volume BIGINT,
        gold_correlation DECIMAL(5, 4) COMMENT '与金价相关系数',
        website VARCHAR(500),
        description TEXT,
        last_updated DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_category (category),
        INDEX idx_correlation (gold_correlation)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✓ 创建 stock_metadata 表")
    
    # 3. 股票新闻表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_news (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20),
        title TEXT,
        content TEXT,
        url VARCHAR(500),
        source VARCHAR(100),
        published_at DATETIME,
        sentiment_label VARCHAR(20),
        sentiment_score DECIMAL(5, 4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol_published (symbol, published_at),
        INDEX idx_sentiment (sentiment_label),
        FULLTEXT INDEX ft_content (content)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✓ 创建 stock_news 表")
    
    # 4. 股票预警表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        alert_type VARCHAR(50) COMMENT 'price_breakout, rsi_oversold, correlation_divergence等',
        alert_message TEXT,
        trigger_value DECIMAL(10, 2),
        current_value DECIMAL(10, 2),
        severity VARCHAR(20) DEFAULT 'info' COMMENT 'info, warning, critical',
        status VARCHAR(20) DEFAULT 'active' COMMENT 'active, acknowledged, resolved',
        triggered_at DATETIME,
        acknowledged_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol_status (symbol, status),
        INDEX idx_triggered (triggered_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✓ 创建 stock_alerts 表")
    
    # 5. 股票-贵金属关联表（用于存储相关性数据）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_metal_correlation (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stock_symbol VARCHAR(20),
        metal_type VARCHAR(50),
        correlation_coefficient DECIMAL(5, 4),
        period_days INT COMMENT '计算周期（天数）',
        calculation_date DATE,
        INDEX idx_stock_metal (stock_symbol, metal_type),
        INDEX idx_calculation_date (calculation_date),
        UNIQUE KEY unique_stock_metal_date (stock_symbol, metal_type, calculation_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✓ 创建 stock_metal_correlation 表")
    
    # 提交更改
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n数据库表创建完成!")

def insert_sample_metadata():
    """插入示例股票元数据"""
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("\n插入示例股票元数据...")
    
    sample_stocks = [
        ('GLD', 'SPDR Gold Shares', 'N/A', 'Exchange Traded Fund', 'ETF'),
        ('SLV', 'iShares Silver Trust', 'N/A', 'Exchange Traded Fund', 'ETF'),
        ('GDX', 'VanEck Gold Miners ETF', 'N/A', 'Exchange Traded Fund', 'ETF'),
        ('NEM', 'Newmont Corporation', 'Basic Materials', 'Gold', 'Mining'),
        ('GOLD', 'Barrick Gold Corporation', 'Basic Materials', 'Gold', 'Mining'),
        ('AEM', 'Agnico Eagle Mines', 'Basic Materials', 'Gold', 'Mining'),
        ('WPM', 'Wheaton Precious Metals', 'Basic Materials', 'Other Precious Metals & Mining', 'Mining'),
        ('FNV', 'Franco-Nevada Corporation', 'Basic Materials', 'Gold', 'Mining'),
    ]
    
    for symbol, name, sector, industry, category in sample_stocks:
        try:
            cursor.execute("""
            INSERT INTO stock_metadata 
            (symbol, company_name, sector, industry, category, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            company_name = VALUES(company_name),
            sector = VALUES(sector),
            industry = VALUES(industry),
            category = VALUES(category),
            last_updated = VALUES(last_updated)
            """, (symbol, name, sector, industry, category, datetime.now()))
            print(f"  ✓ {symbol} - {name}")
        except Exception as e:
            print(f"  ✗ {symbol} 插入失败: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n示例数据插入完成!")

def verify_tables():
    """验证表创建"""
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("\n验证数据库表...")
    
    tables = [
        'stock_prices',
        'stock_metadata',
        'stock_news',
        'stock_alerts',
        'stock_metal_correlation'
    ]
    
    for table in tables:
        cursor.execute(f"SHOW TABLES LIKE '{table}'")
        result = cursor.fetchone()
        if result:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table} (记录数: {count})")
        else:
            print(f"  ✗ {table} 不存在")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    print("="*60)
    print("PreciousInsight 股票数据库扩展")
    print("="*60)
    
    try:
        create_stock_tables()
        insert_sample_metadata()
        verify_tables()
        
        print("\n" + "="*60)
        print("✅ 数据库扩展完成!")
        print("="*60)
        
    except mysql.connector.Error as e:
        print(f"\n❌ 数据库错误: {e}")
        print("\n请确保:")
        print("  1. MySQL服务正在运行")
        print("  2. 数据库 'precious_insight' 已创建")
        print("  3. DB_PASSWORD 环境变量已设置")
