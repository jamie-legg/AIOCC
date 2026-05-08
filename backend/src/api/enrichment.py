"""AI enrichment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..database import get_db
from ..models import User
from ..services.ai_service import AIService
from ..services.quota_service import QuotaService
from ..api.auth import get_current_user_from_api_key

router = APIRouter(prefix="/api/v1/enrichment", tags=["enrichment"])
ai_service = AIService()


class EnrichmentRequest(BaseModel):
    """Request for AI metadata generation."""
    filename: str
    game_context: str = "gaming"


class EnrichmentResponse(BaseModel):
    """Response with generated metadata."""
    title: str
    caption: str
    hashtags: str
    quota_remaining: Optional[int] = None


@router.post("/generate", response_model=EnrichmentResponse)
def generate_metadata(
    request: EnrichmentRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered metadata for a video file.
    
    Requires API key authentication via X-API-Key header.
    Consumes 1 quota unit per request.
    """
    
    # Authenticate user with API key
    user = get_current_user_from_api_key(x_api_key, db)
    
    # Check rate limit (10 requests per minute)
    if not QuotaService.check_rate_limit(user.id, "ai_enrichment", limit=10, window=60):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 requests per minute."
        )
    
    # Check quota
    quota_info = QuotaService.check_quota(db, user)
    if not quota_info.get("is_unlimited", False):
        if quota_info.get("remaining", 0) <= 0:
            raise HTTPException(
                status_code=403,
                detail="Quota exceeded. Please upgrade your subscription."
            )
    
    # Use quota
    if not QuotaService.use_quota(db, user, amount=1):
        raise HTTPException(
            status_code=403,
            detail="Failed to use quota. Please try again."
        )
    
    # Generate metadata
    try:
        metadata = ai_service.generate_metadata(
            request.filename,
            request.game_context
        )
        
        # Get updated quota info
        quota_info = QuotaService.check_quota(db, user)
        
        return EnrichmentResponse(
            title=metadata.get("title", ""),
            caption=metadata.get("caption", ""),
            hashtags=metadata.get("hashtags", ""),
            quota_remaining=quota_info.get("remaining")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate metadata: {str(e)}"
        )


@router.get("/quota")
def check_quota(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """Check user's quota status."""
    
    user = get_current_user_from_api_key(x_api_key, db)
    quota_info = QuotaService.check_quota(db, user)
    
    return quota_info

