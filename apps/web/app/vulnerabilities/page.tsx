'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { api, type Vulnerability, type VulnerabilitySummary } from '@/lib/api'

const EMPTY_SUMMARY: VulnerabilitySummary = {
  total: 0, active: 0, critical: 0, high: 0, exploitable: 0,
  internet_exposed: 0, overdue: 0, by_provider: {}, by_priority: {},
}

function errorMessage(cause: unknown) {
  if (!(cause instanceof Error)) return String(cause)
  try {
    const parsed = JSON.parse(cause.message)
    return parsed.detail || cause.message
  } catch {
    return cause.message
  }
}

function dateLabel(value?: string | null) {
  if (!value) return 'sem SLA'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

export default function VulnerabilitiesPage() {
  const [rows, setRows] = useState<Vulnerability[]>([])
  const [summary, setSummary] = useState<VulnerabilitySummary>(EMPTY_SUMMARY)
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [provider, setProvider] = useState('')
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    const [findings, totals] = await Promise.all([
      api.vulnerabilities({ status, severity, provider }),
      api.vulnerabilitySummary(),
    ])
    setRows(findings)
    setSummary(totals)
  }

  useEffect(() => {
    let active = true
    Promise.all([api.vulnerabilities({ status, severity, provider }), api.vulnerabilitySummary()])
      .then(([findings, totals]) => { if (active) { setRows(findings); setSummary(totals) } })
      .catch((cause) => { if (active) setError(errorMessage(cause)) })
    return () => { active = false }
  }, [status, severity, provider])

  const providers = useMemo(
    () => Object.keys(summary.by_provider).sort(),
    [summary.by_provider],
  )

  async function changeStatus(row: Vulnerability, nextStatus: 'accepted' | 'resolved' | 'false_positive') {
    setBusy(row.id)
    setError('')
    try {
      await api.updateVulnerabilityStatus(row.id, nextStatus)
      setMessage(nextStatus === 'accepted' ? 'Risco aceito e registrado na auditoria.' : 'Finding atualizado com sucesso.')
      await load()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy('')
    }
  }

  async function requestRemediation(row: Vulnerability) {
    setBusy(row.id)
    setError('')
    try {
      await api.requestVulnerabilityRemediation(row.id, { dry_run: true })
      setMessage('Proposta dry-run criada. Um owner/admin deve aprová-la em Remediações.')
      await load()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="vuln-page">
      <header className="page-header">
        <div>
          <span className="migration-eyebrow">Segurança · cloud e on-premises</span>
          <h1 className="page-header-title">Vulnerabilidades</h1>
          <p className="page-header-desc">Findings normalizados por recurso, produto e tenancy, com priorização por exposição e exploração.</p>
        </div>
        <button className="btn" onClick={() => load()} disabled={Boolean(busy)}>Atualizar visão</button>
      </header>

      <section className="vuln-privacy card">
        <strong>Isolamento e aprovação por padrão</strong>
        <span>Payloads ficam na tenancy atual. O Observa não aplica patches: ele cria uma proposta auditável e começa sempre em dry-run.</span>
      </section>

      <section className="vuln-kpis">
        <article className="card"><span>Ativas</span><strong>{summary.active}</strong><small>{summary.total} findings totais</small></article>
        <article className="card danger"><span>Críticas</span><strong>{summary.critical}</strong><small>{summary.high} altas</small></article>
        <article className="card"><span>Exploráveis</span><strong>{summary.exploitable}</strong><small>evidência do scanner</small></article>
        <article className="card"><span>Expostas</span><strong>{summary.internet_exposed}</strong><small>{summary.overdue} fora do SLA</small></article>
      </section>

      <section className="card vuln-toolbar">
        <label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option><option value="open">Aberta</option><option value="remediation_pending">Correção pendente</option><option value="accepted">Risco aceito</option><option value="resolved">Resolvida</option><option value="false_positive">Falso positivo</option></select></label>
        <label>Severidade<select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">Todas</option><option value="critical">Crítica</option><option value="high">Alta</option><option value="medium">Média</option><option value="low">Baixa</option></select></label>
        <label>Ambiente<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="">Todos</option>{providers.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <span>{rows.length} resultado(s)</span>
      </section>

      {message && <div className="demo-banner">{message} <Link href="/remediations">Abrir remediações →</Link></div>}
      {error && <div className="migration-error">{error}</div>}

      <section className="vuln-list">
        {rows.map((row) => (
          <article className={`card vuln-finding priority-${row.priority}`} key={row.id}>
            <div className="vuln-finding-head">
              <div className="vuln-title">
                <span className={`vuln-severity ${row.severity}`}>{row.severity}</span>
                <div><h2>{row.title}</h2><p>{row.provider} · {row.resource_id}</p></div>
              </div>
              <div className="vuln-score"><strong>{row.risk_score.toFixed(1)}</strong><span>{row.priority}</span></div>
            </div>
            <div className="vuln-tags">
              {row.cve && <span>{row.cve}</span>}
              {row.product && <span>produto: {row.product}</span>}
              {row.environment && <span>env: {row.environment}</span>}
              {row.exploitable && <span className="danger">explorável</span>}
              {row.internet_exposed && <span className="danger">internet</span>}
              <span>status: {row.status}</span>
            </div>
            {row.description && <p className="vuln-description">{row.description}</p>}
            <div className="vuln-details">
              <div><span>Origem</span><strong>{row.source}</strong></div>
              <div><span>Pacote</span><strong>{row.package_name || 'configuração / recurso'}</strong></div>
              <div><span>Versão</span><strong>{row.installed_version || '—'} → {row.fixed_version || 'mitigação manual'}</strong></div>
              <div><span>SLA</span><strong>{dateLabel(row.due_at)}</strong></div>
            </div>
            <div className="vuln-actions">
              {row.status !== 'resolved' && row.status !== 'false_positive' && <>
                <button className="btn btn-primary" disabled={busy === row.id || row.status === 'remediation_pending'} onClick={() => requestRemediation(row)}>{row.status === 'remediation_pending' ? 'Aguardando aprovação' : 'Solicitar correção dry-run'}</button>
                <button className="btn" disabled={busy === row.id} onClick={() => changeStatus(row, 'accepted')}>Aceitar risco</button>
                <button className="btn" disabled={busy === row.id} onClick={() => changeStatus(row, 'resolved')}>Marcar resolvida</button>
                <button className="btn" disabled={busy === row.id} onClick={() => changeStatus(row, 'false_positive')}>Falso positivo</button>
              </>}
            </div>
          </article>
        ))}
        {!rows.length && <div className="card muted">Nenhum finding corresponde aos filtros desta tenancy.</div>}
      </section>
    </div>
  )
}
