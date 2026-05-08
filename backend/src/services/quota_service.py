"""Quota tracking and rate limiting service."""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import redis
from ..models import User, Subscription
from ..config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class QuotaService:
    """Manage user quotas and rate limiting."""
    
    @staticmethod
    def get_or_create_subscription(db: Session, user: User) -> Subscription:
        """Get or create subscription for user."""
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if not subscription:
            # Create subscription based on user tier
            quota_limit = {
                "free": settings.free_tier_quota,
                "pro": settings.pro_tier_quota,
                "enterprise": settings.enterprise_tier_quota,
            }.get(user.subscription_tier, settings.free_tier_quota)
            
            subscription = Subscription(
                user_id=user.id,
                tier=user.subscription_tier,
                quota_limit=quota_limit,
                quota_used=0,
                reset_date=datetime.utcnow() + timedelta(days=30)
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        
        return subscription
    
    @staticmethod
    def check_quota(db: Session, user: User) -> dict:
        """Check user's quota status."""
        subscription = QuotaService.get_or_create_subscription(db, user)
        return subscription.get_quota_info()
    
    @staticmethod
    def use_quota(db: Session, user: User, amount: int = 1) -> bool:
        """Use user's quota. Returns True if successful."""
        subscription = QuotaService.get_or_create_subscription(db, user)
        
        if subscription.use_quota(amount):
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def check_rate_limit(user_id: int, operation: str, limit: int = 10, window: int = 60) -> bool:
        """
        Check if user is within rate limit.
        
        Args:
            user_id: User ID
            operation: Operation name (e.g., 'api_call', 'upload')
            limit: Maximum number of operations within window
            window: Time window in seconds
        
        Returns:
            True if within limit, False if exceeded
        """
        key = f"rate_limit:{user_id}:{operation}"
        
        try:
            # Get current count
            count = redis_client.get(key)
            
            if count is None:
                # First request in window
                redis_client.setex(key, window, 1)
                return True
            
            count = int(count)
            
            if count >= limit:
                return False
            
            # Increment count
            redis_client.incr(key)
            return True
            
        except Exception as e:
            # If Redis fails, allow the request
            print(f"Rate limit check failed: {e}")
            return True
    
    @staticmethod
    def reset_quota(db: Session, user: User):
        """Reset user's quota (for testing or admin purposes)."""
        subscription = QuotaService.get_or_create_subscription(db, user)
        subscription.quota_used = 0
        subscription.reset_date = datetime.utcnow() + timedelta(days=30)
        db.commit()

