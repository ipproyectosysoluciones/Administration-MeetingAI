import { forwardRef } from 'react';
import type { ReactNode, HTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { ChevronUp, ChevronDown } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  accessor: string | ((row: T) => ReactNode);
  sortable?: boolean;
  className?: string;
  width?: string;
  render?: (value: any, row: T) => ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyAccessor: (row: T) => string;
  isLoading?: boolean;
  emptyMessage?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  rowClassName?: (row: T) => string;
  onRowClick?: (row: T) => void;
  className?: string;
}

export function Table<T>({
  columns,
  data,
  keyAccessor,
  isLoading = false,
  emptyMessage = 'No hay datos disponibles',
  sortBy,
  sortOrder,
  onSort,
  rowClassName,
  onRowClick,
  className,
}: TableProps<T>) {
  const handleSort = (key: string) => {
    if (!onSort) return;
    onSort(key);
  };

  const getSortIcon = (key: string) => {
    if (sortBy !== key) return null;
    return sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />;
  };

  if (isLoading) {
    return (
      <div className="table-container">
        <table className="table" role="grid">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={col.className} style={{ width: col.width }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                <div className="flex flex-col items-center gap-2">
                  <svg className="w-8 h-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-sm">Cargando...</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="table-container">
        <table className="table" role="grid">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={col.className} style={{ width: col.width }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className={clsx('table-container', className)}>
      <table className="table" role="grid">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  col.className,
                  col.sortable && 'cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-gray-700/50'
                )}
                style={{ width: col.width }}
                onClick={() => col.sortable && handleSort(col.key)}
                scope="col"
              >
                <div className="flex items-center gap-1">
                  <span>{col.header}</span>
                  {col.sortable && getSortIcon(col.key)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={keyAccessor(row)}
              className={clsx(
                'transition-colors',
                onRowClick && 'cursor-pointer',
                rowClassName?.(row)
              )}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => {
                const cellValue = typeof col.accessor === 'function' ? col.accessor(row) : (row as any)[col.accessor];
                return (
                <td key={col.key} className={col.className}>
                  {col.render
                    ? col.render(cellValue, row)
                    : cellValue as ReactNode}
                </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, startPage + 4);

  const pages = Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);

  return (
    <div className={clsx('flex flex-col sm:flex-row items-center justify-between gap-4 py-4', className)}>
      <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
        <span>
          Mostrando {(currentPage - 1) * pageSize + 1} a {Math.min(currentPage * pageSize, totalItems)} de {totalItems}
        </span>
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(parseInt(e.target.value, 10))}
            className="input w-auto py-1.5 pl-3 pr-8"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} por página
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="btn-ghost btn-sm p-2 disabled:opacity-50"
          aria-label="Primera página"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="btn-ghost btn-sm p-2 disabled:opacity-50"
          aria-label="Página anterior"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {pages.length > 2 && startPage > 1 && (
          <span className="px-2 text-gray-400 dark:text-gray-500">...</span>
        )}

        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={clsx(
              'w-8 h-8 rounded-lg text-sm font-medium transition-colors',
              currentPage === page
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            )}
            aria-current={currentPage === page ? 'page' : undefined}
            aria-label={`Página ${page}`}
          >
            {page}
          </button>
        ))}

        {endPage < totalPages && (
          <span className="px-2 text-gray-400 dark:text-gray-500">...</span>
        )}

        {endPage < totalPages && totalPages > 1 && (
          <button
            key={totalPages}
            onClick={() => onPageChange(totalPages)}
            className={clsx(
              'w-8 h-8 rounded-lg text-sm font-medium transition-colors',
              currentPage === totalPages
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            )}
            aria-current={currentPage === totalPages ? 'page' : undefined}
            aria-label={`Página ${totalPages}`}
          >
            {totalPages}
          </button>
        )}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="btn-ghost btn-sm p-2 disabled:opacity-50"
          aria-label="Página siguiente"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="btn-ghost btn-sm p-2 disabled:opacity-50"
          aria-label="Última página"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}