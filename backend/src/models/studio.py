"""Upload Studio models for the flat-file upload workflow."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class UploadedClip(Base):
    """A source clip uploaded through the simplified studio UI."""

    __tablename__ = "uploaded_clips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=False, default="")
    description = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    visibility = Column(String(50), nullable=False, default="public")
    status = Column(String(50), nullable=False, default="uploaded")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    platform_uploads = relationship("PlatformUpload", back_populates="clip", cascade="all, delete-orphan")


class PlatformUpload(Base):
    """Per-platform result for a studio clip upload."""

    __tablename__ = "platform_uploads"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("uploaded_clips.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_video_id = Column(String(200), nullable=True)
    platform_url = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="uploaded")
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    clip = relationship("UploadedClip", back_populates="platform_uploads")
