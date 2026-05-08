import { Clock3, FileVideo, Maximize2, Pencil, Play } from 'lucide-react';

interface ClipPreviewProps {
  file?: File | null;
  previewUrl?: string | null;
  onChangeFile: () => void;
}

function formatSize(bytes: number) {
  if (!bytes) return '78.6 MB';
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

export function ClipPreview({ file, previewUrl, onChangeFile }: ClipPreviewProps) {
  const fileName = file?.name || 'Warzone_Clutch_Win.mp4';

  return (
    <div className="mt-4 rounded-xl border border-studio-border bg-studio-panelSoft/80 p-3">
      <div className="flex gap-4">
        <div className="relative h-40 w-72 overflow-hidden rounded-lg border border-white/10 bg-gradient-to-br from-slate-700 via-slate-900 to-black">
          {previewUrl ? <video src={previewUrl} className="h-full w-full object-cover" muted /> : null}
          {!previewUrl ? (
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(80,120,130,0.6),transparent_35%),linear-gradient(135deg,#32404a,#111821_55%,#070c12)]" />
          ) : null}
          <button className="absolute inset-0 m-auto grid h-14 w-14 place-items-center rounded-full bg-black/60 text-white backdrop-blur">
            <Play fill="currentColor" size={24} />
          </button>
        </div>

        <div className="flex flex-1 flex-col justify-between py-1">
          <div>
            <h3 className="font-semibold text-studio-text">{fileName}</h3>
            <div className="mt-5 space-y-3 text-sm text-studio-muted">
              <div className="flex items-center gap-3">
                <Clock3 size={17} /> <span>00:45</span>
              </div>
              <div className="flex items-center gap-3">
                <Maximize2 size={17} /> <span>1920 x 1080 (16:9)</span>
              </div>
              <div className="flex items-center gap-3">
                <FileVideo size={17} /> <span>{formatSize(file?.size || 0)}</span>
              </div>
            </div>
          </div>
          <button className="secondary-button w-fit" onClick={onChangeFile} type="button">
            <Pencil size={15} />
            Change file
          </button>
        </div>
      </div>
    </div>
  );
}
