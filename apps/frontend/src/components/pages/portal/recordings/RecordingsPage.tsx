import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Play, Pause, MoreVertical, Trash2, Download, Volume2, VolumeX, Loader2, RotateCcw, Upload, FileText } from 'lucide-react';
import { PortalLayout } from '@/components/layout/PortalLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { recordingsApi, jobsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { clsx } from 'clsx';

interface Recording {
  id: string;
  meeting_id: string;
  meeting_title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  storage_path: string;
  duration_seconds: number | null;
  status: 'stored' | 'processing' | 'transcribed' | 'failed';
  uploaded_by: string;
  uploaded_by_name: string;
  created_at: string;
  updated_at: string;
}

export default function RecordingsPage() {
  const [recordings, setRecordings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [deletingRecording, setDeletingRecording] = useState<any>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [transcribingId, setTranscribingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();

  const canUpload = hasPermission('recording.upload');
  const canRead = hasPermission('recording.read');
  const canDelete = hasPermission('recording.delete');

  const fetchRecordings = async () => {
    setLoading(true);
    try {
      const response = await recordingsApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        q: search || undefined,
      });
      setRecordings(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Error fetching recordings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecordings();
  }, [page, pageSize, search, statusFilter]);

  const handleUpload = async (file: File, metadata: any) => {
    try {
      await recordingsApi.upload(file, metadata);
      setShowUploadModal(false);
      fetchRecordings();
    } catch (error) {
      console.error('Error uploading recording:', error);
    }
  };

  const handleDelete = async () => {
    if (!deletingRecording) return;
    try {
      await recordingsApi.delete(deletingRecording.id);
      setConfirmDelete(false);
      setDeletingRecording(null);
      fetchRecordings();
    } catch (error) {
      console.error('Error deleting recording:', error);
    }
  };

  const handleTranscribe = async (recording: any) => {
    setTranscribingId(recording.id);
    try {
      await jobsApi.enqueueTranscription(recording.id, recording.meeting_id);
      fetchRecordings();
    } catch (error) {
      console.error('Error enqueuing transcription:', error);
    } finally {
      setTranscribingId(null);
    }
  };

  const handleDownload = async (recording: any) => {
    try {
      const blob = await recordingsApi.download(recording.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = recording.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading recording:', error);
    }
  };

  const openDeleteConfirm = (recording: any) => {
    setDeletingRecording(recording);
    setConfirmDelete(true);
  };

  const handlePlay = async (recording: any) => {
    if (playingId === recording.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    try {
      const blob = await recordingsApi.download(recording.id);
      const url = URL.createObjectURL(blob);
      audioRef.current = new Audio(url);
      audioRef.current.play();
      setPlayingId(recording.id);

      audioRef.current.onended = () => {
        setPlayingId(null);
        URL.revokeObjectURL(url);
      };
    } catch (error) {
      console.error('Error playing recording:', error);
    }
  };

  const handleStop = () => {
    audioRef.current?.pause();
    setPlayingId(null);
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: es });
  };

  const columns = [
    {
      key: 'filename',
      header: 'Archivo',
      accessor: 'filename',
      render: (value: string, row: any) => (
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          <span className="max-w-[200px] truncate">{value}</span>
        </div>
      ),
    },
    {
      key: 'meeting',
      header: 'Reunión',
      accessor: 'meeting_title',
    },
    {
      key: 'size',
      header: 'Tamaño',
      accessor: 'size_bytes',
      render: (value: number) => formatFileSize(value),
    },
    {
      key: 'duration',
      header: 'Duración',
      accessor: 'duration_seconds',
      render: (value: number | null) => formatDuration(value),
    },
    {
      key: 'status',
      header: 'Estado',
      accessor: 'status',
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: 'uploaded_at',
      header: 'Subido',
      accessor: 'created_at',
      render: (value: string) => format(new Date(value), 'dd/MM/yyyy', { locale: es }),
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
            { label: 'Reproducir', onClick: () => handlePlay(row), icon: <Play className="w-4 h-4" /> },
            { label: 'Descargar', onClick: () => handleDownload(row), icon: <Download className="w-4 h-4" /> },
            { divider: true },
            { label: 'Transcribir', onClick: () => handleTranscribe(row), icon: <Loader2 className="w-4 h-4" />, disabled: row.status === 'transcribed' || row.status === 'processing' },
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
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Grabaciones</h1>
            <p className="text-gray-600 dark:text-gray-400">Gestiona las grabaciones de audio de las reuniones</p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={() => setShowUploadModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Subir Grabación
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="space-y-4">
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Buscar grabaciones..."
                  value={search}

                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos los estados' },
                  { value: 'stored', label: 'Guardado' },
                  { value: 'processing', label: 'Procesando' },
                  { value: 'transcribed', label: 'Transcrito' },
                  { value: 'failed', label: 'Fallido' },
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

        {/* Recordings Table */}
        <Card>
          <CardContent>
            <Table
              columns={columns}
              data={recordings}
              keyAccessor={(row) => row.id}
              isLoading={loading}
              emptyMessage="No se encontraron grabaciones"
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
          onClose={() => setShowUploadModal(false)}
          title="Subir Grabación"
          size="lg"
        >
          <RecordingUploadForm
            onSubmit={handleUpload}
            onClose={() => setShowUploadModal(false)}
            loading={loading}
          />
        </Modal>

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={confirmDelete}
          onClose={() => { setConfirmDelete(false); setDeletingRecording(null); }}
          onConfirm={handleDelete}
          title="Eliminar Grabación"
          message={`¿Estás seguro de que quieres eliminar la grabación "${deletingRecording?.filename}"? Esta acción no se puede deshacer.`}
          confirmText="Eliminar"
          cancelText="Cancelar"
          variant="danger"
        />
      </div>
    </PortalLayout>
  );
}

function RecordingUploadForm({ onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    meeting_id: '',
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

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert('Por favor selecciona un archivo');
      return;
    }
    onSubmit(file, formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className={clsx(
        'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
        dragActive
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-300 dark:border-gray-600'
      )}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false); }}
        onDrop={(e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false); handleDrop(e); }}
      >
        <input
          type="file"
          id="file-upload"
          onChange={(e) => { if (e.target.files && e.target.files[0]) setFile(e.target.files[0]); }}
          className="hidden"
          accept="audio/*,video/*"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <Upload className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500 mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Arrastra y suelta un archivo aquí, o haz clic para seleccionar
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            MP3, WAV, M4A, MP4, WEBM • Máx. 500MB
          </p>
        </label>
        </div>

      <div>
        <label htmlFor="title" className="label">Título *</label>
        <input
          type="text"
          id="title"
          name="title"
          value={formData.title}
          onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
          required
          className="input"
          placeholder="Título de la grabación"
        />
      </div>

      <div>
        <label htmlFor="description" className="label">Descripción</label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          className="input min-h-[100px] resize-y"
          placeholder="Descripción de la grabación..."
        />
      </div>

      <div>
        <label htmlFor="meeting_id" className="label">Reunión asociada</label>
        <select
          id="meeting_id"
          name="meeting_id"
          value={formData.meeting_id}
          onChange={(e) => setFormData(prev => ({ ...prev, meeting_id: e.target.value }))}
          className="input"
        >
          <option value="">Sin reunión asociada</option>
        </select>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button type="button" onClick={onClose} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Subiendo...' : 'Subir Grabación'}
        </button>
      </div>
    </form>
  );
}