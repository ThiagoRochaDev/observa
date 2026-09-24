'use client'

import { FormEvent, ReactNode, useEffect, useState } from 'react'
import { api, clearApiKey, getApiKey, setApiKey } from '@/lib/api'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Continue with Google',
  gitlab: 'Continue with GitLab',
}

/**
 * Gates the whole app behind a credential. Two shapes, decided by the
 * backend's auth mode (checked before anything else, unauthenticated —
 * see /auth/mode):
 *   - local: paste the shared key printed on first boot (unchanged).
 *   - oidc: "Continue with <provider>" buttons that hand off to the
 *     backend's /auth/authorize/<provider> redirect. The resulting session
 *     token lands back here via /auth/callback (see that page) and is
 *     stored in the exact same slot the shared key used to occupy — api.ts
 *     doesn't need to know which kind of credential it's holding.
 */
export function ApiKeyGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [needsKey, setNeedsKey] = useState(false)
  const [mode, setMode] = useState<'local' | 'oidc'>('local')
  const [providers, setProviders] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    async function initialize() {
      try {
        const authMode = await api.authMode()
        setMode(authMode.mode)
        setProviders(authMode.providers)
      } catch {
        // API unreachable — fall through to the local-mode form so the
        // error surfaces on submit instead of a blank screen.
      }

      const storedKey = getApiKey()
      if (!storedKey) {
        setNeedsKey(true)
        setReady(true)
        return
      }

      try {
        await api.health()
        setNeedsKey(false)
      } catch {
        clearApiKey()
        setNeedsKey(true)
      } finally {
        setReady(true)
      }
    }

    void initialize()
  }, [])

  async function trySubmit(e: FormEvent) {
    e.preventDefault()
    const key = input.trim()
    if (!key) return
    setChecking(true)
    setError(null)
    setApiKey(key)
    try {
      await api.health()
      setNeedsKey(false)
    } catch {
      setError('Key rejected — check the value in the API container logs or data/api_key.')
    } finally {
      setChecking(false)
    }
  }

  if (!ready) return null

  if (!needsKey) return <>{children}</>

  if (mode === 'oidc') {
    return (
      <div className="auth-gate">
        <div className="auth-gate-card">
          <div className="auth-gate-brand"><span aria-hidden="true"><i /></span>Observa</div>
          <div className="eyebrow">Acesso corporativo</div>
          <h1>Entrar no Observa</h1>
          <p className="auth-gate-copy">Use o provedor de identidade configurado para continuar.</p>
          {error && <p className="error">{error}</p>}
          {providers.length === 0 ? (
            <p className="muted">
              O modo OIDC está ativo, mas nenhum provedor foi habilitado. Um administrador precisa
              concluir a configuração em Segurança e acesso.
            </p>
          ) : (
            <div className="auth-gate-actions">
              {providers.map((p) => (
                <button
                  key={p}
                  className="btn btn-primary"
                  onClick={() => {
                    window.location.href = `${BASE}/auth/authorize/${p}`
                  }}
                >
                  {PROVIDER_LABELS[p] || `Continue with ${p}`}
                </button>
              ))}
            </div>
          )}
          <p className="auth-gate-security"><span aria-hidden="true" />Company e tenancy permanecem isoladas.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-gate">
      <form className="auth-gate-card" onSubmit={trySubmit}>
        <div className="auth-gate-brand"><span aria-hidden="true"><i /></span>Observa</div>
        <div className="eyebrow">Acesso local protegido</div>
        <h1>Entrar no Observa</h1>
        <p className="auth-gate-copy">
          Informe a chave gerada pela API na primeira inicialização. Ela fica salva localmente em{' '}
          <code>data/api_key</code>.
        </p>
        <div className="auth-gate-field">
          <label htmlFor="observa-api-key">
            Chave da API
            <input
              id="observa-api-key"
              type="password"
              autoFocus
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Cole sua chave local"
              autoComplete="current-password"
            />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={checking}>
          {checking ? 'Validando…' : 'Acessar plataforma'}
        </button>
        <p className="auth-gate-security"><span aria-hidden="true" />A chave é validada somente pela sua API do Observa.</p>
      </form>
    </div>
  )
}
