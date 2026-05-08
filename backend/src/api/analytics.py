"""Analytics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..database import get_db
from ..models import User, Upload
from ..api.auth import get_current_user_from_api_key, get_current_user_from_token

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class TrackUploadRequest(BaseModel):
    """Track a video upload."""
    platform: str
    filename: str
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str = "success"
    error_message: Optional[str] = None


class AnalyticsOverview(BaseModel):
    """Analytics overview response."""
    total_uploads: int
    successful_uploads: int
    failed_uploads: int
    uploads_by_platform: Dict[str, int]
    recent_uploads: List[Dict[str, Any]]


@router.post("/track")
def track_upload(
    request: TrackUploadRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Track a video upload event.
    
    Called by desktop client after uploading to a platform.
    """
    
    user = get_current_user_from_api_key(x_api_key, db)
    
    # Create upload record
    import json
    upload = Upload(
        user_id=user.id,
        platform=request.platform,
        video_id=request.video_id,
        video_url=request.video_url,
        filename=request.filename,
        metadata_json=json.dumps(request.metadata) if request.metadata else None,
        status=request.status,
        error_message=request.error_message
    )
    
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    return {
        "success": True,
        "upload_id": upload.id,
        "message": "Upload tracked successfully"
    }


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    current_user: User = Depends(get_current_user_from_token),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get analytics overview for authenticated user.
    
    Used by web dashboard.
    """
    
    # Calculate date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total uploads
    total_uploads = db.query(Upload).filter(
        Upload.user_id == current_user.id,
        Upload.created_at >= start_date
    ).count()
    
    # Successful uploads
    successful_uploads = db.query(Upload).filter(
        Upload.user_id == current_user.id,
        Upload.status == "success",
        Upload.created_at >= start_date
    ).count()
    
    # Failed uploads
    failed_uploads = db.query(Upload).filter(
        Upload.user_id == current_user.id,
        Upload.status == "failed",
        Upload.created_at >= start_date
    ).count()
    
    # Uploads by platform
    platform_counts = db.query(
        Upload.platform,
        func.count(Upload.id)
    ).filter(
        Upload.user_id == current_user.id,
        Upload.created_at >= start_date
    ).group_by(Upload.platform).all()
    
    uploads_by_platform = {platform: count for platform, count in platform_counts}
    
    # Recent uploads
    recent = db.query(Upload).filter(
        Upload.user_id == current_user.id
    ).order_by(Upload.created_at.desc()).limit(10).all()
    
    recent_uploads = [
        {
            "id": upload.id,
            "platform": upload.platform,
            "filename": upload.filename,
            "video_id": upload.video_id,
            "video_url": upload.video_url,
            "status": upload.status,
            "created_at": upload.created_at.isoformat()
        }
        for upload in recent
    ]
    
    return AnalyticsOverview(
        total_uploads=total_uploads,
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        uploads_by_platform=uploads_by_platform,
        recent_uploads=recent_uploads
    )


@router.get("/videos")
def get_videos(
    current_user: User = Depends(get_current_user_from_token),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of uploaded videos with optional platform filter."""
    
    query = db.query(Upload).filter(Upload.user_id == current_user.id)
    
    if platform:
        query = query.filter(Upload.platform == platform)
    
    total = query.count()
    
    uploads = query.order_by(Upload.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "videos": [
            {
                "id": upload.id,
                "platform": upload.platform,
                "filename": upload.filename,
                "video_id": upload.video_id,
                "video_url": upload.video_url,
                "status": upload.status,
                "error_message": upload.error_message,
                "created_at": upload.created_at.isoformat()
            }
            for upload in uploads
        ]
    }


@router.get("/platforms")
def get_platform_stats(
    current_user: User = Depends(get_current_user_from_token),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get detailed platform statistics."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    platforms = ["instagram", "youtube", "tiktok"]
    stats = {}
    
    for platform in platforms:
        total = db.query(Upload).filter(
            Upload.user_id == current_user.id,
            Upload.platform == platform,
            Upload.created_at >= start_date
        ).count()
        
        successful = db.query(Upload).filter(
            Upload.user_id == current_user.id,
            Upload.platform == platform,
            Upload.status == "success",
            Upload.created_at >= start_date
        ).count()
        
        failed = db.query(Upload).filter(
            Upload.user_id == current_user.id,
            Upload.platform == platform,
            Upload.status == "failed",
            Upload.created_at >= start_date
        ).count()
        
        stats[platform] = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0
        }
    
    return stats


@router.get("/trends")
def get_analytics_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get analytics trends data for the specified number of days."""
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        snapshots = []
        current_date = start_date
        
        while current_date <= end_date:
            # Count uploads up to this date
            uploads_count = db.query(Upload).filter(
                Upload.created_at <= current_date
            ).count()
            
            # For now, without metrics tracking, we can only show upload counts
            # In the future, this should query actual metrics
            snapshots.append({
                "date": current_date.isoformat(),
                "total_views": 0,  # Would need metrics table for real data
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "total_videos": uploads_count,
                "platforms": {
                    "youtube": db.query(Upload).filter(
                        Upload.platform == "youtube",
                        Upload.created_at <= current_date
                    ).count(),
                    "instagram": db.query(Upload).filter(
                        Upload.platform == "instagram",
                        Upload.created_at <= current_date
                    ).count(),
                    "tiktok": db.query(Upload).filter(
                        Upload.platform == "tiktok",
                        Upload.created_at <= current_date
                    ).count()
                }
            })
            
            current_date += timedelta(days=1)
        
        return {
            "snapshots": snapshots,
            "days": days,
            "count": len(snapshots)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading trends: {str(e)}")
