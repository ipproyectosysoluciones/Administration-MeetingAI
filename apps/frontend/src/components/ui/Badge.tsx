import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'gray' | 'info';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  icon?: React.ReactNode;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'primary', size = 'md', dot, icon, children, ...props }, ref) => {
    const variants = {
      primary: 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300',
      secondary: 'bg-secondary-100 text-secondary-800 dark:bg-secondary-900/30 dark:text-secondary-300',
      success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
      warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
      danger: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
      gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    };

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-0.5 text-xs',
      lg: 'px-3 py-1 text-sm',
    };

    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center gap-1.5 rounded-full font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        >
        {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', 'bg-current')} />}
        {icon}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

// Status badge helper
export interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusVariants: Record<string, string> = {
  draft: 'gray',
  review: 'info',
  approved: 'success',
  published: 'primary',
  archived: 'gray',
  pending: 'warning',
  processing: 'info',
  completed: 'success',
  failed: 'danger',
  scheduled: 'info',
  in_progress: 'info',
  finished: 'success',
  cancelled: 'danger',
  stored: 'gray',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const variant = statusVariants[status] || 'gray';
  const label = status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ');

  return (
    <Badge variant={variant as any} className={clsx(className)}>
      {label}
    </Badge>
  );
}