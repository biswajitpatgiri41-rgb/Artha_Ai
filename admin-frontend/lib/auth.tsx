'use client';

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
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

const PUBLIC_ADMIN_USER: AdminUser = {
  id: 'public-admin',
  email: 'public@localhost',
  name: 'Admin Panel',
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
    user: PUBLIC_ADMIN_USER,
    isLoading: false,
    isAuthenticated: true,
    error: null,
  });
  const router = useRouter();
  const pathname = usePathname();

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const refreshSession = useCallback(async () => {
    setState({ user: PUBLIC_ADMIN_USER, isLoading: false, isAuthenticated: true, error: null });
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshSession(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshSession]);

  useEffect(() => {
    if (pathname === '/login') {
      router.push('/overview');
    }
  }, [pathname, router]);

  const login = async (_email: string, _password: string) => {
    setState({ user: PUBLIC_ADMIN_USER, isLoading: false, isAuthenticated: true, error: null });
    router.replace('/overview');
  };

  const logout = async () => {
    setState({ user: PUBLIC_ADMIN_USER, isLoading: false, isAuthenticated: true, error: null });
    router.replace('/overview');
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
