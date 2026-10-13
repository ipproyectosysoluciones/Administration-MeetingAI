import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, Settings, Users, Building, Shield, FileText, Bell, Save, Loader2, Eye, Edit, Trash2, MoreVertical, Globe, Mail, Lock, Moon, Sun, Palette, Bell as BellIcon, CheckCircle, XCircle, Archive, Bot } from 'lucide-react';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Dropdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, Pagination } from '@/components/ui/Table';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { useAuthStore } from '@/stores/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { clsx } from 'clsx';

interface Setting {
  key: string;
  value: string;
  type: 'string' | 'number' | 'boolean' | 'json';
  description: string;
  category: string;
}

const SETTINGS_CATEGORIES = [
  'general',
  'email',
  'storage',
  'ai',
  'security',
  'notifications',
  'integrations',
] as const;

const DEFAULT_SETTINGS: Setting[] = [
  // General
  { key: 'app_name', value: 'ReunionAI', type: 'string', description: 'Nombre de la aplicación', category: 'general' },
  { key: 'app_url', value: 'https://reunionai.com', type: 'string', description: 'URL base de la aplicación', category: 'general' },
  { key: 'default_language', value: 'es', type: 'string', description: 'Idioma por defecto', category: 'general' },
  { key: 'timezone', value: 'America/Bogota', type: 'string', description: 'Zona horaria por defecto', category: 'general' },
  { key: 'maintenance_mode', value: 'false', type: 'boolean', description: 'Modo mantenimiento', category: 'general' },

  // Email
  { key: 'smtp_host', value: 'smtp.example.com', type: 'string', description: 'Servidor SMTP', category: 'email' },
  { key: 'smtp_port', value: '587', type: 'number', description: 'Puerto SMTP', category: 'email' },
  { key: 'smtp_username', value: '', type: 'string', description: 'Usuario SMTP', category: 'email' },
  { key: 'smtp_password', value: '', type: 'string', description: 'Contraseña SMTP', category: 'email' },
  { key: 'smtp_encryption', value: 'tls', type: 'string', description: 'Cifrado SMTP (tls/ssl/none)', category: 'email' },
  { key: 'email_from', value: 'noreply@reunionai.com', type: 'string', description: 'Email remitente', category: 'email' },
  { key: 'email_from_name', value: 'ReunionAI', type: 'string', description: 'Nombre remitente', category: 'email' },

  // Storage
  { key: 'storage_driver', value: 'local', type: 'string', description: 'Driver de almacenamiento (local/s3/minio)', category: 'storage' },
  { key: 'storage_path', value: '/var/lib/reunionai/storage', type: 'string', description: 'Ruta de almacenamiento local', category: 'storage' },
  { key: 's3_endpoint', value: '', type: 'string', description: 'Endpoint S3', category: 'storage' },
  { key: 's3_bucket', value: '', type: 'string', description: 'Bucket S3', category: 'storage' },
  { key: 's3_region', value: 'us-east-1', type: 'string', description: 'Región S3', category: 'storage' },
  { key: 's3_access_key', value: '', type: 'string', description: 'Access Key S3', category: 'storage' },
  { key: 's3_secret_key', value: '', type: 'string', description: 'Secret Key S3', category: 'storage' },

  // AI
  { key: 'ai_provider', value: 'nemotron', type: 'string', description: 'Proveedor IA (nemotron/openai/anthropic)', category: 'ai' },
  { key: 'ai_model', value: 'nemotron-3-ultra', type: 'string', description: 'Modelo IA', category: 'ai' },
  { key: 'ai_api_key', value: '', type: 'string', description: 'API Key IA', category: 'ai' },
  { key: 'ai_base_url', value: 'https://integrate.api.nvidia.com/v1', type: 'string', description: 'URL base API IA', category: 'ai' },
  { key: 'ai_temperature', value: '0.3', type: 'number', description: 'Temperatura IA', category: 'ai' },
  { key: 'ai_max_tokens', value: '4096', type: 'number', description: 'Max tokens IA', category: 'ai' },

  // Security
  { key: 'jwt_access_ttl', value: '15', type: 'number', description: 'TTL Access Token (minutos)', category: 'security' },
  { key: 'jwt_refresh_ttl', value: '30', type: 'number', description: 'TTL Refresh Token (días)', category: 'security' },
  { key: 'password_min_length', value: '8', type: 'number', description: 'Longitud mínima contraseña', category: 'security' },
  { key: 'mfa_required_for_admins', value: 'true', type: 'boolean', description: 'MFA obligatorio para admins', category: 'security' },
  { key: 'session_timeout', value: '120', type: 'number', description: 'Timeout sesión (minutos)', category: 'security' },
  { key: 'max_login_attempts', value: '5', type: 'number', description: 'Máximo intentos login', category: 'security' },
  { key: 'lockout_duration', value: '15', type: 'number', description: 'Duración bloqueo (minutos)', category: 'security' },

  // Notifications
  { key: 'notification_email_enabled', value: 'true', type: 'boolean', description: 'Notificaciones email habilitadas', category: 'notifications' },
  { key: 'notification_webhook_url', value: '', type: 'string', description: 'Webhook URL notificaciones', category: 'notifications' },

  // Integrations
  { key: 'webhook_secret', value: '', type: 'string', description: 'Secreto webhook', category: 'integrations' },
  { key: 'rate_limit_enabled', value: 'true', type: 'boolean', description: 'Rate limiting habilitado', category: 'integrations' },
  { key: 'rate_limit_requests', value: '100', type: 'number', description: 'Requests por minuto', category: 'integrations' },
];

