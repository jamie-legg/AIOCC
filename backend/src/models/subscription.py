"""Subscription and quota tracking models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from ..database import Base


class Subscription(Base):
    """Subscription tracking and quota management."""
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(String, nullable=False)
    quota_used = Column(Integer, default=0, nullable=False)
    quota_limit = Column(Integer, nullable=False)
    reset_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def is_quota_available(self) -> bool:
        """Check if user has quota available."""
        # Unlimited quota (enterprise)
        if self.quota_limit == -1:
            return True
        
        # Check if reset date has passed
        if datetime.utcnow() >= self.reset_date:
            return True
        
        # Check if under quota
        return self.quota_used < self.quota_limit
    
    def use_quota(self, amount: int = 1) -> bool:
        """Use quota and return True if successful."""
        if not self.is_quota_available():
            return False
        
        # Reset quota if period has passed
        if datetime.utcnow() >= self.reset_date:
            self.quota_used = 0
            self.reset_date = datetime.utcnow() + timedelta(days=30)
        
        # Unlimited quota
        if self.quota_limit == -1:
            self.quota_used += amount
            return True
        
        # Use quota if available
        if self.quota_used + amount <= self.quota_limit:
            self.quota_used += amount
            return True
        
        return False
    
    def get_quota_info(self) -> dict:
        """Get quota usage information."""
        return {
            "tier": self.tier,
            "used": self.quota_used,
            "limit": self.quota_limit,
            "remaining": self.quota_limit - self.quota_used if self.quota_limit != -1 else -1,
            "reset_date": self.reset_date.isoformat(),
            "is_unlimited": self.quota_limit == -1
        }
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, tier={self.tier}, used={self.quota_used}/{self.quota_limit})>"

