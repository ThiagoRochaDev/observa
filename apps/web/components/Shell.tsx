'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

const ICON_STROKE = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.75 } as const

const ICONS: Record<string, ReactNode> = {
  overview: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M8 15l3-4 3 2 4-6" />
    </svg>
  ),
  products: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  maps: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="12" cy="18" r="2.5" />
      <path d="M8 7.2L11 16M16 7.2L13 16" />
    </svg>
  ),
  inventory: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <ellipse cx="12" cy="6" rx="8" ry="3" />
      <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" />
      <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
    </svg>
  ),
  dashboards: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18M9 21V9" />
    </svg>
  ),
  observability: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M3 12h4l2-7 4 14 2-7h6" />
    </svg>
  ),
  logs: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M4 6h16M4 12h16M4 18h10" />
    </svg>
  ),
  traces: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <rect x="3" y="5" width="12" height="3" rx="1" />
      <rect x="7" y="10.5" width="14" height="3" rx="1" />
      <rect x="5" y="16" width="9" height="3" rx="1" />
    </svg>
  ),
  monitors: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M12 3a6 6 0 0 1 6 6c0 4-2.5 5.5-2.5 8.5h-7C8.5 14.5 6 13 6 9a6 6 0 0 1 6-6Z" />
      <path d="M9.5 20.5h5" />
    </svg>
  ),
  rum: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M3.5 12h17M12 3.5c2.5 2.3 3.9 5.3 3.9 8.5s-1.4 6.2-3.9 8.5c-2.5-2.3-3.9-5.3-3.9-8.5S9.5 5.8 12 3.5Z" />
    </svg>
  ),
  gcp: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M7 17a4.5 4.5 0 0 1-.6-8.96 5.5 5.5 0 0 1 10.7-1.6A4 4 0 0 1 17 17H7Z" />
    </svg>
  ),
  alerts: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M10.3 3.9 2.6 18a1.5 1.5 0 0 0 1.3 2.2h16.2a1.5 1.5 0 0 0 1.3-2.2L13.7 3.9a1.5 1.5 0 0 0-2.6 0Z" />
      <path d="M12 10v4M12 17.2v.1" />
    </svg>
  ),
  connections: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M9 15 15 9M8.5 8.5l-2 2a3.5 3.5 0 0 0 5 5l2-2M15.5 15.5l2-2a3.5 3.5 0 0 0-5-5l-2 2" />
    </svg>
  ),
  auth: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  ),
}

const GROUPS = [
  {
    title: 'FinOps & Catalog',
    links: [
      { href: '/', label: 'Overview', description: 'Cost & health at a glance', icon: 'overview' },
      { href: '/products', label: 'Products', description: 'Business catalog & spend', icon: 'products' },
      { href: '/maps', label: 'Ecosystem maps', description: 'Service topology', icon: 'maps' },
      { href: '/inventory', label: 'Inventory', description: 'Cloud resources', icon: 'inventory' },
    ],
  },
  {
    title: 'Observability',
    links: [
      { href: '/dashboards', label: 'Dashboards', description: 'Custom widget boards', icon: 'dashboards' },
      { href: '/observability', label: 'APM & Infra', description: 'Latency, errors, DB', icon: 'observability' },
      { href: '/logs', label: 'Logs', description: 'Search & filter events', icon: 'logs' },
      { href: '/traces', label: 'Traces', description: 'Distributed request flow', icon: 'traces' },
      { href: '/monitors', label: 'Monitors', description: 'Alert rules & status', icon: 'monitors' },
      { href: '/rum', label: 'RUM & Synthetics', description: 'Real users & uptime', icon: 'rum' },
      { href: '/gcp', label: 'GCP Monitoring', description: 'Metrics & logging', icon: 'gcp' },
      { href: '/alerts', label: 'Alerts', description: 'Open incidents', icon: 'alerts' },
    ],
  },
  {
    title: 'Platform',
    links: [
      { href: '/connections', label: 'Connections', description: 'Connectors & credentials', icon: 'connections' },
      { href: '/settings/auth', label: 'Authentication', description: 'SSO & access', icon: 'auth' },
    ],
  },
] as const

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="dash-layout">
      <aside className="dash-sidebar">
        <Link href="/" className="dash-brand">
          <div className="dash-brand-mark">O</div>
          <div>
            <div className="dash-brand-title">Observa</div>
            <div className="dash-brand-sub">connect · catalog · observe</div>
          </div>
        </Link>

        <nav className="dash-nav" aria-label="Main navigation">
          {GROUPS.map((g) => (
            <div key={g.title}>
              <span className="dash-nav-section">{g.title}</span>
              {g.links.map((l) => {
                const active = pathname === l.href || (l.href !== '/' && pathname.startsWith(`${l.href}/`))
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    prefetch
                    className={`dash-nav-link ${active ? 'active' : ''}`}
                  >
                    <span className="dash-nav-icon">{ICONS[l.icon]}</span>
                    <span className="dash-nav-text">
                      <span className="dash-nav-label">{l.label}</span>
                      <span className="dash-nav-desc">{l.description}</span>
                    </span>
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="dash-sidebar-foot">
          <span>TGR Technology</span>
          <span className="dash-foot-muted">Open source · Apache-2.0</span>
        </div>
      </aside>
      <div className="dash-main">
        <main className="dash-content">{children}</main>
      </div>
    </div>
  )
}
