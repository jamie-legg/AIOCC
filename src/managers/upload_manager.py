"""Upload manager for posting videos to social media platforms."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .oauth_manager import OAuthManager
from .discord_service import DiscordWebhookService
from content_creation.types import FTPUploader, UploadResult
from platform_uploaders import InstagramUploader, YouTubeUploader, TikTokUploader

class UploadManager:
    """Manages video uploads to multiple social media platforms."""
    
    def __init__(self, oauth_manager: OAuthManager):
        self.oauth_manager = oauth_manager
        self.ftp_uploader = FTPUploader()
        
        # Initialize platform uploaders
        self.instagram_uploader = InstagramUploader(self.ftp_uploader)
        self.youtube_uploader = YouTubeUploader()
        self.tiktok_uploader = TikTokUploader()
        
        # Initialize Discord webhook service
        self.discord_service = DiscordWebhookService()
        
        # Failed uploads tracking
        self.failed_uploads_file = Path.home() / ".content_creation" / "failed_uploads.json"
        self.failed_uploads_file.parent.mkdir(exist_ok=True)
        
        # Initialize local analytics tracking (auto-detect)
        self.analytics_url: Optional[str] = None
        analytics_url = os.getenv("ANALYTICS_API_URL", "http://localhost:8000")
        
        # Try to connect to local analytics server
        try:
            import requests
            response = requests.get(f"{analytics_url}/health", timeout=2)
            if response.status_code == 200:
                self.analytics_url = analytics_url
                print(f"[📊] Analytics tracking enabled: {analytics_url}")
        except Exception:
            # Analytics server not running, disable tracking silently
            pass
    
    def upload_to_instagram(self, video_path: Path, metadata: Dict[str, str], thumbnail_path: Optional[Path] = None) -> UploadResult:
        """Upload video to Instagram Reels using FTP server and video_url parameter."""
        creds = self.oauth_manager.get_credentials("instagram")
        if not creds:
            return UploadResult("instagram", False, error="Not authenticated")
        
        return self.instagram_uploader.upload(video_path, metadata, creds, thumbnail_path=thumbnail_path)
    
    
    def upload_to_youtube(self, video_path: Path, metadata: Dict[str, str], thumbnail_path: Optional[Path] = None) -> UploadResult:
        """Upload video to YouTube Shorts with retry logic."""
        creds = self.oauth_manager.get_credentials("youtube")
        if not creds:
            return UploadResult("youtube", False, error="Not authenticated")
        
        return self.youtube_uploader.upload(video_path, metadata, creds, thumbnail_path=thumbnail_path)
    
    
    def upload_to_tiktok(self, video_path: Path, metadata: Dict[str, str], thumbnail_path: Optional[Path] = None) -> UploadResult:
        """Upload video to TikTok using Content Posting API (Inbox Upload)."""
        creds = self.oauth_manager.get_credentials("tiktok")
        if not creds:
            return UploadResult("tiktok", False, error="Not authenticated")
        
        return self.tiktok_uploader.upload(video_path, metadata, creds, thumbnail_path=thumbnail_path)
    
    def _track_upload_analytics(self, platform: str, video_path: Path, metadata: Dict[str, str], result: UploadResult):
        """Track upload to local analytics server (delivery notification)."""
        if not self.analytics_url:
            return  # Analytics server not running
        
        try:
            import requests
            
            # Create video record if successful
            if result.success:
                video_data = {
                    "video_id": video_path.stem,
                    "title": metadata.get("title", ""),
                    "description": metadata.get("caption", ""),
                    "platform": platform,
                    "platform_video_id": result.video_id or "",
                    "platform_url": result.url or "",
                    "duration": 0.0,
                    "file_path": str(video_path)
                }
                
                response = requests.post(
                    f"{self.analytics_url}/videos",
                    json=video_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"[📊] Tracked {platform.upper()} upload to analytics")
        except Exception as e:
            # Silently fail - analytics is optional
            pass
    
    def _notify_discord(self, platform: str, video_path: Path, metadata: Dict[str, str], result: UploadResult):
        """Send Discord webhook notifications for successful uploads."""
        if not result.success:
            print(f"[Discord] Skipping notification for {platform} - upload failed")
            return  # Only notify on successful uploads
        
        print(f"[Discord] Attempting to send notification for {platform} upload")
        
        try:
            from .config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Get webhooks configured for this platform
            webhooks = config_manager.get_discord_webhooks_for_platform(platform)
            
            if not webhooks:
                print(f"[Discord] No webhooks configured for platform: {platform}")
                return  # No webhooks configured for this platform
            
            print(f"[Discord] Found {len(webhooks)} webhook(s) for {platform}")
            
            # Get video title from metadata
            title = metadata.get("title", f"Video from {video_path.stem}")
            
            # Send notification to each webhook
            for webhook in webhooks:
                webhook_url = webhook.get("url")
                webhook_name = webhook.get("name", "Unnamed")
                if webhook_url:
                    print(f"[Discord] Sending notification to webhook: {webhook_name}")
                    success = self.discord_service.send_upload_notification(
                        webhook_url=webhook_url,
                        platform=platform,
                        title=title,
                        video_url=result.url
                    )
                    if success:
                        print(f"[Discord] Successfully sent notification to {webhook_name}")
                    else:
                        print(f"[Discord] Failed to send notification to {webhook_name}")
                else:
                    print(f"[Discord] No URL found for webhook: {webhook_name}")
                    
        except Exception as e:
            # Log error but don't fail the upload process
            print(f"[Discord] Error sending notification: {e}")
            import traceback
            traceback.print_exc()
    
    def _validate_metadata(self, metadata: Dict[str, str], video_path: Path) -> Dict[str, str]:
        """Validate and ensure metadata has required fields with fallbacks."""
        validated = metadata.copy() if metadata else {}
        
        # Ensure we have a title
        if not validated.get('title', '').strip():
            validated['title'] = f"Gaming Clip - {video_path.stem}"
            print(f"[WARNING] No title in metadata, using fallback: {validated['title']}")
        
        # Ensure we have caption or hashtags
        if not validated.get('caption', '').strip() and not validated.get('hashtags', '').strip():
            validated['caption'] = "Check out this epic gaming moment! 🎮"
            validated['hashtags'] = "#gaming #shorts"
            print(f"[WARNING] No caption/hashtags in metadata, using fallback")
        
        return validated

    def upload_to_all_platforms(self, video_path: Path, metadata: Dict[str, str], 
                              platforms: List[str] = None) -> Dict[str, UploadResult]:
        """Upload video to all specified platforms with platform-specific optimization."""
        if platforms is None:
            platforms = ["instagram", "youtube", "tiktok"]
        
        results = {}
        
        print(f"Uploading {video_path.name} to {len(platforms)} platforms...")
        
        # Validate and fix metadata
        validated_metadata = self._validate_metadata(metadata, video_path)
        
        # Import video processor for optimization
        from content_creation.video_processor import VideoProcessor
        video_processor = VideoProcessor()
        
        for platform in platforms:
            print(f"\n--- Uploading to {platform.upper()} ---")
            
            # Optimize video for platform-specific requirements
            try:
                optimized_video = video_processor.optimize_for_platform(video_path, platform)
                print(f"Using optimized video: {optimized_video.name}")
            except Exception as e:
                print(f"[WARNING] Optimization failed for {platform}: {e}")
                print("Using original video...")
                optimized_video = video_path
            
            if platform == "instagram":
                results[platform] = self.upload_to_instagram(optimized_video, validated_metadata)
            elif platform == "youtube":
                results[platform] = self.upload_to_youtube(optimized_video, validated_metadata)
            elif platform == "tiktok":
                results[platform] = self.upload_to_tiktok(optimized_video, validated_metadata)
            else:
                results[platform] = UploadResult(platform, False, error="Unknown platform")
            
            # Track upload to analytics server (delivery notification)
            result = results[platform]
            self._track_upload_analytics(platform, video_path, validated_metadata, result)
            
            # Send Discord notifications for successful uploads
            self._notify_discord(platform, video_path, validated_metadata, result)
            
            # Print result
            if result.success:
                print(f"[SUCCESS] {platform.upper()}: Success! Video ID: {result.video_id}")
                if result.url:
                    print(f"   URL: {result.url}")
            else:
                print(f"[ERROR] {platform.upper()}: Failed - {result.error}")
        
        # Track failed uploads for retry
        self._track_failed_uploads(video_path, validated_metadata, results)
        
        return results
    
    def _track_failed_uploads(self, video_path: Path, metadata: Dict[str, str], results: Dict[str, UploadResult]):
        """Track failed uploads for later retry."""
        failed_uploads = self._load_failed_uploads()
        
        for platform, result in results.items():
            if not result.success:
                failed_entry = {
                    "video_path": str(video_path),
                    "platform": platform,
                    "metadata": metadata,
                    "error": result.error,
                    "timestamp": datetime.now().isoformat(),
                    "retry_count": 0
                }
                
                # Check if this video/platform combination already exists
                existing_key = f"{video_path.name}_{platform}"
                if existing_key not in failed_uploads:
                    failed_uploads[existing_key] = failed_entry
                    print(f"[RETRY] Added {platform.upper()} upload to retry queue")
        
        self._save_failed_uploads(failed_uploads)
    
    def _load_failed_uploads(self) -> Dict[str, Any]:
        """Load failed uploads from file."""
        if not self.failed_uploads_file.exists():
            return {}
        
        try:
            with open(self.failed_uploads_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load failed uploads: {e}")
            return {}
    
    def _save_failed_uploads(self, failed_uploads: Dict[str, Any]):
        """Save failed uploads to file."""
        try:
            with open(self.failed_uploads_file, 'w') as f:
                json.dump(failed_uploads, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Could not save failed uploads: {e}")
    
    def list_failed_uploads(self) -> Dict[str, Any]:
        """List all failed uploads available for retry."""
        return self._load_failed_uploads()
    
    def retry_failed_upload(self, video_name: str, platform: str) -> UploadResult:
        """Retry a specific failed upload."""
        failed_uploads = self._load_failed_uploads()
        key = f"{video_name}_{platform}"
        
        if key not in failed_uploads:
            return UploadResult(platform, False, error="Failed upload not found")
        
        failed_entry = failed_uploads[key]
        video_path = Path(failed_entry["video_path"])
        metadata = failed_entry["metadata"]
        
        if not video_path.exists():
            return UploadResult(platform, False, error="Video file no longer exists")
        
        print(f"[RETRY] Retrying {platform.upper()} upload for {video_name}")
        
        # Optimize video for platform-specific requirements
        from content_creation.video_processor import VideoProcessor
        video_processor = VideoProcessor()
        
        try:
            optimized_video = video_processor.optimize_for_platform(video_path, platform)
            print(f"[OPTIMIZE] Using optimized video: {optimized_video.name}")
        except Exception as e:
            print(f"[WARNING] Optimization failed for {platform}: {e}")
            print("[WARNING] Using original video...")
            optimized_video = video_path
        
        # Retry the upload with optimized video
        if platform == "instagram":
            result = self.upload_to_instagram(optimized_video, metadata)
        elif platform == "youtube":
            result = self.upload_to_youtube(optimized_video, metadata)
        elif platform == "tiktok":
            result = self.upload_to_tiktok(optimized_video, metadata)
        else:
            return UploadResult(platform, False, error="Unknown platform")
        
        # Update retry count
        failed_entry["retry_count"] += 1
        
        if result.success:
            # Remove from failed uploads if successful
            del failed_uploads[key]
            print(f"[SUCCESS] {platform.upper()} retry successful!")
        else:
            # Update error message
            failed_entry["error"] = result.error
            failed_entry["timestamp"] = datetime.now().isoformat()
            print(f"[FAILED] {platform.upper()} retry failed: {result.error}")
        
        self._save_failed_uploads(failed_uploads)
        return result
    
    def retry_all_failed_uploads(self, platforms: List[str] = None) -> Dict[str, UploadResult]:
        """Retry all failed uploads for specified platforms."""
        if platforms is None:
            platforms = ["instagram", "youtube", "tiktok"]
        
        failed_uploads = self._load_failed_uploads()
        results = {}
        
        print(f"[RETRY] Retrying failed uploads for platforms: {', '.join(platforms)}")
        
        for key, failed_entry in list(failed_uploads.items()):
            platform = failed_entry["platform"]
            if platform in platforms:
                video_name = failed_entry["video_path"].split("\\")[-1]  # Get just filename
                result = self.retry_failed_upload(video_name, platform)
                results[f"{video_name}_{platform}"] = result
        
        return results
    
    def clear_failed_uploads(self, platform: str = None):
        """Clear failed uploads (optionally for specific platform)."""
        failed_uploads = self._load_failed_uploads()
        
        if platform:
            # Remove only specific platform failures
            keys_to_remove = [key for key, entry in failed_uploads.items() if entry["platform"] == platform]
            for key in keys_to_remove:
                del failed_uploads[key]
            print(f"[CLEAR] Cleared failed uploads for {platform.upper()}")
        else:
            # Clear all failed uploads
            failed_uploads.clear()
            print("[CLEAR] Cleared all failed uploads")
        
        self._save_failed_uploads(failed_uploads)
    
    def _extract_hashtags(self, hashtags_str: str) -> List[str]:
        """Extract hashtags from string and return as list."""
        if not hashtags_str:
            return []
        
        # Split by space and filter hashtags
        tags = [tag.strip() for tag in hashtags_str.split() if tag.strip().startswith('#')]
        # Remove # symbol for YouTube tags
        return [tag[1:] for tag in tags if len(tag) > 1]
    
    def get_upload_status(self, platform: str) -> Dict[str, Any]:
        """Get upload status and account info for a platform."""
        creds = self.oauth_manager.get_credentials(platform)
        if not creds:
            return {"authenticated": False, "error": "Not authenticated"}
        
        try:
            if platform == "instagram":
                return self.instagram_uploader.get_upload_status(creds)
            elif platform == "youtube":
                return self.youtube_uploader.get_upload_status(creds)
            elif platform == "tiktok":
                return self.tiktok_uploader.get_upload_status(creds)
            else:
                return {"authenticated": False, "error": "Unknown platform"}
            
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
    
    def check_instagram_rate_limit(self) -> Dict[str, Any]:
        """Check Instagram publishing rate limits."""
        creds = self.oauth_manager.get_credentials("instagram")
        if not creds:
            return {"error": "Not authenticated"}
        
        return self.instagram_uploader.check_rate_limit(creds)
