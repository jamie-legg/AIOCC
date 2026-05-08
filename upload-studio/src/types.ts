export type PlatformKey = 'youtube' | 'instagram' | 'tiktok';

export interface PlatformStatus {
  platform: PlatformKey;
  label: string;
  handle: string;
  connected: boolean;
  accent: string;
  detail?: string | null;
}

export interface Metadata {
  title: string;
  description: string;
  hashtags: string;
  visibility: 'public' | 'unlisted' | 'private';
}

export interface RecentUpload {
  id: string;
  uploadId: number;
  platform: PlatformKey;
  title: string;
  status: 'uploaded' | 'saved' | 'failed' | 'pending';
  uploadedAt: string;
  url?: string;
  error?: string;
}

export interface StudioStatus {
  authenticated: boolean;
  user: {
    name: string;
    avatarUrl?: string;
  };
  platforms: PlatformStatus[];
}

export interface UploadResult {
  clipId: string;
  uploads: RecentUpload[];
  message: string;
}

export interface AuthStartResult {
  platform: PlatformKey;
  started: boolean;
  message: string;
  authUrl?: string;
}

export interface RetryUploadResult {
  upload: RecentUpload;
  uploads: RecentUpload[];
  message: string;
}
