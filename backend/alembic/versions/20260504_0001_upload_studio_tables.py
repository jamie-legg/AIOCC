"""add upload studio tables

Revision ID: 20260504_0001
Revises:
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uploaded_clips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("stored_path", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=50), nullable=False, server_default="public"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_uploaded_clips_id", "uploaded_clips", ["id"])
    op.create_index("ix_uploaded_clips_user_id", "uploaded_clips", ["user_id"])

    op.create_table(
        "platform_uploads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("uploaded_clips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_video_id", sa.String(length=200), nullable=True),
        sa.Column("platform_url", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_platform_uploads_id", "platform_uploads", ["id"])
    op.create_index("ix_platform_uploads_clip_id", "platform_uploads", ["clip_id"])
    op.create_index("ix_platform_uploads_platform", "platform_uploads", ["platform"])


def downgrade() -> None:
    op.drop_index("ix_platform_uploads_platform", table_name="platform_uploads")
    op.drop_index("ix_platform_uploads_clip_id", table_name="platform_uploads")
    op.drop_index("ix_platform_uploads_id", table_name="platform_uploads")
    op.drop_table("platform_uploads")
    op.drop_index("ix_uploaded_clips_user_id", table_name="uploaded_clips")
    op.drop_index("ix_uploaded_clips_id", table_name="uploaded_clips")
    op.drop_table("uploaded_clips")
