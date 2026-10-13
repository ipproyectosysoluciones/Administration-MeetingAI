import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, FileText, Eye, Edit, MoreVertical, Clock, Download, AlertCircle, CheckCircle, XCircle, Loader2, Trash2 } from 'lucide-react';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { meetingsApi, minutesApi, transcriptionsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { MinutesService } from '@/lib/minutes';

interface Minute {
  id: string;
  meeting_id: string;
  meeting_title: string;
  title: string;
  content: string;
  version: number;
  status: 'draft' | 'review' | 'approved' | 'published' | 'archived';
  created_by: string;
  created_by_name: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  published_by: string | null;
  published_at: string | null;
  archived_at: string | null;
  ai_provider: string | null;
  ai_model: string | null;
  ai_request_id: string | null;
  created_at: string;
  updated_at: string;
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  review: 'En Revisión',
  approved: 'Aprobado',
  published: 'Publicado',
  archived: 'Archivado',
};

export default function MinutesPage() {
  const [minutes, setMinutes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generatingMeeting, setGeneratingMeeting] = useState<any>(null);
  const [viewingMinute, setViewingMinute] = useState<any>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deletingMinute, setDeletingMinute] = useState<any>(null);

  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canCreate = hasPermission('minutes.write');
  const canUpdate = hasPermission('minutes.write');
  const canApprove = hasPermission('minutes.approve');
  const canPublish = hasPermission('minutes.publish');
  const canRead = hasPermission('minutes.read');

  const fetchMinutes = async () => {
    setLoading(true);
    try {
      const response = await minutesApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        q: search || undefined,
      });
      setMinutes(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching minutes:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMinutes();
  }, [page, pageSize, search, statusFilter]);

  const handleGenerate = async (meetingId: string) => {
    try {
      await minutesApi.generate(meetingId);
      setShowGenerateModal(false);
      fetchMinutes();
    } catch (error) {
      console.error('Error generating minutes:', error);
    }
  };

  const handleApprove = async (minuteId: string) => {
    try {
      await minutesApi.approve(minuteId);
      fetchMinutes();
    } catch (error) {
      console.error('Error approving minutes:', error);
    }
  };

  const handlePublish = async (minuteId: string) => {
    try {
      await minutesApi.publish(minuteId);
      fetchMinutes();
    } catch (error) {
      console.error('Error publishing minutes:', error);
    }
  };

  const handleArchive = async (minuteId: string) => {
    try {
      await minutesApi.archive(minuteId);
      fetchMinutes();
    } catch (error) {
      console.error('Error archiving minutes:', error);
    }
  };

  const handleDelete = async () => {
    if (!deletingMinute) return;
    try {
      await minutesApi.delete(deletingMinute.id);
      setConfirmDelete(false);
      setDeletingMinute(null);
      fetchMinutes();
    } catch (error) {
      console.error('Error deleting minutes:', error);
    }
  };

  const openGenerateModal = (meeting: any) => {
    setGeneratingMeeting(meeting);
    setShowGenerateModal(true);
  };

  const openViewModal = (minute: any) => {
    setViewingMinute(minute);
  };

  const openDeleteConfirm = (minute: any) => {
    setDeletingMinute(minute);
    setConfirmDelete(true);
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const columns = [
    {
      key: 'title',
      header: 'Título',
      accessor: 'title',
    },
    {
      key: 'meeting',
      header: 'Reunión',
      accessor: 'meeting_title',
    },
    {
      key: 'version',
      header: 'Versión',
      accessor: 'version',
    },
    {
      key: 'status',
      header: 'Estado',
      accessor: 'status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: 'created_at',
      header: 'Creado',
      accessor: 'created_at',
      render: (value: string) => formatDate(value),
    },
    {
      key: 'updated_at',
      header: 'Actualizado',
      accessor: 'updated_at',
      render: (value: string) => formatDate(value),
    },
    {
      key: 'actions',
      header: 'Acciones',
      accessor: 'id',
      render: (_: any, row: any) => {
        const buildItems = () => {
          const items = [
            { label: 'Ver', onClick: () => openViewModal(row), icon: <Eye className="w-4 h-4" /> },
            { label: 'Historial de versiones', onClick: () => navigate(`/portal/minutes/${row.id}/versions`), icon: <Clock className="w-4 h-4" /> },
            { divider: true },
            { label: 'Generar desde transcripción', onClick: () => openGenerateModal(row), icon: <FileText className="w-4 h-4" />, disabled: !row.meeting_id },
            { divider: true },
          ];
          
          if (row.status === 'draft') {
            items.push({ label: 'Enviar a revisión', onClick: () => {}, icon: <AlertCircle className="w-4 h-4" /> });
          } else if (row.status === 'review') {
            items.push({ label: 'Aprobar', onClick: () => handleApprove(row.id), icon: <CheckCircle className="w-4 h-4" /> });
          } else if (row.status === 'approved') {
            items.push({ label: 'Publicar', onClick: () => handlePublish(row.id), icon: <Download className="w-4 h-4" /> });
          } else if (row.status === 'published') {
            items.push({ label: 'Archivar', onClick: () => handleArchive(row.id), icon: <XCircle className="w-4 h-4" /> });
          }
          
          items.push({ divider: true });
          items.push({ label: 'Eliminar', onClick: () => openDeleteConfirm(row), icon: <Trash2 className="w-4 h-4" />, danger: true });
          
          return items;
        };
        
        return (
          <Dropdown
            trigger={
              <button className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                <MoreVertical className="w-5 h-5" />
              </button>
            }
            items={buildItems()}
          />
        );
      },
    },
  ];

  return (
    <PortalLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Actas</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona las actas de reuniones</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={() => { setEditingMinute(null); setShowCreateModal(true); }}>
              <Plus className="w-4 h-4 mr-2" />
              Nueva Acta
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar actas..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar por título..."
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los estados' },
                  { value: 'draft', label: 'Borrador' },
                  { value: 'review', label: 'En Revisión' },
                  { value: 'approved', label: 'Aprobado' },
                  { value: 'published', label: 'Publicado' },
                  { value: 'archived', label: 'Archivado' },
                ]}
                placeholder="Filtrar por estado"
              />
              <Select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                options={[
                  { value: '10', label: '10 por página' },
                  { value: '20', label: '20 por página' },
                  { value: '50', label: '50 por página' },
                  { value: '100', label: '100 por página' },
                ]}
                placeholder="Por página"
              />
            </div>
          </CardContent>
        </Card>

        {/* Minutes Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={minutes}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron actas"
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

        {/* Create/Edit Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => { setShowCreateModal(false); setEditingMinute(null); }}
          title={editingMinute ? 'Editar Acta' : 'Nueva Acta'}
          size="lg"
        >
          <MinuteForm
            initialData={editingMinute}
            onSubmit={editingMinute ? handleUpdate : handleCreate}
            onClose={() => { setShowCreateModal(false); setEditingMinute(null); }}
            loading={loading}
          />
        </Modal>

        {/* Generate Modal */}
        <Modal
          isOpen={showGenerateModal}
          onClose={() => { setShowGenerateModal(false); setGeneratingMeeting(null); }}
          title="Generar Acta desde Transcripción"
          size="md"
        >
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-400">
              Se generará un borrador de acta basado en la transcripción de la reunión seleccionada.
            </p>
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="secondary" onClick={() => { setShowGenerateModal(false); setGeneratingMeeting(null); }}>
                Cancelar
              </Button>
              <Button variant="primary" onClick={() => handleGenerate(generatingMeeting.id)} loading={loading}>
                Generar Borrador
              </Button>
            </div>
          </div>
        </Modal>

        {/* View Modal */}
        <Modal
          isOpen={!!viewingMinute}
          onClose={() => setViewingMinute(null)}
          title={viewingMinute?.title}
          size="xl"
        >
          {viewingMinute && (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <StatusBadge status={viewingMinute.status} />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  v{viewingMinute.version} • {formatDate(viewingMinute.updated_at)}
                </span>
              </div>
              <div className="prose dark:prose-invert max-w-none">
                <div dangerouslySetInnerHTML={{ __html: viewingMinute.content }} />
              </div>
            </div>
          )}
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingMinute(null); }}
          onConfirm={handleDelete}
          title="Eliminar Acta"
          message={`¿Estás seguro de que quieres eliminar la acta "${deletingMinute?.title}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          variant="danger"
        />
      </div>
    </PortalLayout>
  );
}

function MinuteForm({ initialData, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    content: initialData?.content || '',
    meeting_id: initialData?.meeting_id || '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="title" className="label">Título *</label>
        <input
          type="text"
          id="title"
          name="title"
          value={formData.title}
          onChange={handleChange}
          required
          className="input"
          placeholder="Título del acta"
        />
      </div>

      <div>
        <label htmlFor="content" className="label">Contenido *</label>
        <textarea
          id="content"
          name="content"
          value={formData.content}
          onChange={handleChange}
          required
          className="input min-h-[200px] resize-y"
          placeholder="Contenido del acta (HTML permitido)..."
        />
      </div>

      <div>
        <label htmlFor="meeting_id" className="label">Reunión asociada</label>
        <select
          id="meeting_id"
          name="meeting_id"
          value={formData.meeting_id}
          onChange={handleChange}
          className="input"
        >
          <option value="">Seleccionar reunión (opcional)</option>
        </select>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button type="button" onClick={onClose} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </form>
  );
}