'use client'

import { useMemo } from 'react'
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import { graphlib, layout as dagreLayout } from '@dagrejs/dagre'
import '@xyflow/react/dist/style.css'
import type { Ecosystem } from '@/lib/api'

const KIND_COLOR: Record<string, string> = {
  frontend: '#3b82f6',
  api: '#22c55e',
  worker: '#f59e0b',
  resource: '#64748b',
  external: '#a855f7',
  service: '#22c55e',
}

const KIND_LABEL: Record<string, string> = {
  frontend: 'Frontend',
  api: 'API',
  worker: 'Worker',
  resource: 'Cloud resource',
  external: 'External',
}

type EcoData = { label: string; kind: string; type?: string }

function EcoNode({ data }: NodeProps & { data: EcoData }) {
  const color = KIND_COLOR[data.kind] || '#8b95a8'
  return (
    <div className="map-node" style={{ borderColor: color }}>
      <Handle type="target" position={Position.Top} style={{ background: color }} />
      <div className="map-node-kind" style={{ color }}>
        {KIND_LABEL[data.kind] || data.kind}
        {data.type ? ` · ${data.type}` : ''}
      </div>
      <strong>{data.label}</strong>
      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  )
}

const nodeTypes = { eco: EcoNode }

function layoutWithDagre(data: Ecosystem): { nodes: Node[]; edges: Edge[] } {
  const g = new graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 48, ranksep: 72, marginx: 24, marginy: 24 })

  for (const n of data.nodes) {
    g.setNode(n.id, { width: 168, height: 72 })
  }
  for (const e of data.edges) {
    g.setEdge(e.source, e.target)
  }
  dagreLayout(g)

  const nodes: Node[] = data.nodes.map((n) => {
    const pos = g.node(n.id)
    return {
      id: n.id,
      type: 'eco',
      position: { x: (pos?.x || 0) - 84, y: (pos?.y || 0) - 36 },
      data: { label: n.label, kind: n.kind, type: n.type },
    }
  })

  const edges: Edge[] = data.edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#5d87ff' },
    style: { stroke: '#5d87ff', strokeWidth: 1.5 },
    labelStyle: { fill: '#8b9cb3', fontSize: 10 },
    labelBgStyle: { fill: '#0b1220', fillOpacity: 0.85 },
  }))

  return { nodes, edges }
}

export function EcosystemMap({ data }: { data: Ecosystem }) {
  const { nodes, edges } = useMemo(() => layoutWithDagre(data), [data])

  return (
    <div className="map-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.4}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#243044" gap={18} />
        <Controls />
      </ReactFlow>
    </div>
  )
}
