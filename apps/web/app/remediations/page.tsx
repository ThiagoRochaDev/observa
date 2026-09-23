'use client'

import { useEffect, useState } from 'react'
import { api, type RemediationProposal } from '@/lib/api'

export default function RemediationsPage() {
  const [rows, setRows] = useState<RemediationProposal[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    setRows(await api.remediations())
  }

  useEffect(() => {
    let active = true
    api.remediations()
      .then((result) => { if (active) setRows(result) })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : String(cause)) })
    return () => { active = false }
  }, [])

  async function analyze() {
    setBusy(true)
    setError('')
    try {
      const result = await api.analyzeRemediations({ dry_run: true })
      setMessage(`${result.logs_scanned} logs analisados localmente; ${result.count} sugestões.`)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  async function decide(id: string, approve: boolean) {
    setBusy(true)
    try {
      if (approve) await api.approveRemediation(id)
      else await api.rejectRemediation(id, 'Rejeitado pelo owner no Observa')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Diagnóstico e remediação</h1>
          <p className="page-header-desc">
            Analisa logs dentro da tenancy, propõe correções e só executa mudanças após aprovação explícita.
          </p>
        </div>
        <button className="btn btn-primary" disabled={busy} onClick={analyze}>
          {busy ? 'Analisando…' : 'Analisar logs localmente'}
        </button>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <strong>Privacidade por padrão</strong>
        <p className="muted">Nenhum log ou segredo é enviado para IA externa. Execuções reais exigem owner/admin, conexão executora e aprovação.</p>
      </div>
      {message && <p className="muted">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid grid-2" style={{ marginTop: '1rem' }}>
        {rows.map((row) => (
          <article className="card" key={row.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h3>{row.title}</h3>
              <span className="badge">{row.status}</span>
            </div>
            <p className="muted" style={{ marginTop: '0.75rem' }}>{row.diagnosis}</p>
            <p style={{ marginTop: '0.75rem' }}>{row.recommendation}</p>
            <p className="muted" style={{ marginTop: '0.75rem' }}>{row.evidence_count} ocorrências correlacionadas</p>
            {row.result_message && <p className="muted">{row.result_message}</p>}
            {row.status === 'suggested' && (
              <div className="row" style={{ marginTop: '1rem' }}>
                <button className="btn btn-primary" disabled={busy} onClick={() => decide(row.id, true)}>Aprovar dry-run</button>
                <button className="btn" disabled={busy} onClick={() => decide(row.id, false)}>Rejeitar</button>
              </div>
            )}
          </article>
        ))}
        {rows.length === 0 && <div className="card muted">Nenhuma remediação proposta nesta tenancy.</div>}
      </div>
    </div>
  )
}
