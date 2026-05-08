"""Configuration manager for Upload Studio server-side upload helpers."""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Config:
    """Runtime options used by the web upload flow."""

    upload_to_instagram: bool = os.getenv("UPLOAD_TO_INSTAGRAM", "true").lower() in ("true", "1", "yes", "on")
    upload_to_youtube: bool = os.getenv("UPLOAD_TO_YOUTUBE", "true").lower() in ("true", "1", "yes", "on")
    upload_to_tiktok: bool = os.getenv("UPLOAD_TO_TIKTOK", "true").lower() in ("true", "1", "yes", "on")
    backend_api_url: str = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    api_key: str = os.getenv("CONTENT_CREATION_API_KEY", "")
    discord_webhooks: List[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.discord_webhooks is None:
            self.discord_webhooks = []


class ConfigManager:
    """Manages persisted Upload Studio helper configuration."""

    def __init__(self, config_file: Path = Path.home() / ".content_creation" / "config.json"):
        self.config_file = config_file
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> Config:
        config = Config()

        if not self.config_file.exists():
            return config

        try:
            with open(self.config_file, "r") as file:
                file_data = json.load(file)

            if not os.getenv("UPLOAD_TO_INSTAGRAM"):
                config.upload_to_instagram = file_data.get("upload_to_instagram", config.upload_to_instagram)
            if not os.getenv("UPLOAD_TO_YOUTUBE"):
                config.upload_to_youtube = file_data.get("upload_to_youtube", config.upload_to_youtube)
            if not os.getenv("UPLOAD_TO_TIKTOK"):
                config.upload_to_tiktok = file_data.get("upload_to_tiktok", config.upload_to_tiktok)

            config.backend_api_url = file_data.get("backend_api_url", config.backend_api_url)
            config.api_key = file_data.get("api_key", config.api_key)
            config.discord_webhooks = file_data.get("discord_webhooks", [])
        except Exception as error:
            print(f"Error loading Upload Studio config: {error}")

        return config

    def _save_config(self) -> None:
        try:
            with open(self.config_file, "w") as file:
                json.dump(asdict(self.config), file, indent=2)
        except Exception as error:
            print(f"Error saving Upload Studio config: {error}")

    def get_config(self) -> Config:
        return self.config

    def set_upload_platform(self, platform: str, enabled: bool) -> bool:
        if platform == "instagram":
            self.config.upload_to_instagram = enabled
        elif platform == "youtube":
            self.config.upload_to_youtube = enabled
        elif platform == "tiktok":
            self.config.upload_to_tiktok = enabled
        else:
            print(f"Unknown platform: {platform}")
            return False

        self._save_config()
        return True

    def set_platform_upload(self, platform: str, enabled: bool) -> bool:
        return self.set_upload_platform(platform, enabled)

    def get_upload_platforms(self) -> List[str]:
        platforms = []
        if self.config.upload_to_instagram:
            platforms.append("instagram")
        if self.config.upload_to_youtube:
            platforms.append("youtube")
        if self.config.upload_to_tiktok:
            platforms.append("tiktok")
        return platforms

    def set_backend_config(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> bool:
        if api_url is not None:
            self.config.backend_api_url = api_url
        if api_key is not None:
            self.config.api_key = api_key

        self._save_config()
        return True

    def add_discord_webhook(self, name: str, url: str, platforms: List[str]) -> str:
        webhook_id = str(uuid.uuid4())
        self.config.discord_webhooks.append(
            {
                "id": webhook_id,
                "name": name,
                "url": url,
                "platforms": platforms,
            }
        )
        self._save_config()
        return webhook_id

    def remove_discord_webhook(self, webhook_id: str) -> bool:
        initial_count = len(self.config.discord_webhooks)
        self.config.discord_webhooks = [
            webhook for webhook in self.config.discord_webhooks if webhook.get("id") != webhook_id
        ]

        changed = len(self.config.discord_webhooks) < initial_count
        if changed:
            self._save_config()
        return changed

    def list_discord_webhooks(self) -> List[Dict[str, Any]]:
        return self.config.discord_webhooks.copy()

    def update_discord_webhook(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        platforms: Optional[List[str]] = None,
    ) -> bool:
        for webhook in self.config.discord_webhooks:
            if webhook.get("id") == webhook_id:
                if name is not None:
                    webhook["name"] = name
                if url is not None:
                    webhook["url"] = url
                if platforms is not None:
                    webhook["platforms"] = platforms

                self._save_config()
                return True

        return False

    def get_discord_webhooks_for_platform(self, platform: str) -> List[Dict[str, Any]]:
        return [
            webhook
            for webhook in self.config.discord_webhooks
            if platform in webhook.get("platforms", [])
        ]
