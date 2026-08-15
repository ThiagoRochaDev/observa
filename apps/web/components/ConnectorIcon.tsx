import { CONNECTOR_ICONS } from '@/lib/api'

export default function ConnectorIcon({ icon, size = 36 }: { icon: string; size?: number }) {
  const meta = CONNECTOR_ICONS[icon] || CONNECTOR_ICONS.generic
  return (
    <div
      aria-hidden
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.28,
        background: meta.color,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: size * 0.34,
        letterSpacing: '-0.02em',
        flexShrink: 0,
      }}
    >
      {meta.mono}
    </div>
  )
}
