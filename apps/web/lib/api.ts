const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(body || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const PROVIDER_COLORS: Record<string, string> = {
  gcp: '#4285F4',
  aws: '#FF9900',
  datadog: '#632CA6',
  gitlab: '#FC6D26',
}

export const PROVIDER_LABELS: Record<string, string> = {
  gcp: 'Google Cloud',
  aws: 'AWS',
  datadog: 'Datadog',
  gitlab: 'GitLab CI',
}

// Badge color + monogram per connector `icon` slug. Used by <ConnectorIcon>
// instead of shipping real trademarked logo artwork — a colored badge with
// the tool's initials is enough to make each connector recognizable in the
// catalog without redistributing anyone's brand assets.
export const CONNECTOR_ICONS: Record<string, { label: string; color: string; mono: string }> = {
  mock: { label: 'Mock Demo', color: '#6b7280', mono: 'MD' },
  aws: { label: 'AWS', color: '#FF9900', mono: 'AW' },
  gcp: { label: 'Google Cloud', color: '#4285F4', mono: 'GC' },
  azure: { label: 'Azure', color: '#0078D4', mono: 'AZ' },
  oci: { label: 'Oracle Cloud', color: '#F80000', mono: 'OC' },
  digitalocean: { label: 'DigitalOcean', color: '#0080FF', mono: 'DO' },
  linode: { label: 'Linode', color: '#00A95C', mono: 'LI' },
  cloudflare: { label: 'Cloudflare', color: '#F38020', mono: 'CF' },
  vercel: { label: 'Vercel', color: '#000000', mono: 'VC' },
  netlify: { label: 'Netlify', color: '#00C7B7', mono: 'NF' },
  mongodb: { label: 'MongoDB Atlas', color: '#00ED64', mono: 'MG' },
  datadog: { label: 'Datadog', color: '#632CA6', mono: 'DD' },
  newrelic: { label: 'New Relic', color: '#008C99', mono: 'NR' },
  grafana: { label: 'Grafana Cloud', color: '#F46800', mono: 'GF' },
  elastic: { label: 'Elastic', color: '#005571', mono: 'EL' },
  sentry: { label: 'Sentry', color: '#362D59', mono: 'SN' },
  pagerduty: { label: 'PagerDuty', color: '#06AC38', mono: 'PD' },
  opsgenie: { label: 'Opsgenie', color: '#2684FF', mono: 'OG' },
  github: { label: 'GitHub', color: '#181717', mono: 'GH' },
  gitlab: { label: 'GitLab', color: '#FC6D26', mono: 'GL' },
  bitbucket: { label: 'Bitbucket', color: '#0052CC', mono: 'BB' },
  kubernetes: { label: 'Kubernetes', color: '#326CE5', mono: 'K8' },
  onprem: { label: 'On-premise', color: '#4b5563', mono: 'OP' },
  splunk: { label: 'Splunk', color: '#000000', mono: 'SP' },
  stripe: { label: 'Stripe', color: '#635BFF', mono: 'ST' },
  snowflake: { label: 'Snowflake', color: '#29B5E8', mono: 'SF' },
  generic: { label: 'Custom', color: '#9ca3af', mono: '?' },
}

export const CATEGORY_LABELS: Record<string, string> = {
  demo: 'Demo',
  cloud: 'Cloud providers',
  observability: 'Observability & APM',
  incident: 'Incident management',
  vcs_cicd: 'Source control & CI/CD',
  on_prem: 'On-premise & self-hosted',
  saas: 'Billing & data SaaS',
}

export const api = {
  health: () => req<Health>('/api/health'),
  seedDemo: () => req<Record<string, unknown>>('/api/demo/seed', { method: 'POST' }),
  connectors: () => req<Connector[]>('/api/connectors'),
  connections: () => req<Connection[]>('/api/connections'),
  createConnection: (body: {
    name: string
    connector_id: string
    config: Record<string, unknown>
    secrets: Record<string, unknown>
  }) =>
    req<Connection>('/api/connections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteConnection: (id: string) =>
    req<{ ok: boolean }>(`/api/connections/${id}`, { method: 'DELETE' }),
  syncConnection: (id: string) =>
    req<Record<string, unknown>>(`/api/connections/${id}/sync`, { method: 'POST' }),
  testConnection: (body: {
    connector_id: string
    config: Record<string, unknown>
    secrets: Record<string, unknown>
  }) =>
    req<{ ok: boolean; message: string }>('/api/connections/test', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  authSettings: () => req<AuthSettings>('/api/auth/settings'),
  saveAuthSettings: (body: AuthSettings) =>
    req<{ ok: boolean }>('/api/auth/settings', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  costSummary: (days = 30) => req<CostSummary>(`/api/costs/summary?days=${days}`),
  costTrend: (days = 30) => req<TrendPoint[]>(`/api/costs/trend?days=${days}`),
  products: () => req<Product[]>('/api/products'),
  product: (slug: string) => req<ProductDetail>(`/api/products/${encodeURIComponent(slug)}`),
  resources: (product?: string) =>
    req<Resource[]>(`/api/resources${product ? `?product=${encodeURIComponent(product)}` : ''}`),
  observability: () => req<ObservabilityOverview>('/api/observability'),
  metricSeries: (name: string, product?: string) => {
    const q = new URLSearchParams({ name })
    if (product) q.set('product', product)
    return req<MetricPoint[]>(`/api/metrics/series?${q}`)
  },
  alerts: (status?: string) =>
    req<Alert[]>(`/api/alerts${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  ecosystem: (product = 'hiperlocal') =>
    req<Ecosystem>(`/api/ecosystem?product=${encodeURIComponent(product)}`),
  dashboards: () => req<DashboardMeta[]>('/api/dashboards'),
  dashboard: (id: string) => req<DashboardDetail>(`/api/dashboards/${encodeURIComponent(id)}`),
  monitors: () => req<Monitor[]>('/api/monitors'),
  logs: (params?: {
    limit?: number
    product?: string
    severity?: string
    source?: string
    q?: string
  }) => {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.product) q.set('product', params.product)
    if (params?.severity) q.set('severity', params.severity)
    if (params?.source) q.set('source', params.source)
    if (params?.q) q.set('q', params.q)
    const s = q.toString()
    return req<LogRow[]>(`/api/logs${s ? `?${s}` : ''}`)
  },
  traces: () => req<TraceRow[]>('/api/traces'),
  gcpMonitoring: () => req<GcpMonitoring>('/api/gcp/monitoring'),
  rum: () => req<RumSummary>('/api/rum'),
  synthetics: () => req<Synthetic[]>('/api/synthetics'),
}

export type Health = {
  status: string
  connections: number
  cost_records: number
  open_alerts?: number
  metric_series?: number
  auth_mode: string
  demo?: boolean
}

export type Connector = {
  id: string
  name: string
  description: string
  capabilities: string[]
  category: string
  icon: string
  docs_url: string
  config_schema: JsonSchema
  secrets_schema: JsonSchema
}

export type JsonSchema = {
  type?: string
  properties?: Record<
    string,
    { type?: string; title?: string; default?: unknown; minimum?: number; maximum?: number }
  >
  required?: string[]
}

export type Connection = {
  id: string
  name: string
  connector_id: string
  config: Record<string, unknown>
  enabled: boolean
  last_sync_at?: string | null
  last_sync_status?: string | null
  last_sync_message?: string | null
}

export type AuthSettings = {
  mode: string
  providers: Record<
    string,
    {
      enabled?: boolean
      client_id?: string
      client_secret?: string
      issuer?: string
      redirect_uri?: string
      has_client_secret?: boolean
    }
  >
}

export type CostSummary = {
  days: number
  total: number
  previous_total?: number
  change_pct?: number
  by_provider: Record<string, number>
  by_product: Record<string, number>
  by_squad?: Record<string, number>
  records: number
  open_alerts?: number
}

export type TrendPoint = {
  date: string
  total: number
  gcp?: number
  aws?: number
  datadog?: number
  gitlab?: number
}

export type Product = {
  slug: string
  name?: string
  squad?: string
  tribe?: string
  aliases?: string[]
  services?: string[]
  total_brl: number
  service_count: number
  resource_count: number
}

export type ProductDetail = Product & {
  by_provider: Record<string, number>
  service_costs: { service: string; total_brl: number }[]
  resources: Resource[]
  metrics_latest: MetricSample[]
}

export type Resource = {
  provider: string
  type: string
  id: string
  name?: string
  region?: string
  product?: string
  squad?: string
  status?: string
  labels?: Record<string, string>
}

export type MetricSample = {
  name: string
  value: number
  unit: string
  ts: string
  resource_id?: string
  product?: string
  labels?: Record<string, string>
}

export type MetricPoint = { ts: string; value: number; unit?: string }

export type ObservabilityOverview = {
  products: {
    product: string
    latency_p95_ms: number | null
    error_rate_pct: number | null
    rpm: number | null
    cpu_pct: number | null
    db_connections: number | null
    db_cpu_pct: number | null
  }[]
  metric_count: number
  alert_count: number
}

export type Alert = {
  id: string
  severity: string
  category: string
  product?: string
  title: string
  message?: string
  status: string
  detected_at: string
}

export type Ecosystem = {
  product: string
  nodes: { id: string; label: string; kind: string; tier: number; type?: string }[]
  edges: { source: string; target: string; label?: string }[]
}

export type DashboardMeta = {
  id: string
  title: string
  source: string
  description: string
  widgets: number
  tags: string[]
}

export type DashboardPanel = {
  id: string
  title: string
  type: string
  series?: { ts: string; value: number }[]
  items?: { name: string; value: number }[]
  value?: number
  unit?: string
  status?: string
}

export type DashboardDetail = {
  id: string
  title: string
  panels: DashboardPanel[]
}

export type Monitor = {
  id: string
  name: string
  type: string
  status: string
  product?: string
  query: string
  source: string
}

export type LogRow = {
  ts: string
  severity: string
  product: string
  service: string
  source: string
  message: string
  trace_id?: string
  labels?: Record<string, string>
}

export type TraceSpan = {
  service: string
  name: string
  start_ms: number
  duration_ms: number
  status: string
}

export type TraceRow = {
  trace_id: string
  product: string
  service: string
  resource: string
  duration_ms: number
  status: string
  spans: number
  span_details?: TraceSpan[]
  ts: string
}

export type GcpMonitoring = {
  project: string
  metrics: { type: string; display: string; series: { ts: string; value: number }[] }[]
}

export type RumSummary = {
  sessions_30d: number
  avg_lcp_ms: number
  js_errors: number
  crash_free_pct: number
  top_views: { view: string; sessions: number; errors: number }[]
}

export type Synthetic = {
  id: string
  name: string
  type: string
  status: string
  locations: number
  uptime_pct: number
}

export function formatMoney(value: number, currency = 'BRL') {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatPct(value: number) {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}
