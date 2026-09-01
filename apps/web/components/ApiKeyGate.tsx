'use client'

import { FormEvent, ReactNode, useEffect, useState } from 'react'
import { api, getApiKey, setApiKey } from '@/lib/api'

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
    api
      .authMode()
      .then((m) => {
        setMode(m.mode)
        setProviders(m.providers)
      })
      .catch(() => {
        // API unreachable — fall through to the local-mode form so the
        // error surfaces on submit instead of a blank screen.
      })
      .finally(() => {
        setNeedsKey(!getApiKey())
        setReady(true)
      })
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
      <div className="dash-layout" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div className="card" style={{ maxWidth: '28rem', width: '100%', margin: '4rem auto' }}>
          <h1 style={{ marginBottom: '0.5rem' }}>Observa</h1>
          <p className="muted" style={{ marginBottom: '1.25rem' }}>
            Sign in to continue.
          </p>
          {error && <p className="error">{error}</p>}
          {providers.length === 0 ? (
            <p className="muted">
              OIDC mode is on, but no provider is enabled yet — an operator needs to finish
              setup in Settings → Authentication.
            </p>
          ) : (
            <div className="form" style={{ gap: '0.5rem' }}>
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
        </div>
      </div>
    )
  }

  return (
    <div className="dash-layout" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <form
        className="card"
        onSubmit={trySubmit}
        style={{ maxWidth: '28rem', width: '100%', margin: '4rem auto' }}
      >
        <h1 style={{ marginBottom: '0.5rem' }}>Observa</h1>
        <p className="muted" style={{ marginBottom: '1rem' }}>
          Paste the API key printed by the <code>api</code> service on first boot (also saved to{' '}
          <code>data/api_key</code>).
        </p>
        <div className="form">
          <label>
            API key
            <input
              type="password"
              autoFocus
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="..."
            />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={checking}>
          {checking ? 'Checking…' : 'Unlock'}
        </button>
      </form>
    </div>
  )
}
