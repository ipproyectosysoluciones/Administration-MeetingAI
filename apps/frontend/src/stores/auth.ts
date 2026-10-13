import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  permissions: string[];
  tenant_id: string | null;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (accessToken: string, user: User) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setLoading: (loading: boolean) => void;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,

      login: (accessToken: string, user: User) => {
        localStorage.setItem('access_token', accessToken);
        set({ accessToken, user, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('access_token');
        set({ user: null, accessToken: null, isAuthenticated: false });
      },

      setUser: (user: User) => set({ user }),

      setLoading: (loading: boolean) => set({ isLoading: loading }),

      hasPermission: (permission: string) => {
        const { user } = get();
        if (!user) return false;
        return user.permissions.includes(permission);
      },

      hasAnyPermission: (permissions: string[]) => {
        const { user } = get();
        if (!user) return false;
        return permissions.some(p => user.permissions.includes(p));
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors for common permissions
export const useCanCreateMeetings = () => useAuthStore(state => state.hasPermission('meeting.create'));
export const useCanReadMeetings = () => useAuthStore(state => state.hasPermission('meeting.read'));
export const useCanUpdateMeetings = () => useAuthStore(state => state.hasPermission('meeting.update'));
export const useCanDeleteMeetings = () => useAuthStore(state => state.hasPermission('meeting.delete'));
export const useCanManageParticipants = () => useAuthStore(state => state.hasPermission('meeting.participant_manage'));

export const useCanUploadRecordings = () => useAuthStore(state => state.hasPermission('recording.upload'));
export const useCanReadRecordings = () => useAuthStore(state => state.hasPermission('recording.read'));
export const useCanDeleteRecordings = () => useAuthStore(state => state.hasPermission('recording.delete'));

export const useCanUploadDocuments = () => useAuthStore(state => state.hasPermission('document.upload'));
export const useCanReadDocuments = () => useAuthStore(state => state.hasPermission('document.read'));
export const useCanUpdateDocuments = () => useAuthStore(state => state.hasPermission('document.update'));
export const useCanDeleteDocuments = () => useAuthStore(state => state.hasPermission('document.delete'));
export const useCanTriggerOCR = () => useAuthStore(state => state.hasPermission('document.ocr'));

export const useCanCreateMinutes = () => useAuthStore(state => state.hasPermission('minutes.write'));
export const useCanReadMinutes = () => useAuthStore(state => state.hasPermission('minutes.read'));
export const useCanApproveMinutes = () => useAuthStore(state => state.hasPermission('minutes.approve'));
export const useCanPublishMinutes = () => useAuthStore(state => state.hasPermission('minutes.publish'));

export const useCanManageUsers = () => useAuthStore(state => state.hasPermission('user.create') || state.hasPermission('user.update') || state.hasPermission('user.delete'));
export const useCanManageRoles = () => useAuthStore(state => state.hasPermission('role.create') || state.hasPermission('role.update') || state.hasPermission('role.delete'));
export const useCanManagePermissions = () => useAuthStore(state => state.hasPermission('permission.read') || state.hasPermission('role.permission.assign'));