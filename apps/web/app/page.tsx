'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  api,
  formatMoney,
  formatPct,
  PROVIDER_COLORS,
  PROVIDER_LABELS,
  type CostSummary,
  type TrendPoint,
} from '@/lib/api'

export default function HomePage() {
  const [summary, setSummary] = useState<CostSummary | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.costSummary(30), api.costTrend(30)])
      .then(([s, t]) => {
        setSummary(s)
        setTrend(t)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const change = summary?.change_pct ?? 0

  return (
    <div>
      <div className="demo-banner">
        Dataset completo simulado (GCP / AWS / Datadog / GitLab + APM + Cloud SQL). Isto é o visual
        alvo com tudo conectado — troque o Mock Demo por conectores reais na UI.
      </div>
      <h1 className="page-title">Visão geral FinOps</h1>
      <p className="page-sub">
        Custos por provider, produto e squad, tudo em um só lugar.
      </p>
      {error && <p className="error">{error}</p>}

      <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Total 30d</h3>
          <div className="value">{summary ? formatMoney(summary.total) : '—'}</div>
          <div className={`delta ${change >= 0 ? 'up' : 'down'}`}>
            {formatPct(change)} vs período anterior
          </div>
        </div>
        <div className="card">
          <h3>Produtos</h3>
          <div className="value">{summary ? Object.keys(summary.by_product).length : '—'}</div>
        </div>
        <div className="card">
          <h3>Providers</h3>
          <div className="value">{summary ? Object.keys(summary.by_provider).length : '—'}</div>
        </div>
        <div className="card">
          <h3>Alertas abertos</h3>
          <div className="value">{summary?.open_alerts ?? '—'}</div>
          <div className="muted" style={{ marginTop: 4 }}>
            <Link href="/alerts">ver alertas →</Link>
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Tendência diária</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fill: '#8b9cb3', fontSize: 11 }} hide={trend.length > 20} />
                <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#151b26', border: '1px solid #243044' }}
                  formatter={(v: number) => formatMoney(v)}
                />
                <Area type="monotone" dataKey="total" stroke="#5d87ff" fill="#5d87ff33" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h3>Por provider</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(summary?.by_provider || {}).map(([k, v]) => ({
                  name: PROVIDER_LABELS[k] || k,
                  key: k,
                  value: v,
                }))}
              >
                <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: '#8b9cb3', fontSize: 11 }} />
                <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#151b26', border: '1px solid #243044' }}
                  formatter={(v: number) => formatMoney(v)}
                />
                <Bar dataKey="value" fill="#13deb9" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="pill-row">
            {Object.keys(summary?.by_provider || {}).map((k) => (
              <span key={k} className="badge">
                <span className="legend-dot" style={{ background: PROVIDER_COLORS[k] || '#888' }} />
                {PROVIDER_LABELS[k] || k}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Por produto</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Custo</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary?.by_product || {}).map(([k, v]) => (
                <tr key={k}>
                  <td>
                    <Link href={`/products/${k}`}>{k}</Link>
                  </td>
                  <td>{formatMoney(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Por squad</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Squad</th>
                <th>Custo</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary?.by_squad || {}).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{formatMoney(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
