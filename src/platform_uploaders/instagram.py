"""Instagram Reels uploader using Instagram Graph API."""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

from managers.oauth_manager import OAuthCredentials
from content_creation.types import FTPUploader, UploadResult

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # Python < 3.7


@dataclass
class InstagramUploader:
    """Handles Instagram Reels uploads using FTP server and video_url parameter."""
    
    def __init__(self, ftp_uploader: FTPUploader):
        self.ftp_uploader = ftp_uploader

    def _assert_public_video_url(self, video_url: str) -> Optional[str]:
        """Return an actionable error when Instagram cannot fetch the hosted video."""
        parsed = urlparse(video_url)
        if parsed.scheme != "https":
            return "Instagram requires a public HTTPS video URL. Configure FTP_URL/public hosting with HTTPS."

        try:
            print("[DEBUG] Testing hosted video URL accessibility...")
            test_response = requests.head(video_url, timeout=15, allow_redirects=True)
            print(f"[DEBUG] Hosted video URL response: {test_response.status_code}")
            if test_response.status_code >= 400:
                return f"Hosted video URL is not publicly accessible: HTTP {test_response.status_code}"
        except requests.exceptions.SSLError as e:
            return f"Hosted video URL SSL validation failed. The public certificate may be expired or invalid: {e}"
        except requests.RequestException as e:
            return f"Hosted video URL is not reachable by Instagram: {e}"

        return None
    
    def upload(self, video_path: Path, metadata: Dict[str, str], creds: OAuthCredentials, thumbnail_path: Optional[Path] = None) -> UploadResult:
        """Upload video to Instagram Reels using FTP server and video_url parameter."""
        try:
            # Step 1: Get Instagram Business Account ID directly
            user_url = f"https://graph.instagram.com/v23.0/me?fields=id,name&access_token={creds.access_token}"

            user_response = requests.get(user_url)
            user_response.raise_for_status()
                
            user_data = user_response.json()
            if not user_data.get('id'):
                return UploadResult("instagram", False, error="No Instagram Business Account found.")
            
            instagram_account_id = user_data['id']
            print(f"[SUCCESS] Found Instagram Business Account: {instagram_account_id}")
            
            # Step 2: Upload video to FTP server
            print("[UPLOAD] Uploading video to FTP server...")
            video_url = self.ftp_uploader.upload_video(video_path)
            if not video_url:
                return UploadResult("instagram", False, error="Failed to upload video to FTP server")
            
            print(f"[SUCCESS] Video uploaded to FTP: {video_url}")
            
            accessibility_error = self._assert_public_video_url(video_url)
            if accessibility_error:
                print(f"[ERROR] {accessibility_error}")
                return UploadResult("instagram", False, error=accessibility_error)
            
            # Validate video for Instagram Reels
            try:
                from content_creation.video_processor import VideoProcessor
                vp = VideoProcessor()
                instagram_check = vp.check_instagram_requirements(video_path)
                
                print(f"[DEBUG] DEBUG: Instagram compliance check:")
                print(f"   Duration: {instagram_check.get('duration', 0):.1f}s")
                print(f"   Resolution: {instagram_check.get('width', 0)}x{instagram_check.get('height', 0)}")
                print(f"   Frame rate: {instagram_check.get('fps', 0):.1f}fps")
                print(f"   Video codec: {instagram_check.get('codec', 'unknown')}")
                print(f"   File size: {instagram_check.get('file_size', 0) / (1024*1024):.1f}MB")
                print(f"   Video bitrate: {instagram_check.get('bitrate', 0) / (1024*1024):.1f}Mbps")
                print(f"   Audio codec: {instagram_check.get('audio_codec', 'unknown')}")
                print(f"   Audio bitrate: {instagram_check.get('audio_bitrate', 0) / 1000:.0f}kbps")
                print(f"   Sample rate: {instagram_check.get('sample_rate', 0)}Hz")
                print(f"   Channels: {instagram_check.get('channels', 0)}")
                print(f"   Compliant: {instagram_check.get('compliant', False)}")
                
                if not instagram_check.get('compliant', False):
                    issues = instagram_check.get('issues', [])
                    print(f"[WARNING]  Instagram compliance issues: {issues}")
                    # Don't fail immediately, let Instagram handle it, but warn
                    print("[WARNING]  Video may not meet Instagram requirements, but continuing...")
                else:
                    print("[SUCCESS] Video meets Instagram Reels requirements")
                    
            except Exception as e:
                print(f"[WARNING]  Could not validate video: {e}")
                # Continue anyway, let Instagram handle validation
            
            # Step 3: Create media container with video_url
            media_url = f"https://graph.instagram.com/v23.0/{instagram_account_id}/media"
            
            # Create caption with fallbacks
            caption = metadata.get('caption', '').strip()
            hashtags = metadata.get('hashtags', '').strip()
            
            if not caption and not hashtags:
                caption_text = "Check out this epic gaming moment! 🎮 #gaming #shorts"
                print(f"[WARNING]  Empty caption and hashtags in metadata, using fallback: {caption_text}")
            else:
                caption_text = f"{caption}\n\n{hashtags}".strip()
            
            media_data = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption_text,
                "access_token": creds.access_token
            }
            
            print("Creating Instagram Reels container...")
            print(f"[DEBUG] Media URL: {media_url}")
            print(f"[DEBUG] Video URL: {video_url}")
            
            # Ensure caption is properly encoded
            if 'caption' in media_data:
                media_data['caption'] = media_data['caption'].encode('utf-8', errors='replace').decode('utf-8')
            
            media_response = requests.post(media_url, data=media_data)
            print(f"[DEBUG] Container response status: {media_response.status_code}")
            print(f"[DEBUG] Container response: {media_response.text}")
            
            media_response.raise_for_status()
            
            container_data = media_response.json()
            print(f"[DEBUG] Container data: {container_data}")
            
            if 'error' in container_data:
                error_details = container_data['error']
                error_msg = error_details.get('message', 'Unknown error')
                error_code = error_details.get('code', 'Unknown code')
                error_type = error_details.get('type', 'Unknown type')
                print(f"[ERROR] Instagram container creation error: {error_type} - {error_msg} (Code: {error_code})")
                return UploadResult("instagram", False, error=f"Container creation failed: {error_type} - {error_msg}")
            
            container_id = container_data['id']
            print(f"[SUCCESS] Container created: {container_id}")
            
            # Step 4: Check container status before publishing
            # Request additional fields to get more detailed error information
            status_url = f"https://graph.instagram.com/v23.0/{container_id}?fields=status_code,status&access_token={creds.access_token}"
            

            # Wait for container to be ready (max 5 minutes)
            max_attempts = 30
            for attempt in range(max_attempts):
                print(f"[DEBUG] Status check attempt {attempt + 1}/{max_attempts}")
                status_response = requests.get(status_url)
                print(f"[DEBUG] Status response code: {status_response.status_code}")
                print(f"[DEBUG] Status response: {status_response.text}")
                status_response.raise_for_status()
                
                status_data = status_response.json()
                status = status_data.get('status_code')
                print(f"[DEBUG] Parsed status: {status}")
                print(f"[DEBUG] Full status data: {status_data}")
                
                if status == 'FINISHED':
                    print("[SUCCESS] Container processing finished!")
                    break
                elif status == 'ERROR':
                    error_details = status_data.get('error', {})
                    error_msg = error_details.get('message', 'Unknown error')
                    error_code = error_details.get('code', 'Unknown code')
                    error_type = error_details.get('type', 'Unknown type')
                    print(f"[ERROR] Instagram container error: {error_type} - {error_msg} (Code: {error_code})")
                    print(f"[DEBUG] Full error response: {error_details}")
                    return UploadResult("instagram", False, error=f"Container processing failed: {error_type} - {error_msg}")
                elif status == 'EXPIRED':
                    return UploadResult("instagram", False, error="Container expired")
                elif status == 'IN_PROGRESS':
                    print("[WAIT] Container still processing, waiting 10 seconds...")
                    time.sleep(10)  # Wait 10 seconds
                else:
                    print(f"[WARNING]  Unknown container status: {status}")
                    print(f"[DEBUG] Full status response: {status_data}")
                    # Don't fail immediately for unknown status, wait a bit more
                    if attempt < max_attempts - 1:
                        print("[WAIT] Waiting 10 seconds before retry...")
                        time.sleep(10)
                    else:
                        return UploadResult("instagram", False, error=f"Unknown container status: {status}")
            else:
                return UploadResult("instagram", False, error="Container processing timeout")
            
            # Step 5: Publish the Reel
            publish_url = f"https://graph.instagram.com/v23.0/{instagram_account_id}/media_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": creds.access_token
            }
            
            print("Publishing Instagram Reel...")
            publish_response = requests.post(publish_url, data=publish_data)

            publish_response.raise_for_status()
            
            publish_result = publish_response.json()

            if 'error' in publish_result:
                return UploadResult("instagram", False, error=f"Publishing failed: {publish_result['error']['message']}")
            
            media_id = publish_result['id']
            reel_url = f"https://www.instagram.com/reel/{media_id}/"
            
            print(f"[SUCCESS] Instagram Reel published successfully! Media ID: {media_id}")
            print(f"[URL] Reel URL: {reel_url}")
            
            return UploadResult(
                "instagram",
                True,
                video_id=media_id,
                url=reel_url
            )
            
        except Exception as e:
            return UploadResult("instagram", False, error=str(e))
    
    def get_upload_status(self, creds: OAuthCredentials) -> Dict[str, any]:
        """Get Instagram upload status and account info."""
        try:
            # Get Instagram Business Account info and rate limits
            user_url = f"https://graph.instagram.com/v23.0/me?fields=id,name&access_token={creds.access_token}"
            user_response = requests.get(user_url)
            user_response.raise_for_status()
            
            user_data = user_response.json()
            if not user_data.get('id'):
                return {"authenticated": False, "error": "No Instagram Business Account found"}
            
            instagram_account_id = user_data['id']
            
            # Get rate limit info
            rate_limit_url = f"https://graph.instagram.com/v23.0/{instagram_account_id}/content_publishing_limit?access_token={creds.access_token}"
            rate_limit_response = requests.get(rate_limit_url)
            
            rate_limit_info = {}
            if rate_limit_response.status_code == 200:
                rate_limit_info = rate_limit_response.json()
            
            return {
                "authenticated": True, 
                "instagram_account_id": instagram_account_id,
                "rate_limits": rate_limit_info
            }
            
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
    
    def check_rate_limit(self, creds: OAuthCredentials) -> Dict[str, any]:
        """Check Instagram publishing rate limits."""
        try:
            # Get Instagram Business Account ID
            user_url = f"https://graph.instagram.com/v23.0/me?fields=id,name&access_token={creds.access_token}"
            user_response = requests.get(user_url)
            user_response.raise_for_status()
            
            user_data = user_response.json()
            if not user_data.get('id'):
                return {"error": "No Instagram Business Account found"}
            
            instagram_account_id = user_data['id']
            
            # Get rate limit info
            rate_limit_url = f"https://graph.instagram.com/v23.0/{instagram_account_id}/content_publishing_limit?access_token={creds.access_token}"
            rate_limit_response = requests.get(rate_limit_url)
            rate_limit_response.raise_for_status()
            
            return rate_limit_response.json()
            
        except Exception as e:
            return {"error": str(e)}
