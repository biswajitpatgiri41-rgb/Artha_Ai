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
import Cookies from "js-cookie";

interface SystemMetrics {
  cpu: number | null;
  memory: number | null;
  disk: number | null;
  network: number | null;
  uptime: number;
  requestsPerSecond: number;
  errorRate: number;
  activeConnections: number;
  incomingMBps: number;
  outgoingMBps: number;
  trafficScope: string;
}

interface TrafficSample {
  time: number;
  incoming: number;
  outgoing: number;
}

interface ServiceStatus {
  name: string;
  status: "healthy" | "degraded" | "critical" | "unknown";
  latency: number | null;
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

interface ActiveVisitor {
  ip_address: string;
  first_seen: string;
  last_seen: string;
  last_path: string;
  request_count: number;
}

interface DashboardData {
  metrics: SystemMetrics | null;
  services: ServiceStatus[];
  activity: ActivityEvent[];
  visitors: ActiveVisitor[];
  lastUpdated: string;
  deployed: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function OverviewPage() {
  const { user, isLoading: authLoading, isAuthenticated } = useAdminAuth();
  const isAdmin = user?.role === 'ADMIN';

  const [data, setData] = useState<DashboardData>({
    metrics: null,
    services: [],
    activity: [],
    visitors: [],
    lastUpdated: new Date().toISOString(),
    deployed: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [trafficSamples, setTrafficSamples] = useState<TrafficSample[]>([]);

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    try {
      setError(null);
      const healthStartedAt = performance.now();
      const token = Cookies.get("admin_session");
      const requestOptions: RequestInit = {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      };
      const [healthRes, metricsRes, activityRes, visitorsRes] = await Promise.all([
        fetch(`${API_BASE}/api/admin/health`, requestOptions),
        fetch(`${API_BASE}/api/admin/metrics`, requestOptions),
        fetch(`${API_BASE}/api/admin/activity`, requestOptions),
        fetch(`${API_BASE}/api/admin/visitors`, requestOptions),
      ]);

      if (!healthRes.ok || !metricsRes.ok || !activityRes.ok) {
        throw new Error("Admin telemetry endpoints are unavailable. Check that FastAPI is running.");
      }

      const [health, metrics, activity, visitors] = await Promise.all([
        healthRes.ok ? healthRes.json() : null,
        metricsRes.ok ? metricsRes.json() : null,
        activityRes.ok ? activityRes.json() : null,
        visitorsRes.ok ? visitorsRes.json() : null,
      ]);
      const healthLatency = Math.round(performance.now() - healthStartedAt);

      setData({
        metrics: metrics?.data ?? null,
        services: (health?.services ?? []).map((service: ServiceStatus) => service.name === "FastAPI"
          ? { ...service, latency: healthLatency }
          : service),
        activity: activity?.data ?? [],
        visitors: visitors?.visitors ?? [],
        lastUpdated: new Date().toISOString(),
        deployed: health?.deployed ?? false,
      });
      if (metrics?.data) {
        setTrafficSamples((samples) => [...samples, {
          time: Date.now(),
          incoming: metrics.data.incomingMBps ?? 0,
          outgoing: metrics.data.outgoingMBps ?? 0,
        }].slice(-36));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch dashboard data");
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const initialFetch = window.setTimeout(() => { void fetchData(); }, 0);
    if (autoRefresh) {
      const interval = setInterval(fetchData, 5000);
      return () => { window.clearTimeout(initialFetch); clearInterval(interval); };
    }
    return () => window.clearTimeout(initialFetch);
  }, [fetchData, autoRefresh]);

  if (authLoading) {
    return <div className="admin-card p-8 text-center font-mono text-sm text-admin-text-secondary">VERIFYING ACCESS...</div>;
  }

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
      value: data.metrics ? data.metrics.uptime / 3600 : null,
      unit: "h",
      icon: Terminal,
      warning: 0,
      critical: 0,
    },
  ];

  const trafficMax = Math.max(0.001, ...trafficSamples.flatMap((sample) => [sample.incoming, sample.outgoing]));
  const trafficLine = (key: "incoming" | "outgoing") => trafficSamples
    .map((sample, index) => {
      const x = trafficSamples.length < 2 ? 0 : (index / (trafficSamples.length - 1)) * 760;
      const y = 180 - (sample[key] / trafficMax) * 160;
      return `${x},${y}`;
    })
    .join(" ");

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
            <span className="font-mono text-xs">AUTO (5s)</span>
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
                {value !== null ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "N/A"}
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

      <div className="admin-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="font-mono text-sm text-admin-text-secondary uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-admin-neon-green" /> ACTIVE WEBSITE VISITORS
            </h2>
            <p className="mt-1 text-xs text-admin-text-muted">Distinct IP addresses making API requests in the last five minutes | auto-refreshes every 5 seconds</p>
          </div>
          <span className="font-mono text-xs text-admin-neon-green">{data.visitors.length} ACTIVE IP{data.visitors.length === 1 ? '' : 'S'}</span>
        </div>
        {data.visitors.length ? <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="text-admin-text-muted border-b border-admin-border"><th className="py-2 pr-4 font-mono">IP ADDRESS</th><th className="py-2 pr-4 font-mono">LAST SEEN</th><th className="py-2 pr-4 font-mono">LAST API PATH</th><th className="py-2 font-mono">REQUESTS</th></tr></thead><tbody>{data.visitors.map((visitor) => <tr key={visitor.ip_address} className="border-b border-admin-border/50"><td className="py-3 pr-4 font-mono text-admin-text-primary">{visitor.ip_address}</td><td className="py-3 pr-4 text-admin-text-secondary">{new Date(visitor.last_seen).toLocaleTimeString()}</td><td className="py-3 pr-4 font-mono text-admin-text-muted">{visitor.last_path}</td><td className="py-3 font-mono text-admin-text-secondary">{visitor.request_count}</td></tr>)}</tbody></table></div> : <p className="py-5 text-center text-xs font-mono text-admin-text-muted">No visitor API requests observed in the last five minutes.</p>}
        <p className="mt-3 text-[11px] text-admin-text-muted">This is an IP-based estimate, not a reliable device or person count. Shared networks and VPNs may show one address for multiple viewers. IPs are held in API process memory only and expire from this view after five minutes.</p>
      </div>

      <div className="admin-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="font-mono text-sm text-admin-text-secondary uppercase tracking-wider flex items-center gap-2">
              <Network className="w-4 h-4 text-admin-neon-green" />
              LIVE API TRAFFIC
            </h2>
            <p className="mt-1 text-xs text-admin-text-muted">Incoming and outgoing HTTP payload rates | sampled every 5 seconds</p>
          </div>
          <div className="flex gap-4 font-mono text-xs">
            <span className="text-cyan-300">IN v {data.metrics?.incomingMBps?.toFixed(4) ?? "0.0000"} MB/s</span>
            <span className="text-admin-neon-green">OUT ^ {data.metrics?.outgoingMBps?.toFixed(4) ?? "0.0000"} MB/s</span>
          </div>
        </div>
        <svg viewBox="0 0 800 210" className="h-52 w-full overflow-visible" role="img" aria-label="Live incoming and outgoing API traffic chart">
          {[20, 60, 100, 140, 180].map((y) => <line key={y} x1="0" x2="760" y1={y} y2={y} stroke="rgba(148,163,184,0.14)" strokeDasharray="4 6" />)}
          <polyline points={trafficLine("incoming")} fill="none" stroke="#67e8f9" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          <polyline points={trafficLine("outgoing")} fill="none" stroke="#00ff9c" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          <text x="0" y="205" fill="#64748b" fontSize="10">older samples</text>
          <text x="700" y="205" fill="#64748b" fontSize="10">latest</text>
        </svg>
        <p className="text-[11px] text-admin-text-muted font-mono">Measured by this FastAPI process from HTTP Content-Length headers. This is application traffic, not whole-machine network-interface traffic.</p>
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
                      <td className="py-3 pr-4 font-mono tabular-nums text-admin-text-secondary">{service.latency === null ? "—" : `${service.latency}ms`}</td>
                      <td className="py-3 pr-4 font-mono text-admin-text-muted">
                        {new Date(service.lastCheck).toLocaleTimeString()}
                      </td>
                      <td className="py-3 text-admin-text-muted text-xs max-w-xs truncate">{service.details || "N/A"}</td>
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
