"""Discord webhook service for sending upload notifications."""

import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class DiscordWebhookService:
    """Service for sending Discord webhook notifications."""
    
    def __init__(self):
        self.platform_emojis = {
            "youtube": "🎬",
            "instagram": "📸", 
            "tiktok": "🎵"
        }
        
        self.platform_colors = {
            "youtube": 0xFF0000,  # Red
            "instagram": 0xE4405F,  # Instagram pink
            "tiktok": 0x000000    # Black
        }
    
    def send_upload_notification(self, webhook_url: str, platform: str, title: str, 
                               video_url: Optional[str] = None) -> bool:
        """
        Send upload notification to Discord webhook.
        
        Args:
            webhook_url: Discord webhook URL
            platform: Platform name (youtube, instagram, tiktok)
            title: Video title
            video_url: Video URL (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get platform emoji and color
            emoji = self.platform_emojis.get(platform.lower(), "📹")
            color = self.platform_colors.get(platform.lower(), 5814783)  # Default blue
            
            # Create Discord embed payload
            embed = {
                "title": f"{emoji} New Video Posted!",
                "description": title,
                "color": color,
                "fields": [
                    {
                        "name": "Platform",
                        "value": platform.upper(),
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add video URL if provided
            if video_url:
                embed["url"] = video_url
            
            payload = {
                "embeds": [embed]
            }
            
            # Send webhook request
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 204:  # Discord returns 204 for successful webhooks
                print(f"[Discord] Successfully sent notification for {platform.upper()} upload")
                return True
            else:
                print(f"[Discord] Failed to send notification: HTTP {response.status_code}")
                print(f"[Discord] Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[Discord] Network error sending notification: {e}")
            return False
        except Exception as e:
            print(f"[Discord] Error sending notification: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_webhook(self, webhook_url: str) -> bool:
        """
        Test Discord webhook with a sample message.
        
        Args:
            webhook_url: Discord webhook URL
            
        Returns:
            True if webhook is working, False otherwise
        """
        return self.send_upload_notification(
            webhook_url=webhook_url,
            platform="test",
            title="🔧 Test Notification - Webhook is working!",
            video_url=None
        )

