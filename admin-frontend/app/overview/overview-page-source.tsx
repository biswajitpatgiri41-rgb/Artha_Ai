"use client"

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Minus,
  Cpu,
  Database,
  HardDrive,
  Network,
  Zap,
  Activity,
  Brain,
  FlaskConical,
  Shield,
  Layers,
  TrendingUp,
  Terminal,
  RefreshCw,
  ChevronRight,
  Bot,
} from "lucide-react";
import { useAdminAuth } from "@/lib/auth";
import { redirect } from "next/navigation";

interface SystemMetrics {
  cpu: number;
  memory: number;
  disk: number;
  network: number;
  uptime: number;
  requestsPerSecond: number;
  errorRate: number;
  activeConnections: number;
}

interface ServiceStatus {
  name: string;
  status: "healthy" | "degraded" | "critical" | "unknown";
  latency: number;
  lastCheck: string;
  details?: string;
}

interface ActivityEvent {
  id: string;
  timestamp: string;
  type: "info" | "warning" | "error" | "success";
  message: string;
  source: string;
  user?: string;
}

interface DashboardData {
  metrics: SystemMetrics | null;
  services: ServiceStatus[];
  activity: ActivityEvent[];
  lastUpdated: string;
  deployed: boolean;
}

export default function OverviewPage() {
  const { user, isLoading: authLoading, isAuthenticated } = useAdminAuth();
  const isAdmin = user?.role === 'ADMIN';

  const [data, setData] = useState<DashboardData>({
    metrics: null,
    services: [],
    activity: [],
    lastUpdated: new Date().toISOString(),
    deployed: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    try {
      setError(null);
      const [healthRes, metricsRes, activityRes] = await Promise.all([
        fetch("/api/admin/health", { cache: "no-store" }),
        fetch("/api/admin/metrics", { cache: "no-store" }),
        fetch("/api/admin/activity", { cache: "no-store" }),
      ]);

      const [health, metrics, activity] = await Promise.all([
        healthRes.ok ? healthRes.json() : null,
        metricsRes.ok ? metricsRes.json() : null,
        activityRes.ok ? activityRes.json() : null,
      ]);

      setData({
        metrics: metrics?.data ?? null,
        services: health?.services ?? [],
        activity: activity?.data ?? [],
        lastUpdated: new Date().toISOString(),
        deployed: health?.deployed ?? false,
      });
    } catch (err) {
      setError("Failed to fetch dashboard data");
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const initialFetch = window.setTimeout(() => { void fetchData(); }, 0);
    if (autoRefresh) {
      const interval = setInterval(fetchData, 30000);
      return () => { window.clearTimeout(initialFetch); clearInterval(interval); };
    }
    return () => window.clearTimeout(initialFetch);
  }, [fetchData, autoRefresh]);

  if (authLoading) return <div className="admin-card p-8 text-center">VERIFYING ACCESS...</div>;
  if (!isAdmin) redirect("/unauthorized");

  const getStatusIcon = (status: ServiceStatus["status"]) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="w-4 h-4 text-admin-neon-green" />;
      case "degraded":
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case "critical":
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Minus className="w-4 h-4 text-admin-text-muted" />;
    }
  };

  const getStatusClass = (status: ServiceStatus["status"]) => {
    switch (status) {
      case "healthy":
        return "text-admin-neon-green";
      case "degraded":
        return "text-yellow-400";
      case "critical":
        return "text-red-400";
      default:
        return "text-admin-text-muted";
    }
  };

  const getMetricStatus = (value: number, warning: number, critical: number) => {
    if (value >= critical) return "critical";
    if (value >= warning) return "degraded";
    return "healthy";
  };

  const metricCards = [
    {
      label: "CPU UTILIZATION",
      value: data.metrics?.cpu ?? null,
      unit: "%",
      icon: Cpu,
      warning: 70,
      critical: 85,
    },
    {
      label: "MEMORY USAGE",
      value: data.metrics?.memory ?? null,
      unit: "%",
      icon: Database,
      warning: 75,
      critical: 90,
    },
    {
      label: "DISK USAGE",
      value: data.metrics?.disk ?? null,
      unit: "%",
      icon: HardDrive,
      warning: 80,
      critical: 95,
    },
    {
      label: "NETWORK I/O",
      value: data.metrics?.network ?? null,
      unit: "MB/s",
      icon: Network,
      warning: 500,
      critical: 1000,
    },
    {
      label: "REQUESTS/SEC",
      value: data.metrics?.requestsPerSecond ?? null,
      unit: "",
      icon: Zap,
      warning: 1000,
      critical: 2000,
    },
    {
      label: "ERROR RATE",
      value: data.metrics?.errorRate ?? null,
      unit: "%",
      icon: AlertTriangle,
      warning: 1,
      critical: 5,
    },
    {
      label: "ACTIVE CONNS",
      value: data.metrics?.activeConnections ?? null,
      unit: "",
      icon: Activity,
      warning: 5000,
      critical: 10000,
    },
    {
      label: "UPTIME",
      value: data.metrics?.uptime ? Math.floor(data.metrics.uptime / 3600) : null,
      unit: "h",
      icon: Terminal,
      warning: 0,
      critical: 0,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="admin-terminal-heading">SYSTEM OVERVIEW</h1>
          <p className="text-admin-text-secondary">Real-time system health and operational metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1 rounded border ${data.deployed ? "border-admin-neon-green/30 bg-admin-neon-green/10" : "border-admin-text-muted/30 bg-admin-bg-tertiary"}`}>
            <span className={`w-2 h-2 rounded-full ${data.deployed ? "bg-admin-neon-green animate-pulse" : "bg-admin-text-muted"}`} />
            <span className="font-mono text-xs text-admin-text-secondary">
              {data.deployed ? "LIVE TELEMETRY" : "NOT DEPLOYED"}
            </span>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="admin-btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`${loading ? "animate-spin" : ""}`} />
            <span className="font-mono text-xs">REFRESH</span>
          </button>
          <label className="admin-btn-secondary flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 accent-admin-neon-green"
            />
            <span className="font-mono text-xs">AUTO (30s)</span>
          </label>
        </div>
      </div>

      {error && (
        <div className="admin-card border-red-500/30 bg-red-500/5 p-4">
          <div className="flex items-center gap-3 text-red-400">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span className="font-mono text-sm">{error}</span>
            <button onClick={fetchData} className="ml-auto text-xs underline hover:text-red-300">
              RETRY
            </button>
          </div>
        </div>
      )}

      <div className="admin-grid-4">
        {metricCards.map((metric, idx) => {
          const Icon = metric.icon;
          const value = metric.value;
          const status = value !== null ? getMetricStatus(value, metric.warning, metric.critical) : "unknown";
          const statusClass = getStatusClass(status);

          return (
            <div key={idx} className="admin-card p-5 group">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Icon className="w-5 h-5 text-admin-neon-green/70" />
                  <span className="font-mono text-xs text-admin-text-secondary uppercase tracking-wider">
                    {metric.label}
                  </span>
                </div>
                <span className={`font-mono text-xs px-2 py-0.5 rounded ${statusClass} border border-current/30 bg-current/10`}>
                  {status.toUpperCase()}
                </span>
              </div>
              <div className="font-mono text-3xl tabular-nums text-admin-text-primary">
                {value !== null ? value.toLocaleString() : "â€”"}
                <span className="text-lg text-admin-text-muted ml-1">{metric.unit}</span>
              </div>
              {value !== null && metric.warning > 0 && (
                <div className="mt-3 h-1.5 bg-admin-bg-tertiary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${status === "critical" ? "bg-red-500" : status === "degraded" ? "bg-yellow-400" : "bg-admin-neon-green"}`}
                    style={{ width: `${Math.min(100, (value / metric.critical) * 100)}%` }}
                  />
                </div>
              )}
              {value === null && (
                <p className="mt-3 text-xs text-admin-text-muted font-mono">No telemetry data available</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="admin-grid-2">
        <div className="admin-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-mono text-sm text-admin-text-secondary uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-admin-neon-green" />
              SERVICE STATUS
            </h2>
            <span className="font-mono text-xs text-admin-text-muted">
              Updated: {new Date(data.lastUpdated).toLocaleTimeString()}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-admin-text-muted uppercase tracking-wider border-b border-admin-border">
                  <th className="pb-2 pr-4 font-mono">SERVICE</th>
                  <th className="pb-2 pr-4 font-mono">STATUS</th>
                  <th className="pb-2 pr-4 font-mono">LATENCY</th>
                  <th className="pb-2 pr-4 font-mono">LAST CHECK</th>
                  <th className="pb-2 font-mono">DETAILS</th>
                </tr>
              </thead>
              <tbody>
                {data.services.length > 0 ? (
                  data.services.map((service) => (
                    <tr key={service.name} className="border-b border-admin-border/50 hover:bg-admin-bg-tertiary/50 transition-colors">
                      <td className="py-3 pr-4 font-mono text-admin-text-primary">{service.name}</td>
                      <td className="py-3 pr-4">
                        <span className={`inline-flex items-center gap-1.5 font-mono text-xs px-2 py-1 rounded ${getStatusClass(service.status)} border border-current/30 bg-current/10`}>
                          {getStatusIcon(service.status)}
                          {service.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-mono tabular-nums text-admin-text-secondary">{service.latency}ms</td>
                      <td className="py-3 pr-4 font-mono text-admin-text-muted">
                        {new Date(service.lastCheck).toLocaleTimeString()}
                      </td>
                      <td className="py-3 text-admin-text-muted text-xs max-w-xs truncate">{service.details || "â€”"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-admin-text-muted font-mono text-xs">
                      No service telemetry available. Deploy backend to enable monitoring.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="admin-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-mono text-sm text-admin-text-secondary uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-admin-neon-green" />
              RECENT ACTIVITY
            </h2>
            <Link href="/activity" className="font-mono text-xs text-admin-neon-green hover:text-admin-neon-green/70 transition-colors flex items-center gap-1">
              VIEW ALL
              <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {data.activity.length > 0 ? (
              data.activity.slice(0, 10).map((event) => (
                <div key={event.id} className="flex gap-3 pb-3 border-b border-admin-border/50 last:border-0">
                  <div className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${event.type === "error" ? "bg-red-400" : event.type === "warning" ? "bg-yellow-400" : event.type === "success" ? "bg-admin-neon-green" : "bg-admin-text-muted"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-admin-text-primary">{event.source}</span>
                      <span className="text-admin-text-muted">{new Date(event.timestamp).toLocaleTimeString()}</span>
                      {event.user && <span className="text-admin-text-muted">by {event.user}</span>}
                    </div>
                    <p className="text-sm text-admin-text-secondary mt-0.5 truncate">{event.message}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-admin-text-muted font-mono text-xs">
                No recent activity. Deploy backend to enable event logging.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="admin-card p-5">
        <h2 className="font-mono text-sm text-admin-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-admin-neon-green" />
          QUICK ACTIONS
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/model-drift" className="admin-btn-secondary flex items-center gap-2">
            <Brain className="w-4 h-4" />
            <span className="font-mono text-xs">MODEL DRIFT</span>
          </Link>
          <Link href="/agent-status" className="admin-btn-secondary flex items-center gap-2">
            <Bot className="w-4 h-4" />
            <span className="font-mono text-xs">AGENT STATUS</span>
          </Link>
          <Link href="/knowledge-base" className="admin-btn-secondary flex items-center gap-2">
            <Layers className="w-4 h-4" />
            <span className="font-mono text-xs">KNOWLEDGE BASE</span>
          </Link>
          <Link href="/forecast-operations" className="admin-btn-secondary flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="font-mono text-xs">FORECAST OPS</span>
          </Link>
          <Link href="/scenario-engine" className="admin-btn-secondary flex items-center gap-2">
            <FlaskConical className="w-4 h-4" />
            <span className="font-mono text-xs">SCENARIO ENGINE</span>
          </Link>
          <Link href="/security" className="admin-btn-secondary flex items-center gap-2">
            <Shield className="w-4 h-4" />
            <span className="font-mono text-xs">SECURITY</span>
          </Link>
          <Link href="/incidents" className="admin-btn-secondary flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="font-mono text-xs">INCIDENTS</span>
          </Link>
          <Link href="/settings" className="admin-btn-secondary flex items-center gap-2">
            <Terminal className="w-4 h-4" />
            <span className="font-mono text-xs">SETTINGS</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
