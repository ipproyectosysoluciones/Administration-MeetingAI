import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Calendar, Users, MoreVertical, Edit, Trash2, Eye, Download, Clock, MapPin, UserCheck } from 'lucide-react';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { meetingsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface Meeting {
  id: string;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  location: string | null;
  modality: 'in_person' | 'virtual' | 'hybrid';
  status: 'scheduled' | 'in_progress' | 'finished' | 'cancelled';
  organization_id: string;
  created_at: string;
  updated_at: string;
}

const modalityLabels: Record<string, string> = {
  in_person: 'Presencial',
  virtual: 'Virtual',
  hybrid: 'Híbrida',
};

const modalityIcons: Record<string, React.ReactNode> = {
  in_person: <MapPin className="w-4 h-4" />,
  virtual: <Users className="w-4 h-4" />,
  hybrid: <div className="flex gap-1"><MapPin className="w-4 h-4" /><Users className="w-4 h-4" /></div>,
};

export default function MeetingsPage() {
  const navigate = useNavigate();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingMeeting, setEditingMeeting] = useState<Meeting | null>(null);
  const [deletingMeeting, setDeletingMeeting] = useState<Meeting | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { hasPermission } = useAuthStore();

  const canCreate = hasPermission('meeting.create');
  const canUpdate = hasPermission('meeting.update');
  const canDelete = hasPermission('meeting.delete');
  const canManageParticipants = hasPermission('meeting.participant_manage');

  const fetchMeetings = async () => {
    setLoading(true);
    try {
      const response = await meetingsApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        q: search || undefined,
      });
      setMeetings(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching meetings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, [page, pageSize, search, statusFilter]);

  const handleCreate = async (data: any) => {
    try {
      await meetingsApi.create(data);
      setShowCreateModal(false);
      fetchMeetings();
    } catch (error) {
      console.error('Error creating meeting:', error);
    }
  };

  const handleUpdate = async (data: any) => {
    if (!editingMeeting) return;
    try {
      await meetingsApi.update(editingMeeting.id, data);
      setEditingMeeting(null);
      fetchMeetings();
    } catch (error) {
      console.error('Error updating meeting:', error);
    }
  };

  const handleDelete = async () => {
    if (!deletingMeeting) return;
    try {
      await meetingsApi.cancel(deletingMeeting.id);
      setDeletingMeeting(null);
      setConfirmDelete(false);
      fetchMeetings();
    } catch (error) {
      console.error('Error deleting meeting:', error);
    }
  };

  const openCreateModal = () => {
    setEditingMeeting(null);
    setShowCreateModal(true);
  };

  const openEditModal = (meeting: Meeting) => {
    setEditingMeeting(meeting);
    setShowCreateModal(true);
  };

  const openDeleteConfirm = (meeting: Meeting) => {
    setDeletingMeeting(meeting);
    setConfirmDelete(true);
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const getStatusBadge = (status: string) => {
    return <StatusBadge status={status} />;
  };

  const columns = [
    {
      key: 'title',
      header: 'Título',
      accessor: 'title',
    },
    {
      key: 'date',
      header: 'Fecha',
      accessor: (row: any) => (
        <div>
          <div className="font-medium">{formatDate(row.starts_at)}</div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {formatDateTime(row.starts_at)} - {formatDateTime(row.ends_at)}
          </div>
        </div>
      ),
    },
    {
      key: 'modality',
      header: 'Modalidad',
      accessor: 'modality',
      render: (value: string) => (
        <span className="inline-flex items-center gap-1">
          {modalityIcons[value]}
          <span>{modalityLabels[value]}</span>
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Estado',
      accessor: 'status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: 'actions',
      header: 'Acciones',
      accessor: 'id',
      render: (_: any, row: any) => (
        <Dropdown
          trigger={
            <button className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <MoreVertical className="w-5 h-5" />
            </button>
          }
          items={[
            { label: 'Ver', onClick: () => navigate(`/portal/meetings/${row.id}`), icon: <Eye className="w-4 h-4" /> },
            canUpdate && { label: 'Editar', onClick: () => openEditModal(row), icon: <Edit className="w-4 h-4" /> },
            canManageParticipants && { label: 'Participantes', onClick: () => navigate(`/portal/meetings/${row.id}/participants`), icon: <UserCheck className="w-4 h-4" /> },
            { divider: true },
            canDelete && { label: 'Cancelar', onClick: () => openDeleteConfirm(row), icon: <Trash2 className="w-4 h-4" />, danger: true },
          ]}
        />
      ),
    },
  ];

  return (
    <PortalLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Reuniones</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona las reuniones de tu organización</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={openCreateModal}>
              <Plus className="w-4 h-4 mr-2" />
              Nueva Reunión
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar reuniones..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los estados' },
                  { value: 'scheduled', label: 'Programada' },
                  { value: 'in_progress', label: 'En curso' },
                  { value: 'finished', label: 'Finalizada' },
                  { value: 'cancelled', label: 'Cancelada' },
                ]}
                placeholder="Filtrar por estado"
              />
              <Select
                value={String(pageSize)}
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

        {/* Meetings Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={meetings}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron reuniones"
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
          onClose={() => { setShowCreateModal(false); setEditingMeeting(null); }}
          title={editingMeeting ? 'Editar Reunión' : 'Nueva Reunión'}
          size="lg"
        >
          <MeetingForm
            initialData={editingMeeting}
            onSubmit={editingMeeting ? handleUpdate : handleCreate}
            onClose={() => { setShowCreateModal(false); setEditingMeeting(null); }}
            loading={loading}
          />
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingMeeting(null); }}
          onConfirm={handleDelete}
          title="Cancelar Reunión"
          message={`¿Estás seguro de que quieres cancelar la reunión "${deletingMeeting?.title}"? Esta acción no se puede deshacer.`}
          confirmText="Cancelar Reunión"
          cancelText="Mantener"
          variant="danger"
        />
      </div>
    </PortalLayout>
  );
}

function MeetingForm({ initialData, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    description: initialData?.description || '',
    starts_at: initialData?.starts_at ? new Date(initialData.starts_at).toISOString().slice(0, 16) : '',
    ends_at: initialData?.ends_at ? new Date(initialData.ends_at).toISOString().slice(0, 16) : '',
    location: initialData?.location || '',
    modality: initialData?.modality || 'in_person',
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
          placeholder="Título de la reunión"
        />
      </div>

      <div>
        <label htmlFor="description" className="label">Descripción</label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          className="input min-h-[100px] resize-y"
          placeholder="Descripción de la reunión..."
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="starts_at" className="label">Fecha y hora de inicio *</label>
          <input
            type="datetime-local"
            id="starts_at"
            name="starts_at"
            value={formData.starts_at}
            onChange={handleChange}
            required
            className="input"
          />
        </div>
        <div>
          <label htmlFor="ends_at" className="label">Fecha y hora de fin *</label>
          <input
            type="datetime-local"
            id="ends_at"
            name="ends_at"
            value={formData.ends_at}
            onChange={handleChange}
            required
            className="input"
          />
        </div>
      </div>

      <div>
        <label htmlFor="location" className="label">Ubicación</label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location}
          onChange={handleChange}
          className="input"
          placeholder="Dirección o enlace de videoconferencia"
        />
      </div>

      <div>
        <label htmlFor="modality" className="label">Modalidad *</label>
        <select
          id="modality"
          name="modality"
          value={formData.modality}
          onChange={handleChange}
          required
          className="input"
        >
          <option value="in_person">Presencial</option>
          <option value="virtual">Virtual</option>
          <option value="hybrid">Híbrida</option>
        </select>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button type="button" onClick={onClose} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Guardando...' : initialData ? 'Actualizar' : 'Crear'}
        </button>
      </div>
    </form>
  );
}