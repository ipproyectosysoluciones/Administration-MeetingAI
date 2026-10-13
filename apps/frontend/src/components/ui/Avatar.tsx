import { clsx } from 'clsx';
import { forwardRef, HTMLAttributes } from 'react';

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  alt?: string;
  name?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  shape?: 'circle' | 'square';
  status?: 'online' | 'offline' | 'busy' | 'away';
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getColorFromName(name: string): string {
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
    'bg-rose-500',
  ];

  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

export const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, alt, name, size = 'md', shape = 'circle', status, children, ...props }, ref) => {
    const sizes = {
      xs: 'w-6 h-6 text-xs',
      sm: 'w-8 h-8 text-xs',
      md: 'w-10 h-10 text-sm',
      lg: 'w-12 h-12 text-base',
      xl: 'w-16 h-16 text-lg',
    };

    const shapes = {
      circle: 'rounded-full',
      square: 'rounded-lg',
    };

    const statusSizes = {
      xs: 'w-2 h-2',
      sm: 'w-2.5 h-2.5',
      md: 'w-3 h-3',
      lg: 'w-3.5 h-3.5',
      xl: 'w-4 h-4',
    };

    const statusColors = {
      online: 'bg-green-500',
      offline: 'bg-gray-400',
      busy: 'bg-red-500',
      away: 'bg-yellow-500',
    };

    const hasImage = src && src.length > 0;
    const hasName = name && name.length > 0;

    return (
      <div
        ref={ref}
        className={clsx(
          'relative inline-flex items-center justify-center overflow-hidden',
          sizes[size],
          shapes[shape],
          'bg-gray-100 dark:bg-gray-700',
          'flex-shrink-0'
        )}
        ref={ref}
      >
        {hasImage ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className={clsx('w-full h-full object-cover', shapes[shape])}
          />
        ) : hasName ? (
          <span className={clsx('font-medium text-white', sizes[size])}>
            {getInitials(name)}
          </span>
        ) : children || (
          <svg className="w-full h-full text-gray-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993C19.738 17.996 20.667 15.199 20.997 12h3.003v3.014A15.037 15.037 0 0112 23.994c-5.883 0-10.996-3.715-11.996-8.994zM12 18c-3.315 0-6-2.685-6-6 0-3.314 2.686-6 6-6 3.314 0 6 2.686 6 6 0 3.315-2.685 6-6 6zm0-10c-2.206 0-4 1.79-4 4s1.791 4 4 4 4-1.79 4-4-1.791-4-4-4z" />
          </svg>
        )}

        {status && (
          <span
            className={clsx(
              'absolute bottom-0 right-0 border-2 border-white dark:border-gray-900',
              'rounded-full',
              statusSizes[size],
              statusColors[status]
            )}
            aria-label={`Estado: ${status}`}
          />
        )}
      </div>
    );
  }
);

Avatar.displayName = 'Avatar';

export const AvatarGroup = forwardRef<HTMLDivElement, { children: React.ReactNode; max?: number; className?: string }>(
  ({ children, max = 5, className, ...props }, ref) => {
    const childrenArray = Array.isArray(children) ? children : [children];
    const visibleChildren = childrenArray.slice(0, max);
    const remainingCount = childrenArray.length - max;

    return (
      <div ref={ref} className={clsx('flex -space-x-2', className)} {...props}>
        {visibleChildren.map((child, index) => (
          <div key={index} className="relative z-[auto]">
            {child}
          </div>
        ))}
        {remainingCount > 0 && (
          <div
            className="flex items-center justify-center bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 font-medium border-2 border-white dark:border-gray-900 rounded-full"
            style={{ width: '2.5rem', height: '2.5rem' }}
          >
            +{remainingCount}
          </div>
        )}
      </div>
    );
  }
);

AvatarGroup.displayName = 'AvatarGroup';