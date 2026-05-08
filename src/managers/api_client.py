"""API client for communicating with the backend API."""

import requests
from typing import Dict, Any, Optional
from pathlib import Path
import json


class APIClient:
    """Client for backend API communication."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.
        
        Args:
            api_key: User's API key for authentication
            base_url: Backend API base URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to backend API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.RequestException: On API error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"❌ API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"   Response: {e.response.text}")
            raise
    
    def generate_metadata(self, filename: str, game_context: str = "gaming") -> Dict[str, Any]:
        """
        Generate AI-powered metadata for a video file.
        
        Args:
            filename: Video filename
            game_context: Game context for AI generation
            
        Returns:
            Dictionary with title, caption, hashtags
        """
        try:
            response = self._make_request(
                "POST",
                "/api/v1/enrichment/generate",
                data={
                    "filename": filename,
                    "game_context": game_context
                }
            )
            
            return {
                "title": response.get("title", ""),
                "caption": response.get("caption", ""),
                "hashtags": response.get("hashtags", "")
            }
            
        except Exception as e:
            print(f"⚠️  Backend AI enrichment failed: {e}")
            raise
    
    def check_quota(self) -> Dict[str, Any]:
        """
        Check user's quota status.
        
        Returns:
            Dictionary with quota information
        """
        try:
            return self._make_request("GET", "/api/v1/enrichment/quota")
        except Exception as e:
            print(f"⚠️  Failed to check quota: {e}")
            return {"error": str(e)}
    
    def get_oauth_url(self, platform: str, redirect_uri: Optional[str] = None) -> str:
        """
        Get OAuth authorization URL for a platform.
        
        Args:
            platform: Platform name (instagram, youtube, tiktok)
            redirect_uri: Optional redirect URI
            
        Returns:
            Authorization URL to redirect user to
        """
        try:
            params = {}
            if redirect_uri:
                params["redirect_uri"] = redirect_uri
            
            response = self._make_request(
                "POST",
                f"/api/v1/oauth/{platform}/initiate",
                params=params
            )
            
            return response.get("auth_url", "")
            
        except Exception as e:
            print(f"⚠️  Failed to get OAuth URL: {e}")
            raise
    
    def complete_oauth_callback(self, platform: str, code: str, state: str) -> bool:
        """
        Complete OAuth callback after user authorization.
        
        Args:
            platform: Platform name
            code: Authorization code
            state: State parameter
            
        Returns:
            True if successful
        """
        try:
            response = self._make_request(
                "POST",
                f"/api/v1/oauth/{platform}/callback",
                data={
                    "code": code,
                    "state": state,
                    "platform": platform
                }
            )
            
            return response.get("success", False)
            
        except Exception as e:
            print(f"⚠️  OAuth callback failed: {e}")
            return False
    
    def get_oauth_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get stored OAuth credentials for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Credentials dictionary or None if not found
        """
        try:
            response = self._make_request(
                "GET",
                f"/api/v1/oauth/{platform}/credentials"
            )
            
            return response
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            print(f"⚠️  Failed to get OAuth credentials: {e}")
            return None
    
    def delete_oauth_credentials(self, platform: str) -> bool:
        """
        Delete OAuth credentials for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            True if successful
        """
        try:
            response = self._make_request(
                "DELETE",
                f"/api/v1/oauth/{platform}/credentials"
            )
            
            return response.get("success", False)
            
        except Exception as e:
            print(f"⚠️  Failed to delete OAuth credentials: {e}")
            return False
    
    def track_upload(
        self,
        platform: str,
        filename: str,
        video_id: Optional[str] = None,
        video_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> bool:
        """
        Track a video upload event.
        
        Args:
            platform: Platform name
            filename: Video filename
            video_id: Platform video ID
            video_url: Platform video URL
            metadata: Video metadata
            status: Upload status (success/failed)
            error_message: Error message if failed
            
        Returns:
            True if successfully tracked
        """
        try:
            response = self._make_request(
                "POST",
                "/api/v1/analytics/track",
                data={
                    "platform": platform,
                    "filename": filename,
                    "video_id": video_id,
                    "video_url": video_url,
                    "metadata": metadata,
                    "status": status,
                    "error_message": error_message
                }
            )
            
            return response.get("success", False)
            
        except Exception as e:
            print(f"⚠️  Failed to track upload: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test connection to backend API.
        
        Returns:
            True if connection successful
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

