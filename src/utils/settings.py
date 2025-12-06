"""
Centralized Settings Configuration
集中配置管理 - 优化项 #19
"""

from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Centralized application settings using Pydantic
    All settings can be overridden via environment variables
    """
    
    # =========================================================================
    # Application
    # =========================================================================
    app_name: str = "Precious Metals Analysis System"
    app_version: str = "2.0.0"
    environment: str = Field("development", description="development, staging, production")
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_prefix: str = "/api/v1"
    
    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = Field(
        "postgresql://postgres:postgres@localhost:5432/precious_metals",
        description="PostgreSQL connection string"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_echo: bool = False
    
    # =========================================================================
    # Redis
    # =========================================================================
    redis_url: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection string"
    )
    redis_ttl_default: int = 300  # 5 minutes
    redis_ttl_price: int = 60     # 1 minute
    redis_ttl_news: int = 300     # 5 minutes
    redis_ttl_sentiment: int = 600  # 10 minutes
    redis_max_connections: int = 50
    
    # =========================================================================
    # Rate Limiting
    # =========================================================================
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    rate_limit_burst: int = 10
    
    # =========================================================================
    # Authentication
    # =========================================================================
    jwt_secret_key: str = Field(
        "change_this_in_production",
        description="JWT signing secret key"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # =========================================================================
    # External APIs
    # =========================================================================
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_api_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    
    # FRED
    fred_api_key: Optional[str] = None
    
    # News API
    news_api_key: Optional[str] = None
    
    # =========================================================================
    # ML Models
    # =========================================================================
    model_path: str = "models/"
    model_default_timeout: int = 5  # seconds
    model_cache_predictions: bool = True
    
    # Prediction settings
    prediction_confidence_threshold: float = 0.7
    prediction_horizon_default: int = 1  # days
    
    # =========================================================================
    # Data Collection
    # =========================================================================
    data_sync_enabled: bool = True
    data_sync_interval_minutes: int = 60
    data_retention_days: int = 365
    
    # Symbols
    gold_etf_symbols: List[str] = ["GLD", "IAU", "GLDM", "SGOL", "PHYS"]
    silver_etf_symbols: List[str] = ["SLV", "SIVR", "PSLV", "AGQ"]
    
    # =========================================================================
    # Monitoring
    # =========================================================================
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    log_level: str = "INFO"
    log_format: str = "json"  # json or console
    
    # =========================================================================
    # Kafka (Optional)
    # =========================================================================
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prices: str = "prices"
    kafka_topic_news: str = "news"
    kafka_consumer_group: str = "precious-metals"
    
    # =========================================================================
    # Cost Control - 优化项 #20
    # =========================================================================
    api_budget_enabled: bool = True
    api_daily_budget_usd: float = 10.0
    api_alert_threshold_pct: float = 80.0  # Alert at 80% of budget
    
    # =========================================================================
    # Security
    # =========================================================================
    encryption_key: Optional[str] = None  # For encrypting sensitive data
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def all_symbols(self) -> List[str]:
        """Get all ETF symbols"""
        return self.gold_etf_symbols + self.silver_etf_symbols
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export singleton
settings = get_settings()


if __name__ == "__main__":
    print("Current Settings:")
    print(f"  Environment: {settings.environment}")
    print(f"  API: {settings.api_host}:{settings.api_port}")
    print(f"  Database: {settings.database_url[:30]}...")
    print(f"  Redis: {settings.redis_url}")
    print(f"  All Symbols: {settings.all_symbols}")
    print(f"  Rate Limit: {settings.rate_limit_per_minute}/min")
