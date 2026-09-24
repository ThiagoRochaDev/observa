import type { CSSProperties, ReactNode } from 'react'
import { CONNECTOR_ICONS } from '@/lib/api'

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  strokeWidth: 1.7,
} as const

function PlatformMark({ icon }: { icon: string }): ReactNode {
  switch (icon) {
    case 'aws':
      return <><path {...stroke} d="M5 15.5c2.7 2 8.7 2.5 13.7-.2" /><path {...stroke} d="m16.7 14.2 2.3 1-.8 2.3" /><path {...stroke} d="M7.2 12.3 9.6 6l2.4 6.3M8 10h3.2M13.2 7.4c.9-1.2 3.9-1 3.9.8 0 2.2-4.2 1-4.2 3 0 1.7 2.8 2.1 4.3.7" /></>
    case 'gcp':
      return <><path d="M7.2 17.5h9.4a4.1 4.1 0 0 0 .8-8.1A6.1 6.1 0 0 0 6 7.7a4.9 4.9 0 0 0 1.2 9.8Z" fill="none" stroke="#4285f4" strokeWidth="2.3" /><path d="M6 7.7a6 6 0 0 1 4.1-1.8" fill="none" stroke="#ea4335" strokeWidth="2.3" /><path d="M10.1 5.9a6.1 6.1 0 0 1 7.3 3.5" fill="none" stroke="#fbbc04" strokeWidth="2.3" /><path d="M7.2 17.5A4.9 4.9 0 0 1 6 7.7" fill="none" stroke="#34a853" strokeWidth="2.3" /></>
    case 'azure':
      return <><path d="m11.2 3.5-5.4 9.1 4.8-.1 5.5-9Z" fill="currentColor" /><path d="m10.5 14.1 2.8 6.4 7-1.2-4.4-7.1Z" fill="currentColor" opacity=".65" /><path d="m5.8 12.6-2.1 3.6 6.8-2.1.1-1.6Z" fill="currentColor" opacity=".4" /></>
    case 'oci':
      return <><path {...stroke} d="M7.3 7h9.4a5 5 0 0 1 0 10H7.3a5 5 0 0 1 0-10Z" /><path {...stroke} d="M7.6 10h8.8a2 2 0 0 1 0 4H7.6a2 2 0 0 1 0-4Z" /></>
    case 'digitalocean':
      return <><path {...stroke} d="M12 4a6.5 6.5 0 1 1-6.5 6.5H9V14H5.5v3.5H2V14" /><path d="M9 17.5h3.5V14H9Z" fill="currentColor" /></>
    case 'linode':
      return <><path {...stroke} d="m12 3 6 3.5-6 3.4-6-3.4L12 3Z" /><path {...stroke} d="m7 10 5 2.9 5-2.9M7.7 14.2l4.3 2.5 4.3-2.5M8.5 18.1 12 20l3.5-1.9" /></>
    case 'cloudflare':
      return <><path d="M7 17h11.2a2.8 2.8 0 0 0 .3-5.6 5.2 5.2 0 0 0-9.7-1.3A3.5 3.5 0 0 0 7 17Z" fill="currentColor" opacity=".78" /><path {...stroke} d="M3.8 17H7M13 6V3.8M7.9 7.9 6.3 6.3M18.1 7.9l1.6-1.6" /></>
    case 'vercel':
      return <path d="m12 4 9 16H3L12 4Z" fill="currentColor" />
    case 'netlify':
      return <><path {...stroke} d="M12 4v16M4 12h16M6.4 6.4l11.2 11.2M17.6 6.4 6.4 17.6" /><circle cx="12" cy="12" r="2.3" fill="currentColor" /></>
    case 'mongodb':
      return <><path d="M12 2.8c3.5 4.3 5.4 7.2 5.4 10.1 0 3.4-2.2 6.1-5.4 8.3-3.2-2.2-5.4-4.9-5.4-8.3 0-2.9 1.9-5.8 5.4-10.1Z" fill="currentColor" /><path d="M12 6v14.8" stroke="#0d1117" strokeWidth="1.5" /></>
    case 'datadog':
      return <><circle cx="8" cy="7" r="2" fill="currentColor" /><circle cx="12" cy="5.8" r="2" fill="currentColor" /><circle cx="16" cy="7" r="2" fill="currentColor" /><path {...stroke} d="M7.5 14.5c0-3 2-5 4.5-5s4.5 2 4.5 5c0 2.3-1.8 3.7-4.5 3.7s-4.5-1.4-4.5-3.7Z" /></>
    case 'newrelic':
      return <><path {...stroke} d="m12 3 7.8 4.5v9L12 21l-7.8-4.5v-9L12 3Z" /><path {...stroke} d="m8 9 4-2.2L16 9v6l-4 2.2L8 15V9Z" /><path {...stroke} d="m8 9 4 2.3L16 9M12 11.3v5.9" /></>
    case 'grafana':
      return <><path {...stroke} d="M18.5 8.2A7.3 7.3 0 1 0 19 16l-3-1.2a4.2 4.2 0 1 1-.2-5.2l2.7-1.4Z" /><path {...stroke} d="M13.8 10.2a2.6 2.6 0 1 0 1 3.4" /></>
    case 'elastic':
      return <><path d="M7 4h7a4 4 0 0 1 3.8 2.7L14 9H7a2.5 2.5 0 0 1 0-5Z" fill="currentColor" /><path d="M17 20h-7a4 4 0 0 1-3.8-2.7L10 15h7a2.5 2.5 0 0 1 0 5Z" fill="currentColor" opacity=".55" /><path d="M6 10h12v4H6a2 2 0 0 1 0-4Z" fill="currentColor" opacity=".75" /></>
    case 'sentry':
      return <><path {...stroke} d="m12 3 8 15H4l8-15Z" /><path {...stroke} d="M8.2 18a5.1 5.1 0 0 0-2.5-4.4M16 18a8.3 8.3 0 0 0-5.8-7.9M18.7 18A11 11 0 0 0 9 7" /></>
    case 'pagerduty':
      return <><path d="M6 4h7a6 6 0 0 1 0 12H9V9h4a1 1 0 0 1 0 2h-1" fill="none" stroke="currentColor" strokeWidth="2.2" /><path d="M6 18h3v3H6z" fill="currentColor" /></>
    case 'opsgenie':
      return <><circle cx="12" cy="7" r="3" fill="currentColor" /><path {...stroke} d="M5 19c.8-4.4 3.1-7 7-7s6.2 2.6 7 7M5 7 3.5 5.5M19 7l1.5-1.5" /></>
    case 'github':
      return <path d="M12 3a9 9 0 0 0-2.8 17.6c.5.1.7-.2.7-.5v-1.8c-2.8.6-3.4-1.2-3.4-1.2-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.4-2.2-.3-4.6-1.1-4.6-5A3.9 3.9 0 0 1 7 8.1c-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.9 1.1A10 10 0 0 1 12 6.2c.9 0 1.8.1 2.6.4 2-1.4 2.9-1.1 2.9-1.1.6 1.4.2 2.4.1 2.7a3.9 3.9 0 0 1 1.1 2.7c0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8v2.5c0 .3.2.6.7.5A9 9 0 0 0 12 3Z" fill="currentColor" />
    case 'gitlab':
      return <path d="m12 20.5 7.8-5.7-2.1-6.5-2.1-5.1-3.6 9-3.6-9-2.1 5.1-2.1 6.5 7.8 5.7Z" fill="currentColor" />
    case 'bitbucket':
      return <><path d="M4 5h16l-2 14H6L4 5Z" fill="currentColor" /><path d="m9 10 .7 4h4.6l.7-4H9Z" fill="#0d1117" /></>
    case 'kubernetes':
      return <><path {...stroke} d="m12 3 7.5 4.3v8.7L12 20.5 4.5 16V7.3L12 3Z" /><circle cx="12" cy="12" r="2.5" fill="currentColor" /><path {...stroke} d="M12 6v3.5M12 14.5V18M6 12h3.5M14.5 12H18M7.8 7.8l2.4 2.4M13.8 13.8l2.4 2.4M16.2 7.8l-2.4 2.4M10.2 13.8l-2.4 2.4" /></>
    case 'onprem':
      return <><rect {...stroke} x="5" y="4" width="14" height="6" rx="1.5" /><rect {...stroke} x="5" y="14" width="14" height="6" rx="1.5" /><circle cx="8" cy="7" r="1" fill="currentColor" /><circle cx="8" cy="17" r="1" fill="currentColor" /><path {...stroke} d="M11 7h5M11 17h5" /></>
    case 'splunk':
      return <><path {...stroke} d="m5 7 6 5-6 5M13 17h6" /></>
    case 'stripe':
      return <path d="M18 7.2c-1.5-.7-3.2-1-4.8-1-2.8 0-4.7 1.4-4.7 3.6 0 3.7 5.1 3.1 5.1 4.7 0 .6-.6.9-1.5.9-1.4 0-3.1-.6-4.5-1.4v3.7c1.6.7 3.3 1.1 5.2 1.1 2.9 0 4.9-1.4 4.9-3.7 0-4-5.1-3.3-5.1-4.8 0-.5.5-.8 1.4-.8 1.2 0 2.7.4 4 1.1V7.2Z" fill="currentColor" />
    case 'snowflake':
      return <><path {...stroke} d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9.8 5.2 12 7.4l2.2-2.2M9.8 18.8l2.2-2.2 2.2 2.2" /></>
    case 'mcp':
      return <><circle {...stroke} cx="6" cy="12" r="2.4" /><circle {...stroke} cx="18" cy="6" r="2.4" /><circle {...stroke} cx="18" cy="18" r="2.4" /><path {...stroke} d="m8.2 10.9 7.6-3.8M8.2 13.1l7.6 3.8" /></>
    case 'mock':
      return <><path {...stroke} d="m12 3 1.2 4.4L17 9l-3.8 1.6L12 15l-1.2-4.4L7 9l3.8-1.6L12 3Z" /><path {...stroke} d="m6 14 .7 2.3L9 17l-2.3.7L6 20l-.7-2.3L3 17l2.3-.7L6 14ZM18 12l.6 1.8 1.9.7-1.9.7L18 17l-.6-1.8-1.9-.7 1.9-.7L18 12Z" /></>
    default:
      return <><path {...stroke} d="M8 8V5M16 8V5M7 8h10v4a5 5 0 0 1-5 5v3M9 12h6" /></>
  }
}

