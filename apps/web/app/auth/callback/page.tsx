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
type CallbackResult =
  | { status: 'working'; message: ''; token: string }
  | { status: 'working'; message: ''; token: null } // SSR/export prerender — no window yet
  | { status: 'error'; message: string; token: null }

/** Reads the redirect's URL once, at mount — kept out of an effect (and out
 * of setState calls inside one) per react-hooks/set-state-in-effect. Safe to
 * call during the static-export prerender too (`window` guard below). */
function readCallbackResult(): CallbackResult {
  if (typeof window === 'undefined') {
    return { status: 'working', message: '', token: null }
  }

  const params = new URLSearchParams(window.location.search)
  const errorCode = params.get('error')
  if (errorCode) {
    return {
      status: 'error',
      message:
        errorCode === 'invalid_state'
          ? 'This login link expired or was already used — start over.'
          : 'Login failed — check the provider is configured correctly in Settings → Authentication.',
      token: null,
    }
  }

  const token = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token')
  if (!token) {
    return { status: 'error', message: 'No token came back from the login redirect.', token: null }
  }
  return { status: 'working', message: '', token }
}

export default function OidcCallbackPage() {
  const [result] = useState(readCallbackResult)

  useEffect(() => {
    if (!result.token) return
    setApiKey(result.token)
    window.location.replace('/')
  }, [result.token])

  return (
    <div className="dash-layout" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ maxWidth: '26rem', width: '100%', margin: '4rem auto' }}>
        {result.status === 'working' ? (
          <p className="muted">Signing you in…</p>
        ) : (
          <>
            <h1 style={{ marginBottom: '0.5rem' }}>Login failed</h1>
            <p className="error" style={{ marginBottom: '1rem' }}>
              {result.message}
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
