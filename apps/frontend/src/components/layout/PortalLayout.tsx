import { Fragment, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { Link, useLocation, NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Calendar, FileText, Settings, LogOut, Menu, X, ChevronLeft, ChevronRight, Bell, Search, Moon, Sun, User, HelpCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Modal } from '@/components/ui/Modal';
import { Dropdown } from '@/components/ui/Dropdown';

interface PortalLayoutProps {
  children: ReactNode;
}

export function PortalLayout({ children }: PortalLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasPermission } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => localStorage.getItem('theme') as any || 'system');

  const navigation = [
    { name: 'Dashboard', href: '/portal', icon: LayoutDashboard, permission: 'dashboard.read' },
    { name: 'Reuniones', href: '/portal/meetings', icon: Calendar, permission: 'meeting.read' },
    { name: 'Actas', href: '/portal/minutes', icon: FileText, permission: 'minutes.read' },
    { name: 'Documentos', href: '/portal/documents', icon: FileText, permission: 'document.read' },
    { name: 'Grabaciones', href: '/portal/recordings', icon: FileText, permission: 'recording.read' },
    { name: 'Notificaciones', href: '/portal/notifications', icon: FileText, permission: 'notification.read' },
  ];

  const adminNavigation = [
    { name: 'Usuarios', href: '/admin/users', icon: Users, permission: 'user.read' },
    { name: 'Organizaciones', href: '/admin/organizations', icon: Users, permission: 'organization.read' },
    { name: 'Roles y Permisos', href: '/admin/rbac', icon: Settings, permission: 'role.read' },
    { name: 'Auditoría', href: '/admin/audit', icon: Settings, permission: 'audit.read' },
    { name: 'Configuración', href: '/admin/settings', icon: Settings, permission: 'admin.settings' },
  ];

  const filteredNavigation = navigation.filter(item => hasPermission(item.permission));
  const filteredAdminNavigation = adminNavigation.filter(item => hasPermission(item.permission));

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);
  const toggleSidebarCollapsed = () => setSidebarCollapsed(!sidebarCollapsed);
  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.remove('light', 'dark');
    if (newTheme === 'dark' || (newTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.add('light');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-50 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700',
          'transition-all duration-300 ease-in-out',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          sidebarCollapsed ? 'w-20' : 'w-64',
          'flex flex-col'
        )}
        aria-label="Navegación principal"
      >
        {/* Logo */}
        <div className={clsx('flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700', 'transition-all duration-300')}>
          <Link to="/portal" className="flex items-center gap-2" aria-label="ReunionAI Home">
            <svg className="w-8 h-8 text-primary-600" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            {!sidebarCollapsed && (
              <span className="text-xl font-bold text-gray-900 dark:text-white transition-opacity duration-200">
                ReunionAI
              </span>
            )}
          </Link>
          {!sidebarCollapsed && (
            <button
              onClick={toggleSidebarCollapsed}
              className="ml-auto p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label={sidebarCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
            >
              {sidebarCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Navegación">
          {filteredNavigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                )
              }
            >
              <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </NavLink>
          ))}

          {filteredAdminNavigation.length > 0 && !sidebarCollapsed && (
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="px-3 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
                Administración
              </p>
              {filteredAdminNavigation.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                    )
                  }
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  <span>{item.name}</span>
                </NavLink>
              ))}
            </div>
          )}
        </nav>

        {/* Bottom user info */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Avatar
              name={user?.full_name || 'Usuario'}
              size="md"
              status="online"
            />
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user?.full_name || 'Usuario'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user?.email}
                </p>
              </div>
            )}
            <Dropdown
              trigger={
                <button
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  aria-label="Opciones de usuario"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              }
              items={[
                { label: 'Mi perfil', onClick: () => navigate('/portal/profile') },
                { label: 'Configuración', onClick: () => navigate('/portal/settings') },
                { divider: true },
                { label: 'Cerrar sesión', onClick: () => logout(), danger: true },
              ]}
            />
          </div>
        </div>
      </aside>

      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 shadow-lg"
        onClick={() => setSidebarOpen(true)}
        aria-label="Abrir menú"
      >
        <Menu className="w-6 h-6" />
      </button>

      {/* Main content */}
      <main className={clsx('flex-1 lg:ml-64 transition-all duration-300', sidebarCollapsed && 'lg:ml-20')}>
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white hidden sm:block">
                {getPageTitle(location.pathname)}
              </h1>
            </div>

            <div className="flex items-center gap-4">
              {/* Search */}
              <div className="relative hidden sm:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="search"
                  placeholder="Buscar..."
                  className="w-64 pl-10 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                />
              </div>

              {/* Theme toggle */}
              <button
                onClick={() => handleThemeChange(theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark')}
                className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label={`Cambiar tema (actual: ${theme})`}
              >
                {theme === 'dark' ? <Moon className="w-5 h-5" /> : theme === 'light' ? <Sun className="w-5 h-5" /> : <HelpCircle className="w-5 h-5" />}
              </button>

              {/* Notifications */}
              <Dropdown
                trigger={
                  <button className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">3</span>
                  </button>
                }
                items={[
                  { label: 'Acta revisada', onClick: () => {} },
                  { label: 'Acta aprobada', onClick: () => {} },
                  { divider: true },
                  { label: 'Ver todas', onClick: () => {} },
                ]}
              />

              {/* User menu */}
              <Dropdown
                trigger={
                  <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                    <Avatar name={user?.full_name || 'Usuario'} size="sm" status="online" />
                    <span className="hidden md:block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {user?.full_name || 'Usuario'}
                    </span>
                    <ChevronDown className="w-4 h-4" />
                  </button>
                }
                items={[
                  { label: 'Mi perfil', onClick: () => navigate('/portal/profile'), icon: <User className="w-4 h-4" /> },
                  { label: 'Configuración', onClick: () => navigate('/portal/settings'), icon: <Settings className="w-4 h-4" /> },
                  { divider: true },
                  { label: 'Cerrar sesión', onClick: () => logout(), danger: true, icon: <LogOut className="w-4 h-4" /> },
                ]}
              />
            </div>
          </div>
        </header>

        <div className="p-4 sm:p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}

function getPageTitle(pathname: string): string {
  const titles: Record<string, string> = {
    '/portal': 'Dashboard',
    '/portal/meetings': 'Reuniones',
    '/portal/minutes': 'Actas',
    '/portal/documents': 'Documentos',
    '/portal/recordings': 'Grabaciones',
    '/portal/notifications': 'Notificaciones',
    '/portal/profile': 'Mi Perfil',
    '/portal/settings': 'Configuración',
    '/admin': 'Administración',
    '/admin/users': 'Usuarios',
    '/admin/organizations': 'Organizaciones',
    '/admin/rbac': 'Roles y Permisos',
    '/admin/audit': 'Auditoría',
    '/admin/settings': 'Configuración',
  };

  for (const [path, title] of Object.entries(titles)) {
    if (pathname.startsWith(path)) return title;
  }
  return 'ReunionAI';
}