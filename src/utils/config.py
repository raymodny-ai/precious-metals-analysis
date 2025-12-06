"""
Application Configuration Module
应用配置模块
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Precious Metals Analysis System"
    debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/precious_metals"
    timescale_enabled: bool = True
    
    # API Keys
    fred_api_key: Optional[str] = None
    news_api_key: Optional[str] = None
    fmp_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Model Settings
    model_dir: Path = Path("./models")
    finbert_model: str = "ProsusAI/finbert"
    
    # Data Collection Settings
    price_update_interval: int = 60  # seconds
    news_update_interval: int = 300  # seconds
    etf_update_interval: int = 3600  # seconds
    
    # ETF Symbols
    gold_etfs: list = ["GLD", "IAU", "GLDM", "SGOL"]
    silver_etfs: list = ["SLV", "SIVR", "AGQ"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
CONFIGS_DIR = PROJECT_ROOT / "configs"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if not exist
for dir_path in [MODELS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
