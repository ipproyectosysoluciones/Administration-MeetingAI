import { Fragment, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { clsx } from 'clsx';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}

export function Tooltip({ content, children, position = 'top', delay = 200 }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const triggerRef = useRef<HTMLElement>(null);

  const show = () => {
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
  };

  const hide = () => {
    clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === 'Escape') setIsVisible(false);
  };

  return (
    <Fragment>
      <span
        ref={triggerRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onKeyDown={handleKeyDown}
        tabIndex={0}
      >
        {children}
      </span>

      {isVisible && createPortal(
        <div
          className={clsx(
            'absolute z-50 px-3 py-2 text-xs font-medium text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg',
            'whitespace-nowrap',
            'animate-fade-in',
            {
              top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
              bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
              left: 'right-full top-1/2 -translate-y-1/2 ml-2',
              right: 'left-full top-1/2 -translate-y-1/2 mr-2',
            }[position]
          )}
          role="tooltip"
        >
          {content}
          <div
            className={clsx(
              'absolute w-0 h-0 border-4 border-transparent',
              {
                top: 'bottom-0 left-1/2 -translate-x-1/2 border-b-gray-900 dark:border-b-gray-700',
                bottom: 'top-0 left-1/2 -translate-x-1/2 border-t-gray-900 dark:border-t-gray-700',
                left: 'right-0 top-1/2 -translate-y-1/2 border-r-gray-900 dark:border-r-gray-700',
                right: 'left-0 top-1/2 -translate-y-1/2 border-l-gray-900 dark:border-l-gray-700',
              }[position]
            )}
          />
        </div>,
        document.body
      )}
    </Fragment>
  );
}

interface TooltipProviderProps {
  children: ReactNode;
}

export function TooltipProvider({ children }: TooltipProviderProps) {
  return <>{children}</>;
}