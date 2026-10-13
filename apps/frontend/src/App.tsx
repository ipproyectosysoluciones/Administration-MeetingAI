import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuthStore } from '@/stores/auth';
import { Toaster } from '@/components/ui/Toaster';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { AdminLayout } from '@/components/layout/AdminLayout';
import MainLayout from '@/layouts/MainLayout';

// Pages
import LandingPage from '@/pages/index.astro';
import LoginPage from '@/pages/auth/login.astro';
import RegisterPage from '@/pages/auth/register.astro';
import MeetingsPage from '@/pages/portal/meetings/index.tsx';
import MinutesPage from '@/pages/portal/minutes/index.tsx';
import DocumentsPage from '@/pages/portal/documents/index.tsx';
import RecordingsPage from '@/pages/portal/recordings/index.tsx';
import DashboardPage from '@/pages/portal/dashboard.tsx';
import AdminDashboardPage from '@/pages/admin/dashboard.tsx';
import AdminUsersPage from '@/pages/admin/users/index.tsx';
import AdminOrganizationsPage from '@/pages/admin/organizations/index.tsx';
import AdminRbacPage from '@/pages/admin/rbac/index.tsx';
import AdminAuditPage from '@/pages/admin/audit/index.tsx';
import AdminSettingsPage from '@/pages/admin/settings/index.tsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function ProtectedRoute({ children, requiredPermission }: { children: React.ReactNode; requiredPermission?: string }) {
  const { isAuthenticated, hasPermission, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="w-8 h-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-600 dark:text-gray-400">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Acceso Denegado</h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">No tienes permisos para acceder a esta página.</p>
          <button onClick={() => window.history.back()} className="btn-primary">
            Volver
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="w-8 h-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-600 dark:text-gray-400">Cargando...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/portal" replace />;
  }

  return <>{children}</>;
}