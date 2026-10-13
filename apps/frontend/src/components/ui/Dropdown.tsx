import { Fragment, ReactNode, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { clsx } from 'clsx';
import { ChevronDown, ChevronUp, X } from 'lucide-react';

interface DropdownItem {
  label: string;
  onClick: () => void;
  icon?: React.ReactNode;
  disabled?: boolean;
  danger?: boolean;
  divider?: boolean;
}

interface DropdownProps {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  triggerClassName?: string;
  menuClassName?: string;
}

export function Dropdown({
  trigger,
  items,
  align = 'right',
  triggerClassName,
  menuClassName,
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        triggerRef.current && !triggerRef.current.contains(e.target as Node) &&
        menuRef.current && !menuRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const toggle = () => setIsOpen(!isOpen);

  return (
    <div className="relative inline-block" ref={triggerRef}>
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'inline-flex items-center gap-1',
          triggerClassName
        )}
        aria-expanded={isOpen}
        aria-haspopup="true"
        type="button"
      >
        {trigger}
        <ChevronDown className={clsx('w-4 h-4 transition-transform', 'duration-200')} />
      </button>

      {isOpen && createPortal(
        <div
          ref={menuRef}
          className={clsx(
            'absolute z-50 mt-2 min-w-[180px] bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-lg',
            'animate-slide-down',
            'py-1',
            align === 'right' ? 'right-0' : 'left-0'
          )}
          role="menu"
          aria-orientation="vertical"
        >
          {items.map((item, index) => (
            item.divider ? (
              <hr key={`divider-${index}`} className="my-1 border-gray-200 dark:border-gray-700" />
            ) : (
              <button
                key={index}
                onClick={() => {
                  if (!item.disabled) {
                    item.onClick();
                    // Don't close immediately if we want to allow multiple selections
                    // setIsOpen(false);
                  }
                }}
                disabled={item.disabled}
                dangerouslySetInnerHTML={{ __html: '' }}
                className={clsx(
                  'w-full px-4 py-2 text-left text-sm flex items-center gap-2',
                  'hover:bg-gray-100 dark:hover:bg-gray-700',
                  'focus:outline-none focus:bg-gray-100 dark:focus:bg-gray-700',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  item.danger && 'text-red-600 dark:text-red-400',
                  item.disabled && 'opacity-50 cursor-not-allowed'
                )}
                role="menuitem"
                tabIndex={-1}
              >
                {item.icon && <span className="w-4 h-4 flex-shrink-0">{item.icon}</span>}
                <span className="flex-1">{item.label}</span>
                {item.danger && (
                  <span className="ml-auto text-red-500 dark:text-red-400" aria-hidden="true">
                    ⚠
                  </span>
                )}
              </button>
            )
          ))}
        </div>
      )}
    </div>
  );
}

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  label?: string;
  error?: string;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

export function Select({
  value,
  onChange,
  options,
  placeholder,
  label,
  error,
  hint,
  disabled,
  required,
  className,
}: SelectProps) {
  const selectId = `select-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={selectId} className="label">
          {label}
          {required && <span className="text-red-500 ml-1" aria-hidden="true">*</span>}
        </label>
      )}
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        required={required}
        aria-invalid={!!error}
        aria-describedby={error ? `${selectId}-error` : undefined}
        className={`input ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''} ${disabled ? 'bg-gray-100 dark:bg-gray-800' : ''} ${className || ''}`}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}