"""Authentication API endpoints."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from ..database import get_db
from ..models import User, UserRole
from ..services.auth_service import AuthService
from ..services.quota_service import QuotaService
from ..config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information response."""
    id: int
    email: str
    api_key: str
    subscription_tier: str
    role: str
    is_active: int
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    api_key: str
    user: UserResponse


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: Literal["admin", "creator", "viewer"] = "creator"


class UpdateUserRequest(BaseModel):
    role: Optional[Literal["admin", "creator", "viewer"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = AuthService.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = AuthService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled"
        )
    
    return user


def require_admin(current_user: User = Depends(get_current_user_from_token)) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_current_user_from_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> User:
    """Get current user from API key (for desktop client)."""
    user = AuthService.get_user_by_api_key(db, api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    if not settings.allow_public_registration and db.query(User).count() > 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Public registration is disabled")
    
    # Check if user already exists
    existing_user = AuthService.get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    role = UserRole.ADMIN.value if db.query(User).count() == 0 else UserRole.CREATOR.value
    user = AuthService.create_user(db, request.email, request.password, role=role)
    
    # Create initial subscription
    QuotaService.get_or_create_subscription(db, user)
    
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token."""
    
    user = AuthService.authenticate_user(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        api_key=user.api_key,
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user_from_token)
):
    """Get current user information."""
    return current_user


@router.post("/refresh-api-key", response_model=UserResponse)
def refresh_api_key(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Generate a new API key for the user."""
    
    # Generate new API key
    current_user.api_key = User.generate_api_key()
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.created_at.desc(), User.id.desc()).all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: CreateUserRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if AuthService.get_user_by_email(db, request.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = AuthService.create_user(db, request.email, request.password, role=request.role)
    QuotaService.get_or_create_subscription(db, user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: UpdateUserRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = 1 if request.is_active else 0
    if request.password:
        user.hashed_password = AuthService.get_password_hash(request.password)
    db.commit()
    db.refresh(user)
    return user

