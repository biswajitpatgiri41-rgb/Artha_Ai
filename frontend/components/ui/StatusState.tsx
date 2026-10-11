import { AlertTriangle, Database, LoaderCircle, RefreshCw, ServerCrash, WifiOff } from 'lucide-react';

export type StatusStateKind = 'loading' | 'empty' | 'warning' | 'error' | 'stale' | 'unavailable-model' | 'unavailable-source' | 'unavailable-agent';

interface StatusStateProps {
  kind: StatusStateKind;
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  compact?: boolean;
}

const defaults: Record<StatusStateKind, { title: string; message: string }> = {
  loading: { title: 'Loading', message: 'Preparing demo data...' },
  empty: { title: 'No data available', message: 'There are no observations to display for this view.' },
  warning: { title: 'Review required', message: 'This result contains uncertainty or assumptions.' },
  error: { title: 'Unable to load', message: 'The requested view could not be prepared.' },
  stale: { title: 'Stale data', message: 'This demo snapshot may not reflect the latest release.' },
  'unavailable-model': { title: 'Model integration pending', message: 'Model output is not connected in this frontend prototype.' },
  'unavailable-source': { title: 'Unavailable source', message: 'This source is not connected. No value is substituted.' },
  'unavailable-agent': { title: 'Agent backend not connected', message: 'Agent execution is represented by static mock events in this frontend prototype.' },
};

export function StatusState({ kind, title, message, actionLabel, onAction, compact = false }: StatusStateProps) {
  const copy = defaults[kind];
  const Icon = kind === 'loading' ? LoaderCircle : kind === 'error' ? ServerCrash : kind === 'unavailable-source' ? WifiOff : kind === 'unavailable-model' || kind === 'unavailable-agent' ? Database : AlertTriangle;
  const tone = kind === 'error' ? 'border-red-200 bg-red-50 text-red-900' : kind === 'warning' || kind === 'stale' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-slate-200 bg-slate-50 text-slate-700';

  return (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`flex items-start gap-3 rounded-lg border ${compact ? 'p-3' : 'p-5'} ${tone}`}>
      <Icon size={compact ? 15 : 18} className={`mt-0.5 shrink-0 ${kind === 'loading' ? 'animate-spin' : ''}`} />
      <div className="min-w-0 flex-1"><p className="text-xs font-semibold">{title ?? copy.title}</p><p className="mt-1 text-xs leading-5 opacity-75">{message ?? copy.message}</p>{actionLabel && onAction && <button type="button" onClick={onAction} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-current/20 px-2.5 py-1.5 text-[10px] font-semibold"><RefreshCw size={12} />{actionLabel}</button>}</div>
    </div>
  );
}
