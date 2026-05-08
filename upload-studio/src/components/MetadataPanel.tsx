import { Globe2, Link2, Lock, RefreshCw, Upload, type LucideIcon } from 'lucide-react';
import type { Metadata } from '../types';

interface MetadataPanelProps {
  metadata: Metadata;
  isGenerating: boolean;
  isUploading: boolean;
  onChange: (metadata: Metadata) => void;
  onRegenerate: () => void;
  onUpload: () => void;
}

export function MetadataPanel({
  metadata,
  isGenerating,
  isUploading,
  onChange,
  onRegenerate,
  onUpload,
}: MetadataPanelProps) {
  const update = <K extends keyof Metadata>(key: K, value: Metadata[K]) => onChange({ ...metadata, [key]: value });
  const visibilityOptions: Array<{ value: Metadata['visibility']; Icon: LucideIcon; label: string }> = [
    { value: 'public', Icon: Globe2, label: 'Public' },
    { value: 'unlisted', Icon: Link2, label: 'Unlisted' },
    { value: 'private', Icon: Lock, label: 'Private' },
  ];

  return (
    <section className="panel h-fit p-5">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-studio-text">
          <span className="mr-2 text-studio-cyan">++</span>
          AI Metadata
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-studio-muted">Generated from clip context</span>
          <span className="h-2 w-2 rounded-full bg-studio-green" />
          <button className="secondary-button" type="button" onClick={onRegenerate} disabled={isGenerating}>
            <RefreshCw size={15} className={isGenerating ? 'animate-spin' : ''} />
            Regenerate
          </button>
        </div>
      </div>

      <label className="field-label">
        <span>Title</span>
        <span>{metadata.title.length} / 100</span>
      </label>
      <input className="studio-input" value={metadata.title} maxLength={100} onChange={(event) => update('title', event.target.value)} />

      <label className="field-label mt-4">
        <span>Description</span>
        <span>{metadata.description.length} / 5000</span>
      </label>
      <textarea
        className="studio-input min-h-[92px] resize-none"
        value={metadata.description}
        maxLength={5000}
        onChange={(event) => update('description', event.target.value)}
      />

      <label className="field-label mt-4">
        <span>Hashtags</span>
        <span>{metadata.hashtags.length} / 500</span>
      </label>
      <input
        className="studio-input"
        value={metadata.hashtags}
        maxLength={500}
        onChange={(event) => update('hashtags', event.target.value)}
      />
      <p className="mt-2 text-xs text-studio-muted">Separate hashtags with spaces</p>

      <div className="mt-6">
        <div className="mb-3 text-sm font-semibold text-studio-text">Visibility</div>
        <div className="grid grid-cols-3 overflow-hidden rounded-lg border border-studio-border">
          {visibilityOptions.map(({ value, Icon, label }) => (
            <button
              key={value}
              type="button"
              className={`flex items-center justify-center gap-2 border-r border-studio-border px-4 py-3 text-sm last:border-r-0 ${
                metadata.visibility === value ? 'bg-studio-cyan/15 text-studio-cyan ring-1 ring-inset ring-studio-cyan' : 'text-studio-muted'
              }`}
              onClick={() => update('visibility', value)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <button className="primary-button mt-5 w-full justify-center py-4" type="button" onClick={onUpload} disabled={isUploading}>
        <Upload size={18} />
        {isUploading ? 'Uploading...' : 'Upload to Selected Platforms'}
      </button>
    </section>
  );
}
