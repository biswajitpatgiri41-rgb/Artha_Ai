'use client';

import { ReactNode, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Activity, AlertOctagon, Bell, Bot, Brain, ChevronLeft, ChevronRight,
  ClipboardList, Command, Cpu, Database, FileText, FlaskConical, GitBranch,
  Layers, LayoutDashboard, LineChart, Menu, Package, Search, Server,
  Settings, Shield, Terminal, TrendingUp, Users, X, Zap,
} from 'lucide-react';

type NavLink = { label: string; href: string; icon: typeof Activity };
type NavSection = { label: string; children: NavLink[] } | NavLink;

export const NAVIGATION: NavSection[] = [
  { label: 'OVERVIEW', href: '/overview', icon: LayoutDashboard },
  { label: 'SYSTEM HEALTH', children: [
    { label: 'System Health', href: '/system-health', icon: Activity },
    { label: 'Infrastructure', href: '/infrastructure', icon: Cpu },
    { label: 'Services', href: '/services', icon: Server },
  ] },
  { label: 'DATA OPERATIONS', children: [
    { label: 'Data Health', href: '/data-health', icon: Database },
    { label: 'Data Pipeline', href: '/data-pipeline', icon: GitBranch },
    { label: 'Data Versions', href: '/data-versions', icon: Package },
    { label: 'Data Validation', href: '/data-validation', icon: Search },
  ] },
  { label: 'MODEL OPS', children: [
    { label: 'Model Registry', href: '/models', icon: Brain },
    { label: 'Model Drift', href: '/model-drift', icon: TrendingUp },
    { label: 'Experiments', href: '/experiments', icon: Zap },
    { label: 'Deployments', href: '/deployments', icon: Shield },
    { label: 'Inference Logs', href: '/inference-logs', icon: Terminal },
  ] },
  { label: 'AGENT OPERATIONS', children: [
    { label: 'Agent Status', href: '/agent-status', icon: Bot },
    { label: 'Agent Executions', href: '/agent-executions', icon: Activity },
  ] },
  { label: 'KNOWLEDGE BASE', children: [
    { label: 'Knowledge Base', href: '/knowledge-base', icon: Database },
    { label: 'Documents', href: '/knowledge-base/documents', icon: FileText },
    { label: 'Index Status', href: '/knowledge-base/index', icon: Cpu },
  ] },
  { label: 'FORECAST & SCENARIO', children: [
    { label: 'Forecast Operations', href: '/forecast-operations', icon: LineChart },
    { label: 'Scenario Engine', href: '/scenario-engine', icon: FlaskConical },
  ] },
  { label: 'SECURITY & ACCESS', children: [
    { label: 'Security Events', href: '/security', icon: Shield },
    { label: 'Users', href: '/users', icon: Users },
    { label: 'Audit Logs', href: '/audit-logs', icon: ClipboardList },
  ] },
  { label: 'INCIDENTS & JOBS', children: [
    { label: 'Incidents', href: '/incidents', icon: AlertOctagon },
    { label: 'Notifications', href: '/notifications', icon: Bell },
    { label: 'Background Jobs', href: '/background-jobs', icon: Layers },
  ] },
  { label: 'ADMINISTRATION', children: [
    { label: 'Settings', href: '/settings', icon: Settings },
  ] },
];

