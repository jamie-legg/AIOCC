import { FolderOpen, UploadCloud } from 'lucide-react';
import { useRef, useState } from 'react';

interface DropZoneProps {
  onSelectFile: (file: File) => void;
}

export function DropZone({ onSelectFile }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      className={`rounded-xl border border-dashed p-8 text-center transition ${
        dragging ? 'border-studio-cyan bg-studio-cyan/10' : 'border-studio-cyan/60 bg-black/10'
      }`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) {
          onSelectFile(file);
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            onSelectFile(file);
          }
        }}
      />
      <UploadCloud className="mx-auto mb-4 text-studio-cyan" size={52} strokeWidth={1.7} />
      <h2 className="text-xl font-semibold text-studio-text">Drop a gameplay clip here</h2>
      <p className="mt-2 text-sm text-studio-muted">Supports MP4, MOV, MKV, WEBM up to 10GB</p>
      <button className="primary-button mx-auto mt-6" onClick={() => inputRef.current?.click()} type="button">
        <FolderOpen size={18} />
        Browse files
      </button>
    </div>
  );
}
