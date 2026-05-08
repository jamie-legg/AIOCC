"""Configuration settings for the backend API."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite:///upload_studio.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: str = ""
    
    # OAuth Credentials
    instagram_client_id: str = ""
    instagram_client_secret: str = ""
    youtube_client_secrets_file: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    upload_to_instagram: bool = False
    upload_to_youtube: bool = False
    upload_to_tiktok: bool = False
    
    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # ngrok
    ngrok_auth_token: str = ""
    ngrok_domain: str = ""

    # Upload Studio
    studio_upload_dir: str = "uploaded_clips"
    studio_public_base_url: str = "http://localhost:8000"
    studio_user_name: str = "AIOCC"
    youtube_handle: str = ""
    instagram_handle: str = ""
    tiktok_handle: str = ""
    
    # Subscription tiers
    free_tier_quota: int = 10
    pro_tier_quota: int = 100
    enterprise_tier_quota: int = -1  # Unlimited
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
    
    def get_allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()

