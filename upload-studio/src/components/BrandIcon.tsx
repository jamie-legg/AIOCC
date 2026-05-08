import type { PlatformKey } from '../types';

interface BrandIconProps {
  platform: PlatformKey;
  size?: 'sm' | 'md' | 'lg';
}

const sizeClass = {
  sm: 'h-8 w-8 text-sm',
  md: 'h-10 w-10 text-base',
  lg: 'h-12 w-12 text-lg',
};

export function BrandIcon({ platform, size = 'md' }: BrandIconProps) {
  const label = platform === 'youtube' ? 'YT' : platform === 'instagram' ? 'IG' : 'TT';
  const className =
    platform === 'youtube'
      ? 'bg-red-600 text-white'
      : platform === 'instagram'
        ? 'bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 text-white'
        : 'bg-black text-white ring-1 ring-cyan-300/30';

  return (
    <div className={`${sizeClass[size]} ${className} grid shrink-0 place-items-center rounded-xl font-bold shadow-lg`}>
      {label}
    </div>
  );
}
