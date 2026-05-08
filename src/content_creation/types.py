"""Common types and classes for the content creation system."""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class UploadResult:
    """Result of an upload operation."""
    platform: str
    success: bool
    video_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


class FTPUploader:
    """Handles video uploads to the FTP server (MinIO)."""
    
    def __init__(self):
        self.endpoint_url = os.getenv("FTP_URL")
        self.access_key = os.getenv("FTP_ACCESS_KEY")
        self.secret_key = os.getenv("FTP_SECRET_KEY")
        self.bucket_name = os.getenv("FTP_BUCKET")
        self.public_base_url = os.getenv("FTP_PUBLIC_BASE_URL", "https://api.uk.syn.gl")
        
        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("FTP credentials not configured. Please set FTP_URL, FTP_ACCESS_KEY, FTP_SECRET_KEY, and FTP_BUCKET in your .env file")

        
        # Initialize S3 client with correct MinIO configuration
        from botocore.config import Config
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='us-east-1',
            config=Config(
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'
                },
                read_timeout=300,  # 5 minutes
                connect_timeout=60,  # 1 minute
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                }
            )
        )
    
    def upload_video(self, video_path: Path, client_folder: str = "content-creation") -> Optional[str]:
        """Upload video to FTP server and return public URL."""
        try:
            # Generate unique filename
            file_extension = video_path.suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # S3 key (path in bucket)
            s3_key = f"{client_folder}/{unique_filename}"
            
            # Test connection first
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print("[SUCCESS] FTP connection successful")
            except ClientError as e:
                print(f"[ERROR] FTP connection failed: {e}")
                print(f"[DEBUG] Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
                return None
            
            # Upload file
            content_type = mimetypes.guess_type(str(video_path))[0] or "video/mp4"
            self.s3_client.upload_file(
                str(video_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000",
                }
            )
            
            # Generate public URL
            # For MinIO, use a public HTTPS URL that crawlers can fetch.
            if self.public_base_url:
                public_url = f"{self.public_base_url.rstrip('/')}/{self.bucket_name}/{s3_key}"
            elif self.endpoint_url.startswith("http://ftp.syn.gl:9000"):
                public_url = f"https://ftp.syn.gl/{self.bucket_name}/{s3_key}"
            elif self.endpoint_url.startswith("http://"):
                public_domain = self.endpoint_url.replace("http://", "https://")
                public_url = f"{public_domain}/{self.bucket_name}/{s3_key}"
            elif self.endpoint_url.startswith("https://"):
                public_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            else:
                public_url = f"https://{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            print(f"[SUCCESS] Video uploaded to FTP: {public_url}")
            
            return public_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = str(e).encode('utf-8', errors='replace').decode('utf-8')
            
            if error_code == 'XMinioStorageFull':
                print(f"[ERROR] FTP upload failed: MinIO storage is full!")
                print(f"[CLEANUP] Attempting automatic cleanup...")
                
                # Try automatic cleanup
                try:
                    from managers.minio_cleanup import MinIOCleanup
                    from managers.config_manager import ConfigManager
                    
                    # Get cleanup configuration
                    config_manager = ConfigManager()
                    config = config_manager.get_config()
                    
                    if not config.auto_cleanup_enabled:
                        print(f"[ERROR] Auto-cleanup is disabled in configuration")
                        print(f"[ERROR] Please manually delete old files from your MinIO bucket")
                        print(f"[ERROR] Access your MinIO console at: {self.endpoint_url}")
                        print(f"[ERROR] Bucket: {self.bucket_name}")
                        return None
                    
                    cleanup = MinIOCleanup()
                    
                    # Emergency cleanup using configured target
                    result = cleanup.emergency_cleanup(target_free_mb=config.emergency_cleanup_target_mb)
                    
                    if result['freed_mb'] > 0:
                        print(f"[SUCCESS] Cleanup freed {result['freed_mb']:.1f}MB, retrying upload...")
                        
                        # Retry the upload
                        try:
                            self.s3_client.upload_file(
                                str(video_path),
                                self.bucket_name,
                                s3_key,
                                ExtraArgs={
                                    "ContentType": content_type,
                                    "CacheControl": "public, max-age=31536000",
                                }
                            )
                            
                            # Generate public URL
                            if self.public_base_url:
                                public_url = f"{self.public_base_url.rstrip('/')}/{self.bucket_name}/{s3_key}"
                            elif self.endpoint_url.startswith("http://ftp.syn.gl:9000"):
                                public_url = f"https://ftp.syn.gl/{self.bucket_name}/{s3_key}"
                            elif self.endpoint_url.startswith("http://"):
                                public_domain = self.endpoint_url.replace("http://", "https://")
                                public_url = f"{public_domain}/{self.bucket_name}/{s3_key}"
                            elif self.endpoint_url.startswith("https://"):
                                public_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
                            else:
                                public_url = f"https://{self.endpoint_url}/{self.bucket_name}/{s3_key}"
                            
                            print(f"[SUCCESS] Video uploaded to FTP after cleanup: {public_url}")
                            return public_url
                            
                        except ClientError as retry_error:
                            print(f"[ERROR] Upload still failed after cleanup: {retry_error}")
                            print(f"[ERROR] Please manually clean up more space or check MinIO console")
                            print(f"[ERROR] Access your MinIO console at: {self.endpoint_url}")
                            print(f"[ERROR] Bucket: {self.bucket_name}")
                    else:
                        print(f"[ERROR] Cleanup failed to free space")
                        print(f"[ERROR] Please manually delete old files from your MinIO bucket")
                        print(f"[ERROR] Access your MinIO console at: {self.endpoint_url}")
                        print(f"[ERROR] Bucket: {self.bucket_name}")
                        
                except Exception as cleanup_error:
                    print(f"[ERROR] Automatic cleanup failed: {cleanup_error}")
                    print(f"[ERROR] Please manually delete old files from your MinIO bucket")
                    print(f"[ERROR] Access your MinIO console at: {self.endpoint_url}")
                    print(f"[ERROR] Bucket: {self.bucket_name}")
            else:
                print(f"[ERROR] FTP upload failed: {error_code} - {error_message}")
            return None
        except Exception as e:
            error_message = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print(f"[ERROR] FTP upload error: {error_message}")
            return None
