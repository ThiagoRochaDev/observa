'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  Background,
  BackgroundVariant,
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

const KIND_META: Record<string, { label: string; code: string }> = {
  frontend: { label: 'Frontend', code: 'WEB' },
  api: { label: 'API', code: 'API' },
  worker: { label: 'Worker', code: 'WRK' },
  resource: { label: 'Cloud resource', code: 'RES' },
  external: { label: 'External', code: 'EXT' },
  service: { label: 'Service', code: 'SVC' },
}

type EcoData = {
  label: string
  kind: string
  type?: string
  tier: number
}

type EcosystemFlowNode = Node<EcoData, 'eco'>

function EcoNode({ data, selected }: NodeProps<EcosystemFlowNode>) {
  const meta = KIND_META[data.kind] || { label: data.kind, code: 'SRV' }

  return (
    <div className={`live-map-node live-map-node-${data.kind}${selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Left} className="live-map-handle" />
      <div className="live-map-node-top">
        <span className="live-map-node-icon" aria-hidden="true">{meta.code}</span>
        <span className="live-map-node-status">Mapeado</span>
      </div>
      <strong>{data.label}</strong>
      <span className="live-map-node-meta">
        {meta.label}
        {data.type ? ` · ${data.type}` : ''}
      </span>
      <span className="live-map-node-tier">Camada {data.tier + 1}</span>
      <Handle type="source" position={Position.Right} className="live-map-handle" />
    </div>
  )
}

const nodeTypes = { eco: EcoNode }

function layoutWithDagre(data: Ecosystem): Node<EcoData, 'eco'>[] {
  const graph = new graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: 'LR', nodesep: 56, ranksep: 92, marginx: 36, marginy: 36 })

  for (const node of data.nodes) graph.setNode(node.id, { width: 190, height: 112 })
  for (const edge of data.edges) graph.setEdge(edge.source, edge.target)
  dagreLayout(graph)

  return data.nodes.map((node) => {
    const position = graph.node(node.id)
    return {
      id: node.id,
      type: 'eco',
      position: { x: (position?.x || 0) - 95, y: (position?.y || 0) - 56 },
      data: { label: node.label, kind: node.kind, type: node.type, tier: node.tier },
    }
  })
}

function buildEdges(data: Ecosystem, selectedNodeId: string | null): Edge[] {
  return data.edges.map((edge, index) => {
    const highlighted = Boolean(
      selectedNodeId && (edge.source === selectedNodeId || edge.target === selectedNodeId),
    )
    return {
      id: `edge-${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      type: 'smoothstep',
      animated: highlighted,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 15,
        height: 15,
        color: highlighted ? '#f0a85f' : '#425370',
      },
      style: {
        stroke: highlighted ? '#f0a85f' : '#425370',
        strokeWidth: highlighted ? 2.2 : 1.4,
      },
      labelStyle: { fill: '#8b9cb3', fontSize: 10, fontWeight: 500 },
      labelBgStyle: { fill: '#111722', fillOpacity: 0.94 },
      labelBgPadding: [5, 3] as [number, number],
      labelBgBorderRadius: 4,
    }
  })
}

