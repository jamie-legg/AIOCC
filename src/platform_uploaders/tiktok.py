"""TikTok uploader using Content Posting API (Inbox Upload)."""

import time
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import requests

from managers.oauth_manager import OAuthCredentials
from content_creation.types import UploadResult


@dataclass
class TikTokUploader:
    """Handles TikTok uploads using Content Posting API (Inbox Upload)."""
    
    def upload(self, video_path: Path, metadata: Dict[str, str], creds: OAuthCredentials, thumbnail_path: Optional[Path] = None) -> UploadResult:
        """Upload video to TikTok using Content Posting API (Inbox Upload)."""
        try:
            # Validate video file according to TikTok requirements
            video_size = video_path.stat().st_size
            if video_size > 4 * 1024 * 1024 * 1024:  # 4GB limit
                return UploadResult("tiktok", False, error="Video file too large (max 4GB)")
            
            if not video_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.3gp']:
                return UploadResult("tiktok", False, error="Unsupported video format. Use MP4, MOV, AVI, or 3GP")
            
            # Step 1: Initialize video upload using Content Posting API (Inbox)
            init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
            
            headers = {
                "Authorization": f"Bearer {creds.access_token}",
                "Content-Type": "application/json"
            }
            
            # TikTok API chunk size requirements:
            # - Each chunk must be between 5MB and 64MB (except final chunk can be up to 128MB)
            # - For single-chunk uploads, chunk_size must equal video_size and be <= 64MB
            MIN_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB minimum
            MAX_CHUNK_SIZE = 64 * 1024 * 1024  # 64MB maximum per chunk
            
            if video_size <= MAX_CHUNK_SIZE:
                # Single chunk upload - chunk_size equals video_size (must be <= 64MB)
                chunk_size = video_size
                total_chunk_count = 1
            else:
                # Multi-chunk upload required for videos > 64MB
                MAX_FINAL_CHUNK = 128 * 1024 * 1024  # 128MB max for final chunk
                
                # Calculate chunk configuration
                # Try to use 2 chunks first (simplest multi-chunk scenario)
                # If that doesn't work, try more chunks
                chunk_size = video_size // 2
                # Round down to nearest MB, ensuring it's within valid range
                chunk_size = (chunk_size // (1024 * 1024)) * 1024 * 1024
                chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, chunk_size))
                total_chunk_count = 2
                last_chunk_size = video_size - chunk_size
                
                # Validate 2-chunk configuration
                if last_chunk_size < MIN_CHUNK_SIZE or last_chunk_size > MAX_FINAL_CHUNK:
                    # 2 chunks won't work, try 3 chunks
                    chunk_size = video_size // 3
                    chunk_size = (chunk_size // (1024 * 1024)) * 1024 * 1024
                    chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, chunk_size))
                    total_chunk_count = 3
                    last_chunk_size = video_size - (chunk_size * 2)
                    
                    # If still invalid, use iterative approach to find valid config
                    if last_chunk_size < MIN_CHUNK_SIZE or last_chunk_size > MAX_FINAL_CHUNK:
                        for test_chunks in range(4, min(1001, (video_size // MIN_CHUNK_SIZE) + 1)):
                            test_chunk_size = video_size // test_chunks
                            test_chunk_size = (test_chunk_size // (1024 * 1024)) * 1024 * 1024
                            test_chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, test_chunk_size))
                            test_total = (video_size + test_chunk_size - 1) // test_chunk_size
                            test_last = video_size - (test_chunk_size * (test_total - 1))
                            
                            if MIN_CHUNK_SIZE <= test_last <= MAX_FINAL_CHUNK:
                                chunk_size = test_chunk_size
                                total_chunk_count = test_total
                                break
                        else:
                            return UploadResult("tiktok", False, error=f"Cannot calculate valid chunk configuration for video size {video_size / (1024*1024):.2f}MB")
            
            init_data = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunk_count
                }
            }
            
            print(f"Initializing TikTok upload for {video_path.name} ({video_size} bytes)...")
            print(f"  Chunk size: {chunk_size} bytes ({chunk_size / (1024*1024):.2f} MB)")
            print(f"  Total chunks: {total_chunk_count}")
            print(f"  Total chunk size: {chunk_size * total_chunk_count} bytes")
            
            init_response = requests.post(init_url, headers=headers, json=init_data)
            
            # Better error handling for 400 errors
            if init_response.status_code == 400:
                try:
                    error_data = init_response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad Request")
                    error_code = error_data.get("error", {}).get("code", "400")
                    try:
                        print(f"[ERROR] TikTok API 400 error: {error_code} - {error_msg}")
                    except UnicodeEncodeError:
                        print("[ERROR] TikTok API 400 error (contains non-ASCII characters)")
                    return UploadResult("tiktok", False, error=f"TikTok API error: {error_code} - {error_msg}")
                except:
                    try:
                        print(f"[ERROR] TikTok API 400 error: {init_response.text}")
                    except UnicodeEncodeError:
                        print("[ERROR] TikTok API 400 error (contains non-ASCII characters)")
                    return UploadResult("tiktok", False, error=f"TikTok API error: {init_response.text}")
            
            init_response.raise_for_status()
            init_result = init_response.json()
            
            # Check if there's an actual error (not just the standard response structure)
            if init_result.get("error") and init_result["error"].get("code") != "ok":
                return UploadResult("tiktok", False, error=init_result["error"]["message"])
            
            upload_url = init_result["data"]["upload_url"]
            publish_id = init_result["data"]["publish_id"]
            
            print(f"Uploading video to TikTok... ({total_chunk_count} chunk(s))")
            # Step 2: Upload video file (chunked if needed)
            with open(video_path, 'rb') as video_file:
                if total_chunk_count == 1:
                    # Single chunk - upload entire file at once
                    video_data = video_file.read()
                    upload_headers = {
                        "Content-Range": f"bytes 0-{video_size-1}/{video_size}",
                        "Content-Length": str(video_size),
                        "Content-Type": "video/mp4"
                    }
                    print(f"Uploading video ({video_size} bytes)...")
                    upload_response = requests.put(upload_url, data=video_data, headers=upload_headers)
                else:
                    # Multiple chunks - upload sequentially
                    for chunk_num in range(total_chunk_count):
                        start_byte = chunk_num * chunk_size
                        # For last chunk, read remaining bytes; for others, read chunk_size
                        if chunk_num == total_chunk_count - 1:
                            # Last chunk - read remaining bytes
                            bytes_to_read = video_size - start_byte
                        else:
                            bytes_to_read = chunk_size
                        
                        chunk_data = video_file.read(bytes_to_read)
                        end_byte = start_byte + len(chunk_data) - 1
                        
                        upload_headers = {
                            "Content-Range": f"bytes {start_byte}-{end_byte}/{video_size}",
                            "Content-Length": str(len(chunk_data)),
                            "Content-Type": "video/mp4"
                        }
                        
                        print(f"Uploading chunk {chunk_num + 1}/{total_chunk_count} ({len(chunk_data)} bytes, range {start_byte}-{end_byte})...")
                        upload_response = requests.put(upload_url, data=chunk_data, headers=upload_headers)
                        
                        # Better error handling for upload errors
                        if upload_response.status_code >= 400:
                            try:
                                print(f"[ERROR] TikTok upload error on chunk {chunk_num + 1}: {upload_response.status_code} - {upload_response.text}")
                            except UnicodeEncodeError:
                                print(f"[ERROR] TikTok upload error on chunk {chunk_num + 1} (contains non-ASCII characters)")
                            return UploadResult("tiktok", False, error=f"Upload failed on chunk {chunk_num + 1}: {upload_response.status_code} - {upload_response.text}")
                        
                        upload_response.raise_for_status()
                
                # Final error check for single chunk uploads
                if total_chunk_count == 1:
                    if upload_response.status_code >= 400:
                        try:
                            print(f"[ERROR] TikTok upload error: {upload_response.status_code} - {upload_response.text}")
                        except UnicodeEncodeError:
                            print(f"[ERROR] TikTok upload error (contains non-ASCII characters)")
                        return UploadResult("tiktok", False, error=f"Upload failed: {upload_response.status_code} - {upload_response.text}")
                    
                    upload_response.raise_for_status()
            
            print(f"Video uploaded successfully. Checking status...")
            # Step 3: Check upload status
            status_url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
            status_data = {"publish_id": publish_id}
            
            # Wait for processing to complete
            max_attempts = 30  # 5 minutes max
            for attempt in range(max_attempts):
                status_response = requests.post(status_url, headers=headers, json=status_data)
                status_response.raise_for_status()
                
                status_result = status_response.json()
                
                # Check if there's an actual error (not just the standard response structure)
                if status_result.get("error") and status_result["error"].get("code") != "ok":
                    return UploadResult("tiktok", False, error=status_result["error"]["message"])
                
                status = status_result["data"]["status"]
                
                if status in ["PROCESSING_DONE", "PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"]:
                    # Upload successful - video is published or in inbox
                    video_id = status_result["data"].get("publish_id", publish_id)
                    share_url = status_result["data"].get("share_url", "")
                    return UploadResult(
                        "tiktok",
                        True,
                        video_id=video_id,
                        url=share_url if share_url else f"Video published to TikTok (ID: {video_id})"
                    )
                elif status == "FAILED":
                    fail_reason = status_result["data"].get("fail_reason", "Unknown reason")
                    return UploadResult("tiktok", False, error=f"Video upload failed: {fail_reason}")
                elif status in ["PROCESSING", "PROCESSING_UPLOAD"]:
                    time.sleep(10)  # Wait 10 seconds before checking again
                else:
                    return UploadResult("tiktok", False, error=f"Unknown status: {status}")
            
            return UploadResult("tiktok", False, error="Upload timeout - processing took too long")
            
        except Exception as e:
            return UploadResult("tiktok", False, error=str(e))
    
    def get_upload_status(self, creds: OAuthCredentials) -> Dict[str, any]:
        """Get TikTok upload status and user info."""
        try:
            # Get user info
            user_info_url = "https://open.tiktokapis.com/v2/user/info/"
            headers = {"Authorization": f"Bearer {creds.access_token}"}
            response = requests.get(
                user_info_url,
                headers=headers,
                params={"fields": "open_id,union_id,avatar_url,display_name"},
                timeout=15,
            )
            response.raise_for_status()
            return {"authenticated": True, "user_info": response.json()}
            
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