function isLink(item: NavSection): item is NavLink {
  return 'href' in item;
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [search, setSearch] = useState('');
  const links = useMemo(() => NAVIGATION.flatMap((section) => isLink(section) ? [section] : section.children), []);
  const filteredLinks = links.filter((item) => item.label.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandPaletteOpen(true);
      }
      if (event.key === 'Escape') setCommandPaletteOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const navigate = (href: string) => {
    setCommandPaletteOpen(false);
    setSidebarOpen(false);
    router.push(href);
  };

  return (
    <div className="min-h-screen bg-admin-bg text-admin-text-primary flex">
      {sidebarOpen && <button className="fixed inset-0 z-40 bg-black/70 lg:hidden" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`fixed lg:sticky top-0 z-50 h-screen shrink-0 transition-all duration-200 bg-admin-card border-r border-admin-border flex flex-col ${sidebarCollapsed ? 'w-16' : 'w-64'} ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="flex items-center justify-between h-16 px-4 border-b border-admin-border shrink-0">
          {!sidebarCollapsed && <Link href="/overview" className="min-w-0">
            <p className="font-bold text-admin-text-primary text-sm">INDIA MACRO AI</p>
            <p className="font-mono text-xs text-admin-neon-green">SYSTEM CONTROL</p>
          </Link>}
          <button onClick={() => setSidebarCollapsed((value) => !value)} className="topbar-item p-2 hidden lg:block" aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
          <button onClick={() => setSidebarOpen(false)} className="topbar-item p-2 lg:hidden" aria-label="Close navigation"><X size={18} /></button>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1" aria-label="Admin navigation">
          {NAVIGATION.map((section) => isLink(section) ? (
            <Link key={section.href} href={section.href} onClick={() => setSidebarOpen(false)} title={section.label} className={`sidebar-nav-item ${pathname === section.href ? 'sidebar-nav-item-active' : ''}`}>
              <section.icon className="sidebar-nav-item-icon" /><span className={sidebarCollapsed ? 'sr-only' : 'font-mono text-xs'}>{section.label}</span>
            </Link>
          ) : <div key={section.label} className="pt-3">
            {!sidebarCollapsed && <p className="sidebar-nav-section">{section.label}</p>}
            {section.children.map((item) => <Link key={item.href} href={item.href} onClick={() => setSidebarOpen(false)} title={item.label} aria-current={pathname === item.href ? 'page' : undefined} className={`sidebar-nav-item ${pathname === item.href ? 'sidebar-nav-item-active' : ''}`}>
              <item.icon className="sidebar-nav-item-icon" /><span className={sidebarCollapsed ? 'sr-only' : 'font-mono text-xs'}>{item.label}</span>
            </Link>)}
          </div>)}
        </nav>
        {!sidebarCollapsed && <div className="p-3 border-t border-admin-border shrink-0">
          <div className="rounded-lg bg-admin-bg-secondary/70 p-3">
            <p className="font-mono text-xs text-admin-text-primary">Local Developer</p>
            <p className="font-mono text-[10px] text-admin-neon-green mt-1">LOCAL DEVELOPMENT ACCESS</p>
          </div>
        </div>}
      </aside>

      <div className="min-w-0 flex-1 flex flex-col">
        <header className="h-16 shrink-0 bg-admin-card/80 backdrop-blur border-b border-admin-border flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="topbar-item p-2 lg:hidden" aria-label="Open navigation"><Menu size={20} /></button>
            <button onClick={() => { setSearch(''); setCommandPaletteOpen(true); }} className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-lg bg-admin-bg-secondary border border-admin-border text-admin-text-muted" aria-label="Search admin pages">
              <Command size={16} /><span className="font-mono text-xs">Search pages...</span><kbd className="text-[10px]">Ctrl K</kbd>
            </button>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline font-mono text-xs text-admin-text-secondary">LOCAL DEV</span>
            <button onClick={() => navigate('/activity')} className="topbar-item p-2" aria-label="View activity"><Bell size={19} /></button>
            <span className="hidden md:inline font-mono text-xs text-admin-text-primary">Local Developer</span>
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6 overflow-auto">{children}</main>
      </div>

      {commandPaletteOpen && <div className="fixed inset-0 z-[60] bg-black/70 flex items-start justify-center p-4 pt-[12vh]" onMouseDown={(event) => { if (event.target === event.currentTarget) setCommandPaletteOpen(false); }}>
        <div className="w-full max-w-xl bg-admin-card border border-admin-border rounded-card shadow-card overflow-hidden">
          <div className="flex items-center gap-3 p-4 border-b border-admin-border"><Search size={18} className="text-admin-text-muted" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search admin pages..." className="flex-1 bg-transparent outline-none text-admin-text-primary" /><button onClick={() => setCommandPaletteOpen(false)} aria-label="Close search"><X size={18} /></button></div>
          <div className="p-2 max-h-[55vh] overflow-y-auto">{filteredLinks.map((item) => <button key={item.href} onClick={() => navigate(item.href)} className="w-full flex items-center gap-3 p-3 rounded-lg text-left hover:bg-admin-bg-secondary"><item.icon size={17} className="text-admin-neon-green" /><span className="text-sm">{item.label}</span><ChevronRight size={15} className="ml-auto text-admin-text-muted" /></button>)}{filteredLinks.length === 0 && <p className="p-4 text-sm text-admin-text-muted">No matching page.</p>}</div>
        </div>
      </div>}
    </div>
  );
}
