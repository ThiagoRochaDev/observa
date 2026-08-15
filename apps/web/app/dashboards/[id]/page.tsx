'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type DashboardDetail, type DashboardPanel } from '@/lib/api'

function statusClass(status?: string) {
  if (status === 'alert') return 'high'
  if (status === 'warn') return 'medium'
  return 'ok'
}

function QueryValue({ panel }: { panel: DashboardPanel }) {
  return (
    <div className="card query-value">
      <h3>{panel.title}</h3>
      <div className="value">
        {typeof panel.value === 'number'
          ? panel.value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
          : '—'}
        {panel.unit ? <span className="qv-unit">{panel.unit}</span> : null}
      </div>
      {panel.status && (
        <span className={`badge ${statusClass(panel.status)}`}>{panel.status}</span>
      )}
    </div>
  )
}

function TimeseriesPanel({ panel }: { panel: DashboardPanel }) {
  const data = panel.series || []
  return (
    <div className="card">
      <h3>{panel.title}</h3>
      <div className="chart-box">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
            <XAxis dataKey="ts" hide />
            <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} width={42} />
            <Tooltip contentStyle={{ background: '#151b26', border: '1px solid #243044' }} />
            <Area type="monotone" dataKey="value" stroke="#3dd6c6" fill="#3dd6c633" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function ToplistPanel({ panel }: { panel: DashboardPanel }) {
  const max = Math.max(...(panel.items || []).map((i) => i.value), 1)
  return (
    <div className="card">
      <h3>{panel.title}</h3>
      <div className="toplist">
        {(panel.items || []).map((it) => (
          <div key={it.name} className="toplist-row">
            <div className="toplist-meta">
              <span>{it.name}</span>
              <strong>{it.value.toLocaleString('pt-BR')}</strong>
            </div>
            <div className="toplist-bar">
              <div style={{ width: `${(it.value / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DashboardDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [dash, setDash] = useState<DashboardDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api
      .dashboard(id)
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [id])

  const { values, rest } = useMemo(() => {
    const panels = dash?.panels || []
    return {
      values: panels.filter((p) => p.type === 'query_value'),
      rest: panels.filter((p) => p.type !== 'query_value'),
    }
  }, [dash])

  if (error) return <p className="error">{error}</p>
  if (!dash) return <p className="muted">Carregando dashboard…</p>

  return (
    <div>
      <p className="muted" style={{ marginBottom: 8 }}>
        <Link href="/dashboards">← dashboards</Link>
      </p>
      <h1 className="page-title">{dash.title}</h1>
      <p className="page-sub">
        Painéis estilo Datadog — query values, timeseries e toplists (demo mock).
      </p>

      {values.length > 0 && (
        <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
          {values.map((p) => (
            <QueryValue key={p.id} panel={p} />
          ))}
        </div>
      )}

      <div className="grid grid-2">
        {rest.map((p) => {
          if (p.type === 'timeseries') return <TimeseriesPanel key={p.id} panel={p} />
          if (p.type === 'toplist') return <ToplistPanel key={p.id} panel={p} />
          return (
            <div className="card" key={p.id}>
              <h3>{p.title}</h3>
              <p className="muted">Widget type: {p.type}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