export function EcosystemMap({ data }: { data: Ecosystem }) {
  const nodes = useMemo(() => layoutWithDagre(data), [data])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(data.nodes[0]?.id || null)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)

  const selectedNode = data.nodes.find((node) => node.id === selectedNodeId) || data.nodes[0] || null
  const edges = useMemo(() => buildEdges(data, selectedNodeId), [data, selectedNodeId])
  const incoming = selectedNode ? data.edges.filter((edge) => edge.target === selectedNode.id) : []
  const outgoing = selectedNode ? data.edges.filter((edge) => edge.source === selectedNode.id) : []
  const externalCount = data.nodes.filter((node) => node.kind === 'external').length

  useEffect(() => {
    if (!assistantOpen) return
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setAssistantOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [assistantOpen])

  function localAnswer() {
    if (!selectedNode) return
    setAnswer(
      `${selectedNode.label} possui ${incoming.length} conexão(ões) de entrada e ${outgoing.length} de saída no contexto ${data.product}. A análise foi feita localmente usando somente a topologia desta tenancy. Nenhuma alteração foi executada.`,
    )
  }

  function askObserva(event: FormEvent) {
    event.preventDefault()
    if (!question.trim()) return
    localAnswer()
  }

  function handleSuggestedQuestion(value: string) {
    setQuestion(value)
    localAnswer()
  }

  return (
    <div className="live-map-shell">
      <div className="live-map-canvas-wrap">
        <div className="live-map-canvas-head">
          <div>
            <strong>Topologia observada</strong>
            <span>Selecione um componente para investigar dependências.</span>
          </div>
          <div className="live-map-summary" aria-label="Resumo do ecossistema">
            <span><b>{data.nodes.length}</b> componentes</span>
            <span><b>{data.edges.length}</b> conexões</span>
            <span><b>{externalCount}</b> externos</span>
          </div>
        </div>
        <div className="live-map-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id)
              setAnswer(null)
            }}
            fitView
            fitViewOptions={{ padding: 0.22 }}
            minZoom={0.35}
            maxZoom={1.6}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} color="#29364a" gap={22} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </div>

      <aside className="live-map-inspector" aria-label="Detalhes do componente selecionado">
        {selectedNode ? (
          <>
            <div className="live-map-inspector-head">
              <div>
                <span className={`live-map-kind kind-${selectedNode.kind}`}>
                  {KIND_META[selectedNode.kind]?.label || selectedNode.kind}
                </span>
                <h2>{selectedNode.label}</h2>
                <p>{selectedNode.type || 'Tipo não informado pelo conector'}</p>
              </div>
              <span className="live-map-health">Mapeado</span>
            </div>

            <div className="live-map-detail-grid">
              <div><span>Produto</span><strong>{data.product}</strong></div>
              <div><span>Camada</span><strong>{selectedNode.tier + 1}</strong></div>
              <div><span>Entradas</span><strong>{incoming.length}</strong></div>
              <div><span>Saídas</span><strong>{outgoing.length}</strong></div>
            </div>

            <div className="live-map-section">
              <div className="live-map-section-title">Dependências diretas</div>
              {incoming.length + outgoing.length > 0 ? (
                <div className="live-map-dependencies">
                  {incoming.map((edge) => (
                    <button key={`in-${edge.source}`} type="button" onClick={() => setSelectedNodeId(edge.source)}>
                      <span>Recebe de</span>
                      <strong>{data.nodes.find((node) => node.id === edge.source)?.label}</strong>
                    </button>
                  ))}
                  {outgoing.map((edge) => (
                    <button key={`out-${edge.target}`} type="button" onClick={() => setSelectedNodeId(edge.target)}>
                      <span>Envia para</span>
                      <strong>{data.nodes.find((node) => node.id === edge.target)?.label}</strong>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="muted">Nenhuma dependência direta registrada.</p>
              )}
            </div>

            <div className="live-map-section">
              <div className="live-map-section-title">Identificador</div>
              <code className="live-map-id">{selectedNode.id}</code>
            </div>

            <div className="live-map-local-note">
              <span className="live-map-ai-mark" aria-hidden="true">✦</span>
              <div>
                <strong>Análise local por padrão</strong>
                <p>Nenhum dado deste componente é enviado para IA externa.</p>
              </div>
            </div>
          </>
        ) : (
          <p className="muted">Selecione um componente no mapa.</p>
        )}
      </aside>

      <button
        type="button"
        className="live-map-ask-button"
        onClick={() => setAssistantOpen(true)}
        aria-expanded={assistantOpen}
      >
        <span aria-hidden="true">✦</span>
        Pergunte ao Observa
      </button>

      {assistantOpen && (
        <div className="live-map-ai-panel" role="dialog" aria-label="Pergunte ao Observa">
          <div className="live-map-ai-head">
            <div><span>Análise local</span><h2>Pergunte ao Observa</h2></div>
            <button type="button" onClick={() => setAssistantOpen(false)} aria-label="Fechar assistente" autoFocus>×</button>
          </div>
          <div className="live-map-ai-context">
            <span>Contexto atual</span>
            <strong>{data.product} / {selectedNode?.label || 'Ecossistema'}</strong>
          </div>
          <div className="live-map-suggestions">
            {[
              'Quais são as dependências deste componente?',
              'Existe algum ponto único de falha?',
              'Que dados estão disponíveis para analisar custos?',
            ].map((suggestion) => (
              <button key={suggestion} type="button" onClick={() => handleSuggestedQuestion(suggestion)}>{suggestion}</button>
            ))}
          </div>
          {answer && <div className="live-map-ai-answer" aria-live="polite">{answer}</div>}
          <form className="live-map-ai-form" onSubmit={askObserva}>
            <label htmlFor="ecosystem-question">Pergunta</label>
            <textarea
              id="ecosystem-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Pergunte sobre dependências, risco ou custo…"
            />
            <button type="submit" disabled={!question.trim()}>Analisar localmente</button>
          </form>
          <p className="live-map-ai-privacy">Company e tenancy ativas são respeitadas. Nenhuma ação real será executada.</p>
        </div>
      )}
    </div>
  )
}
