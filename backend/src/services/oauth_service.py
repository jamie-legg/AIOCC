"""OAuth service for managing platform authentication."""

import os
import requests
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from ..models import User, OAuthCredential
from ..config import settings

# Initialize encryption
# In production, store this securely in environment or key management service
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)


class OAuthService:
    """Manage OAuth flows and credential storage."""
    
    @staticmethod
    def encrypt_token(token: str) -> str:
        """Encrypt a token for secure storage."""
        return cipher_suite.encrypt(token.encode()).decode()
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Decrypt a stored token."""
        return cipher_suite.decrypt(encrypted_token.encode()).decode()
    
    @staticmethod
    def store_credentials(
        db: Session,
        user: User,
        platform: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        scope: Optional[str] = None,
        user_platform_id: Optional[str] = None
    ) -> OAuthCredential:
        """Store OAuth credentials securely."""
        
        # Encrypt tokens
        encrypted_access = OAuthService.encrypt_token(access_token)
        encrypted_refresh = OAuthService.encrypt_token(refresh_token) if refresh_token else None
        
        # Calculate expiry
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Check if credential exists
        credential = db.query(OAuthCredential).filter(
            OAuthCredential.user_id == user.id,
            OAuthCredential.platform == platform
        ).first()
        
        if credential:
            # Update existing
            credential.access_token = encrypted_access
            credential.refresh_token = encrypted_refresh
            credential.expires_at = expires_at
            credential.scope = scope
            credential.user_platform_id = user_platform_id
        else:
            # Create new
            credential = OAuthCredential(
                user_id=user.id,
                platform=platform,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                expires_at=expires_at,
                scope=scope,
                user_platform_id=user_platform_id
            )
            db.add(credential)
        
        db.commit()
        db.refresh(credential)
        
        return credential
    
    @staticmethod
    def get_credentials(db: Session, user: User, platform: str) -> Optional[Dict]:
        """Get decrypted OAuth credentials for a platform."""
        credential = db.query(OAuthCredential).filter(
            OAuthCredential.user_id == user.id,
            OAuthCredential.platform == platform
        ).first()
        
        if not credential:
            return None
        
        # Decrypt tokens
        access_token = OAuthService.decrypt_token(credential.access_token)
        refresh_token = None
        if credential.refresh_token:
            refresh_token = OAuthService.decrypt_token(credential.refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": credential.token_type,
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "scope": credential.scope,
            "user_platform_id": credential.user_platform_id,
            "platform": credential.platform
        }
    
    @staticmethod
    def delete_credentials(db: Session, user: User, platform: str) -> bool:
        """Delete OAuth credentials for a platform."""
        result = db.query(OAuthCredential).filter(
            OAuthCredential.user_id == user.id,
            OAuthCredential.platform == platform
        ).delete()
        
        db.commit()
        return result > 0
    
    @staticmethod
    def refresh_instagram_token(db: Session, user: User) -> Optional[Dict]:
        """Refresh Instagram long-lived token."""
        credential = db.query(OAuthCredential).filter(
            OAuthCredential.user_id == user.id,
            OAuthCredential.platform == "instagram"
        ).first()
        
        if not credential:
            return None
        
        try:
            access_token = OAuthService.decrypt_token(credential.access_token)
            
            # Instagram token refresh
            refresh_url = (
                f"https://graph.instagram.com/refresh_access_token"
                f"?grant_type=ig_refresh_token"
                f"&access_token={access_token}"
            )
            
            response = requests.get(refresh_url)
            response.raise_for_status()
            
            data = response.json()
            
            # Store new token
            OAuthService.store_credentials(
                db, user, "instagram",
                access_token=data["access_token"],
                expires_in=data.get("expires_in")
            )
            
            return OAuthService.get_credentials(db, user, "instagram")
            
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return None

