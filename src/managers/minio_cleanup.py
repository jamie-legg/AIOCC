"""MinIO cleanup utility for managing storage space."""

import os
import boto3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from botocore.config import Config

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class MinIOCleanup:
    """Handles MinIO storage cleanup operations."""
    
    def __init__(self):
        self.endpoint_url = os.getenv("FTP_URL")
        self.access_key = os.getenv("FTP_ACCESS_KEY")
        self.secret_key = os.getenv("FTP_SECRET_KEY")
        self.bucket_name = os.getenv("FTP_BUCKET")
        
        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("MinIO credentials not configured. Please set FTP_URL, FTP_ACCESS_KEY, FTP_SECRET_KEY, and FTP_BUCKET in your .env file")

        # Initialize S3 client with MinIO configuration
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
                }
            )
        )
    
    def get_bucket_usage(self) -> Dict[str, any]:
        """Get current bucket usage statistics."""
        try:
            # List all objects to calculate usage
            paginator = self.s3_client.get_paginator('list_objects_v2')
            total_size = 0
            total_objects = 0
            content_creation_size = 0
            content_creation_objects = 0
            
            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        size = obj['Size']
                        total_size += size
                        total_objects += 1
                        
                        # Check if it's in content-creation folder
                        if obj['Key'].startswith('content-creation/'):
                            content_creation_size += size
                            content_creation_objects += 1
            
            return {
                'total_size_mb': total_size / (1024 * 1024),
                'total_objects': total_objects,
                'content_creation_size_mb': content_creation_size / (1024 * 1024),
                'content_creation_objects': content_creation_objects,
                'other_size_mb': (total_size - content_creation_size) / (1024 * 1024),
                'other_objects': total_objects - content_creation_objects
            }
        except Exception as e:
            print(f"[ERROR] Failed to get bucket usage: {e}")
            return {}
    
    def list_old_files(self, days_old: int = 7, folder: str = "content-creation") -> List[Dict[str, any]]:
        """List files older than specified days in the given folder."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            old_files = []
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=f"{folder}/"):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        last_modified = obj['LastModified'].replace(tzinfo=None)
                        if last_modified < cutoff_date:
                            old_files.append({
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': last_modified,
                                'size_mb': obj['Size'] / (1024 * 1024)
                            })
            
            # Sort by last modified date (oldest first)
            old_files.sort(key=lambda x: x['last_modified'])
            return old_files
            
        except Exception as e:
            print(f"[ERROR] Failed to list old files: {e}")
            return []
    
    def delete_files(self, file_keys: List[str]) -> Dict[str, any]:
        """Delete specified files from the bucket."""
        if not file_keys:
            return {'deleted': 0, 'failed': 0, 'freed_mb': 0}
        
        deleted = 0
        failed = 0
        freed_bytes = 0
        
        try:
            # Get file sizes before deletion
            for key in file_keys:
                try:
                    response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    freed_bytes += response['ContentLength']
                except:
                    pass
            
            # Delete files in batches (S3 allows up to 1000 objects per request)
            batch_size = 1000
            for i in range(0, len(file_keys), batch_size):
                batch = file_keys[i:i + batch_size]
                
                delete_objects = {
                    'Objects': [{'Key': key} for key in batch]
                }
                
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_objects
                )
                
                deleted += len(response.get('Deleted', []))
                failed += len(response.get('Errors', []))
                
                if response.get('Errors'):
                    for error in response['Errors']:
                        print(f"[ERROR] Failed to delete {error['Key']}: {error['Message']}")
        
        except Exception as e:
            print(f"[ERROR] Failed to delete files: {e}")
            failed = len(file_keys)
        
        return {
            'deleted': deleted,
            'failed': failed,
            'freed_mb': freed_bytes / (1024 * 1024)
        }
    
    def cleanup_old_files(self, days_old: int = 7, folder: str = "content-creation", 
                         max_files: Optional[int] = None, dry_run: bool = False) -> Dict[str, any]:
        """Clean up old files from the specified folder."""
        print(f"[CLEANUP] Looking for files older than {days_old} days in '{folder}' folder...")
        
        old_files = self.list_old_files(days_old, folder)
        
        if not old_files:
            print(f"[CLEANUP] No files older than {days_old} days found.")
            return {'deleted': 0, 'failed': 0, 'freed_mb': 0}
        
        print(f"[CLEANUP] Found {len(old_files)} old files:")
        for file_info in old_files[:10]:  # Show first 10 files
            print(f"  - {file_info['key']} ({file_info['size_mb']:.1f}MB, {file_info['last_modified']})")
        
        if len(old_files) > 10:
            print(f"  ... and {len(old_files) - 10} more files")
        
        # Limit files to delete if specified
        files_to_delete = old_files
        if max_files and max_files < len(old_files):
            files_to_delete = old_files[:max_files]
            print(f"[CLEANUP] Limiting deletion to {max_files} files (oldest first)")
        
        if dry_run:
            total_size = sum(f['size_mb'] for f in files_to_delete)
            print(f"[CLEANUP] DRY RUN: Would delete {len(files_to_delete)} files ({total_size:.1f}MB)")
            return {'deleted': 0, 'failed': 0, 'freed_mb': total_size}
        
        # Confirm deletion
        total_size = sum(f['size_mb'] for f in files_to_delete)
        print(f"[CLEANUP] Deleting {len(files_to_delete)} files ({total_size:.1f}MB)...")
        
        file_keys = [f['key'] for f in files_to_delete]
        result = self.delete_files(file_keys)
        
        print(f"[CLEANUP] Cleanup completed:")
        print(f"  - Deleted: {result['deleted']} files")
        print(f"  - Failed: {result['failed']} files")
        print(f"  - Freed: {result['freed_mb']:.1f}MB")
        
        return result
    
    def emergency_cleanup(self, target_free_mb: int = 1000) -> Dict[str, any]:
        """Emergency cleanup to free up space, deleting oldest files first."""
        print(f"[EMERGENCY] Starting emergency cleanup to free {target_free_mb}MB...")
        
        # Start with very old files (30+ days)
        result = self.cleanup_old_files(days_old=30, max_files=50)
        freed_mb = result['freed_mb']
        
        if freed_mb < target_free_mb:
            print(f"[EMERGENCY] Freed {freed_mb:.1f}MB, need more space...")
            # Try 14+ days old files
            result_14 = self.cleanup_old_files(days_old=14, max_files=100)
            freed_mb += result_14['freed_mb']
            
            if freed_mb < target_free_mb:
                print(f"[EMERGENCY] Freed {freed_mb:.1f}MB, trying 7+ days old files...")
                # Try 7+ days old files
                result_7 = self.cleanup_old_files(days_old=7, max_files=200)
                freed_mb += result_7['freed_mb']
        
        print(f"[EMERGENCY] Emergency cleanup completed, freed {freed_mb:.1f}MB")
        return {'freed_mb': freed_mb, 'deleted': result['deleted']}


def main():
    """CLI interface for MinIO cleanup."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MinIO Storage Cleanup Utility')
    parser.add_argument('--days', type=int, default=7, help='Delete files older than N days (default: 7)')
    parser.add_argument('--folder', default='content-creation', help='Folder to clean up (default: content-creation)')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to delete')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--emergency', action='store_true', help='Emergency cleanup to free space')
    parser.add_argument('--target-mb', type=int, default=1000, help='Target MB to free in emergency mode (default: 1000)')
    parser.add_argument('--status', action='store_true', help='Show storage status and recommendations')
    
    args = parser.parse_args()
    
    try:
        cleanup = MinIOCleanup()
        
        if args.status:
            usage = cleanup.get_bucket_usage()
            old_files = cleanup.list_old_files(days_old=7)
            
            print(f"[STATUS] Storage Health Check:")
            print(f"  Total size: {usage.get('total_size_mb', 0):.1f}MB")
            print(f"  Content-creation size: {usage.get('content_creation_size_mb', 0):.1f}MB")
            print(f"  Old files (7+ days): {len(old_files)}")
            
            if usage.get('content_creation_size_mb', 0) > 5000:  # 5GB
                print(f"  Recommendation: Consider cleaning up old content-creation files (>5GB)")
            
            if len(old_files) > 100:
                print(f"  Recommendation: Found {len(old_files)} files older than 7 days")
        
        elif args.emergency:
            cleanup.emergency_cleanup(args.target_mb)
        
        else:
            cleanup.cleanup_old_files(
                days_old=args.days,
                folder=args.folder,
                max_files=args.max_files,
                dry_run=args.dry_run
            )
    
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
