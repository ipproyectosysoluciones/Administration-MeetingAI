import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Calendar, Users, FileText, Settings, TrendingUp, Clock, CheckCircle, AlertCircle, XCircle, Loader2, BarChart3, FileText as FileTextIcon, Users as UsersIcon, Calendar as CalendarIcon, Mic, Archive, Building , ShieldCheck } from 'lucide-react';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { organizationsApi, usersApi, meetingsApi, minutesApi, documentsApi, recordingsApi, transcriptionsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { StatusBadge } from '@/components/ui/Badge';

interface Stats {
  totalOrganizations: number;
  totalUsers: number;
  totalMeetings: number;
  totalMinutes: number;
  totalDocuments: number;
  totalRecordings: number;
  totalTranscriptions: number;
  totalStorageUsed: number;
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentOrganizations, setRecentOrganizations] = useState<any[]>([]);
  const [recentUsers, setRecentUsers] = useState<any[]>([]);
  const [recentMeetings, setRecentMeetings] = useState<any[]>([]);
  const [recentMinutes, setRecentMinutes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [
        orgsResponse,
        usersResponse,
        meetingsResponse,
        minutesResponse,
        documentsResponse,
        recordingsResponse,
        transcriptionsResponse,
      ] = await Promise.all([
        organizationsApi.list({ page_size: 100 }),
        usersApi.list({ page_size: 100 }),
        meetingsApi.list({ page_size: 100 }),
        minutesApi.list({ page_size: 100 }),
        documentsApi.list({ page_size: 100 }),
        recordingsApi.list({ page_size: 100 }),
        transcriptionsApi.list({ page_size: 100 }),
      ]);

      setStats({
        totalOrganizations: orgsResponse.total,
        totalUsers: usersResponse.total,
        totalMeetings: meetingsResponse.total,
        totalMinutes: minutesResponse.total,
        totalDocuments: documentsResponse.total,
        totalRecordings: recordingsResponse.total,
        totalTranscriptions: transcriptionsResponse.total,
        totalStorageUsed: 0, // TODO: calculate from documents + recordings
      });

      // Fetch recent items
      const [
        recentOrgsResponse,
        recentUsersResponse,
        recentMeetingsResponse,
        recentMinutesResponse,
      ] = await Promise.all([
        organizationsApi.list({ page_size: 5 }),
        usersApi.list({ page_size: 5 }),
        meetingsApi.list({ page_size: 5 }),
        minutesApi.list({ page_size: 5 }),
      ]);

      setRecentOrganizations(recentOrgsResponse.items);
      setRecentUsers(recentUsersResponse.items);
      setRecentMeetings(recentMeetingsResponse.items);
      setRecentMinutes(recentMinutesResponse.items);
    } catch (error) {
      console.error('Error fetching admin dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <svg className="w-12 h-12 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-gray-600 dark:text-gray-400">Cargando panel de administracion...</p>
          </div>
        </div>
      </AdminLayout>
    );
  }

  const quickActions = [
    {
      label: 'Nueva Organizacion',
      icon: Plus,
      href: '/admin/organizations/new',
      permission: 'organization.create',
      color: 'bg-primary-600 hover:bg-primary-700',
      iconColor: 'text-primary-600',
    },
    {
      label: 'Nuevo Usuario',
      icon: Users,
      href: '/admin/users/new',
      permission: 'user.create',
      color: 'bg-green-600 hover:bg-green-700',
      iconColor: 'text-green-600',
    },
    {
      label: 'Nuevo Rol',
      icon: ShieldCheck,
      href: '/admin/rbac/new',
      permission: 'role.create',
      color: 'bg-purple-600 hover:bg-purple-700',
      iconColor: 'text-purple-600',
    },
    {
      label: 'Ver Auditoria',
      icon: FileText,
      href: '/admin/audit',
      permission: 'audit.read',
      color: 'bg-blue-600 hover:bg-blue-700',
      iconColor: 'text-blue-600',
    },
  ].filter(action => hasPermission(action.permission));

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Panel de Administracion</h1>
            <p className="text-gray-600 dark:text-gray-400">Vision general de la plataforma</p>
          </div>
        </div>

        { /* Stats Grid */ }
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                <Building className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Organizaciones</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalOrganizations || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center">
                <UsersIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Usuarios Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalUsers || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                <CalendarIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Reuniones Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalMeetings || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                <FileTextIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Actas Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalMinutes || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-xl flex items-center justify-center">
                <FileTextIcon className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Documentos Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalDocuments || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-pink-100 dark:bg-pink-900/30 rounded-xl flex items-center justify-center">
                <Mic className="w-6 h-6 text-pink-600 dark:text-pink-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Grabaciones Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalRecordings || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-indigo-600 dark:text-indigo-400 animate-spin" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Transcripciones Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalTranscriptions || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center">
                <Archive className="w-6 h-6 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Almacenamiento Usado</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatFileSize(stats?.totalStorageUsed || 0)}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        
        <Card>
          <CardHeader>
            <CardTitle>Acciones Rapidas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {quickActions.map((action) => (
                <Link
                  key={action.label}
                  to={action.href}
                  className={clsx(
                    'flex flex-col items-center gap-2 p-4 rounded-xl border border-gray-200 dark:border-gray-700',
                    'hover:shadow-md transition-shadow duration-200',
                    action.color
                  )}
                >
                  <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', action.iconColor)}>
                    <action.icon className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-sm font-medium text-white text-center">{action.label}</span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Organizaciones Recientes</CardTitle>
              <Link to="/admin/organizations" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentOrganizations.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay organizaciones recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentOrganizations.slice(0, 5).map((org: any) => (
                    <Link
                      key={org.id}
                      to={`/admin/organizations/${org.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{org.name}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">{org.slug}</p>
                      </div>
                      <Badge variant={org.deleted_at ? 'danger' : 'success'}>
                        {org.deleted_at ? 'Eliminada' : 'Activa'}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>

          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Usuarios Recientes</CardTitle>
              <Link to="/admin/users" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todos
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentUsers.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay usuarios recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentUsers.slice(0, 5).map((user: any) => (
                    <Link
                      key={user.id}
                      to={`/admin/users/${user.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{user.full_name || 'Sin nombre'}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {user.is_super_admin && <Badge variant="warning">Super Admin</Badge>}
                        {user.is_active ? <Badge variant="success">Activo</Badge> : <Badge variant="danger">Inactivo</Badge>}
                      </div>
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>
        </div>

        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Reuniones Recientes</CardTitle>
              <Link to="/admin/meetings" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentMeetings.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay reuniones recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentMeetings.slice(0, 5).map((meeting: any) => (
                    <Link
                      key={meeting.id}
                      to={`/admin/meetings/${meeting.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{meeting.title}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                          <CalendarIcon className="w-4 h-4" />
                          <span>{formatDateTime(meeting.starts_at)}</span>
                        </p>
                      </div>
                      <Badge variant={
                        meeting.status === 'scheduled' ? 'info' :
                        meeting.status === 'in_progress' ? 'warning' :
                        meeting.status === 'finished' ? 'success' : 'danger'
                      }>
                        {meeting.status === 'scheduled' ? 'Programada' :
                        meeting.status === 'in_progress' ? 'En curso' :
                        meeting.status === 'finished' ? 'Finalizada' : 'Cancelada'}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Actas Recientes</CardTitle>
              <Link to="/admin/minutes" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentMinutes.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay actas recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentMinutes.slice(0, 5).map((minute: any) => (
                    <Link
                      key={minute.id}
                      to={`/admin/minutes/${minute.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{minute.title}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          v{minute.version} * {formatDate(minute.updated_at)}
                        </p>
                      </div>
                      <StatusBadge status={minute.status} />
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}

function formatDate(dateStr: string) {
  return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
}

function formatDateTime(dateStr: string) {
  return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}