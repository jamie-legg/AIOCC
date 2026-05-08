export type PlatformKey = 'youtube' | 'instagram' | 'tiktok';
export type UserRole = 'admin' | 'creator' | 'viewer';

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
  role: UserRole;
  user: {
    name: string;
    avatarUrl?: string;
  };
  platforms: PlatformStatus[];
}

export interface AuthUser {
  id: number;
  email: string;
  api_key: string;
  subscription_tier: string;
  role: UserRole;
  is_active: number;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  api_key: string;
  user: AuthUser;
}

export interface AdminUpload {
  uploadId: number;
  clipId: number;
  userEmail: string;
  platform: PlatformKey;
  title: string;
  status: string;
  uploadedAt: string;
  url?: string | null;
  error?: string | null;
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
