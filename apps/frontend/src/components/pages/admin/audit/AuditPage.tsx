import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Filter, FileText, Download, MoreVertical, Calendar, Filter as FilterIcon, ChevronLeft, ChevronRight } from 'lucide-react';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal } from '@/components/ui/Modal';
import { auditApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface AuditEvent {
  id: string;
  actor_user_id: string;
  actor_name: string;
  actor_email: string;
  tenant_id: string;
  action: string;
  resource: string;
  resource_id: string | null;
  ip: string | null;
  user_agent: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
}

export default function AdminAuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewingEvent, setViewingEvent] = useState<any>(null);

  const { hasPermission } = useAuthStore();

  const canExport = hasPermission('audit.export');

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const response = await auditApi.list({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        resource: resourceFilter || undefined,
        actor_id: actorFilter || undefined,
        start_date: dateFrom || undefined,
        end_date: dateTo || undefined,
      });
      setEvents(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching audit events:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [page, pageSize, search, actionFilter, resourceFilter, actorFilter, dateFrom, dateTo]);

  const handleExport = async () => {
    try {
      const blob = await auditApi.export({
        format: 'csv',
        start_date: dateFrom || undefined,
        end_date: dateTo || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-export-${format(new Date(), 'yyyy-MM-dd')}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting audit:', error);
    }
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm:ss', { locale: es });
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const columns = [
    {
      key: 'created_at',
      header: 'Fecha y Hora',
      accessor: 'created_at',
      render: (value: string) => formatDateTime(value),
      width: '160px',
    },
    {
      key: 'actor',
      header: 'Actor',
      accessor: 'actor_name',
      render: (value: string, row: any) => (
        <div>
          <div className="font-medium">{row.actor_name}</div>
          <div className="text-sm text-gray-500 dark:text-gray-400">{row.actor_email}</div>
        </div>
      ),
    },
    {
      key: 'action',
      header: 'Acción',
      accessor: 'action',
      render: (value: string) => (
        <Badge variant="info" className="text-xs">{value}</Badge>
      ),
    },
    {
      key: 'resource',
      header: 'Recurso',
      accessor: 'resource',
      render: (value: string, row: any) => (
        <div>
          <div className="font-medium">{value}</div>
          {row.resource_id && <div className="text-sm text-gray-500 dark:text-gray-400">{row.resource_id}</div>}
        </div>
      ),
    },
    {
      key: 'ip',
      header: 'IP',
      accessor: 'ip',
      render: (value: string | null) => value ? <span className="font-mono text-sm">{value}</span> : '-',
    },
    {
      key: 'details',
      header: 'Detalles',
      accessor: 'metadata_json',
      render: (value: any) => (
        <button
          onClick={() => setViewingEvent({ metadata_json: value })}
          className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 text-sm underline"
        >
          Ver detalles
        </button>
      ),
    },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Auditoría</h1>
            <p className="text-gray-600 dark:text-gray-400">Registro de eventos y acciones del sistema</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleExport} disabled={!canExport}>
              <Download className="w-4 h-4 mr-2" />
              Exportar CSV
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex-1">
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar en metadatos..."
                />
              </div>
              <Select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todas las acciones' },
                  { value: 'auth.login', label: 'Login' },
                  { value: 'auth.register', label: 'Registro' },
                  { value: 'meeting.create', label: 'Crear reunión' },
                  { value: 'minutes.create', label: 'Crear acta' },
                  { value: 'minutes.approve', label: 'Aprobar acta' },
                  { value: 'minutes.publish', label: 'Publicar acta' },
                  { value: 'document.upload', label: 'Subir documento' },
                  { value: 'recording.upload', label: 'Subir grabación' },
                ]}
                placeholder="Filtrar por acción"
              />
              <Select
                value={resourceFilter}
                onChange={(e) => setResourceFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los recursos' },
                  { value: 'user', label: 'Usuario' },
                  { value: 'meeting', label: 'Reunión' },
                  { value: 'minutes', label: 'Acta' },
                  { value: 'document', label: 'Documento' },
                  { value: 'recording', label: 'Grabación' },
                  { value: 'transcription', label: 'Transcripción' },
                  { value: 'organization', label: 'Organización' },
                ]}
                placeholder="Filtrar por recurso"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Input
                type="date"
                label="Fecha desde"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
              <Input
                type="date"
                label="Fecha hasta"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
              <Input
                label="Actor (email/ID)"
                value={actorFilter}
                onChange={(e) => setActorFilter(e.target.value)}
                placeholder="actor@ejemplo.com"
              />
              <div className="flex items-end">
                <Button variant="outline" onClick={() => {
                  setActionFilter('');
                  setResourceFilter('');
                  setActorFilter('');
                  setDateFrom('');
                  setDateTo('');
                  setSearch('');
                }}>
                  <FilterIcon className="w-4 h-4 mr-2" />
                  Limpiar filtros
                </Button>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar en metadatos..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select
                value={String(pageSize)}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                options={[
                  { value: '25', label: '25 por página' },
                  { value: '50', label: '50 por página' },
                  { value: '100', label: '100 por página' },
                  { value: '200', label: '200 por página' },
                ]}
                placeholder="Por página"
              />
            </div>
          </CardContent>
        </Card>

        {/* Audit Events Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={events}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron eventos de auditoría"
            />
            {total > 0 && (
              <Pagination
                currentPage={page}
                totalPages={Math.ceil(total / pageSize)}
                totalItems={total}
                pageSize={pageSize}
                onPageChange={setPage}
                onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
              />
            )}
          </CardContent>
        </Card>

        {/* Event Detail Modal */}
        <Modal
          isOpen={!!viewingEvent}
          onClose={() => setViewingEvent(null)}
          title="Detalles del Evento de Auditoría"
          size="xl"
        >
          {viewingEvent && (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">ID</p>
                  <p className="font-mono text-sm">{viewingEvent.id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Fecha y Hora</p>
                  <p className="font-medium">{formatDateTime(viewingEvent.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Acción</p>
                  <p className="font-medium">{viewingEvent.action}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Recurso</p>
                  <p className="font-medium">{viewingEvent.resource}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Recurso ID</p>
                  <p className="font-mono text-sm">{viewingEvent.resource_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Actor</p>
                  <p className="font-medium">{viewingEvent.actor_name} ({viewingEvent.actor_email})</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">IP</p>
                  <p className="font-mono text-sm">{viewingEvent.ip || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">User Agent</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">{viewingEvent.user_agent || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Fecha</p>
                  <p className="font-medium">{formatDateTime(viewingEvent.created_at)}</p>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <h4 className="font-medium mb-3">Metadatos completos</h4>
                <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg text-xs overflow-x-auto max-h-64 overflow-y-auto">
                  {JSON.stringify(viewingEvent.metadata_json, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </AdminLayout>
  );
}

function formatDate(dateStr: string) {
  return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
}

function formatDateTime(dateStr: string) {
  return format(new Date(dateStr), 'dd/MM/yyyy HH:mm:ss', { locale: es });
}