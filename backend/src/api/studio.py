"""Upload Studio API for the simplified flat-file workflow."""

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..api.auth import get_current_user_from_token
from ..models import PlatformUpload, UploadedClip, User, UserRole
from ..services.ai_service import AIService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from managers.oauth_manager import OAuthCredentials, OAuthManager  # noqa: E402
from managers.upload_manager import UploadManager  # noqa: E402

def require_creator(current_user: User = Depends(get_current_user_from_token)) -> User:
    if current_user.role not in {UserRole.ADMIN.value, UserRole.CREATOR.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator access required")
    return current_user


def require_admin(current_user: User = Depends(get_current_user_from_token)) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


router = APIRouter(prefix="/api/v1/studio", tags=["studio"])
callback_router = APIRouter(prefix="/api/oauth", tags=["studio-oauth"])

PLATFORMS = ("youtube", "instagram", "tiktok")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUTH_STATES: dict[str, dict[str, object]] = {}
AUTH_STATE_TTL_SECONDS = 600


class PlatformStatus(BaseModel):
    platform: str
    label: str
    handle: str
    connected: bool
    accent: str
    detail: str | None = None


class StudioStatus(BaseModel):
    authenticated: bool
    role: Literal["admin", "creator", "viewer"]
    user: dict
    platforms: list[PlatformStatus]


class MetadataRequest(BaseModel):
    filename: str
    game_context: str = "gaming"


class MetadataResponse(BaseModel):
    title: str
    description: str
    hashtags: str
    visibility: Literal["public", "unlisted", "private"] = "public"


class RecentUploadResponse(BaseModel):
    id: str
    uploadId: int
    platform: str
    title: str
    status: str
    uploadedAt: str
    url: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    clipId: str
    uploads: list[RecentUploadResponse]
    message: str


class AuthStartResponse(BaseModel):
    platform: str
    started: bool
    message: str
    authUrl: str | None = None


class RetryUploadResponse(BaseModel):
    upload: RecentUploadResponse
    uploads: list[RecentUploadResponse]
    message: str


class AdminUploadResponse(BaseModel):
    uploadId: int
    clipId: int
    userEmail: str
    platform: str
    title: str
    status: str
    uploadedAt: str
    url: str | None = None
    error: str | None = None


def _upload_dir() -> Path:
    output_dir = Path(settings.studio_upload_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _safe_filename(filename: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._")
    return clean or "clip.mp4"


def _fallback_metadata(filename: str) -> MetadataResponse:
    clean_name = Path(filename).stem.replace("_", " ").replace("-", " ").strip().title()
    title = clean_name if clean_name else "Untitled Clip"
    return MetadataResponse(
        title=f"{title}!",
        description="Fresh gameplay clip ready to post.",
        hashtags="#gaming #clips #AIOCC",
        visibility="public",
    )


def _get_or_create_studio_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "studio@local.a iocc".replace(" ", "")).first()
    if user:
        return user

    user = User(
        email="studio@local.aiocc",
        hashed_password="local-studio-user",
        api_key=User.generate_api_key(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _format_uploaded_at(value: datetime | None) -> str:
    if not value:
        return "just now"
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - value).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def _public_error_message(error: str | None) -> str | None:
    if not error:
        return None
    return "Upload failed. Check the platform connection and try again."


def _recent_upload_response(upload: PlatformUpload) -> RecentUploadResponse:
    return RecentUploadResponse(
        id=f"{upload.platform}-{upload.id}",
        uploadId=upload.id,
        platform=upload.platform,
        title=upload.clip.title,
        status=upload.status,
        uploadedAt=_format_uploaded_at(upload.uploaded_at),
        url=upload.platform_url,
        error=_public_error_message(upload.error_message),
    )


def _configured_platforms() -> dict[str, bool]:
    return {
        "youtube": settings.upload_to_youtube or bool(settings.youtube_client_secrets_file),
        "instagram": settings.upload_to_instagram or bool(settings.instagram_client_id and settings.instagram_client_secret),
        "tiktok": settings.upload_to_tiktok or bool(settings.tiktok_client_key and settings.tiktok_client_secret),
    }


def _extract_account_handle(platform: str, status: dict, fallback_user_id: str | None = None) -> str:
    if platform == "youtube":
        channels = status.get("channels") or []
        if channels:
            snippet = channels[0].get("snippet") or {}
            if snippet.get("title"):
                return snippet["title"]

    if platform == "instagram":
        if status.get("name"):
            return status["name"]
        if status.get("instagram_account_id"):
            return f"Instagram ID {status['instagram_account_id']}"

    if platform == "tiktok":
        user_info = status.get("user_info") or {}
        data = user_info.get("data") if isinstance(user_info, dict) else None
        user = data.get("user") if isinstance(data, dict) else None
        if isinstance(user, dict):
            return user.get("display_name") or user.get("username") or user.get("open_id") or fallback_user_id or "Connected"
        if isinstance(data, dict):
            return data.get("display_name") or data.get("username") or data.get("open_id") or fallback_user_id or "Connected"

    return fallback_user_id or "Connected"


def _get_upload_manager() -> UploadManager:
    return UploadManager(OAuthManager())


def _metadata_from_clip(clip: UploadedClip) -> dict[str, str]:
    return {
        "title": clip.title or clip.original_filename,
        "caption": clip.description or "",
        "description": clip.description or "",
        "hashtags": clip.hashtags or "",
        "visibility": clip.visibility or "public",
    }


def _public_base_url() -> str:
    return (
        os.getenv("OAUTH_REDIRECT_BASE_URL")
        or os.getenv("BACKEND_URL")
        or settings.studio_public_base_url
    ).rstrip("/")


def _callback_url(platform: str) -> str:
    specific = os.getenv(f"{platform.upper()}_REDIRECT_URI")
    if specific:
        return specific
    return f"{_public_base_url()}/api/oauth/{platform}/callback"


def _remember_auth_state(platform: str) -> str:
    token = uuid4().hex
    AUTH_STATES[token] = {"platform": platform, "created_at": time.time()}
    return token


def _consume_auth_state(platform: str, state: str | None) -> bool:
    if not state:
        return False

    record = AUTH_STATES.pop(state, None)
    if not record:
        return False

    created_at = float(record.get("created_at", 0))
    return record.get("platform") == platform and time.time() - created_at <= AUTH_STATE_TTL_SECONDS


def _oauth_success_html(platform: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <html>
          <head>
            <title>{platform.title()} connected</title>
            <meta http-equiv="refresh" content="2;url=/" />
          </head>
          <body>
            <h1>{platform.title()} connected</h1>
            <p>You can return to Upload Studio. This page will redirect shortly.</p>
          </body>
        </html>
        """
    )


def _oauth_failure_html(platform: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <html>
          <head><title>{platform.title()} authentication failed</title></head>
          <body>
            <h1>{platform.title()} authentication failed</h1>
            <p>Return to Upload Studio and try connecting this platform again.</p>
          </body>
        </html>
        """,
        status_code=400,
    )


def _build_auth_url(platform: str) -> str:
    state = _remember_auth_state(platform)
    redirect_uri = _callback_url(platform)

    if platform == "instagram":
        if not settings.instagram_client_id:
            raise HTTPException(status_code=503, detail="Instagram connection is not available right now.")

        return "https://api.instagram.com/oauth/authorize?" + urlencode(
            {
                "client_id": settings.instagram_client_id,
                "redirect_uri": redirect_uri,
                "scope": "instagram_business_basic,instagram_business_content_publish",
                "response_type": "code",
                "state": state,
            }
        )

    if platform == "tiktok":
        if not settings.tiktok_client_key:
            raise HTTPException(status_code=503, detail="TikTok connection is not available right now.")

        return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(
            {
                "client_key": settings.tiktok_client_key,
                "response_type": "code",
                "scope": "user.info.profile,user.info.stats,video.upload,video.publish,video.list",
                "redirect_uri": redirect_uri,
                "state": state,
                "disable_auto_auth": "1",
            }
        )

    if platform == "youtube":
        client_secrets_file = settings.youtube_client_secrets_file
        if not client_secrets_file or not Path(client_secrets_file).exists():
            raise HTTPException(status_code=503, detail="YouTube connection is not available right now.")

        flow = Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=[
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/youtube.upload",
            ],
            redirect_uri=redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return auth_url

    raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


def _save_oauth_credentials(platform: str, credentials: OAuthCredentials) -> None:
    manager = OAuthManager()
    manager.credentials[platform] = credentials
    manager._save_credentials()


@router.get("/status", response_model=StudioStatus)
def get_status(current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    """Return the upload studio shell state."""
    oauth_manager = OAuthManager()
    configured_platforms = _configured_platforms()

    platform_meta = {
        "youtube": (
            "YouTube",
            "#ff1f3d",
        ),
        "instagram": (
            "Instagram",
            "#d946ef",
        ),
        "tiktok": (
            "TikTok",
            "#32c7f4",
        ),
    }
    platform_statuses: list[PlatformStatus] = []

    upload_manager: UploadManager | None = None
    for platform, (label, accent) in platform_meta.items():
        creds = oauth_manager.credentials.get(platform)
        configured = configured_platforms[platform]

        if not creds:
            platform_statuses.append(
                PlatformStatus(
                    platform=platform,
                    label=label,
                    handle="Not authenticated",
                    connected=False,
                    accent=accent,
                    detail="Ready to connect" if configured else "Connection unavailable",
                )
            )
            continue

        if creds.expires_at and creds.expires_at <= int(time.time()):
            platform_statuses.append(
                PlatformStatus(
                    platform=platform,
                    label=label,
                    handle=_extract_account_handle(platform, {}, creds.user_id),
                    connected=False,
                    accent=accent,
                    detail="OAuth token expired; re-authenticate this platform",
                )
            )
            continue

        detail = "Ready to publish"
        handle = _extract_account_handle(platform, {}, creds.user_id)
        try:
            upload_manager = upload_manager or _get_upload_manager()
            account_status = upload_manager.get_upload_status(platform)
            if account_status.get("authenticated"):
                handle = _extract_account_handle(platform, account_status, creds.user_id)
            elif account_status.get("error"):
                detail = "Connected; account lookup needs attention"
        except Exception as exc:
            print(f"{platform} account lookup failed: {exc}")
            detail = "Connected; account lookup needs attention"

        platform_statuses.append(
            PlatformStatus(
                platform=platform,
                label=label,
                handle=handle,
                connected=True,
                accent=accent,
                detail=detail,
            )
        )

    return StudioStatus(
        authenticated=True,
        role=current_user.role,
        user={"name": current_user.email},
        platforms=platform_statuses,
    )


@router.post("/metadata", response_model=MetadataResponse)
def generate_metadata(request: MetadataRequest, _: User = Depends(require_creator)):
    """Generate upload-ready metadata from the selected clip name."""
    try:
        metadata = AIService().generate_metadata(request.filename, request.game_context)
        return MetadataResponse(
            title=metadata.get("title", ""),
            description=metadata.get("caption") or metadata.get("description", ""),
            hashtags=metadata.get("hashtags", ""),
            visibility="public",
        )
    except Exception:
        return _fallback_metadata(request.filename)


@router.post("/auth/{platform}/start", response_model=AuthStartResponse)
def start_platform_auth(platform: str, _: User = Depends(require_admin)):
    """Return a hosted OAuth URL for a platform."""
    if platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    auth_url = _build_auth_url(platform)
    return AuthStartResponse(
        platform=platform,
        started=True,
        authUrl=auth_url,
        message=f"Redirecting to {platform.title()} to connect your account.",
    )


@callback_router.get("/{platform}/callback")
def complete_platform_auth(
    platform: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """Complete hosted OAuth and keep tokens server-side."""
    if platform not in PLATFORMS or error or not code or not _consume_auth_state(platform, state):
        return _oauth_failure_html(platform)

    redirect_uri = _callback_url(platform)
    try:
        if platform == "instagram":
            token_response = requests.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": settings.instagram_client_id,
                    "client_secret": settings.instagram_client_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                timeout=30,
            )
            token_response.raise_for_status()
            token_info = token_response.json()

            long_lived_response = requests.get(
                "https://graph.instagram.com/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": settings.instagram_client_secret,
                    "access_token": token_info["access_token"],
                },
                timeout=30,
            )
            long_lived_response.raise_for_status()
            long_lived_info = long_lived_response.json()

            _save_oauth_credentials(
                "instagram",
                OAuthCredentials(
                    access_token=long_lived_info.get("access_token", token_info["access_token"]),
                    expires_at=int(time.time()) + int(long_lived_info.get("expires_in", 3600)),
                    platform="instagram",
                ),
            )

        elif platform == "tiktok":
            token_response = requests.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": settings.tiktok_client_key,
                    "client_secret": settings.tiktok_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=30,
            )
            token_response.raise_for_status()
            token_info = token_response.json()
            if token_info.get("error"):
                return _oauth_failure_html(platform)

            _save_oauth_credentials(
                "tiktok",
                OAuthCredentials(
                    access_token=token_info["access_token"],
                    refresh_token=token_info.get("refresh_token"),
                    expires_at=int(time.time()) + int(token_info.get("expires_in", 3600)),
                    scope=token_info.get("scope"),
                    user_id=token_info.get("open_id"),
                    platform="tiktok",
                ),
            )

        elif platform == "youtube":
            client_secrets_file = settings.youtube_client_secrets_file
            if not client_secrets_file:
                return _oauth_failure_html(platform)

            flow = Flow.from_client_secrets_file(
                client_secrets_file,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.readonly",
                    "https://www.googleapis.com/auth/youtube.force-ssl",
                    "https://www.googleapis.com/auth/youtube.upload",
                ],
                redirect_uri=redirect_uri,
            )
            flow.fetch_token(code=code)
            google_creds = flow.credentials
            token_file = OAuthManager().credentials_dir / "youtube_token.json"
            with token_file.open("w", encoding="utf-8") as token:
                token.write(google_creds.to_json())

            _save_oauth_credentials(
                "youtube",
                OAuthCredentials(
                    access_token=google_creds.token,
                    refresh_token=google_creds.refresh_token,
                    expires_at=OAuthManager._expiry_timestamp(google_creds.expiry),
                    scope=" ".join(google_creds.scopes or []),
                    platform="youtube",
                ),
            )
    except Exception as exc:
        print(f"{platform} OAuth callback failed: {exc}")
        return _oauth_failure_html(platform)

    return _oauth_success_html(platform)


@router.post("/upload", response_model=UploadResponse)
async def upload_clip(
    video: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    hashtags: str = Form(""),
    visibility: Literal["public", "unlisted", "private"] = Form("public"),
    platforms: str = Form("[]"),
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db),
):
    """Save a flat-file clip upload and record selected platform results."""
    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")

    suffix = Path(video.filename).suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported video type: {suffix}")

    try:
        selected_platforms = json.loads(platforms)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid platforms payload") from exc

    if not isinstance(selected_platforms, list) or not selected_platforms:
        raise HTTPException(status_code=400, detail="Select at least one platform")

    invalid_platforms = [platform for platform in selected_platforms if platform not in PLATFORMS]
    if invalid_platforms:
        raise HTTPException(status_code=400, detail=f"Unsupported platforms: {', '.join(invalid_platforms)}")

    safe_name = _safe_filename(video.filename)
    stored_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}_{safe_name}"
    stored_path = _upload_dir() / stored_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    metadata = {
        "title": title,
        "caption": description,
        "description": description,
        "hashtags": hashtags,
        "visibility": visibility,
    }
    upload_results = _get_upload_manager().upload_to_all_platforms(stored_path, metadata, selected_platforms)
    any_success = any(result.success for result in upload_results.values())

    clip = UploadedClip(
        user_id=current_user.id,
        original_filename=safe_name,
        stored_path=str(stored_path),
        title=title,
        description=description,
        hashtags=hashtags,
        visibility=visibility,
        status="uploaded" if any_success else "failed",
    )
    db.add(clip)
    db.flush()

    for platform in selected_platforms:
        result = upload_results.get(platform)
        db.add(
            PlatformUpload(
                clip_id=clip.id,
                platform=platform,
                platform_video_id=result.video_id if result else None,
                platform_url=result.url if result and result.url else None,
                status="uploaded" if result and result.success else "failed",
                error_message=None if result and result.success else (result.error if result else "Upload did not run"),
            )
        )
    db.commit()

    failures = [platform for platform, result in upload_results.items() if not result.success]
    message = (
        "Published successfully."
        if any_success and not failures
        else f"Published to {sum(1 for result in upload_results.values() if result.success)} platform(s). {len(failures)} platform(s) need attention."
    )

    return UploadResponse(
        clipId=str(clip.id),
        uploads=[_recent_upload_response(upload) for upload in get_recent_upload_rows(db, current_user)],
        message=message,
    )


