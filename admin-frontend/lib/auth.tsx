'use client';

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import Cookies from 'js-cookie';
import { useRouter, usePathname } from 'next/navigation';

// Types
export type AdminRole = 'ADMIN' | 'RESEARCHER' | 'ANALYST' | 'VIEWER';

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: AdminRole;
  createdAt: string;
  lastLogin: string;
}

export interface AuthState {
  user: AdminUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const SESSION_COOKIE = 'admin_session';
// The admin API currently has no authentication endpoints. Allow local UI work
// without a login, but keep the existing session flow in production builds.
const LOCAL_DEV_ACCESS = process.env.NODE_ENV === 'development';
const LOCAL_DEV_USER: AdminUser = {
  id: 'local-admin',
  email: 'local@localhost',
  name: 'Local Developer',
  role: 'ADMIN',
  createdAt: new Date(0).toISOString(),
  lastLogin: new Date(0).toISOString(),
};

// Role hierarchy for authorization
const ROLE_HIERARCHY: Record<AdminRole, number> = {
  VIEWER: 1,
  ANALYST: 2,
  RESEARCHER: 3,
  ADMIN: 4,
};

export function hasPermission(userRole: AdminRole, requiredRole: AdminRole): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: LOCAL_DEV_ACCESS ? LOCAL_DEV_USER : null,
    isLoading: !LOCAL_DEV_ACCESS,
    isAuthenticated: LOCAL_DEV_ACCESS,
    error: null,
  });
  const router = useRouter();
  const pathname = usePathname();

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const refreshSession = useCallback(async () => {
    if (LOCAL_DEV_ACCESS) {
      setState({ user: LOCAL_DEV_USER, isLoading: false, isAuthenticated: true, error: null });
      return;
    }

    try {
      const sessionToken = Cookies.get(SESSION_COOKIE);
      if (!sessionToken) {
        setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
        return;
      }

      const response = await fetch(`${API_BASE}/api/admin/auth/me`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setState({
          user: data.user,
          isLoading: false,
          isAuthenticated: true,
          error: null,
        });
      } else {
        Cookies.remove(SESSION_COOKIE);
        setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
      }
    } catch {
      Cookies.remove(SESSION_COOKIE);
      setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshSession(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshSession]);

  // Redirect to login if not authenticated and not on login page
  useEffect(() => {
    if (!state.isLoading && !state.isAuthenticated && pathname !== '/login') {
      router.push('/login');
    }
    if (state.isAuthenticated && pathname === '/login') {
      router.push('/overview');
    }
  }, [state.isLoading, state.isAuthenticated, pathname, router]);

  const login = async (email: string, password: string) => {
    if (LOCAL_DEV_ACCESS) {
      setState({ user: LOCAL_DEV_USER, isLoading: false, isAuthenticated: true, error: null });
      router.replace('/overview');
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await fetch(`${API_BASE}/api/admin/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      if (data.session_token) {
        Cookies.set(SESSION_COOKIE, data.session_token, {
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          expires: 7,
        });
      }

      setState({
        user: data.user,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      });

      router.push('/overview');
      router.refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setState(prev => ({ ...prev, isLoading: false, error: message }));
      throw err;
    }
  };

  const logout = async () => {
    if (LOCAL_DEV_ACCESS) {
      router.replace('/overview');
      return;
    }

    setState(prev => ({ ...prev, isLoading: true }));
    try {
      const sessionToken = Cookies.get(SESSION_COOKIE);
      if (sessionToken) {
        await fetch(`${API_BASE}/api/admin/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        });
      }
    } finally {
      Cookies.remove(SESSION_COOKIE);
      setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
      router.push('/login');
      router.refresh();
    }
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshSession, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within AdminAuthProvider');
  }
  return context;
}

export function useAdminRole(requiredRole: AdminRole) {
  const { user, isAuthenticated } = useAdminAuth();
  
  if (!isAuthenticated || !user) return false;
  return hasPermission(user.role, requiredRole);
}

export function AdminOnly({ children, requiredRole = 'ADMIN' }: { 
  children: ReactNode; 
  requiredRole?: AdminRole; 
}) {
  const { user, isAuthenticated, isLoading } = useAdminAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-admin-neon-green animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !user || !hasPermission(user.role, requiredRole)) {
    return (
      <div className="admin-card p-8 text-center">
        <AlertTriangle className="w-12 h-12 text-admin-amber mx-auto mb-4" />
        <h3 className="text-admin-text-primary text-lg font-medium mb-2">
          Access Denied
        </h3>
        <p className="text-admin-text-secondary">
          This section requires {requiredRole} role or higher.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
