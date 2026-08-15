'use client'

import { FormEvent, useEffect, useState } from 'react'
import { api, type AuthSettings } from '@/lib/api'

const empty: AuthSettings = {
  mode: 'local',
  providers: {
    gitlab: {
      enabled: false,
      client_id: '',
      client_secret: '',
      issuer: 'https://gitlab.com',
      redirect_uri: 'http://localhost:8080/auth/callback/gitlab',
    },
    google: {
      enabled: false,
      client_id: '',
      client_secret: '',
      issuer: 'https://accounts.google.com',
      redirect_uri: 'http://localhost:8080/auth/callback/google',
    },
  },
}

export default function AuthSettingsPage() {
  const [settings, setSettings] = useState<AuthSettings>(empty)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .authSettings()
      .then((s) =>
        setSettings({
          mode: s.mode || 'local',
          providers: {
            ...empty.providers,
            ...s.providers,
          },
        }),
      )
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  function updateProvider(
    key: string,
    patch: Partial<AuthSettings['providers'][string]>,
  ) {
    setSettings((prev) => ({
      ...prev,
      providers: {
        ...prev.providers,
        [key]: { ...prev.providers[key], ...patch },
      },
    }))
  }

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.saveAuthSettings(settings)
      setMsg('Authentication settings saved. OIDC login flow will be wired next; config is stored now.')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <div>
      <h1 className="page-title">Authentication</h1>
      <p className="page-sub">
        Configure SSO (GitLab / Google) directly in Observa. Local mode is open for laptop
        validation; enable OIDC when you are ready.
      </p>

      {error && <p className="error">{error}</p>}
      {msg && <p className="muted">{msg}</p>}

      <form className="form" onSubmit={onSave}>
        <label>
          Mode
          <select
            value={settings.mode}
            onChange={(e) => setSettings({ ...settings, mode: e.target.value })}
          >
            <option value="local">Local (dev)</option>
            <option value="oidc">OIDC (GitLab / Google)</option>
          </select>
        </label>

        {(['gitlab', 'google'] as const).map((key) => {
          const p = settings.providers[key] || {}
          return (
            <div key={key} className="card" style={{ maxWidth: '36rem' }}>
              <h3 style={{ color: 'var(--text)', marginBottom: '0.75rem' }}>
                {key === 'gitlab' ? 'GitLab OIDC' : 'Google / GCP SSO'}
              </h3>
              <div className="form">
                <label>
                  <span className="row">
                    <input
                      type="checkbox"
                      checked={Boolean(p.enabled)}
                      onChange={(e) => updateProvider(key, { enabled: e.target.checked })}
                    />
                    Enabled
                  </span>
                </label>
                <label>
                  Client ID
                  <input
                    value={p.client_id || ''}
                    onChange={(e) => updateProvider(key, { client_id: e.target.value })}
                  />
                </label>
                <label>
                  Client Secret
                  <input
                    type="password"
                    value={p.client_secret || ''}
                    onChange={(e) => updateProvider(key, { client_secret: e.target.value })}
                    placeholder={p.has_client_secret ? '•••••••• (leave to keep)' : ''}
                  />
                </label>
                <label>
                  Issuer
                  <input
                    value={p.issuer || ''}
                    onChange={(e) => updateProvider(key, { issuer: e.target.value })}
                  />
                </label>
                <label>
                  Redirect URI (register in the IdP)
                  <input
                    value={p.redirect_uri || ''}
                    onChange={(e) => updateProvider(key, { redirect_uri: e.target.value })}
                  />
                </label>
              </div>
            </div>
          )
        })}

        <button className="btn btn-primary" type="submit">
          Save authentication
        </button>
      </form>
    </div>
  )
}
