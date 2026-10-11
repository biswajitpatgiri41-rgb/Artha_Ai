import { ReactNode } from 'react';
import { AdminAuthProvider } from '@/lib/auth';
import './globals.css';

export const metadata = {
  title: 'INDIA MACRO AI - SYSTEM CONTROL',
  description: 'Agentic Monetary Policy Administration Terminal',
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen bg-admin-bg text-admin-text-primary font-sans antialiased">
        <AdminAuthProvider>
          {children}
        </AdminAuthProvider>
      </body>
    </html>
  );
}
