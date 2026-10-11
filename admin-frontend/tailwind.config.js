/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Admin Cyber Operations Terminal Theme
        'admin-bg': '#030712',
        'admin-bg-secondary': '#07111F',
        'admin-card': '#0B1728',
        'admin-neon-green': '#00FF9C',
        'admin-neon-cyan': '#00D9FF',
        'admin-purple': '#A855F7',
        'admin-amber': '#FFB020',
        'admin-red': '#FF3B5C',
        'admin-text-primary': '#E6FFF5',
        'admin-text-secondary': '#94A3B8',
        'admin-text-muted': '#64748B',
        'admin-border': 'rgba(0, 255, 156, 0.12)',
        'admin-border-hover': 'rgba(0, 255, 156, 0.3)',
        'admin-sidebar-bg': '#050B16',
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'card': '12px',
        'card-lg': '16px',
      },
      boxShadow: {
        'card': '0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(0, 255, 156, 0.05)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(0, 255, 156, 0.1), 0 0 0 1px rgba(0, 255, 156, 0.2)',
        'neon-green': '0 0 20px rgba(0, 255, 156, 0.3)',
        'neon-cyan': '0 0 20px rgba(0, 217, 255, 0.3)',
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(0, 255, 156, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 156, 0.03) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};