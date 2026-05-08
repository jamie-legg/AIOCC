import type { AdminUpload, AuthStartResult, AuthUser, LoginResult, Metadata, PlatformKey, RecentUpload, RetryUploadResult, StudioStatus, UploadResult, UserRole } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const ACCESS_TOKEN_STORAGE_KEY = 'aiocc_access_token';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const fallbackStatus: StudioStatus = {
  authenticated: false,
  role: 'viewer',
  user: {
    name: 'AIOCC',
  },
  platforms: [
    { platform: 'youtube', label: 'YouTube', handle: 'Not connected', connected: false, accent: '#ff1f3d' },
    { platform: 'instagram', label: 'Instagram', handle: 'Not connected', connected: false, accent: '#d946ef' },
    { platform: 'tiktok', label: 'TikTok', handle: 'Not connected', connected: false, accent: '#32c7f4' },
  ],
};

const fallbackUploads: RecentUpload[] = [];

export function getStoredAdminToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || '';
}

export function setStoredAdminToken(token: string) {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearStoredAdminToken() {
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

async function request<T>(path: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const headers = new Headers(init?.headers);
    const adminToken = getStoredAdminToken();
    if (adminToken) {
      headers.set('Authorization', `Bearer ${adminToken}`);
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) {
      let message = 'Request failed.';
      try {
        const body = await response.json();
        message = body.detail || message;
      } catch {
        message = await response.text();
      }
      throw new ApiError(message, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      throw error;
    }
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

export const studioApi = {
  login: (email: string, password: string) =>
    request<LoginResult>('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => request<AuthUser>('/api/v1/auth/me'),

  listUsers: () => request<AuthUser[]>('/api/v1/auth/users'),

  createUser: (email: string, password: string, role: UserRole) =>
    request<AuthUser>('/api/v1/auth/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, role }),
    }),

  getAdminUploads: () => request<AdminUpload[]>('/api/v1/studio/admin/uploads'),

  getStatus: () => request<StudioStatus>('/api/v1/studio/status', undefined, fallbackStatus),

  getRecentUploads: () => request<RecentUpload[]>('/api/v1/studio/recent-uploads', undefined, fallbackUploads),

  startAuth: (platform: PlatformKey) =>
    request<AuthStartResult>(`/api/v1/studio/auth/${platform}/start`, {
      method: 'POST',
    }),

  retryUpload: (uploadId: number) =>
    request<RetryUploadResult>(`/api/v1/studio/uploads/${uploadId}/retry`, {
      method: 'POST',
    }),

  generateMetadata: (filename: string) =>
    request<Metadata>(
      '/api/v1/studio/metadata',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, game_context: 'gaming' }),
      },
      {
        title: filename.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ') || 'Untitled Clip',
        description: 'Fresh gameplay clip ready to post.',
        hashtags: '#gaming #clips #AIOCC',
        visibility: 'public',
      },
    ),

  uploadClip: (file: File, metadata: Metadata, platforms: string[]) => {
    const form = new FormData();
    form.append('video', file);
    form.append('title', metadata.title);
    form.append('description', metadata.description);
    form.append('hashtags', metadata.hashtags);
    form.append('visibility', metadata.visibility);
    form.append('platforms', JSON.stringify(platforms));

    return request<UploadResult>('/api/v1/studio/upload', {
      method: 'POST',
      body: form,
    });
  },
};
