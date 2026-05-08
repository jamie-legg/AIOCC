"""OAuth proxy API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict
import os
import requests
import secrets
from ..database import get_db
from ..models import User
from ..services.oauth_service import OAuthService
from ..api.auth import get_current_user_from_api_key
from ..config import settings

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth URL to redirect user to."""
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data from client."""
    code: str
    state: str
    platform: str


class OAuthCredentialsResponse(BaseModel):
    """OAuth credentials response."""
    platform: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None
    user_platform_id: Optional[str] = None


@router.post("/{platform}/initiate", response_model=OAuthInitiateResponse)
def initiate_oauth(
    platform: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth flow for a platform.
    
    Returns authorization URL for user to visit.
    """
    
    user = get_current_user_from_api_key(x_api_key, db)
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in Redis with user_id for 10 minutes
    from ..services.quota_service import redis_client
    redis_client.setex(f"oauth_state:{state}", 600, str(user.id))
    
    # Default redirect URI (backend callback)
    if not redirect_uri:
        redirect_uri = f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/oauth/{platform}/callback"
    
    if platform == "instagram":
        if not settings.instagram_client_id:
            raise HTTPException(status_code=500, detail="Instagram OAuth not configured")
        
        auth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={settings.instagram_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=instagram_business_basic,instagram_business_content_publish"
            f"&response_type=code"
            f"&state={state}"
        )
    
    elif platform == "tiktok":
        if not settings.tiktok_client_key:
            raise HTTPException(status_code=500, detail="TikTok OAuth not configured")
        
        auth_url = (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={settings.tiktok_client_key}"
            f"&response_type=code"
            f"&scope=user.info.stats,video.list,video.publish,video.upload,user.info.profile"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
    
    elif platform == "youtube":
        # YouTube uses different flow - client should use Google OAuth library
        raise HTTPException(
            status_code=400,
            detail="YouTube OAuth should use Google OAuth library on client side"
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    return OAuthInitiateResponse(auth_url=auth_url, state=state)


@router.post("/{platform}/callback")
def oauth_callback(
    platform: str,
    request: OAuthCallbackRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from platform.
    
    Exchanges authorization code for access token and stores credentials.
    """
    
    user = get_current_user_from_api_key(x_api_key, db)
    
    # Verify state
    from ..services.quota_service import redis_client
    stored_user_id = redis_client.get(f"oauth_state:{request.state}")
    
    if not stored_user_id or int(stored_user_id) != user.id:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Delete used state
    redis_client.delete(f"oauth_state:{request.state}")
    
    try:
        if platform == "instagram":
            # Exchange code for token
            token_url = "https://api.instagram.com/oauth/access_token"
            token_data = {
                "client_id": settings.instagram_client_id,
                "client_secret": settings.instagram_client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/oauth/instagram/callback",
                "code": request.code
            }
            
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token_info = response.json()
            
            # Get long-lived token
            long_lived_url = (
                f"https://graph.instagram.com/access_token"
                f"?grant_type=ig_exchange_token"
                f"&client_secret={settings.instagram_client_secret}"
                f"&access_token={token_info['access_token']}"
            )
            long_lived_response = requests.get(long_lived_url)
            long_lived_response.raise_for_status()
            long_lived_info = long_lived_response.json()
            
            # Store credentials
            OAuthService.store_credentials(
                db, user, "instagram",
                access_token=long_lived_info.get("access_token", token_info["access_token"]),
                expires_in=long_lived_info.get("expires_in")
            )
            
            return {"success": True, "platform": "instagram"}
        
        elif platform == "tiktok":
            # Exchange code for token
            token_url = "https://open.tiktokapis.com/v2/oauth/token/"
            token_data = {
                "client_key": settings.tiktok_client_key,
                "client_secret": settings.tiktok_client_secret,
                "code": request.code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/oauth/tiktok/callback"
            }
            
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token_info = response.json()
            
            # Store credentials
            OAuthService.store_credentials(
                db, user, "tiktok",
                access_token=token_info["access_token"],
                refresh_token=token_info.get("refresh_token"),
                expires_in=token_info.get("expires_in"),
                scope=token_info.get("scope"),
                user_platform_id=token_info.get("open_id")
            )
            
            return {"success": True, "platform": "tiktok"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")


@router.get("/{platform}/credentials", response_model=OAuthCredentialsResponse)
def get_credentials(
    platform: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """Get stored OAuth credentials for a platform."""
    
    user = get_current_user_from_api_key(x_api_key, db)
    
    credentials = OAuthService.get_credentials(db, user, platform)
    
    if not credentials:
        raise HTTPException(
            status_code=404,
            detail=f"No credentials found for {platform}. Please authenticate first."
        )
    
    return OAuthCredentialsResponse(**credentials)


@router.delete("/{platform}/credentials")
def delete_credentials(
    platform: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """Delete OAuth credentials for a platform."""
    
    user = get_current_user_from_api_key(x_api_key, db)
    
    success = OAuthService.delete_credentials(db, user, platform)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No credentials found for {platform}"
        )
    
    return {"success": True, "message": f"Credentials for {platform} deleted"}

