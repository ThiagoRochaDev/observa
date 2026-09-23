'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { api, getCompanyId, getTenancyId, setTenantContext, type Company, type Tenancy } from '@/lib/api'

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
  governance: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M12 3 4 7v5c0 5 3.5 8 8 9 4.5-1 8-4 8-9V7l-8-4Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  ),
  budgets: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <circle cx="12" cy="12" r="9" />
      <path d="M16 8.5c-.8-.7-2-1-3.4-1-1.9 0-3.1.8-3.1 2s1.1 1.8 3.1 2.2 3.3.8 3.3 2.4-1.4 2.4-3.5 2.4c-1.5 0-2.9-.4-3.8-1.2M12 5.5v13" />
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
  remediations: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="m14.5 6.5 3-3 3 3-3 3M13 8l-8.5 8.5a2.1 2.1 0 0 0 3 3L16 11" />
      <path d="M4 5h6M7 2v6" />
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
  organizations: (
    <svg width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
      <path d="M4 21V7l8-4 8 4v14M8 21v-4h8v4M8 9h1M12 9h1M16 9h1M8 13h1M12 13h1M16 13h1" />
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
      { href: '/budgets', label: 'Budgets', description: 'Limits, forecast & actions', icon: 'budgets' },
      { href: '/governance', label: 'Governance', description: 'Tags, schedules & approvals', icon: 'governance' },
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
      { href: '/remediations', label: 'Remediations', description: 'Diagnose & approve fixes', icon: 'remediations' },
    ],
  },
  {
    title: 'Platform',
    links: [
      { href: '/settings/organizations', label: 'Organizations', description: 'Companies & tenancies', icon: 'organizations' },
      { href: '/connections', label: 'Connections', description: 'Connectors & credentials', icon: 'connections' },
      { href: '/settings/auth', label: 'Authentication', description: 'SSO & access', icon: 'auth' },
    ],
  },
] as const

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [companies, setCompanies] = useState<Company[]>([])
  const [tenancies, setTenancies] = useState<Tenancy[]>([])
  const [companyId, setCompanyId] = useState('')
  const [tenancyId, setTenancyId] = useState('')

  useEffect(() => {
    Promise.all([api.companies(), api.tenancies()]).then(([companyRows, tenancyRows]) => {
      const selectedCompany = companyRows.some((row) => row.id === getCompanyId())
        ? getCompanyId()
        : companyRows[0]?.id || ''
      const companyTenancies = tenancyRows.filter((row) => row.company_id === selectedCompany)
      const selectedTenancy = companyTenancies.some((row) => row.id === getTenancyId())
        ? getTenancyId()
        : companyTenancies[0]?.id || ''
      setCompanies(companyRows)
      setTenancies(tenancyRows)
      setCompanyId(selectedCompany)
      setTenancyId(selectedTenancy)
      if (selectedCompany && selectedTenancy) setTenantContext(selectedCompany, selectedTenancy)
    }).catch(() => undefined)
  }, [])

  function selectCompany(nextCompanyId: string) {
    const firstTenancy = tenancies.find((row) => row.company_id === nextCompanyId)
    setCompanyId(nextCompanyId)
    setTenancyId(firstTenancy?.id || '')
    if (firstTenancy) {
      setTenantContext(nextCompanyId, firstTenancy.id)
      window.location.reload()
    }
  }

  function selectTenancy(nextTenancyId: string) {
    setTenancyId(nextTenancyId)
    setTenantContext(companyId, nextTenancyId)
    window.location.reload()
  }

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

        <div className="tenant-switcher">
          <label>
            Company
            <select value={companyId} onChange={(event) => selectCompany(event.target.value)}>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </label>
          <label>
            Tenancy
            <select value={tenancyId} onChange={(event) => selectTenancy(event.target.value)}>
              {tenancies.filter((row) => row.company_id === companyId).map((tenancy) => (
                <option key={tenancy.id} value={tenancy.id}>{tenancy.name}</option>
              ))}
            </select>
          </label>
        </div>

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
