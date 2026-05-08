"""Probe an Instagram media container without printing tokens."""

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from managers.oauth_manager import OAuthManager


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: probe_instagram_container.py <container_id>")
        return 2

    creds = OAuthManager().get_credentials("instagram")
    if not creds:
        print("No Instagram credentials")
        return 1

    fields_list = [
        "status_code,status",
        "status_code,status,error",
        "status_code,status,error_message",
        "status_code,status,video_status",
        "status_code,status,permalink",
    ]
    for fields in fields_list:
        response = requests.get(
            f"https://graph.instagram.com/v23.0/{sys.argv[1]}",
            params={"fields": fields, "access_token": creds.access_token},
            timeout=20,
        )
        print(fields, response.status_code, response.text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
