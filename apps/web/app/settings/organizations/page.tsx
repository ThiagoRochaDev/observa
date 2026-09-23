'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { api, setTenantContext, type Company, type CompanyMember, type Tenancy } from '@/lib/api'

export default function OrganizationsPage() {
  const router = useRouter()
  const [companies, setCompanies] = useState<Company[]>([])
  const [tenancies, setTenancies] = useState<Tenancy[]>([])
  const [companyName, setCompanyName] = useState('')
  const [tenancyName, setTenancyName] = useState('')
  const [companyId, setCompanyId] = useState('')
  const [members, setMembers] = useState<CompanyMember[]>([])
  const [memberSubject, setMemberSubject] = useState('')
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('viewer')
  const [error, setError] = useState('')

  async function load() {
    const [companyRows, tenancyRows] = await Promise.all([api.companies(), api.tenancies()])
    setCompanies(companyRows)
    setTenancies(tenancyRows)
    setCompanyId((current) => current || companyRows[0]?.id || '')
  }

  useEffect(() => {
    let active = true
    Promise.all([api.companies(), api.tenancies()])
      .then(([companyRows, tenancyRows]) => {
        if (!active) return
        setCompanies(companyRows)
        setTenancies(tenancyRows)
        setCompanyId(companyRows[0]?.id || '')
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : String(cause))
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!companyId) return
    api.companyMembers(companyId).then(setMembers).catch(() => setMembers([]))
  }, [companyId])

  async function addCompany(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const company = await api.createCompany({ name: companyName })
      setCompanyName('')
      setCompanyId(company.id)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function addTenancy(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await api.createTenancy({ company_id: companyId, name: tenancyName })
      setTenancyName('')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function addMember(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await api.saveCompanyMember(companyId, {
        subject: memberSubject,
        email: memberEmail || undefined,
        role: memberRole,
      })
      setMemberSubject('')
      setMemberEmail('')
      setMembers(await api.companyMembers(companyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    }
  }

  function openTenancy(tenancy: Tenancy) {
    setTenantContext(tenancy.company_id, tenancy.id)
    router.push('/')
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Companies e tenancies</h1>
          <p className="page-header-desc">
            Cada empresa possui ambientes isolados para conexões, custos, inventário, budgets e automações.
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="grid grid-2">
        <form className="card form" onSubmit={addCompany}>
          <h2>Nova company</h2>
          <label>Nome<input value={companyName} onChange={(event) => setCompanyName(event.target.value)} required /></label>
          <button className="btn btn-primary" type="submit">Criar company</button>
        </form>
        <form className="card form" onSubmit={addTenancy}>
          <h2>Nova tenancy</h2>
          <label>
            Company
            <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} required>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </label>
          <label>Nome<input value={tenancyName} onChange={(event) => setTenancyName(event.target.value)} required /></label>
          <button className="btn btn-primary" type="submit">Criar tenancy</button>
        </form>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <h2>Ambientes cadastrados</h2>
        <div className="grid grid-2" style={{ marginTop: '1rem' }}>
          {companies.map((company) => (
            <div className="card" key={company.id}>
              <h3>{company.name}</h3>
              <p className="muted">{company.slug} · {company.id}</p>
              <div className="form" style={{ marginTop: '1rem' }}>
                {tenancies.filter((tenancy) => tenancy.company_id === company.id).map((tenancy) => (
                  <button className="btn" key={tenancy.id} onClick={() => openTenancy(tenancy)}>
                    Abrir {tenancy.name}
                  </button>
                ))}
                {!tenancies.some((tenancy) => tenancy.company_id === company.id) && (
                  <p className="muted">Nenhuma tenancy criada.</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Owners e membros autorizados</h2>
        <p className="muted">Somente identidades explicitamente vinculadas acessam os dados da company.</p>
        <form className="form" onSubmit={addMember} style={{ marginTop: '1rem' }}>
          <label>
            Company
            <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} required>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </label>
          <label>Subject OIDC<input value={memberSubject} onChange={(event) => setMemberSubject(event.target.value)} placeholder="google:123... ou gitlab:456..." required /></label>
          <label>E-mail<input type="email" value={memberEmail} onChange={(event) => setMemberEmail(event.target.value)} /></label>
          <label>
            Papel
            <select value={memberRole} onChange={(event) => setMemberRole(event.target.value)}>
              <option value="viewer">Viewer</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
              <option value="owner">Owner</option>
            </select>
          </label>
          <button className="btn btn-primary" type="submit">Autorizar membro</button>
        </form>
        <div className="form" style={{ marginTop: '1rem' }}>
          {members.map((member) => (
            <div key={member.subject} className="muted">
              {member.email || member.subject} · {member.role}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
