import { Check, ShieldCheck } from 'lucide-react';
import type { PlatformKey, PlatformStatus } from '../types';
import { BrandIcon } from './BrandIcon';

interface PlatformPickerProps {
  platforms: PlatformStatus[];
  selected: PlatformKey[];
  onToggle: (platform: PlatformKey) => void;
}

export function PlatformPicker({ platforms, selected, onToggle }: PlatformPickerProps) {
  return (
    <section className="panel mt-4 p-4">
      <h2 className="mb-4 text-base font-semibold text-studio-text">Upload to</h2>
      {platforms.length === 0 ? (
        <div className="rounded-lg border border-studio-border bg-black/10 p-4 text-sm text-studio-muted">
          No connected platforms yet. Connect a platform from the cards above before uploading.
        </div>
      ) : null}
      <div className="grid grid-cols-3 gap-4">
        {platforms.map((platform) => {
          const active = selected.includes(platform.platform);
          return (
            <button
              key={platform.platform}
              type="button"
              onClick={() => onToggle(platform.platform)}
              className={`relative rounded-xl border p-4 text-left transition hover:border-studio-cyan ${
                active ? 'border-studio-cyan bg-studio-cyan/10 shadow-glow' : 'border-studio-border bg-black/10'
              }`}
            >
              <span
                className={`absolute right-3 top-3 grid h-5 w-5 place-items-center rounded ${
                  active ? 'bg-studio-cyan text-studio-bg' : 'bg-white/10 text-studio-muted'
                }`}
              >
                <Check size={14} strokeWidth={3} />
              </span>
              <BrandIcon platform={platform.platform} size="sm" />
              <div className="mt-4 font-semibold text-studio-text">{platform.label}</div>
              <div className="mt-1 text-sm text-studio-muted">{platform.handle}</div>
            </button>
          );
        })}
      </div>
      {platforms.length > 0 ? (
        <div className="mt-5 flex items-center gap-2 text-sm text-studio-muted">
          <ShieldCheck size={18} className="text-studio-cyan" />
          Connected accounts are ready to publish.
        </div>
      ) : null}
    </section>
  );
}
