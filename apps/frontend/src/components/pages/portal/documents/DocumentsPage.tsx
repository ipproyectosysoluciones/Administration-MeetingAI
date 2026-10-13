import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Eye, Edit, Trash2, MoreVertical, Download, Upload, FileText, AlertCircle, CheckCircle, XCircle, Loader2, RotateCcw } from 'lucide-react';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { documentsApi, jobsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { clsx } from 'clsx';

interface Document {
  id: string;
  title: string;
  description: string | null;
  type: 'pdf' | 'jpg' | 'jpeg' | 'png' | 'tiff';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_path: string;
  file_size: number;
  sha256: string;
  mime_type: string;
  version: number;
  ocr_text: string | null;
  ocr_confidence: number | null;
  ocr_status: string;
  ocr_error: string | null;
  pages: number | null;
  meeting_id: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

const typeLabels: Record<string, string> = {
  pdf: 'PDF',
  jpg: 'JPG',
  jpeg: 'JPEG',
  png: 'PNG',
  tiff: 'TIFF',
};

const typeIcons: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-4 h-4 text-red-500" />,
  jpg: <FileText className="w-4 h-4 text-green-500" />,
  jpeg: <FileText className="w-4 h-4 text-green-500" />,
  png: <FileText className="w-4 h-4 text-blue-500" />,
  tiff: <FileText className="w-4 h-4 text-purple-500" />,
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [editingDocument, setEditingDocument] = useState<Document | null>(null);
  const [deletingDocument, setDeletingDocument] = useState<Document | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [ocrDocument, setOcrDocument] = useState<Document | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);

  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canCreate = hasPermission('document.upload');
  const canUpdate = hasPermission('document.update');
  const canDelete = hasPermission('document.delete');
  const canOcr = hasPermission('document.ocr');

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const response = await documentsApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
        q: search || undefined,
      });
      setDocuments(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [page, pageSize, search, statusFilter, typeFilter]);

  const handleUpload = async (file: File, metadata: any) => {
    setUploadProgress(0);
    try {
      // Simulate upload progress
      const interval = setInterval(() => {
        setUploadProgress(prev => Math.min((prev || 0) + 10, 90));
      }, 200);

      const result = await documentsApi.upload(file, metadata);
      clearInterval(interval);
      setUploadProgress(100);
      setShowUploadModal(false);
      setTimeout(() => setUploadProgress(null), 1000);
      fetchDocuments();
    } catch (error) {
      setUploadProgress(null);
      console.error('Error uploading document:', error);
    }
  };

  const handleUpdate = async (data: any) => {
    if (!editingDocument) return;
    try {
      await documentsApi.update(editingDocument.id, data);
      setEditingDocument(null);
      fetchDocuments();
    } catch (error) {
      console.error('Error updating document:', error);
    }
  };

  const handleDelete = async () => {
    if (!deletingDocument) return;
    try {
      await documentsApi.delete(deletingDocument.id);
      setConfirmDelete(false);
      setDeletingDocument(null);
      fetchDocuments();
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  const confirmOcr = async () => {
    if (!ocrDocument) return;
    await handleOcr(ocrDocument);
  };

  const handleOcr = async (document: Document) => {
    setOcrDocument(document);
    setOcrLoading(true);
    try {
      await documentsApi.triggerOcr(document.id);
      fetchDocuments();
    } catch (error) {
      console.error('Error triggering OCR:', error);
    } finally {
      setOcrLoading(false);
      setOcrDocument(null);
    }
  };

  const handleCreateVersion = async (file: File, metadata: any) => {
    if (!editingDocument) return;
    try {
      const sha256Hash = await computeSHA256(file);
      const fileSize = file.size;
      const mimeType = file.type;

      await documentsApi.createVersion(editingDocument.id, {
        file_path: `mock/${sha256Hash}`,
        file_size: fileSize,
        sha256: sha256Hash,
        ocr_text: metadata.ocr_text,
        ocr_confidence: metadata.ocr_confidence,
        ocr_status: metadata.ocr_status,
        pages: metadata.pages,
        metadata_json: metadata.metadata_json,
      });
      setEditingDocument(null);
      fetchDocuments();
    } catch (error) {
      console.error('Error creating version:', error);
    }
  };

  async function computeSHA256(file: File): Promise<string> {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  const openUploadModal = () => {
    setEditingDocument(null);
    setShowUploadModal(true);
  };

  const openEditModal = (document: Document) => {
    setEditingDocument(document);
    setShowUploadModal(true);
  };

  const openDeleteConfirm = (document: Document) => {
    setDeletingDocument(document);
    setConfirmDelete(true);
  };

  const openOcrConfirm = (document: Document) => {
    setOcrDocument(document);
  };

  const formatDateTime = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: es });
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const columns = [
    {
      key: 'title',
      header: 'Título',
      accessor: 'title',
    },
    {
      key: 'type',
      header: 'Tipo',
      accessor: 'type',
      render: (value: string) => (
        <span className="inline-flex items-center gap-1">
          {typeIcons[value]}
          <span>{typeLabels[value]}</span>
        </span>
      ),
    },
    {
      key: 'size',
      header: 'Tamaño',
      accessor: 'file_size',
      render: (value: number) => formatFileSize(value),
    },
    {
      key: 'status',
      header: 'Estado',
      accessor: 'status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: 'ocr_status',
      header: 'OCR',
      accessor: 'ocr_status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: 'version',
      header: 'Versión',
      accessor: 'version',
    },
    {
      key: 'pages',
      header: 'Páginas',
      accessor: 'pages',
      render: (value: number | null) => value ? value.toString() : '-',
    },
    {
      key: 'uploaded_at',
      header: 'Subido',
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
            { label: 'Ver', onClick: () => navigate(`/portal/documents/${row.id}`), icon: <Eye className="w-4 h-4" /> },
            { label: 'Descargar', onClick: () => navigate(`/portal/documents/${row.id}/download`), icon: <Download className="w-4 h-4" /> },
            { divider: true },
            { label: 'Versiones', onClick: () => navigate(`/portal/documents/${row.id}/versions`), icon: <RotateCcw className="w-4 h-4" /> },
            canOcr && row.ocr_status !== 'processing' && row.ocr_status !== 'completed' && { label: 'Ejecutar OCR', onClick: () => openOcrConfirm(row), icon: <RotateCcw className="w-4 h-4" /> },
            { divider: true },
            { label: 'Editar', onClick: () => openEditModal(row), icon: <Edit className="w-4 h-4" /> },
            { divider: true },
            { label: 'Eliminar', onClick: () => openDeleteConfirm(row), icon: <Trash2 className="w-4 h-4" />, danger: true },
          ].filter(Boolean)}
        />
      ),
    },
  ];

  return (
    <PortalLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documentos</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona los documentos de tu organización</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={openUploadModal}>
              <Upload className="w-4 h-4 mr-2" />
              Subir Documento
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar documentos..."
                  value={search}

                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los estados' },
                  { value: 'pending', label: 'Pendiente' },
                  { value: 'processing', label: 'Procesando' },
                  { value: 'completed', label: 'Completado' },
                  { value: 'failed', label: 'Fallido' },
                ]}
                placeholder="Filtrar por estado"
              />
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los tipos' },
                  { value: 'pdf', label: 'PDF' },
                  { value: 'jpg', label: 'JPG' },
                  { value: 'jpeg', label: 'JPEG' },
                  { value: 'png', label: 'PNG' },
                  { value: 'tiff', label: 'TIFF' },
                ]}
                placeholder="Filtrar por tipo"
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

        {/* Documents Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={documents}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron documentos"
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

        {/* Upload Modal */}
        <Modal
          isOpen={showUploadModal}
          onClose={() => { setShowUploadModal(false); setEditingDocument(null); }}
          title={editingDocument ? 'Editar Documento' : 'Subir Documento'}
          size="lg"
        >
          <DocumentUploadForm
            initialData={editingDocument}
            onSubmit={editingDocument ? handleUpdate : handleUpload}
            onClose={() => { setShowUploadModal(false); setEditingDocument(null); }}
            loading={loading}
            onCreateVersion={handleCreateVersion}
            isEditing={!!editingDocument}
          />
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingDocument(null); }}
          onConfirm={handleDelete}
          title="Eliminar Documento"
          message={`¿Estás seguro de que quieres eliminar el documento "${deletingDocument?.title}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          variant="danger"
        />

        {/* OCR Confirmation */}
        <ConfirmDialog
          isOpen={!!ocrDocument}
          onClose={() => { setOcrDocument(null); setOcrLoading(false); }}
          onConfirm={confirmOcr}
          title="Ejecutar OCR"
          message={`¿Ejecutar OCR en el documento "${ocrDocument?.title}"? Esto procesará el documento para extraer texto.`}
          confirmText="Ejecutar OCR"
          cancelText="Cancelar"
          variant="primary"
          isLoading={ocrLoading}
        />

        {/* Upload Progress Toast */}
        {uploadProgress !== null && (
          <div className="fixed bottom-4 right-4 z-50 animate-slide-up">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 min-w-[300px] border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Subiendo documento...</span>
                {uploadProgress === 100 && <span className="text-green-500">Completado</span>}
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <div className="text-sm text-gray-500 mt-1 text-right">
                {uploadProgress}%
              </div>
            </div>
          </div>
        )}
      </div>
    </PortalLayout>
  );
}

function DocumentUploadForm({ initialData, onSubmit, onClose, loading, onCreateVersion, isEditing }: any) {
  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    description: initialData?.description || '',
    type: initialData?.type || 'pdf',
    meeting_id: initialData?.meeting_id || '',
  });
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEditing && !file) {
      alert('Por favor selecciona un archivo');
      return;
    }
    onSubmit(file, formData);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {!isEditing && (
        <div
          className={clsx(
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            dragActive
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-600'
            )}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            onChange={handleFileChange}
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png,.tiff"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500 mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              Arrastra y suelta un archivo aquí, o haz clic para seleccionar
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              PDF, JPG, JPEG, PNG, TIFF • Máx. 50MB
            </p>
          </label>
        </div>
      )}

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
          placeholder="Título del documento"
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
          placeholder="Descripción del documento..."
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="type" className="label">Tipo *</label>
          <select
            id="type"
            name="type"
            value={formData.type}
            onChange={handleChange}
            required
            className="input"
          >
            <option value="pdf">PDF</option>
            <option value="jpg">JPG</option>
            <option value="jpeg">JPEG</option>
            <option value="png">PNG</option>
            <option value="tiff">TIFF</option>
          </select>
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
            <option value="">Sin reunión asociada</option>
          </select>
        </div>
      </div>

      {isEditing && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h3 className="text-lg font-semibold mb-4">Crear nueva versión</h3>
          <div className="space-y-4">
            <div>
              <label className="label">Archivo nueva versión *</label>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.tiff"
                onChange={handleFileChange}
                required
                className="input"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="ocr_text" className="label">Texto OCR</label>
                <textarea
                  id="ocr_text"
                  name="ocr_text"
                  className="input min-h-[100px] resize-y"
                  placeholder="Texto extraído por OCR..."
                />
              </div>
              <div>
                <label htmlFor="ocr_confidence" className="label">Confianza OCR (0-1)</label>
                <input
                  type="number"
                  id="ocr_confidence"
                  name="ocr_confidence"
                  min="0"
                  max="1"
                  step="0.01"
                  className="input"
                  placeholder="0.95"
                />
              </div>
              <div>
                <label htmlFor="ocr_status" className="label">Estado OCR</label>
                <select
                  id="ocr_status"
                  name="ocr_status"
                  className="input"
                >
                  <option value="pending">Pendiente</option>
                  <option value="processing">Procesando</option>
                  <option value="completed">Completado</option>
                  <option value="failed">Fallido</option>
                </select>
              </div>
              <div>
                <label htmlFor="pages" className="label">Páginas</label>
                <input
                  type="number"
                  id="pages"
                  name="pages"
                  min="1"
                  className="input"
                  placeholder="Número de páginas"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button type="button" onClick={onClose} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Subiendo...' : 'Subir Documento'}
        </button>
      </div>
    </form>
  );
}