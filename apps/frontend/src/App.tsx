import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';
import PortalDashboardPage from '@/components/pages/portal/DashboardPage';
import MeetingsPage from '@/components/pages/portal/meetings/MeetingsPage';
import MinutesPage from '@/components/pages/portal/minutes/MinutesPage';
import DocumentsPage from '@/components/pages/portal/documents/DocumentsPage';
import RecordingsPage from '@/components/pages/portal/recordings/RecordingsPage';
import AdminDashboardPage from '@/components/pages/admin/DashboardPage';
import AdminOrganizationsPage from '@/components/pages/admin/organizations/OrganizationsPage';
import AdminRbacPage from '@/components/pages/admin/rbac/RbacPage';
import AdminAuditPage from '@/components/pages/admin/audit/AuditPage';
import AdminSettingsPage from '@/components/pages/admin/settings/SettingsPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600 dark:text-gray-400">Cargando…</p>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/auth/login" element={<Navigate to="/auth/login.astro" replace />} />
      <Route path="/portal" element={<ProtectedRoute><PortalDashboardPage /></ProtectedRoute>} />
      <Route path="/portal/dashboard" element={<ProtectedRoute><PortalDashboardPage /></ProtectedRoute>} />
      <Route path="/portal/meetings" element={<ProtectedRoute><MeetingsPage /></ProtectedRoute>} />
      <Route path="/portal/minutes" element={<ProtectedRoute><MinutesPage /></ProtectedRoute>} />
      <Route path="/portal/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
      <Route path="/portal/recordings" element={<ProtectedRoute><RecordingsPage /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute><AdminDashboardPage /></ProtectedRoute>} />
      <Route path="/admin/dashboard" element={<ProtectedRoute><AdminDashboardPage /></ProtectedRoute>} />
      <Route path="/admin/organizations" element={<ProtectedRoute><AdminOrganizationsPage /></ProtectedRoute>} />
      <Route path="/admin/rbac" element={<ProtectedRoute><AdminRbacPage /></ProtectedRoute>} />
      <Route path="/admin/audit" element={<ProtectedRoute><AdminAuditPage /></ProtectedRoute>} />
      <Route path="/admin/settings" element={<ProtectedRoute><AdminSettingsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/portal" replace />} />
    </Routes>
  );
}
