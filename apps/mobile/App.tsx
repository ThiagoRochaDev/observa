import * as SecureStore from 'expo-secure-store'
import { StatusBar } from 'expo-status-bar'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

type Summary = { total: number; change_pct: number; open_alerts: number }
type Resource = { uid: number; provider: string; name?: string; id: string; product?: string }
type Action = { id: string; action: string; resource_uid: number; status: string; reason?: string }

const KEY = 'observa_api_key'

export default function App() {
  const [apiUrl, setApiUrl] = useState('http://10.0.2.2:8080')
  const [apiKey, setApiKey] = useState('')
  const [savedKey, setSavedKey] = useState('')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [resources, setResources] = useState<Resource[]>([])
  const [actions, setActions] = useState<Action[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    SecureStore.getItemAsync(KEY).then((value) => {
      if (value) {
        setApiKey(value)
        setSavedKey(value)
      }
    })
  }, [])

  useEffect(() => {
    if (savedKey) refresh()
  }, [savedKey])

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl.replace(/\/$/, '')}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', 'X-Observa-Api-Key': savedKey, ...init?.headers },
    })
    if (!response.ok) throw new Error(`API ${response.status}: ${await response.text()}`)
    return response.json()
  }

  async function refresh() {
    setLoading(true)
    setError('')
    try {
      const [cost, unmapped, pending] = await Promise.all([
        request<Summary>('/api/costs/summary'),
        request<Resource[]>('/api/resources?untagged=true'),
        request<Action[]>('/api/automation/actions?status=pending_approval'),
      ])
      setSummary(cost)
      setResources(unmapped)
      setActions(pending)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setLoading(false)
    }
  }

  async function login() {
    await SecureStore.setItemAsync(KEY, apiKey.trim())
    setSavedKey(apiKey.trim())
  }

  async function decide(actionId: string, approve: boolean) {
    await request(`/api/automation/actions/${actionId}/${approve ? 'approve' : 'reject'}`, {
      method: 'POST',
      body: approve ? '{}' : JSON.stringify({ reason: 'Rejeitado no app mobile' }),
    })
    await refresh()
  }

  if (!savedKey) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="light" />
        <View style={styles.login}>
          <Text style={styles.brand}>Observa</Text>
          <Text style={styles.subtitle}>FinOps e governança multicloud</Text>
          <TextInput style={styles.input} value={apiUrl} onChangeText={setApiUrl} autoCapitalize="none" />
          <TextInput
            style={styles.input}
            value={apiKey}
            onChangeText={setApiKey}
            placeholder="API key"
            placeholderTextColor="#718096"
            secureTextEntry
            autoCapitalize="none"
          />
          <Pressable style={styles.primaryButton} onPress={login}><Text style={styles.primaryText}>Conectar</Text></Pressable>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} tintColor="#59d9b5" />}
      >
        <Text style={styles.brand}>Observa</Text>
        <Text style={styles.subtitle}>Custos, recursos e aprovações</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {loading && !summary ? <ActivityIndicator color="#59d9b5" /> : null}

        <View style={styles.metrics}>
          <Metric label="Custo 30 dias" value={summary ? money(summary.total) : '—'} />
          <Metric label="Variação" value={summary ? `${summary.change_pct.toFixed(1)}%` : '—'} />
          <Metric label="Alertas" value={String(summary?.open_alerts ?? 0)} />
        </View>

        <Text style={styles.sectionTitle}>Aprovações pendentes</Text>
        {actions.length === 0 ? <Empty text="Nenhuma ação aguardando você." /> : actions.map((action) => (
          <View style={styles.card} key={action.id}>
            <Text style={styles.cardTitle}>{action.action.toUpperCase()} · recurso #{action.resource_uid}</Text>
            <Text style={styles.cardText}>{action.reason || 'Ação agendada'}</Text>
            <View style={styles.actions}>
              <Pressable style={styles.primaryButton} onPress={() => decide(action.id, true)}><Text style={styles.primaryText}>Aprovar</Text></Pressable>
              <Pressable style={styles.dangerButton} onPress={() => decide(action.id, false)}><Text style={styles.dangerText}>Rejeitar</Text></Pressable>
            </View>
          </View>
        ))}

        <Text style={styles.sectionTitle}>Recursos sem mapeamento</Text>
        {resources.length === 0 ? <Empty text="Todos os recursos estão mapeados." /> : resources.slice(0, 20).map((resource) => (
          <View style={styles.card} key={resource.uid}>
            <Text style={styles.cardTitle}>{resource.name || resource.id}</Text>
            <Text style={styles.cardText}>{resource.provider} · #{resource.uid}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <View style={styles.metric}><Text style={styles.metricValue}>{value}</Text><Text style={styles.cardText}>{label}</Text></View>
}

function Empty({ text }: { text: string }) {
  return <View style={styles.card}><Text style={styles.cardText}>{text}</Text></View>
}

function money(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value)
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#080b10' },
  content: { padding: 20, paddingBottom: 48 },
  login: { flex: 1, justifyContent: 'center', padding: 28, gap: 14 },
  brand: { color: '#f5f7fa', fontSize: 32, fontWeight: '800' },
  subtitle: { color: '#94a3b8', marginBottom: 20 },
  input: { backgroundColor: '#121821', borderColor: '#263244', borderWidth: 1, borderRadius: 10, color: '#f5f7fa', padding: 14 },
  metrics: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  metric: { flex: 1, backgroundColor: '#121821', borderRadius: 12, padding: 12, borderColor: '#263244', borderWidth: 1 },
  metricValue: { color: '#59d9b5', fontSize: 18, fontWeight: '800' },
  sectionTitle: { color: '#f5f7fa', fontSize: 19, fontWeight: '700', marginTop: 8, marginBottom: 10 },
  card: { backgroundColor: '#121821', borderRadius: 12, padding: 15, borderColor: '#263244', borderWidth: 1, marginBottom: 10 },
  cardTitle: { color: '#f5f7fa', fontWeight: '700' },
  cardText: { color: '#94a3b8', marginTop: 4 },
  actions: { flexDirection: 'row', gap: 10, marginTop: 14 },
  primaryButton: { backgroundColor: '#59d9b5', borderRadius: 9, paddingVertical: 11, paddingHorizontal: 16 },
  primaryText: { color: '#07110e', fontWeight: '800', textAlign: 'center' },
  dangerButton: { borderColor: '#f87171', borderWidth: 1, borderRadius: 9, paddingVertical: 10, paddingHorizontal: 16 },
  dangerText: { color: '#f87171', fontWeight: '700' },
  error: { color: '#f87171', marginBottom: 12 },
})
