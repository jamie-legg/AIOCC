"""Upload tracking models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from ..database import Base


class Upload(Base):
    """Track video uploads across platforms."""
    
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    video_id = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON string of title, caption, hashtags
    status = Column(String, default="pending", nullable=False)  # pending, success, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Upload(id={self.id}, platform={self.platform}, status={self.status})>"


class OAuthCredential(Base):
    """Store OAuth credentials securely."""
    
    __tablename__ = "oauth_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_type = Column(String, default="Bearer")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String, nullable=True)
    user_platform_id = Column(String, nullable=True)  # Platform-specific user ID
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<OAuthCredential(user_id={self.user_id}, platform={self.platform})>"

