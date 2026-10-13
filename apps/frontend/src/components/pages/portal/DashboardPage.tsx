import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Calendar, Users, FileText, Settings, TrendingUp, Clock, CheckCircle, AlertCircle, XCircle, Loader2, BarChart3, FileText as FileTextIcon, Users as UsersIcon, Calendar as CalendarIcon, Mic, Archive } from 'lucide-react';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { meetingsApi, minutesApi, documentsApi, recordingsApi, transcriptionsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface Stats {
  totalMeetings: number;
  upcomingMeetings: number;
  totalMinutes: number;
  pendingMinutes: number;
  totalDocuments: number;
  pendingOcr: number;
  totalRecordings: number;
  pendingTranscriptions: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [upcomingMeetings, setUpcomingMeetings] = useState<any[]>([]);
  const [recentMinutes, setRecentMinutes] = useState<any[]>([]);
  const [recentDocuments, setRecentDocuments] = useState<any[]>([]);
  const [recentRecordings, setRecentRecordings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canCreateMeeting = hasPermission('meeting.create');
  const canCreateMinute = hasPermission('minutes.write');
  const canUploadDocument = hasPermission('document.upload');
  const canUploadRecording = hasPermission('recording.upload');

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch stats
      const [
        meetingsResponse,
        minutesResponse,
        documentsResponse,
        recordingsResponse,
        transcriptionsResponse,
      ] = await Promise.all([
        meetingsApi.list({ page_size: 100 }),
        minutesApi.list({ page_size: 100 }),
        documentsApi.list({ page_size: 100 }),
        recordingsApi.list({ page_size: 100 }),
        transcriptionsApi.list({ page_size: 100 }),
      ]);

      setStats({
        totalMeetings: meetingsResponse.total,
        upcomingMeetings: meetingsResponse.items.filter((m: any) => m.status === 'scheduled').length,
        totalMinutes: minutesResponse.total,
        pendingMinutes: minutesResponse.items.filter((m: any) => m.status === 'review').length,
        totalDocuments: documentsResponse.total,
        pendingOcr: documentsResponse.items.filter((d: any) => d.ocr_status === 'pending' || d.ocr_status === 'processing').length,
        totalRecordings: recordingsResponse.total,
        pendingTranscriptions: transcriptionsResponse.items.filter((t: any) => t.status === 'pending' || t.status === 'processing').length,
      });

      // Fetch recent items
      const [
        upcomingMeetingsResponse,
        recentMinutesResponse,
        recentDocumentsResponse,
        recentRecordingsResponse,
      ] = await Promise.all([
        meetingsApi.list({ page_size: 5, status: 'scheduled' }),
        minutesApi.list({ page_size: 5, status: 'draft' }),
        documentsApi.list({ page_size: 5 }),
        recordingsApi.list({ page_size: 5 }),
      ]);

      setUpcomingMeetings(upcomingMeetingsResponse.items);
      setRecentMinutes(recentMinutesResponse.items);
      setRecentDocuments(recentDocumentsResponse.items);
      setRecentRecordings(recentRecordingsResponse.items);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
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
      <PortalLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <svg className="w-12 h-12 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-gray-600 dark:text-gray-400">Cargando dashboard...</p>
          </div>
        </div>
      </PortalLayout>
    );
  }

  const quickActions = [
    {
      label: 'Nueva Reunión',
      icon: Plus,
      href: '/portal/meetings/new',
      permission: 'meeting.create',
      color: 'bg-primary-600 hover:bg-primary-700',
      iconColor: 'text-primary-600',
    },
    {
      label: 'Subir Documento',
      icon: Upload,
      href: '/portal/documents/upload',
      permission: 'document.upload',
      color: 'bg-green-600 hover:bg-green-700',
      iconColor: 'text-green-600',
    },
    {
      label: 'Subir Grabación',
      icon: Upload,
      href: '/portal/recordings/upload',
      permission: 'recording.upload',
      color: 'bg-purple-600 hover:bg-purple-700',
      iconColor: 'text-purple-600',
    },
    {
      label: 'Nueva Acta',
      icon: FileTextIcon,
      href: '/portal/minutes/new',
      permission: 'minutes.write',
      color: 'bg-blue-600 hover:bg-blue-700',
      iconColor: 'text-blue-600',
    },
    {
      label: 'Nueva Reunión',
      icon: Plus,
      href: '/portal/meetings/new',
      permission: 'meeting.create',
      color: 'bg-primary-600 hover:bg-primary-700',
      iconColor: 'text-primary-600',
    },
  ].filter(action => hasPermission(action.permission));

  return (
    <PortalLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400">Bienvenido a tu panel de control</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                <CalendarIcon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Reuniones Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalMeetings || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Próximas Reuniones</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.upcomingMeetings || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                <FileTextIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Actas Totales</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.totalMinutes || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardContent className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                <Archive className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Actas Pendientes</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.pendingMinutes || 0}</p>
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
              <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">OCR Pendientes</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.pendingOcr || 0}</p>
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
                <p className="text-sm text-gray-500 dark:text-gray-400">Transcripciones Pendientes</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.pendingTranscriptions || 0}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        {quickActions.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Acciones Rápidas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
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
        )}

        {/* Upcoming Meetings & Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upcoming Meetings */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Próximas Reuniones</CardTitle>
              <Link to="/portal/meetings" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : upcomingMeetings.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay reuniones programadas
                </div>
              ) : (
                <div className="space-y-3">
                  {upcomingMeetings.slice(0, 5).map((meeting: any) => (
                    <Link
                      key={meeting.id}
                      to={`/portal/meetings/${meeting.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{meeting.title}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                          <CalendarIcon className="w-4 h-4" />
                          <span>{formatDateTime(meeting.starts_at)}</span>
                        </p>
                      </div>
                      <Badge variant={meeting.status === 'scheduled' ? 'info' : meeting.status === 'in_progress' ? 'warning' : 'secondary'}>
                        {meeting.status === 'scheduled' ? 'Programada' : meeting.status === 'in_progress' ? 'En curso' : meeting.status}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>

          {/* Recent Minutes */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Actas Recientes</CardTitle>
              <Link to="/portal/minutes" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
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
                      to={`/portal/minutes/${minute.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white truncate">{minute.title}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          v{minute.version} • {formatDate(minute.updated_at)}
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

        {/* Recent Documents & Recordings */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Documents */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Documentos Recientes</CardTitle>
              <Link to="/portal/documents" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todos
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentDocuments.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay documentos recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentDocuments.slice(0, 5).map((doc: any) => (
                    <Link
                      key={doc.id}
                      to={`/portal/documents/${doc.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                          <FileTextIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{doc.title}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(doc.file_size)} • {doc.type.toUpperCase()}</p>
                        </div>
                      </div>
                      <StatusBadge status={doc.ocr_status} />
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>

          {/* Recent Recordings */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Grabaciones Recientes</CardTitle>
              <Link to="/portal/recordings" className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                Ver todas
              </Link>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                </div>
              ) : recentRecordings.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No hay grabaciones recientes
                </div>
              ) : (
                <div className="space-y-3">
                  {recentRecordings.slice(0, 5).map((rec: any) => (
                    <Link
                      key={rec.id}
                      to={`/portal/recordings/${rec.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-pink-100 dark:bg-pink-900/30 rounded-lg flex items-center justify-center">
                          <Mic className="w-5 h-5 text-pink-600 dark:text-pink-400" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{rec.filename}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(rec.size_bytes)} • {formatDate(rec.created_at)}</p>
                        </div>
                      </div>
                      <StatusBadge status={rec.status} />
                    </Link>
                  ))}
                </div>
              )}

            </CardContent>
          </Card>
        </div>
      </div>
    </PortalLayout>
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