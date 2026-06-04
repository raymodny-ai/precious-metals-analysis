"""
Logging Configuration
日志配置模块
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from pythonjsonlogger import jsonlogger

from .config import get_settings, LOGS_DIR


def setup_logging(name: str = "precious_metals") -> logging.Logger:
    """Setup application logging with JSON format"""
    
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    return logger


# Default logger instance
logger = setup_logging()