def get_recent_upload_rows(db: Session, current_user: User) -> list[PlatformUpload]:
    query = (
        db.query(PlatformUpload)
        .join(UploadedClip)
    )
    if current_user.role != UserRole.ADMIN.value:
        query = query.filter(UploadedClip.user_id == current_user.id)
    return query.order_by(PlatformUpload.uploaded_at.desc(), PlatformUpload.id.desc()).limit(12).all()


@router.get("/recent-uploads", response_model=list[RecentUploadResponse])
def recent_uploads(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Return the recent per-platform upload rows shown in the studio."""
    return [_recent_upload_response(upload) for upload in get_recent_upload_rows(db, current_user)]


@router.get("/admin/uploads", response_model=list[AdminUploadResponse])
def admin_uploads(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PlatformUpload)
        .join(UploadedClip)
        .join(User, UploadedClip.user_id == User.id)
        .order_by(PlatformUpload.uploaded_at.desc(), PlatformUpload.id.desc())
        .limit(100)
        .all()
    )
    return [
        AdminUploadResponse(
            uploadId=row.id,
            clipId=row.clip.id,
            userEmail=row.clip.user.email if getattr(row.clip, "user", None) else "",
            platform=row.platform,
            title=row.clip.title,
            status=row.status,
            uploadedAt=_format_uploaded_at(row.uploaded_at),
            url=row.platform_url,
            error=_public_error_message(row.error_message),
        )
        for row in rows
    ]


@router.post("/uploads/{upload_id}/retry", response_model=RetryUploadResponse)
def retry_upload(
    upload_id: int,
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db),
):
    """Retry a failed upload row using the real uploader."""
    upload = db.query(PlatformUpload).filter(PlatformUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload row not found")
    if current_user.role != UserRole.ADMIN.value and upload.clip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Upload is not available")
    if upload.platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {upload.platform}")

    clip = upload.clip
    video_path = Path(clip.stored_path)
    if not video_path.exists():
        upload.status = "failed"
        print(f"Retry source video no longer exists: {video_path}")
        upload.error_message = "Source clip is no longer available"
        db.commit()
        db.refresh(upload)
        return RetryUploadResponse(
            upload=_recent_upload_response(upload),
            uploads=[_recent_upload_response(item) for item in get_recent_upload_rows(db, current_user)],
            message="The source clip is no longer available for retry.",
        )

    result = _get_upload_manager().upload_to_all_platforms(video_path, _metadata_from_clip(clip), [upload.platform]).get(upload.platform)
    if result and result.success:
        upload.status = "uploaded"
        upload.platform_video_id = result.video_id
        upload.platform_url = result.url
        upload.error_message = None
        clip.status = "uploaded"
        message = f"Retry succeeded for {upload.platform}."
    else:
        upload.status = "failed"
        upload.error_message = result.error if result else "Retry did not run"
        message = f"Retry failed for {upload.platform}. Check the platform connection and try again."

    db.commit()
    db.refresh(upload)
    return RetryUploadResponse(
        upload=_recent_upload_response(upload),
        uploads=[_recent_upload_response(item) for item in get_recent_upload_rows(db, current_user)],
        message=message,
    )


@router.get("/health")
async def studio_health():
    """Health check for the upload studio API."""
    return {"status": "healthy", "service": "upload-studio"}


