"""
Input Validation with Pydantic v2
输入验证模型
"""

from datetime import date, datetime
from typing import Optional, List, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============================================================================
# Constants
# ============================================================================

ALLOWED_SYMBOLS = ['GLD', 'IAU', 'GLDM', 'SGOL', 'PHYS', 'SLV', 'SIVR', 'PSLV', 'AGQ']
ALLOWED_INTERVALS = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']


# ============================================================================
# Price Data Validators
# ============================================================================

class PriceQuery(BaseModel):
    """Price data query parameters"""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    start_date: Optional[date] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="End date (YYYY-MM-DD)")
    interval: str = Field("1d", description="Data interval")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ALLOWED_SYMBOLS:
            raise ValueError(f"Invalid symbol. Allowed: {', '.join(ALLOWED_SYMBOLS)}")
        return v
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ALLOWED_INTERVALS:
            raise ValueError(f"Invalid interval. Allowed: {', '.join(ALLOWED_INTERVALS)}")
        return v
    
    @model_validator(mode='after')
    def validate_date_range(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before or equal to end_date")
        return self


class LatestPriceQuery(BaseModel):
    """Latest price query parameters"""
    
    symbols: Optional[str] = Field(None, description="Comma-separated symbols")
    
    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        symbols = [s.strip().upper() for s in v.split(',')]
        invalid = [s for s in symbols if s not in ALLOWED_SYMBOLS]
        
        if invalid:
            raise ValueError(f"Invalid symbols: {', '.join(invalid)}")
        
        return ','.join(symbols)


# ============================================================================
# ETF Flow Validators
# ============================================================================

class ETFFlowQuery(BaseModel):
    """ETF flow query parameters"""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ALLOWED_SYMBOLS:
            raise ValueError(f"Invalid symbol. Allowed: {', '.join(ALLOWED_SYMBOLS)}")
        return v


# ============================================================================
# News & Sentiment Validators
# ============================================================================

class NewsQuery(BaseModel):
    """News query parameters"""
    
    symbol: Optional[str] = Field(None, description="Filter by symbol")
    limit: int = Field(50, ge=1, le=200)
    include_sentiment: bool = True
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.upper().strip()


class SentimentAnalysisRequest(BaseModel):
    """Request for sentiment analysis"""
    
    text: str = Field(..., min_length=10, max_length=10000)
    model: Literal['finbert', 'deepseek', 'hybrid'] = 'finbert'
    
    @field_validator('text')
    @classmethod
    def clean_text(cls, v: str) -> str:
        # Remove excessive whitespace
        return ' '.join(v.split())


class BatchSentimentRequest(BaseModel):
    """Batch sentiment analysis request"""
    
    texts: List[str] = Field(..., min_length=1, max_length=100)
    model: Literal['finbert', 'deepseek', 'hybrid'] = 'finbert'


# ============================================================================
# Prediction Validators
# ============================================================================

class PredictionQuery(BaseModel):
    """Prediction query parameters"""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    horizon: int = Field(1, ge=1, le=30, description="Prediction horizon in days")
    model: Optional[str] = Field(None, description="Specific model to use")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ALLOWED_SYMBOLS:
            raise ValueError(f"Invalid symbol. Allowed: {', '.join(ALLOWED_SYMBOLS)}")
        return v


# ============================================================================
# User/Auth Validators
# ============================================================================

class UserCreate(BaseModel):
    """User registration request"""
    
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=100)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    """User login request"""
    
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


# ============================================================================
# Alert Validators
# ============================================================================

class AlertConfig(BaseModel):
    """Alert configuration"""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    alert_type: Literal['price', 'flow', 'sentiment', 'prediction']
    threshold: float = Field(..., description="Threshold value")
    direction: Literal['above', 'below', 'any'] = 'any'
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().strip()


# ============================================================================
# Common Response Models
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    
    page: int = Field(1, ge=1, le=10000)
    per_page: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class DateRangeParams(BaseModel):
    """Date range parameters"""
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = Field(None, ge=1, le=365)
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.days and (self.start_date or self.end_date):
            raise ValueError("Cannot specify both 'days' and date range")
        return self


if __name__ == "__main__":
    print("Testing Validators...")
    
    # Test price query
    try:
        q = PriceQuery(symbol="gld", interval="1D")
        print(f"PriceQuery: {q.symbol}, {q.interval}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test invalid symbol
    try:
        q = PriceQuery(symbol="INVALID")
    except Exception as e:
        print(f"Expected error: {e}")
    
    # Test user creation
    try:
        u = UserCreate(email="Test@Example.COM", password="Password123")
        print(f"User: {u.email}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nValidators test complete!")
