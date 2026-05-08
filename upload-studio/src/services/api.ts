import type { AuthStartResult, Metadata, PlatformKey, RecentUpload, RetryUploadResult, StudioStatus, UploadResult } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const fallbackStatus: StudioStatus = {
  authenticated: false,
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

async function request<T>(path: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, init);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return (await response.json()) as T;
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

export const studioApi = {
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