const getCategoryIcon = (category: string) => {
  const icons: Record<string, any> = {
    general: Settings,
    email: Mail,
    storage: Archive,
    ai: Bot,
    security: Shield,
    notifications: BellIcon,
    integrations: Globe,
  };
  return icons[category] || Settings;
};

const getCategoryLabel = (category: string) => {
  const labels: Record<string, string> = {
    general: 'General',
    email: 'Email',
    storage: 'Almacenamiento',
    ai: 'Inteligencia Artificial',
    security: 'Seguridad',
    notifications: 'Notificaciones',
    integrations: 'Integraciones',
  };
  return labels[category] || category;
};

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<Setting[]>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeCategory, setActiveCategory] = useState<typeof SETTINGS_CATEGORIES[0]>('general');
  const [search, setSearch] = useState('');
  const { hasPermission } = useAuthStore();

  const canManageSettings = hasPermission('admin.settings');

  useEffect(() => {
    // TODO: Load settings from API
    // For now, use defaults
  }, []);

  const filteredSettings = settings.filter(s => {
    const matchesCategory = s.category === activeCategory;
    const matchesSearch = s.key.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleChange = (key: string, value: string | number | boolean) => {
    setSettings(prev => prev.map(s => s.key === key ? { ...s, value: String(value) } : s));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // TODO: Call API to save settings
      await new Promise(resolve => setTimeout(resolve, 1000));
      alert('Configuración guardada correctamente');
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = () => {
    if (confirm('¿Restaurar valores por defecto? Se perderán los cambios no guardados.')) {
      setSettings(DEFAULT_SETTINGS);
    }
  };

  const renderSettingInput = (setting: Setting) => {
    switch (setting.type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={setting.value === 'true'}
              onChange={(e) => handleChange(setting.key, e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Habilitado</span>
          </label>
        );
      case 'number':
        return (
          <input
            type="number"
            value={setting.value}
            onChange={(e) => handleChange(setting.key, e.target.value)}
            className="input w-full max-w-xs"
            min={0}
          />
        );
      case 'json':
        return (
          <textarea
            value={setting.value}
            onChange={(e) => handleChange(setting.key, e.target.value)}
            className="input min-h-[100px] font-mono text-sm"
            placeholder="JSON válido"
          />
        );
      default:
        return (
          <input
            type={setting.key.includes('password') || setting.key.includes('secret') || setting.key.includes('key') ? 'password' : 'text'}
            value={setting.value}
            onChange={(e) => handleChange(setting.key, e.target.value)}
            className="input"
            placeholder={setting.description}
          />
        );
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Configuración</h1>
            <p className="text-gray-600 dark:text-gray-400">Configura los parámetros de la plataforma</p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={resetToDefaults} disabled={saving}>
              <XCircle className="w-4 h-4 mr-2" />
              Restaurar defaults
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Guardar cambios
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex gap-1 overflow-x-auto pb-2" aria-label="Categorías de configuración">
            {SETTINGS_CATEGORIES.map(category => (
              <button
                key={category}
                onClick={() => setActiveCategory(category as any)}
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap',
                  activeCategory === category
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}>
                <div className="flex items-center gap-2">
                  {getCategoryIcon(category)}
                  <span>{getCategoryLabel(category)}</span>
                </div>
              </button>
            ))}
          </nav>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar configuración..."
              className="input pl-10"
            />
          </div>
        </div>

        {/* Settings Grid */}
        <div className="space-y-6">
          {SETTINGS_CATEGORIES.map(category => {
            const categorySettings = filteredSettings.filter(s => s.category === category);
            if (categorySettings.length === 0) return null;

            return (
              <Card key={category} className="space-y-4">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getCategoryIcon(category)}
                    <CardTitle>{getCategoryLabel(category)}</CardTitle>
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{categorySettings.length} opciones</span>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {categorySettings.map(setting => (
                      <div key={setting.key} className="space-y-1">
                        <label htmlFor={setting.key} className="label">
                          {setting.key}
                          {setting.key.includes('password') || setting.key.includes('secret') || setting.key.includes('key') ? (
                            <span className="text-xs text-gray-400 ml-1">(oculto)</span>
                          ) : null}
                        </label>
                        <div className="relative">
                          {renderSettingInput(setting)}
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{setting.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
          </div>

          {filteredSettings.length === 0 && search && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">No se encontraron configuraciones para "{search}"</p>
            </div>
          )}
        </div>
    </AdminLayout>
  );
}