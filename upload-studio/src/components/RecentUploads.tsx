import { ExternalLink, RotateCcw } from 'lucide-react';
import type { RecentUpload } from '../types';
import { BrandIcon } from './BrandIcon';

interface RecentUploadsProps {
  uploads: RecentUpload[];
  retryingUploadId: number | null;
  onRetry: (upload: RecentUpload) => void;
}

export function RecentUploads({ uploads, retryingUploadId, onRetry }: RecentUploadsProps) {
  return (
    <section className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-studio-text">Recent Uploads</h2>
        <button className="text-sm font-medium text-studio-cyan" type="button">
          View all
        </button>
      </div>
      <div className="space-y-2">
        {uploads.map((upload) => (
          <div key={upload.id} className="flex items-center gap-3 rounded-lg bg-black/15 px-2 py-2">
            <BrandIcon platform={upload.platform} size="sm" />
            <div className="min-w-0 flex-1">
              <div className="font-semibold capitalize text-studio-text">{upload.platform}</div>
              <div className="truncate text-xs text-studio-muted">{upload.title}</div>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                upload.status === 'uploaded' || upload.status === 'saved'
                  ? 'bg-studio-green/10 text-studio-green'
                  : upload.status === 'failed'
                    ? 'bg-studio-danger/10 text-studio-danger'
                    : 'bg-white/10 text-studio-muted'
              }`}
            >
              {upload.status === 'uploaded' ? 'Uploaded' : upload.status === 'saved' ? 'Saved' : upload.status}
            </span>
            <span className="w-24 text-sm text-studio-muted">{upload.uploadedAt}</span>
            {upload.status === 'failed' ? (
              <button
                className="inline-flex items-center gap-1 rounded border border-studio-danger/40 px-2 py-1 text-xs font-semibold text-studio-danger transition hover:bg-studio-danger/10 disabled:opacity-50"
                type="button"
                onClick={() => onRetry(upload)}
                disabled={retryingUploadId === upload.uploadId}
                title={upload.error || 'Retry failed upload'}
              >
                <RotateCcw size={14} className={retryingUploadId === upload.uploadId ? 'animate-spin' : ''} />
                Retry
              </button>
            ) : (
              <a href={upload.url || '#'} className="text-studio-cyan" aria-label="Open upload">
                <ExternalLink size={18} />
              </a>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
