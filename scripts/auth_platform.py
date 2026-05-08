#!/usr/bin/env python3
"""Run the existing OAuth flow for one platform."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from managers.oauth_manager import OAuthManager


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: auth_platform.py <youtube|instagram|tiktok>")
        return 2

    platform = sys.argv[1].lower()
    manager = OAuthManager()

    if platform == "youtube":
        ok = manager.authenticate_youtube(force=True)
    elif platform == "instagram":
        ok = manager.authenticate_instagram()
    elif platform == "tiktok":
        ok = manager.authenticate_tiktok()
    else:
        print(f"Unsupported platform: {platform}")
        return 2

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
