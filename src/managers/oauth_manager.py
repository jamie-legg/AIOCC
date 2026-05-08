"""OAuth authentication manager for social media platforms."""

import os
import json
import time
import webbrowser
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import timezone
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from content_creation.callback_server import handle_oauth_flow

load_dotenv()

@dataclass
class OAuthCredentials:
    """Container for OAuth credentials."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    scope: Optional[str] = None
    user_id: Optional[str] = None
    platform: str = ""

class OAuthManager:
    """Manages OAuth authentication for multiple social media platforms."""
    
    def __init__(self, credentials_dir: Path = Path.home() / ".content_creation", db=None):
        self.credentials_dir = credentials_dir
        self.credentials_dir.mkdir(exist_ok=True)
        self.credentials_file = self.credentials_dir / "credentials.json"
        self.db = db  # AnalyticsDatabase instance for database-backed storage
        
        # Load existing credentials (from database if available, else from file)
        self.credentials = self._load_credentials()

    @staticmethod
    def _expiry_timestamp(expiry) -> Optional[int]:
        """Convert Google credential expiry to a Unix timestamp, treating naive values as UTC."""
        if not expiry:
            return None
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return int(expiry.timestamp())
    
    def _load_credentials(self) -> Dict[str, OAuthCredentials]:
        """Load stored credentials from database (if available) or file."""
        creds_dict = {}
        
        # Try to load from database first
        if self.db:
            try:
                platforms = ["youtube", "instagram", "tiktok"]
                for platform in platforms:
                    db_creds = self.db.get_oauth_credentials(platform)
                    if db_creds:
                        token_data = db_creds.get("token_data", {})
                        creds_dict[platform] = OAuthCredentials(
                            access_token=db_creds["access_token"],
                            refresh_token=db_creds.get("refresh_token"),
                            expires_at=db_creds.get("expires_at"),
                            scope=token_data.get("scope") if isinstance(token_data, dict) else None,
                            user_id=token_data.get("user_id") or token_data.get("open_id") if isinstance(token_data, dict) else None,
                            platform=platform
                        )
            except Exception as e:
                print(f"Error loading credentials from database: {e}")
        
        # Fall back to file-based storage if database doesn't have credentials
        if not creds_dict and self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                    for platform, creds in data.items():
                        if platform not in creds_dict:  # Don't overwrite database credentials
                            creds_dict[platform] = OAuthCredentials(**creds)
            except Exception as e:
                print(f"Error loading credentials from file: {e}")

        # YouTube historically stores a Google authorized-user token separately.
        # Prefer it over the generic credentials file because Google's refresh
        # metadata is complete there.
        token_file = self.credentials_dir / "youtube_token.json"
        if token_file.exists():
            try:
                google_creds = Credentials.from_authorized_user_file(str(token_file))
                creds_dict["youtube"] = OAuthCredentials(
                    access_token=google_creds.token,
                    refresh_token=google_creds.refresh_token,
                    expires_at=self._expiry_timestamp(google_creds.expiry),
                    scope=" ".join(google_creds.scopes or []),
                    platform="youtube",
                )
            except Exception as e:
                print(f"Error loading YouTube token file: {e}")
        
        return creds_dict
    
    def _save_credentials(self):
        """Save credentials to database (if available) or file."""
        # Save to database if available
        if self.db:
            try:
                for platform, creds in self.credentials.items():
                    token_data = {}
                    if creds.scope:
                        token_data["scope"] = creds.scope
                    if creds.user_id:
                        token_data["user_id"] = creds.user_id
                    
                    self.db.save_oauth_credentials(
                        platform=platform,
                        access_token=creds.access_token,
                        refresh_token=creds.refresh_token,
                        expires_at=creds.expires_at,
                        token_data=token_data if token_data else None
                    )
                return  # Don't save to file if database is available
            except Exception as e:
                print(f"Error saving credentials to database: {e}")
                # Fall through to file-based save
        
        # Fall back to file-based storage
        data = {
            platform: {
                "access_token": creds.access_token,
                "refresh_token": creds.refresh_token,
                "expires_at": creds.expires_at,
                "platform": creds.platform
            }
            for platform, creds in self.credentials.items()
        }
        
        with open(self.credentials_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def authenticate_instagram(self) -> bool:
        """Authenticate with Instagram Graph API for business accounts."""
        client_id = os.getenv("INSTAGRAM_CLIENT_ID")
        client_secret = os.getenv("INSTAGRAM_CLIENT_SECRET")
        if not client_id or not client_secret:
            print("Instagram credentials not found. Please set INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET")
            return False
        
        print("Starting Instagram Graph API authentication...")
        print("Note: This requires a Facebook Page connected to an Instagram Business Account")
        
        # Start callback server first to get the redirect URI
        from content_creation.callback_server import OAuthCallbackServer
        # Use reserved ngrok domain for consistent URLs
        ngrok_domain = os.getenv("NGROK_DOMAIN", "uninclinable-ontogenetic-leoma.ngrok-free.dev")
        temp_server = OAuthCallbackServer(use_ngrok=True, ngrok_domain=ngrok_domain)
        if not temp_server.start_server():
            print("Failed to start callback server")
            return False
        
        redirect_uri = (
            os.getenv("INSTAGRAM_REDIRECT_URI")
            or f"{os.getenv('OAUTH_REDIRECT_BASE_URL', '').rstrip('/')}/api/oauth/instagram/callback"
            if os.getenv("OAUTH_REDIRECT_BASE_URL")
            else temp_server.get_callback_url()
        )
        print(f"Using redirect URI: {redirect_uri}")
        
        # Step 1: Get authorization code using Instagram Business Login
        auth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights"
            f"&response_type=code"
        )
        
        callback_result = handle_oauth_flow(auth_url, use_ngrok=True, server=temp_server)
        
        # Clean up temp server
        temp_server.stop_server()
        
        if callback_result.get('error'):
            print(f"Instagram authentication failed: {callback_result.get('error_description', callback_result['error'])}")
            return False
        
        auth_code = callback_result.get('code')
        if not auth_code:
            print("No authorization code received")
            return False
        
        # Step 2: Exchange code for access token
        token_url = "https://api.instagram.com/oauth/access_token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": auth_code
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_info = response.json()
            
            if 'error' in token_info:
                print(f"Instagram authentication failed: {token_info['error']['message']}")
                return False
            
            # Get long-lived access token
            long_lived_url = f"https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret={client_secret}&access_token={token_info['access_token']}"
            long_lived_response = requests.get(long_lived_url)
            long_lived_response.raise_for_status()
            long_lived_info = long_lived_response.json()
            
            # Calculate actual expiration timestamp for Instagram
            expires_in = long_lived_info.get("expires_in", 3600)
            expires_at = int(time.time()) + expires_in
            
            self.credentials["instagram"] = OAuthCredentials(
                access_token=long_lived_info.get("access_token", token_info["access_token"]),
                expires_at=expires_at,
                platform="instagram"
            )
            
            self._save_credentials()
            print("Instagram Graph API authentication successful!")
            print("You can now upload Reels to your Instagram Business Account")
            return True
            
        except Exception as e:
            print(f"Instagram authentication failed: {e}")
            return False
    
    def authenticate_youtube(self, force: bool = False) -> bool:
        """Authenticate with YouTube Data API v3."""
        client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
        
        if not client_secrets_file:
            print("YouTube client secrets file not found. Please set YOUTUBE_CLIENT_SECRETS_FILE")
            return False
        
        SCOPES = [
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl',
            'https://www.googleapis.com/auth/youtube.upload'
        ]

        configured_redirect_uri = (
            os.getenv("YOUTUBE_REDIRECT_URI")
            or f"{os.getenv('OAUTH_REDIRECT_BASE_URL', '').rstrip('/')}/api/oauth/youtube/callback"
            if os.getenv("OAUTH_REDIRECT_BASE_URL")
            else None
        )

        if configured_redirect_uri:
            from content_creation.callback_server import OAuthCallbackServer

            print("Starting YouTube authentication with configured redirect URI...")
            ngrok_domain = os.getenv("NGROK_DOMAIN")
            temp_server = OAuthCallbackServer(use_ngrok=True, ngrok_domain=ngrok_domain)
            if not temp_server.start_server():
                print("Failed to start callback server")
                return False

            try:
                flow = Flow.from_client_secrets_file(
                    client_secrets_file,
                    scopes=SCOPES,
                    redirect_uri=configured_redirect_uri,
                )
                auth_url, _state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                    prompt="consent",
                )
                print(f"Using redirect URI: {configured_redirect_uri}")
                callback_result = handle_oauth_flow(auth_url, use_ngrok=True, server=temp_server)

                if callback_result.get("error"):
                    print(f"YouTube authentication failed: {callback_result.get('error_description', callback_result['error'])}")
                    return False

                auth_code = callback_result.get("code")
                if not auth_code:
                    print("No authorization code received")
                    return False

                flow.fetch_token(code=auth_code)
                creds = flow.credentials

                token_file = self.credentials_dir / "youtube_token.json"
                with open(token_file, "w") as token:
                    token.write(creds.to_json())

                self.credentials["youtube"] = OAuthCredentials(
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expires_at=self._expiry_timestamp(creds.expiry),
                    scope=" ".join(creds.scopes or []),
                    platform="youtube",
                )

                self._save_credentials()
                print("YouTube authentication successful!")
                return True
            except Exception as e:
                print(f"YouTube authentication failed: {e}")
                return False
            finally:
                temp_server.stop_server()
        
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, SCOPES)
        
        # Check if we have valid credentials
        creds = None
        token_file = self.credentials_dir / "youtube_token.json"
        needs_reauth = False
        
        if token_file.exists() and not force:
            # Read the actual scopes from the token file
            import json
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                actual_scopes = token_data.get('scopes', [])
            
            # Check if we have all required scopes
            missing_scopes = set(SCOPES) - set(actual_scopes)
            if missing_scopes:
                print(f"⚠️  Token missing required scopes:")
                for scope in missing_scopes:
                    print(f"   - {scope}")
                print(f"   Re-authenticating to get all permissions...")
                needs_reauth = True
            else:
                # Load existing credentials
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid or needs_reauth:
            if creds and creds.expired and creds.refresh_token and not needs_reauth:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"YouTube token refresh failed: {e}")
                    print("Opening browser for YouTube re-authorization...")
                    creds = flow.run_local_server(port=0)
            else:
                print("Opening browser for YouTube authorization...")
                print("   Please approve ALL permissions when prompted!")
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            
            print(f"Token saved with {len(creds.scopes)} scopes")
        
        # Store credentials in our format
        self.credentials["youtube"] = OAuthCredentials(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expires_at=self._expiry_timestamp(creds.expiry),
            platform="youtube"
        )
        
        self._save_credentials()
        print("YouTube authentication successful!")
        return True
    
    def authenticate_tiktok(self) -> bool:
        """Authenticate with TikTok for Developers API."""
        client_key = os.getenv("TIKTOK_CLIENT_KEY")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        if not client_key or not client_secret:
            print("TikTok credentials not found. Please set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")
            return False
        
        print("Starting TikTok authentication...")
        
        # Start callback server first to get the redirect URI
        from content_creation.callback_server import OAuthCallbackServer
        # Use reserved ngrok domain for consistent URLs
        ngrok_domain = os.getenv("NGROK_DOMAIN", "uninclinable-ontogenetic-leoma.ngrok-free.dev")
        temp_server = OAuthCallbackServer(use_ngrok=True, ngrok_domain=ngrok_domain)
        if not temp_server.start_server():
            print("Failed to start callback server")
            return False
        
        redirect_uri = (
            os.getenv("TIKTOK_REDIRECT_URI")
            or f"{os.getenv('OAUTH_REDIRECT_BASE_URL', '').rstrip('/')}/api/oauth/tiktok/callback"
            if os.getenv("OAUTH_REDIRECT_BASE_URL")
            else temp_server.get_callback_url()
        )
        print(f"Using redirect URI: {redirect_uri}")
        
        # Step 1: Get authorization code using callback server
        import secrets
        state = secrets.token_urlsafe(32)
        
        auth_url = (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={client_key}"
            f"&response_type=code"
            f"&scope=user.info.stats,video.list,video.publish,video.upload,user.info.profile"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&disable_auto_auth=1"
        )
        
        callback_result = handle_oauth_flow(auth_url, use_ngrok=True, server=temp_server)
        
        # Clean up temp server
        temp_server.stop_server()
        
        if callback_result.get('error'):
            print(f"TikTok authentication failed: {callback_result.get('error_description', callback_result['error'])}")
            return False
        
        auth_code = callback_result.get('code')
        if not auth_code:
            print("No authorization code received")
            print(f"Callback result: {callback_result}")
            return False
        
        
        # Step 2: Exchange code for access token
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        token_data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            
            # Debug: Print response details
            print(f"TikTok token response status: {response.status_code}")
            print(f"TikTok token response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"TikTok token exchange failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error response text: {response.text}")
                return False
            
            token_info = response.json()
            print(f"TikTok token response: {token_info}")
            
            if token_info.get("error"):
                print(f"TikTok authentication failed: {token_info['error']['message']}")
                return False
            
            # Calculate actual expiration timestamp
            import time
            expires_in = token_info.get("expires_in", 3600)  # Default to 1 hour if not provided
            expires_at = int(time.time()) + expires_in
            
            self.credentials["tiktok"] = OAuthCredentials(
                access_token=token_info["access_token"],
                refresh_token=token_info.get("refresh_token"),
                expires_at=expires_at,
                scope=token_info.get("scope"),
                user_id=token_info.get("open_id"),
                platform="tiktok"
            )
            
            self._save_credentials()
            print("TikTok authentication successful!")
            return True
            
        except Exception as e:
            print(f"TikTok authentication failed: {e}")
            return False
    
    def extend_instagram_token(self, creds: OAuthCredentials) -> bool:
        """Extend Instagram long-lived access token."""
        client_secret = os.getenv("INSTAGRAM_CLIENT_SECRET")
        
        if not client_secret:
            print("Instagram client secret not found for token extension")
            return False
        
        # Instagram token extension uses POST request with form data
        extend_url = "https://graph.instagram.com/access_token"
        data = {
            "grant_type": "ig_exchange_token",
            "client_secret": client_secret,
            "access_token": creds.access_token
        }
        
        try:
            response = requests.post(extend_url, data=data)
            
            if response.status_code != 200:
                print(f"Instagram token extension failed: {response.status_code} - {response.text}")
                return False
            
            token_info = response.json()
            
            if token_info.get("error"):
                print(f"Instagram token extension failed: {token_info['error']['message']}")
                return False
            
            # Update credentials with extended token
            expires_in = token_info.get("expires_in", 3600)
            expires_at = int(time.time()) + expires_in
            
            creds.access_token = token_info["access_token"]
            creds.expires_at = expires_at
            
            self._save_credentials()
            print("Instagram token extended successfully!")
            return True
            
        except Exception as e:
            print(f"Instagram token extension failed: {e}")
            return False
    
    def refresh_tiktok_token(self, creds: OAuthCredentials) -> bool:
        """Refresh TikTok access token using refresh token."""
        if not creds.refresh_token:
            print("No refresh token available for TikTok")
            return False
        
        client_key = os.getenv("TIKTOK_CLIENT_KEY")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        
        if not client_key or not client_secret:
            print("TikTok credentials not found for token refresh")
            return False
        
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        token_data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": creds.refresh_token,
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_info = response.json()
            
            if token_info.get("error"):
                print(f"TikTok token refresh failed: {token_info['error']['message']}")
                return False
            
            # Update credentials with new token
            import time
            expires_in = token_info.get("expires_in", 3600)
            expires_at = int(time.time()) + expires_in
            
            creds.access_token = token_info["access_token"]
            creds.refresh_token = token_info.get("refresh_token", creds.refresh_token)  # Keep old refresh token if not provided
            creds.expires_at = expires_at
            
            self._save_credentials()
            print("TikTok token refreshed successfully!")
            return True
            
        except Exception as e:
            print(f"TikTok token refresh failed: {e}")
            return False
    
    def refresh_youtube_token(self, creds: OAuthCredentials) -> bool:
        """Refresh YouTube access token using Google's OAuth system."""
        client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
        
        if not client_secrets_file:
            print("YouTube client secrets file not found for token refresh")
            return False
        
        # MUST use ALL scopes, not just upload!
        SCOPES = [
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl',
            'https://www.googleapis.com/auth/youtube.upload'
        ]
        
        try:
            # Get client_id and client_secret from client_secrets_file
            import json
            with open(client_secrets_file, 'r') as f:
                secrets_data = json.load(f)
                client_config = secrets_data.get('installed') or secrets_data.get('web') or {}
                client_id = client_config.get('client_id')
                client_secret = client_config.get('client_secret')
            
            if not client_id or not client_secret:
                print("Could not extract client_id and client_secret from secrets file")
                return False
            
            # Create Credentials object from stored data
            google_creds = Credentials(
                token=creds.access_token,
                refresh_token=creds.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
            
            # Refresh the token
            google_creds.refresh(Request())
            
            # Update our stored credentials
            creds.access_token = google_creds.token
            creds.refresh_token = google_creds.refresh_token
            creds.expires_at = self._expiry_timestamp(google_creds.expiry)
            
            # Save updated credentials (to database if available, else to file)
            self._save_credentials()
            
            # Also save to Google's token file format for compatibility
            token_file = self.credentials_dir / "youtube_token.json"
            with open(token_file, 'w') as token:
                token.write(google_creds.to_json())
            
            print("YouTube token refreshed successfully!")
            return True
            
        except Exception as e:
            print(f"YouTube token refresh failed: {e}")
            return False
    
    def get_credentials(self, platform: str) -> Optional[OAuthCredentials]:
        """Get credentials for a specific platform, refreshing if needed."""
        creds = self.credentials.get(platform)
        if not creds:
            return None
        
        # Check if token needs refresh/extension
        if creds.expires_at and creds.expires_at <= int(time.time()):
            print(f"[AUTH] {platform.upper()} token expired, attempting refresh...")
            if platform == "tiktok" and creds.refresh_token:
                if self.refresh_tiktok_token(creds):
                    return creds
                else:
                    print(f"[AUTH] {platform.upper()} token refresh failed, re-authentication required")
                    return None
            elif platform == "instagram":
                if self.extend_instagram_token(creds):
                    return creds
                else:
                    print(f"[AUTH] {platform.upper()} token extension failed, re-authentication required")
                    return None
            elif platform == "youtube" and creds.refresh_token:
                if self.refresh_youtube_token(creds):
                    return creds
                else:
                    print(f"[AUTH] {platform.upper()} token refresh failed, re-authentication required")
                    return None
            else:
                print(f"[AUTH] {platform.upper()} token expired and no refresh mechanism available")
                return None
        
        return creds
    
    def is_authenticated(self, platform: str) -> bool:
        """Check if we have valid credentials for a platform."""
        creds = self.get_credentials(platform)
        return creds is not None and creds.access_token is not None
    
    def reset_platform_auth(self, platform: str) -> bool:
        """Reset authentication for a specific platform."""
        # Delete from database if available
        if self.db:
            try:
                self.db.delete_oauth_credentials(platform)
            except Exception as e:
                print(f"Error deleting credentials from database: {e}")
        
        # Remove from in-memory credentials
        if platform in self.credentials:
            del self.credentials[platform]
            # Only save to file if not using database
            if not self.db:
                self._save_credentials()
            print(f"[SUCCESS] {platform.upper()} authentication reset")
            return True
        else:
            print(f"[INFO] {platform.upper()} was not authenticated")
            return True
    
    def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate with all platforms."""
        results = {}
        
        print("Starting authentication for all platforms...")
        
        # Instagram
        print("\n=== Instagram Authentication ===")
        results["instagram"] = self.authenticate_instagram()
        
        # YouTube
        print("\n=== YouTube Authentication ===")
        results["youtube"] = self.authenticate_youtube()
        
        # TikTok
        print("\n=== TikTok Authentication ===")
        results["tiktok"] = self.authenticate_tiktok()
        
        return results
