import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ClipPreview } from './components/ClipPreview';
import { DropZone } from './components/DropZone';
import { Header } from './components/Header';
import { MetadataPanel } from './components/MetadataPanel';
import { PlatformCard } from './components/PlatformCard';
import { PlatformPicker } from './components/PlatformPicker';
import { RecentUploads } from './components/RecentUploads';
import { ApiError, clearStoredAdminToken, getStoredAdminToken, setStoredAdminToken, studioApi } from './services/api';
import type { Metadata, PlatformKey, RecentUpload, StudioStatus } from './types';

const initialMetadata: Metadata = {
  title: '',
  description: '',
  hashtags: '',
  visibility: 'public',
};

const initialStatus: StudioStatus = {
  authenticated: false,
  user: { name: 'AIOCC' },
  platforms: [
    { platform: 'youtube', label: 'YouTube', handle: 'Not connected', connected: false, accent: '#ff1f3d' },
    { platform: 'instagram', label: 'Instagram', handle: 'Not connected', connected: false, accent: '#d946ef' },
    { platform: 'tiktok', label: 'TikTok', handle: 'Not connected', connected: false, accent: '#32c7f4' },
  ],
};

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<StudioStatus>(initialStatus);
  const [metadata, setMetadata] = useState<Metadata>(initialMetadata);
  const [recentUploads, setRecentUploads] = useState<RecentUpload[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<PlatformKey[]>(['youtube', 'instagram', 'tiktok']);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [authenticating, setAuthenticating] = useState<PlatformKey | null>(null);
  const [retryingUploadId, setRetryingUploadId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLocked, setIsLocked] = useState(false);
  const [adminToken, setAdminToken] = useState(() => getStoredAdminToken());

  const refreshStatus = async () => {
    try {
      const data = await studioApi.getStatus();
      setStatus(data);
      setSelectedPlatforms(data.platforms.filter((platform) => platform.connected).map((platform) => platform.platform));
      setIsLocked(false);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setIsLocked(true);
        return false;
      }
      throw error;
    }
  };

  useEffect(() => {
    refreshStatus();
    studioApi.getRecentUploads().then(setRecentUploads).catch((error) => {
      if (!(error instanceof ApiError && error.status === 401)) {
        throw error;
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const connectedPlatforms = useMemo(() => status.platforms.filter((platform) => platform.connected), [status.platforms]);

  const handleSelectFile = async (file: File) => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setNotice(null);
    setIsGenerating(true);
    try {
      setMetadata(await studioApi.generateMetadata(file.name));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async () => {
    setIsGenerating(true);
    try {
      setMetadata(await studioApi.generateMetadata(selectedFile?.name || 'clip.mp4'));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleTogglePlatform = (platform: PlatformKey) => {
    setSelectedPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform],
    );
  };

  const handlePlatformAuth = async (platform: PlatformKey) => {
    setAuthenticating(platform);
    setNotice(null);
    try {
      const result = await studioApi.startAuth(platform);
      if (result.authUrl) {
        window.location.assign(result.authUrl);
        return;
      }
      setNotice(result.message || `Could not start ${platform} authentication.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : `Failed to start ${platform} authentication.`);
    } finally {
      setAuthenticating(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setNotice('Choose a clip before uploading.');
      return;
    }
    if (selectedPlatforms.length === 0) {
      setNotice('Select at least one platform.');
      return;
    }
    setIsUploading(true);
    setNotice(null);
    try {
      const result = await studioApi.uploadClip(selectedFile, metadata, selectedPlatforms);
      setRecentUploads(result.uploads);
      setNotice(result.message || `Saved clip for ${selectedPlatforms.length} selected platform(s).`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRetryUpload = async (upload: RecentUpload) => {
    setRetryingUploadId(upload.uploadId);
    setNotice(null);
    try {
      const result = await studioApi.retryUpload(upload.uploadId);
      setRecentUploads(result.uploads);
      setNotice(result.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : `Retry failed for ${upload.platform}.`);
    } finally {
      setRetryingUploadId(null);
    }
  };

  const handleUnlock = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStoredAdminToken(adminToken.trim());
    setNotice(null);
    const unlocked = await refreshStatus();
    if (!unlocked) {
      setNotice('Invalid admin token.');
      return;
    }
    await studioApi.getRecentUploads().then(setRecentUploads);
  };

  const handleLock = () => {
    clearStoredAdminToken();
    setAdminToken('');
    setIsLocked(true);
    setNotice(null);
  };

  if (isLocked) {
    return (
      <div className="min-h-screen bg-studio-bg text-studio-text">
        <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_10%_0%,rgba(50,199,244,0.14),transparent_32%),radial-gradient(circle_at_95%_10%,rgba(217,70,239,0.12),transparent_30%)]" />
        <main className="mx-auto flex min-h-screen max-w-xl items-center px-6">
          <form className="panel w-full p-6" onSubmit={handleUnlock}>
            <div className="text-sm font-semibold uppercase tracking-[0.3em] text-studio-cyan">Admin Access</div>
            <h1 className="mt-3 text-2xl font-bold">Unlock Upload Studio</h1>
            <p className="mt-3 text-sm text-studio-muted">
              Production access is restricted. Enter the admin token to manage connections, generate metadata, and publish uploads.
            </p>
            {notice ? <div className="mt-4 rounded-lg border border-studio-danger/30 bg-studio-danger/10 px-4 py-3 text-sm text-studio-danger">{notice}</div> : null}
            <input
              className="studio-input mt-5"
              type="password"
              value={adminToken}
              onChange={(event) => setAdminToken(event.target.value)}
              placeholder="Admin token"
              autoFocus
            />
            <button className="primary-button mt-5 w-full justify-center" type="submit">
              Unlock Studio
            </button>
          </form>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-studio-bg text-studio-text">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_10%_0%,rgba(50,199,244,0.14),transparent_32%),radial-gradient(circle_at_95%_10%,rgba(217,70,239,0.12),transparent_30%)]" />
      <Header status={status} />

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="mb-4 flex justify-end">
          <button className="secondary-button" type="button" onClick={handleLock}>
            Lock Studio
          </button>
        </div>
        <div className="grid grid-cols-3 gap-5">
          {status.platforms.map((platform) => (
            <PlatformCard key={platform.platform} platform={platform} onClick={(item) => handlePlatformAuth(item.platform)} />
          ))}
        </div>

        {authenticating ? (
          <div className="mt-4 rounded-lg border border-studio-cyan/30 bg-studio-cyan/10 px-4 py-3 text-sm text-studio-cyan">
            Starting {authenticating} authentication...
          </div>
        ) : null}

        {notice ? <div className="mt-4 rounded-lg border border-studio-cyan/30 bg-studio-cyan/10 px-4 py-3 text-sm text-studio-cyan">{notice}</div> : null}

        <div className="mt-5 grid grid-cols-[1fr_0.96fr] gap-5">
          <section className="panel p-4">
            <DropZone onSelectFile={handleSelectFile} />
            <ClipPreview file={selectedFile} previewUrl={previewUrl} onChangeFile={() => fileInputRef.current?.click()} />
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) handleSelectFile(file);
              }}
            />
            <PlatformPicker platforms={connectedPlatforms} selected={selectedPlatforms} onToggle={handleTogglePlatform} />
          </section>

          <div className="space-y-4">
            <MetadataPanel
              metadata={metadata}
              isGenerating={isGenerating}
              isUploading={isUploading}
              onChange={setMetadata}
              onRegenerate={handleRegenerate}
              onUpload={handleUpload}
            />
            <RecentUploads uploads={recentUploads} retryingUploadId={retryingUploadId} onRetry={handleRetryUpload} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
