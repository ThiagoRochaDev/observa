'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  api,
  formatMoney,
  PROVIDER_COLORS,
  PROVIDER_LABELS,
  type MetricPoint,
  type ProductDetail,
} from '@/lib/api'

export default function ProductDetailPage() {
  const params = useParams<{ slug: string }>()
  const slug = params.slug
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [latency, setLatency] = useState<MetricPoint[]>([])
  const [errors, setErrors] = useState<MetricPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    Promise.all([
      api.product(slug),
      api.metricSeries('apm.latency_p95_ms', slug),
      api.metricSeries('apm.error_rate_pct', slug),
    ])
      .then(([p, l, e]) => {
        setProduct(p)
        setLatency(l)
        setErrors(e)
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [slug])

  if (error) return <p className="error">{error}</p>
  if (!product) return <p className="muted">Carregando…</p>

  return (
    <div>
      <p className="muted" style={{ marginBottom: 8 }}>
        <Link href="/products">← produtos</Link>
      </p>
      <h1 className="page-title">{product.name || product.slug}</h1>
      <p className="page-sub">
        {product.squad} · {product.tribe} · {formatMoney(product.total_brl)} nos últimos 30d ·{' '}
        <Link href={`/maps?product=${product.slug}`}>ver mapa de ecossistema →</Link>
      </p>

      <div className="grid grid-3" style={{ marginBottom: '1rem' }}>
        {Object.entries(product.by_provider || {}).map(([k, v]) => (
          <div className="card" key={k}>
            <h3>
              <span className="legend-dot" style={{ background: PROVIDER_COLORS[k] || '#888' }} />
              {PROVIDER_LABELS[k] || k}
            </h3>
            <div className="value">{formatMoney(v)}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
        <div className="card">
          <h3>Latência P95 (24h)</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={latency}>
                <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                <XAxis dataKey="ts" hide />
                <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#151b26', border: '1px solid #243044' }} />
                <Area type="monotone" dataKey="value" stroke="#5d87ff" fill="#5d87ff33" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h3>Error rate % (24h)</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={errors}>
                <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                <XAxis dataKey="ts" hide />
                <YAxis tick={{ fill: '#8b9cb3', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#151b26', border: '1px solid #243044' }} />
                <Area type="monotone" dataKey="value" stroke="#fa896b" fill="#fa896b33" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Custo por serviço</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Serviço</th>
                <th>Custo</th>
              </tr>
            </thead>
            <tbody>
              {product.service_costs.map((s) => (
                <tr key={s.service}>
                  <td>{s.service}</td>
                  <td>{formatMoney(s.total_brl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Recursos</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Nome</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {product.resources.map((r) => (
                <tr key={r.id}>
                  <td>
                    <span className="badge">{r.type}</span>
                  </td>
                  <td>{r.name || r.id}</td>
                  <td>
                    <span className="badge ok">{r.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
