"""
Authentication Router
认证路由
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status

from .auth import (
    auth_service,
    get_current_user,
    require_admin,
    TokenData,
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    USERS_DB
)
from ..utils.logger import setup_logging

logger = setup_logging("auth_router")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
    Register a new user
    
    - **email**: User email address
    - **password**: User password (min 8 characters)
    """
    try:
        user = auth_service.register_user(
            email=user_data.email,
            password=user_data.password
        )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login and get access token
    
    Returns JWT access token and refresh token
    """
    user = auth_service.authenticate_user(
        credentials.email,
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = auth_service.create_access_token(
        user.id,
        user.email,
        user.role
    )
    
    refresh_token = auth_service.create_refresh_token(user.id)
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    token_data = auth_service.verify_token(refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Find user
    user = None
    for u in USERS_DB.values():
        if u.id == token_data.user_id:
            user = u
            break
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    new_access_token = auth_service.create_access_token(
        user.id,
        user.email,
        user.role
    )
    
    new_refresh_token = auth_service.create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current user information
    
    Requires authentication
    """
    # Find full user data
    user = None
    for u in USERS_DB.values():
        if u.id == current_user.user_id:
            user = u
            break
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_admin)
):
    """
    List all users (admin only)
    """
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active
        )
        for user in USERS_DB.values()
    ]


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(require_admin)
):
    """
    Delete a user (admin only)
    """
    for email, user in list(USERS_DB.items()):
        if user.id == user_id:
            del USERS_DB[email]
            logger.info(f"User deleted: {email}")
            return {"message": "User deleted"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
