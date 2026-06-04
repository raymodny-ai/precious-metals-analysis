"""
JWT Authentication Module
JWT认证模块
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("auth")
settings = get_settings()


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
http_bearer = HTTPBearer()


@dataclass
class TokenData:
    """JWT Token data"""
    user_id: str
    email: str
    role: str
    exp: datetime


@dataclass
class User:
    """User model"""
    id: str
    email: str
    hashed_password: str
    role: str = "user"  # user, admin, analyst
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


# In-memory user store (replace with database in production)
USERS_DB: Dict[str, User] = {
    "admin@example.com": User(
        id="1",
        email="admin@example.com",
        hashed_password=pwd_context.hash("admin123"),
        role="admin"
    )
}


class AuthService:
    """
    Authentication service
    
    Handles:
    - User registration
    - Password verification
    - JWT token generation/validation
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key or getattr(settings, 'jwt_secret_key', 'your-secret-key-change-in-production')
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str
    ) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + self.access_token_expire
        
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + self.refresh_token_expire
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            return TokenData(
                user_id=payload.get("sub"),
                email=payload.get("email", ""),
                role=payload.get("role", "user"),
                exp=datetime.fromtimestamp(payload.get("exp", 0))
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email/password"""
        user = USERS_DB.get(email)
        
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    def register_user(
        self,
        email: str,
        password: str,
        role: str = "user"
    ) -> User:
        """Register new user"""
        if email in USERS_DB:
            raise ValueError("User already exists")
        
        user = User(
            id=str(len(USERS_DB) + 1),
            email=email,
            hashed_password=self.hash_password(password),
            role=role
        )
        
        USERS_DB[email] = user
        logger.info(f"User registered: {email}")
        
        return user


# Global auth service
auth_service = AuthService()


# FastAPI dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> TokenData:
    """
    FastAPI dependency to get current authenticated user
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = auth_service.verify_token(credentials.credentials)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token_data


async def require_role(required_role: str):
    """
    Factory for role-based access control dependency
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    
    return role_checker


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency requiring admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Pydantic models for API
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool


if __name__ == "__main__":
    # Test auth module
    print("Testing Auth Module...")
    
    # Test password hashing
    password = "test123"
    hashed = auth_service.hash_password(password)
    print(f"Password hashed: {hashed[:20]}...")
    assert auth_service.verify_password(password, hashed)
    print("Password verification: OK")
    
    # Test token creation
    token = auth_service.create_access_token("1", "test@example.com", "user")
    print(f"Access token: {token[:50]}...")
    
    # Test token verification
    data = auth_service.verify_token(token)
    print(f"Token data: user_id={data.user_id}, email={data.email}, role={data.role}")
    
    # Test user registration
    user = auth_service.register_user("newuser@example.com", "password123")
    print(f"User registered: {user.email}")
    
    # Test authentication
    auth_user = auth_service.authenticate_user("newuser@example.com", "password123")
    print(f"Authentication: {'OK' if auth_user else 'FAILED'}")
    
    print("\nAuth module tests complete!")