const NATIVE_MARKS = new Set([
  'aws', 'gcp', 'azure', 'oci', 'digitalocean', 'linode', 'cloudflare', 'vercel', 'netlify',
  'mongodb', 'datadog', 'newrelic', 'grafana', 'elastic', 'sentry', 'pagerduty', 'opsgenie',
  'github', 'gitlab', 'bitbucket', 'kubernetes', 'onprem', 'splunk', 'stripe', 'snowflake', 'mcp', 'mock',
])

function initials(label: string) {
  const parts = label.replace(/[^a-zA-Z0-9 ]/g, ' ').split(/\s+/).filter(Boolean)
  return (parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : parts[0]?.slice(0, 2) || '?').toUpperCase()
}

function colorFor(label: string) {
  const colors = ['#70a7ff', '#55d6a4', '#c88cff', '#f2a65a', '#5ec8e5', '#e879a8', '#a5c96a']
  const hash = [...label].reduce((total, character) => total + character.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

export default function ConnectorIcon({ icon, label, size = 40 }: { icon: string; label?: string; size?: number }) {
  const meta = CONNECTOR_ICONS[icon] || CONNECTOR_ICONS.generic
  const color = CONNECTOR_ICONS[icon] ? meta.color : colorFor(label || icon)

  return (
    <span
      className="connector-platform-icon"
      aria-hidden="true"
      style={{ '--connector-color': color, width: size, height: size } as CSSProperties}
    >
      {NATIVE_MARKS.has(icon) ? (
        <svg viewBox="0 0 24 24" focusable="false"><PlatformMark icon={icon} /></svg>
      ) : (
        <span className="connector-platform-monogram">{initials(label || meta.label)}</span>
      )}
    </span>
  )
}
