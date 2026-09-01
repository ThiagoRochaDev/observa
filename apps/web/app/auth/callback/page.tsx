'use client'

import { useEffect, useState } from 'react'
import { setApiKey } from '@/lib/api'

/**
 * Landing spot for the OIDC redirect (see backend's /auth/callback/<provider>
 * — auth_flow_router.py). Only ever reached via that redirect, never linked
 * to directly. A token in the URL fragment (never sent to any server, unlike
 * a query param) means login succeeded; an `error` query param means it
 * didn't.
 */
export default function OidcCallbackPage() {
  const [status, setStatus] = useState<'working' | 'error'>('working')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const errorCode = params.get('error')
    if (errorCode) {
      setStatus('error')
      setMessage(
        errorCode === 'invalid_state'
          ? 'This login link expired or was already used — start over.'
          : 'Login failed — check the provider is configured correctly in Settings → Authentication.',
      )
      return
    }

    const token = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token')
    if (!token) {
      setStatus('error')
      setMessage('No token came back from the login redirect.')
      return
    }
    setApiKey(token)
    window.location.replace('/')
  }, [])

  return (
    <div className="dash-layout" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ maxWidth: '26rem', width: '100%', margin: '4rem auto' }}>
        {status === 'working' ? (
          <p className="muted">Signing you in…</p>
        ) : (
          <>
            <h1 style={{ marginBottom: '0.5rem' }}>Login failed</h1>
            <p className="error" style={{ marginBottom: '1rem' }}>
              {message}
            </p>
            <a className="btn btn-primary" href="/">
              Back to login
            </a>
          </>
        )}
      </div>
    </div>
  )
}
