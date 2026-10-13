import { useAuthStore } from '@/stores/auth';

const API_BASE = import.meta.env.PUBLIC_API_BASE || '/api/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  responseType?: 'json' | 'blob';
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, headers, responseType, ...fetchOptions } = options;
  const { accessToken } = useAuthStore.getState();

  // Build URL with query params
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const requestHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(headers as Record<string, string>),
  };

  if (accessToken) {
    (requestHeaders as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url.toString(), {
    ...fetchOptions,
    headers: requestHeaders,
  });

  if (response.status === 401) {
    // Token expired or invalid
    useAuthStore.getState().logout();
    window.location.href = '/auth/login';
    throw new ApiError(401, 'UNAUTHORIZED', 'Sesión expirada. Por favor inicia sesión nuevamente.');
  }

  if (response.status === 403) {
    throw new ApiError(403, 'FORBIDDEN', 'No tienes permisos para realizar esta acción');
  }

  if (!response.ok) {
    let errorData: { code?: string; message?: string; details?: Record<string, unknown> } = {};
    try {
      errorData = await response.json();
    } catch {
      // Ignore parse error
    }
    throw new ApiError(
      response.status,
      errorData.code || 'API_ERROR',
      errorData.message || `Error ${response.status}`,
      errorData.details
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (responseType === 'blob') {
    return response.blob() as Promise<T>;
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<T>(endpoint, { method: 'GET', params }),

  getBlob: (endpoint: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<Blob>(endpoint, { method: 'GET', params, responseType: 'blob' }),

  post: <T>(endpoint: string, data?: unknown, headers?: Record<string, string>) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    }),

  patch: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),

  // File upload helper
  upload: <T>(endpoint: string, file: File, additionalData?: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    return request<T>(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        // Don't set Content-Type, let browser set it with boundary
      },
    });
  },
};

export { ApiError };
export type { RequestOptions };