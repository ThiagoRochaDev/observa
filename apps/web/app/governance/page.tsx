'use client'

import { FormEvent, useEffect, useState } from 'react'
import {
  api,
  type AutomationAction,
  type AutomationPolicy,
  type Resource,
} from '@/lib/api'

export default function GovernancePage() {
  const [resources, setResources] = useState<Resource[]>([])
  const [policies, setPolicies] = useState<AutomationPolicy[]>([])
  const [actions, setActions] = useState<AutomationAction[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [tagKey, setTagKey] = useState('owner')
  const [tagValue, setTagValue] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    const [resourceRows, policyRows, actionRows] = await Promise.all([
      api.untaggedResources(),
      api.policies(),
      api.actions(),
    ])
    setResources(resourceRows)
    setPolicies(policyRows)
    setActions(actionRows)
    if (!selected && resourceRows[0]) setSelected(resourceRows[0].uid)
  }

  useEffect(() => {
    let active = true
    Promise.all([api.untaggedResources(), api.policies(), api.actions()])
      .then(([resourceRows, policyRows, actionRows]) => {
        if (!active) return
        setResources(resourceRows)
        setPolicies(policyRows)
        setActions(actionRows)
        if (resourceRows[0]) setSelected(resourceRows[0].uid)
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : String(cause))
      })
    return () => { active = false }
  }, [])

  async function applyTag(event: FormEvent) {
    event.preventDefault()
    if (!selected || !tagKey || !tagValue) return
    setError('')
    try {
      const result = await api.updateResourceTags(selected, { [tagKey]: tagValue }, { dry_run: false })
      setMessage(result.message)
      setTagValue('')
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function createSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    const data = new FormData(event.currentTarget)
    setError('')
    try {
      await api.createPolicy({
        name: String(data.get('name')),
        resource_ids: [selected],
        selector: {},
        timezone: String(data.get('timezone')),
        weekdays: [0, 1, 2, 3, 4],
        start_time: String(data.get('start_time')) || null,
        stop_time: String(data.get('stop_time')) || null,
        expires_at: String(data.get('expires_at')) || null,
        expiration_action: 'stop',
        enabled: true,
        require_approval: true,
        dry_run: true,
      })
      setMessage('Política criada em modo seguro (dry-run).')
      event.currentTarget.reset()
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function decide(id: string, approve: boolean) {
    try {
      if (approve) await api.approveAction(id)
      else await api.rejectAction(id, 'Rejeitado no painel web')
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  return (
    <div>
      <h1 className="page-title">Governança FinOps</h1>
      <p className="page-sub">Mapeie recursos sem owner, crie horários e aprove ações com auditoria.</p>
      {message && <div className="demo-banner">{message}</div>}
      {error && <p className="error">{error}</p>}

      <div className="grid grid-3">
        <section className="card">
          <h2>Recursos sem mapeamento</h2>
          <p className="muted">Selecione um recurso para aplicar tags ou criar uma política.</p>
          <select value={selected ?? ''} onChange={(event) => setSelected(Number(event.target.value))}>
            {resources.map((resource) => (
              <option key={resource.uid} value={resource.uid}>
                {resource.provider} · {resource.name || resource.id}
              </option>
            ))}
          </select>
          <form className="form governance-form" onSubmit={applyTag}>
            <label>Tag<input value={tagKey} onChange={(event) => setTagKey(event.target.value)} /></label>
            <label>Valor<input value={tagValue} onChange={(event) => setTagValue(event.target.value)} /></label>
            <button className="btn btn-primary" type="submit">Aplicar na cloud</button>
          </form>
        </section>

        <section className="card">
          <h2>Novo agendamento</h2>
          <form className="form governance-form" onSubmit={createSchedule}>
            <label>Nome<input name="name" required placeholder="Homologação horário comercial" /></label>
            <label>Fuso<input name="timezone" defaultValue="America/Sao_Paulo" /></label>
            <label>Ligar<input name="start_time" type="time" /></label>
            <label>Desligar<input name="stop_time" type="time" /></label>
            <label>Data limite<input name="expires_at" type="datetime-local" /></label>
            <button className="btn btn-primary" type="submit">Criar em dry-run</button>
          </form>
        </section>

        <section className="card">
          <h2>Políticas ativas</h2>
          <div className="toplist">
            {policies.map((policy) => (
              <div className="toplist-row" key={policy.id}>
                <strong>{policy.name}</strong>
                <span className="muted">
                  {policy.start_time || '—'} → {policy.stop_time || '—'} · {policy.timezone}
                </span>
                <span className={`badge ${policy.dry_run ? 'medium' : 'high'}`}>
                  {policy.dry_run ? 'dry-run' : 'execução real'}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card governance-actions">
        <h2>Ações e aprovações</h2>
        <table className="table">
          <thead><tr><th>Ação</th><th>Recurso</th><th>Status</th><th>Motivo</th><th>Decisão</th></tr></thead>
          <tbody>
            {actions.map((action) => (
              <tr key={action.id}>
                <td>{action.action}</td><td>#{action.resource_uid}</td>
                <td><span className="badge">{action.status}</span></td>
                <td>{action.reason || '—'}</td>
                <td className="row">
                  {action.status === 'pending_approval' && <>
                    <button className="btn btn-primary" onClick={() => decide(action.id, true)}>Aprovar</button>
                    <button className="btn-danger" onClick={() => decide(action.id, false)}>Rejeitar</button>
                  </>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
