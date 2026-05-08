import { Check, ChevronRight } from 'lucide-react';
import type { PlatformStatus } from '../types';
import { BrandIcon } from './BrandIcon';

interface PlatformCardProps {
  platform: PlatformStatus;
  onClick: (platform: PlatformStatus) => void;
  canManageConnections: boolean;
}

export function PlatformCard({ platform, onClick, canManageConnections }: PlatformCardProps) {
  return (
    <button
      className={`panel group relative flex min-h-[92px] items-center justify-between overflow-hidden px-5 text-left transition ${
        canManageConnections ? 'hover:-translate-y-0.5 hover:border-cyan-300/60 hover:shadow-glow' : 'cursor-default'
      }`}
      onClick={() => onClick(platform)}
      disabled={!canManageConnections}
      type="button"
      title={canManageConnections ? (platform.connected ? `Reconnect ${platform.label}` : `Authenticate ${platform.label}`) : `${platform.label} connection is managed by an admin`}
    >
      <span className="absolute inset-y-0 left-0 w-1.5" style={{ background: platform.accent }} />
      <div className="flex items-center gap-4">
        <BrandIcon platform={platform.platform} size="lg" />
        <div>
          <div className="text-base font-semibold text-studio-text">{platform.label}</div>
          <div className="mt-1 flex items-center gap-2 text-sm text-studio-muted">
            <span className={`h-2 w-2 rounded-full ${platform.connected ? 'bg-studio-green' : 'bg-studio-danger'}`} />
            {platform.connected ? 'Connected' : 'Disconnected'}
          </div>
          <div className="mt-1 text-xs text-studio-muted">{platform.handle}</div>
          {platform.detail ? <div className="mt-1 max-w-52 truncate text-[11px] text-studio-muted/75">{platform.detail}</div> : null}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span
          className={`grid h-8 w-8 place-items-center rounded-full ${
            platform.connected ? 'bg-studio-green/15 text-studio-green' : 'bg-white/5 text-studio-muted'
          }`}
        >
          {platform.connected ? <Check size={17} strokeWidth={3} /> : null}
        </span>
        {canManageConnections ? <ChevronRight className="text-studio-muted transition group-hover:text-studio-text" size={20} /> : null}
      </div>
    </button>
  );
}
