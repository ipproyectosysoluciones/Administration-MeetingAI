import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Building, Users, MoreVertical, Edit, Trash2, Edit3, Shield, X } from 'lucide-react';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { organizationsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  settings: Record<string, any>;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export default function AdminOrganizationsPage() {
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingOrg, setEditingOrg] = useState<any>(null);
  const [deletingOrg, setDeletingOrg] = useState<any>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [viewingOrg, setViewingOrg] = useState<any>(null);

  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canCreate = hasPermission('organization.create');
  const canUpdate = hasPermission('organization.update');
  const canDelete = hasPermission('organization.delete');

  const fetchOrganizations = async () => {
    setLoading(true);
    try {
      const response = await organizationsApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setOrganizations(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, [page, pageSize, search, statusFilter]);

  const handleCreate = async (data: any) => {
    try {
      await organizationsApi.create(data);
      setShowCreateModal(false);
      fetchOrganizations();
    } catch (error) {
      console.error('Error creating organization:', error);
    }
  };

  const handleUpdate = async (data: any) => {
    if (!editingOrg) return;
    try {
      await organizationsApi.update(editingOrg.id, data);
      setEditingOrg(null);
      fetchOrganizations();
    } catch (error) {
      console.error('Error updating organization:', error);
    }
  };

  const openCreateModal = () => {
    setEditingOrg(null);
    setShowCreateModal(true);
  };

  const openEditModal = (org: any) => {
    setEditingOrg(org);
    setShowCreateModal(true);
  };

  const openViewModal = (org: any) => {
    setViewingOrg(org);
  };

  const openDeleteConfirm = (org: any) => {
    setDeletingOrg(org);
    setConfirmDelete(true);
  };

  const handleDelete = async () => {
    if (!deletingOrg) return;
    try {
      await organizationsApi.delete(deletingOrg.id);
      setConfirmDelete(false);
      setDeletingOrg(null);
      fetchOrganizations();
    } catch (error) {
      console.error('Error deleting organization:', error);
    }
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
  };

  const columns = [
    {
      key: 'name',
      header: 'Nombre',
      accessor: 'name',
    },
    {
      key: 'slug',
      header: 'Slug',
      accessor: 'slug',
    },
    {
      key: 'status',
      header: 'Estado',
      accessor: 'deleted_at',
      render: (value: string | null) => value ? <Badge variant="danger">Eliminada</Badge> : <Badge variant="success">Activa</Badge>,
    },
    {
      key: 'created_at',
      header: 'Creada',
      accessor: 'created_at',
      render: (value: string) => formatDate(value),
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
            { label: 'Ver', onClick: () => openViewModal(row), icon: <Eye className="w-4 h-4" /> },
            { label: 'Editar', onClick: () => openEditModal(row), icon: <Edit className="w-4 h-4" /> },
            { divider: true },
            { label: 'Eliminar', onClick: () => openDeleteConfirm(row), icon: <Trash2 className="w-4 h-4" />, danger: true },
          ]}
        />
      ),
    },
  ];


  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Organizaciones</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona las organizaciones de la plataforma</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={openCreateModal}>
              <Plus className="w-4 h-4 mr-2" />
              Nueva Organización
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar organizaciones..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los estados' },
                  { value: 'active', label: 'Activas' },
                  { value: 'deleted', label: 'Eliminadas' },
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

        {/* Organizations Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={organizations}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron organizaciones"
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
          onClose={() => { setShowCreateModal(false); setEditingOrg(null); }}
          title={editingOrg ? 'Editar Organización' : 'Nueva Organización'}
          size="lg"
        >
          <OrgForm
            initialData={editingOrg}
            onSubmit={editingOrg ? handleUpdate : handleCreate}
            onClose={() => { setShowCreateModal(false); setEditingOrg(null); }}
            loading={loading}
          />
        </Modal>

        {/* View Modal */}
        <Modal
          isOpen={!!viewingOrg}
          onClose={() => setViewingOrg(null)}
          title={viewingOrg?.name}
          size="lg"
        >
          {viewingOrg && (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                    <Building className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{viewingOrg.name}</h3>
                    <p className="text-gray-500 dark:text-gray-400">{viewingOrg.slug}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {viewingOrg.deleted_at ? <Badge variant="danger">Eliminada</Badge> : <Badge variant="success">Activa</Badge>}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">ID</p>
                  <p className="font-mono text-sm">{viewingOrg.id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Slug</p>
                  <p className="font-medium">{viewingOrg.slug}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Creada</p>
                  <p className="font-medium">{formatDateTime(viewingOrg.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Actualizada</p>
                  <p className="font-medium">{formatDateTime(viewingOrg.updated_at)}</p>
                </div>
              </div>

              {viewingOrg.description && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="font-medium mb-3">Descripción</h4>
                  <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{viewingOrg.description}</p>
                </div>
              )}
            </div>
          )}
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingOrg(null); }}
          onConfirm={handleDelete}
          title="Eliminar Organización"
          message={`¿Estás seguro de que quieres eliminar la organización "${deletingOrg?.name}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          variant="danger"
        />
      </div>
    </AdminLayout>
  );
}

function OrgForm({ initialData, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    name: initialData?.name || '',
    slug: initialData?.slug || '',
    description: initialData?.description || '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, slug: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="name" className="label">Nombre *</label>
        <input
          type="text"
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          required
          className="input"
          placeholder="Nombre de la organización"
        />
      </div>

      <div>
        <label htmlFor="slug" className="label">Slug *</label>
        <input
          type="text"
          id="slug"
          name="slug"
          value={formData.slug}
          onChange={handleSlugChange}
          required
          className="input"
          placeholder="mi-organizacion"
          pattern="[a-z0-9-]+"
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Solo letras minúsculas, números y guiones</p>
      </div>

      <div>
        <label htmlFor="description" className="label">Descripción</label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          className="input min-h-[100px] resize-y"
          placeholder="Descripción de la organización..."
        />
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