'use client';

import { useState } from 'react';
import { useAdminAuth } from '@/lib/auth';
import { Lock, Mail, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const { login, error: authError, clearError, isLoading: authLoading } = useAdminAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    setIsSubmitting(true);

    try {
      await login(email, password);
    } catch {
      setLocalError(authError || 'Invalid credentials');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-admin-neon-green/10 border border-admin-neon-green/30 mb-4">
            <Lock className="w-8 h-8 text-admin-neon-green" />
          </div>
          <h1 className="text-2xl font-bold text-admin-text-primary mb-1">
            INDIA MACRO AI<br />
            <span className="text-admin-neon-green">SYSTEM CONTROL</span>
          </h1>
          <p className="text-admin-text-secondary text-sm mt-2">SECURE OPERATIONS TERMINAL</p>
        </div>
        <div className="admin-card admin-card-inner-glow p-6">
          {(localError || authError) && <div role="alert" className="mb-4 flex items-center gap-2 rounded-lg border border-admin-red/30 bg-admin-red/10 p-3 text-sm text-admin-red"><AlertCircle size={16} />{localError || authError}</div>}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-admin-text-secondary mb-1.5">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-admin-text-muted" />
                <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@indiamacro.ai" className="input-admin pl-10" disabled={isSubmitting || authLoading} required />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-admin-text-secondary mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-admin-text-muted" />
                <input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="input-admin pl-10 pr-10" disabled={isSubmitting || authLoading} required />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-admin-text-muted hover:text-admin-text-primary transition-colors" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={isSubmitting || authLoading} className="btn-admin-primary w-full py-3 text-sm font-mono uppercase tracking-wider">
              {isSubmitting || authLoading ? <> <Loader2 className="w-5 h-5 animate-spin mr-2" /> AUTHENTICATING...</> : '> INITIATE SESSION'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
