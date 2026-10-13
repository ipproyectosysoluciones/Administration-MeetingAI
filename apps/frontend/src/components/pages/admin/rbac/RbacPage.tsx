import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Shield, Users, MoreVertical, Edit, Trash2, ShieldCheck, X, Key, Lock, Eye } from 'lucide-react';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import type { DropdownItem } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { rbacApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { clsx } from 'clsx';

interface Role {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_system: boolean;
  is_deletable: boolean;
  organization_id: string | null;
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export default function AdminRbacPage() {
  const [roles, setRoles] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRole, setEditingRole] = useState<any>(null);
  const [deletingRole, setDeletingRole] = useState<any>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [viewingRole, setViewingRole] = useState<any>(null);
  const [assigningPermissions, setAssigningPermissions] = useState<any>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [permissionSearch, setPermissionSearch] = useState('');

  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canCreate = hasPermission('role.create');
  const canUpdate = hasPermission('role.update');
  const canDelete = hasPermission('role.delete');
  const canManagePermissions = hasPermission('role.permission.assign');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rolesResponse, permissionsResponse] = await Promise.all([
        rbacApi.listRoles(),
        rbacApi.listPermissions(),
      ]);
      setRoles(rolesResponse.items || rolesResponse);
      setPermissions(permissionsResponse.items || permissionsResponse);
    } catch (error) {
      console.error('Error fetching RBAC data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (data: any) => {
    try {
      await rbacApi.createRole(data);
      setShowCreateModal(false);
      fetchData();
    } catch (error) {
      console.error('Error creating role:', error);
    }
  };

  const handleUpdate = async (data: any) => {
    if (!editingRole) return;
    try {
      await rbacApi.updateRole(editingRole.id, data);
      setEditingRole(null);
      fetchData();
    } catch (error) {
      console.error('Error updating role:', error);
    }
  };

  const openCreateModal = () => {
    setEditingRole(null);
    setShowCreateModal(true);
  };

  const openEditModal = (role: any) => {
    setEditingRole(role);
    setShowCreateModal(true);
  };

  const openViewModal = (role: any) => {
    setViewingRole(role);
  };

  const openDeleteConfirm = (role: any) => {
    setDeletingRole(role);
    setConfirmDelete(true);
  };

  const openAssignPermissionsModal = (role: any) => {
    setAssigningPermissions(role);
    setSelectedPermissions(role.permissions || []);
  };

  const handleAssignPermissions = async () => {
    if (!assigningPermissions) return;
    try {
      await rbacApi.assignPermissions(assigningPermissions.id, selectedPermissions);
      setAssigningPermissions(null);
      setSelectedPermissions([]);
      fetchData();
    } catch (error) {
      console.error('Error assigning permissions:', error);
    }
  };

  const handleDelete = async () => {
    if (!deletingRole) return;
    try {
      await rbacApi.deleteRole(deletingRole.id);
      setConfirmDelete(false);
      setDeletingRole(null);
      fetchData();
    } catch (error) {
      console.error('Error deleting role:', error);
    }
  };

  const filteredPermissions = permissions.filter((perm: any) =>
    (perm.display_name || perm.name || '').toLowerCase().includes(permissionSearch.toLowerCase()) ||
    `${perm.resource}.${perm.action}`.toLowerCase().includes(permissionSearch.toLowerCase())
  );

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
      key: 'display_name',
      header: 'Nombre visible',
      accessor: 'display_name',
    },
    {
      key: 'type',
      header: 'Tipo',
      accessor: 'is_system',
      render: (value: boolean) => value ? <Badge variant="warning">Sistema</Badge> : <Badge variant="success">Personalizado</Badge>,
    },
    {
      key: 'deletable',
      header: 'Eliminable',
      accessor: 'is_deletable',
      render: (value: boolean) => value ? <Badge variant="success">Sí</Badge> : <Badge variant="danger">No</Badge>,
    },
    {
      key: 'permissions_count',
      header: 'Permisos',
      accessor: 'permissions',
      render: (value: string[]) => <Badge variant="info">{value.length}</Badge>,
    },
    {
      key: 'created_at',
      header: 'Creado',
      accessor: 'created_at',
      render: (value: string) => formatDate(value),
    },
    {
      key: 'actions',
      header: 'Acciones',
      accessor: 'id',
      render: (_: any, row: any) => {
        const buildItems = (): DropdownItem[] => {
          const items: DropdownItem[] = [
            { label: 'Ver', onClick: () => openViewModal(row), icon: <Eye className="w-4 h-4" /> },
            { label: 'Editar', onClick: () => openEditModal(row), icon: <Edit className="w-4 h-4" /> },
            { divider: true },
          ];
          if (canManagePermissions) {
            items.push({ label: 'Gestionar permisos', onClick: () => openAssignPermissionsModal(row), icon: <ShieldCheck className="w-4 h-4" /> });
          }
          items.push({ divider: true });
          if (row.is_deletable) {
            items.push({ label: 'Eliminar', onClick: () => openDeleteConfirm(row), icon: <Trash2 className="w-4 h-4" />, danger: true });
          }
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
    }];

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Roles y Permisos</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona los roles y permisos del sistema</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={openCreateModal}>
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Rol
            </Button>
          </div>
        </div>

        {/* Roles Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={roles}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron roles"
            />
          </CardContent>
        </Card>

        {/* Create/Edit Role Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => { setShowCreateModal(false); setEditingRole(null); }}
          title={editingRole ? 'Editar Rol' : 'Nuevo Rol'}
          size="lg"
        >
          <RoleForm
            initialData={editingRole}
            onSubmit={editingRole ? handleUpdate : handleCreate}
            onClose={() => { setShowCreateModal(false); setEditingRole(null); }}
            loading={loading}
          />
        </Modal>

        {/* View Role Modal */}
        <Modal
          isOpen={!!viewingRole}
          onClose={() => setViewingRole(null)}
          title={viewingRole?.display_name || 'Detalle del Rol'}
          size="lg"
        >
          {viewingRole && (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                    <Shield className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{viewingRole.display_name}</h3>
                    <p className="text-gray-500 dark:text-gray-400">{viewingRole.name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {viewingRole.is_system && <Badge variant="warning">Sistema</Badge>}
                  <Badge variant={viewingRole.is_deletable ? 'success' : 'danger'}>
                    {viewingRole.is_deletable ? 'Eliminable' : 'No eliminable'}
                  </Badge>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">ID</p>
                  <p className="font-mono text-sm">{viewingRole.id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Creado</p>
                  <p className="font-medium">{formatDateTime(viewingRole.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Actualizado</p>
                  <p className="font-medium">{formatDateTime(viewingRole.updated_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Tipo</p>
                  <p className="font-medium">{viewingRole.is_system ? 'Sistema' : 'Personalizado'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Eliminable</p>
                  <p className="font-medium">{viewingRole.is_deletable ? 'Sí' : 'No'}</p>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium">Permisos asignados ({viewingRole.permissions?.length || 0})</h4>
                  {canManagePermissions && (
                    <Button variant="outline" size="sm" onClick={() => openAssignPermissionsModal(viewingRole)}>
                      <ShieldCheck className="w-4 h-4 mr-2" />
                      Gestionar permisos
                    </Button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 max-h-60 overflow-y-auto">
                  {viewingRole.permissions?.map((perm: string) => (
                    <Badge key={perm} variant="info" className="text-xs">
                      {perm}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Modal>

        {/* Assign Permissions Modal */}
        <Modal
          isOpen={!!assigningPermissions}
          onClose={() => { setAssigningPermissions(null); setSelectedPermissions([]); }}
          title={`Gestionar permisos: ${assigningPermissions?.display_name}`}
          size="xl"
        >
          {assigningPermissions && (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium">Permisos disponibles</h4>
                <div className="flex items-center gap-2">
                  <Input
                    placeholder="Buscar permisos..."
                    value={permissionSearch}
                    onChange={(e) => setPermissionSearch(e.target.value)}
                    className="w-64"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-[50vh] overflow-y-auto">
                {filteredPermissions.map((perm: any) => {
                  const isSelected = selectedPermissions.includes(perm.name);
                  return (
                    <label
                      key={perm.id}
                      className={clsx(
                        'flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors',
                        'hover:bg-gray-50 dark:hover:bg-gray-800/50',
                        isSelected ? 'bg-primary-50 border-primary-200 dark:bg-primary-900/30 dark:border-primary-700' : 'border-gray-200 dark:border-gray-700'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {
                          if (isSelected) {
                            setSelectedPermissions(prev => prev.filter(p => p !== perm.name));
                          } else {
                            setSelectedPermissions(prev => [...prev, perm.name]);
                          }
                        }}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 dark:text-white truncate">{perm.display_name || perm.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{perm.resource}.{perm.action}</p>
                      </div>
                    </label>
                  );
                })}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="secondary" onClick={() => { setAssigningPermissions(null); setSelectedPermissions([]); }}>
                  Cancelar
                </Button>
                <Button variant="primary" onClick={handleAssignPermissions} disabled={selectedPermissions.length === 0}>
                  Guardar cambios ({selectedPermissions.length})
                </Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingRole(null); }}
          onConfirm={handleDelete}
          title="Eliminar Rol"
          message={`¿Estás seguro de que quieres eliminar el rol "${deletingRole?.display_name}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          variant="danger"
        />
      </div>
    </AdminLayout>
  );
}

function RoleForm({ initialData, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    name: initialData?.name || '',
    display_name: initialData?.display_name || '',
    description: initialData?.description || '',
    is_system: false,
    is_deletable: true,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="name" className="label">Nombre interno *</label>
        <input
          type="text"
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          required
          disabled={!!initialData}
          className="input"
          placeholder="nombre_interno"
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Solo letras, números y guiones bajos. No se puede cambiar después.</p>
      </div>

      <div>
        <label htmlFor="display_name" className="label">Nombre visible *</label>
        <input
          type="text"
          id="display_name"
          name="display_name"
          value={formData.display_name}
          onChange={handleChange}
          required
          className="input"
          placeholder="Nombre visible del rol"
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
          placeholder="Descripción del rol..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="is_deletable"
            name="is_deletable"
            checked={formData.is_deletable}
            onChange={(e) => setFormData(prev => ({ ...prev, is_deletable: e.target.checked }))}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <label htmlFor="is_deletable" className="text-sm text-gray-700 dark:text-gray-300">
            Eliminable (puede ser borrado)
          </label>
        </div>
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