"""Authentication API endpoints."""

import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import requests
from typing import Literal, Optional
from ..database import get_db
from ..models import User, UserRole
from ..services.auth_service import AuthService
from ..services.quota_service import QuotaService
from ..config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
sso_router = APIRouter(prefix="/auth", tags=["sso"])
security = HTTPBearer()
SSO_STATES: dict[str, bool] = {}


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


class SSOStartResponse(BaseModel):
    authUrl: str


def _issue_token(user: User) -> TokenResponse:
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )
    return TokenResponse(access_token=access_token, api_key=user.api_key, user=user)


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
    
    return _issue_token(user)


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


@router.get("/sso/start", response_model=SSOStartResponse)
def start_sso():
    if not settings.auth_syn_client_id:
        raise HTTPException(status_code=503, detail="SSO is not configured")
    state = secrets.token_urlsafe(24)
    SSO_STATES[state] = True
    params = {
        "client_id": settings.auth_syn_client_id,
        "redirect_uri": settings.auth_syn_redirect_uri,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
    }
    query = "&".join(f"{key}={requests.utils.quote(str(value), safe='')}" for key, value in params.items())
    return SSOStartResponse(authUrl=f"{settings.auth_syn_base_url.rstrip('/')}/oauth/authorize?{query}")


@sso_router.get("/callback")
def sso_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error or not code or not state or not SSO_STATES.pop(state, None):
        return HTMLResponse("<h1>Sign in failed</h1><p>Return to Upload Studio and try again.</p>", status_code=400)

    try:
        token_response = requests.post(
            f"{settings.auth_syn_base_url.rstrip('/')}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.auth_syn_redirect_uri,
                "client_id": settings.auth_syn_client_id,
                "client_secret": settings.auth_syn_client_secret,
            },
            timeout=20,
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        userinfo_response = requests.get(
            f"{settings.auth_syn_base_url.rstrip('/')}/oauth/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=20,
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except Exception as exc:
        print(f"auth.syn.gl SSO callback failed: {exc}")
        return HTMLResponse("<h1>Sign in failed</h1><p>Return to Upload Studio and try again.</p>", status_code=400)

    email = userinfo.get("email")
    if not email:
        return HTMLResponse("<h1>Sign in failed</h1><p>No verified email was returned.</p>", status_code=400)

    user = AuthService.get_user_by_email(db, email)
    if not user:
        default_role = settings.auth_syn_default_role if settings.auth_syn_default_role in {"admin", "creator", "viewer"} else "creator"
        user = AuthService.create_user(db, email, secrets.token_urlsafe(24), role=default_role)
        QuotaService.get_or_create_subscription(db, user)

    local_token = _issue_token(user).access_token
    return HTMLResponse(
        f"""
        <html>
          <head><title>Signed in</title></head>
          <body>
            <p>Signed in. Returning to Upload Studio...</p>
            <script>
              localStorage.setItem('aiocc_access_token', {local_token!r});
              window.location.href = '/';
            </script>
          </body>
        </html>
        """
    )

