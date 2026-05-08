import { ChevronDown } from 'lucide-react';
import type { StudioStatus } from '../types';

interface HeaderProps {
  status: StudioStatus;
}

export function Header({ status }: HeaderProps) {
  return (
    <header className="border-b border-white/10 bg-studio-bg/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-3">
            <div className="relative h-8 w-8">
              <div className="absolute inset-0 rounded-lg bg-cyan-400/20 blur-md" />
              <div className="relative grid h-8 w-8 place-items-center rounded-lg border border-cyan-300/50 text-cyan-300">
                <span className="text-lg font-black">A</span>
              </div>
            </div>
            <span className="text-xl font-extrabold tracking-wide text-white">AIOCC</span>
          </div>
          <div className="rounded-md border border-studio-green/20 bg-studio-green/10 px-3 py-1 text-sm font-medium text-studio-green">
            <span className="mr-2 inline-block h-2 w-2 rounded-full bg-studio-green" />
            {status.authenticated ? 'Authenticated' : 'Offline'}
          </div>
        </div>

        <button className="flex items-center gap-3 rounded-full px-2 py-1 transition hover:bg-white/5">
          <div className="h-9 w-9 overflow-hidden rounded-full bg-gradient-to-br from-slate-200 to-slate-500 ring-2 ring-white/10">
            {status.user.avatarUrl ? <img src={status.user.avatarUrl} alt="" className="h-full w-full object-cover" /> : null}
          </div>
          <span className="text-sm font-medium text-studio-text">{status.user.name}</span>
          <ChevronDown size={16} className="text-studio-muted" />
        </button>
      </div>
    </header>
  );
}
