# Guia completo de testes do Observa

Este documento mostra como validar o Observa de ponta a ponta: infraestrutura local, API,
banco de dados, interface web, conectores, governança FinOps, CLI, aplicativo mobile,
autenticação e testes automatizados.

> **Importante:** comece sempre com o conector `mock-demo` e com políticas em `dry-run`.
> Só habilite alterações reais em uma cloud depois de validar permissões, escopo e recursos.

## 1. O que será testado

| Camada | Funcionalidades |
|---|---|
| API FastAPI | autenticação por API key, catálogo, custos, inventário, métricas, alertas e governança |
| Banco SQLite | conexões, recursos, custos, métricas, políticas, ações e auditoria |
| Web Next.js | todas as telas do menu e fluxos de conexão/governança |
| Conectores | teste de credencial, sincronização e capacidades declaradas |
| CLI | inventário, tags, políticas, execução e aprovações |
| Mobile Expo | custos, recursos sem mapeamento e aprovações |
| Segurança | bloqueio sem API key, `dry-run`, aprovação e write-back controlado |
| Qualidade | testes Python, TypeScript, ESLint e builds |

## 2. Pré-requisitos

### Opção recomendada: Docker

- Docker Desktop com Docker Compose.
- Portas `3000` e `8080` livres.
- PowerShell 7 ou Windows PowerShell.

### Desenvolvimento sem Docker

- Python 3.12 ou superior.
- Node.js 20 ou superior.
- npm.
- Git Bash ou WSL para executar `scripts/dev-local.sh`.
- Android Studio, emulador Android ou Expo Go para o app mobile.

Confirme as ferramentas:

```powershell
docker --version
docker compose version
python --version
node --version
npm.cmd --version
```

## 3. Preparar o projeto

No PowerShell:

```powershell
cd "C:\Users\thiag\Downloads\PROJECTS_TGR_TECHNOLOGY\observa"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

O arquivo `.env` permite alterar as portas:

```dotenv
WEB_PORT=3000
API_PORT=8080
```

## 4. Subir com Docker

```powershell
docker compose up -d --build
docker compose ps
docker compose logs api --tail 100
docker compose logs web --tail 100
```

Resultado esperado:

- Serviço `api` em execução na porta `8080`.
- Serviço `web` em execução na porta `3000`.
- Log da API contendo a chave criada no primeiro boot.
- Seed do `mock-demo` concluído.

Endereços:

- Web: `http://localhost:3000`
- Swagger: `http://localhost:8080/docs`
- Health público: `http://localhost:8080/healthz`

### Encontrar a API key

```powershell
docker compose logs api | Select-String -Pattern "API key|api_key|Observa"
```

Se o projeto estiver rodando localmente, a chave fica em `data/api_key`:

```powershell
$apiKey = (Get-Content .\data\api_key -Raw).Trim()
$apiKey
```

Com Docker, copie a chave exibida no log:

```powershell
$apiKey = "COLE_A_CHAVE_AQUI"
```

Prepare os headers usados nos testes da API:

```powershell
$baseUrl = "http://localhost:8080"
$headers = @{ "X-Observa-Api-Key" = $apiKey }
```

## 5. Smoke test inicial

### Health público

```powershell
Invoke-RestMethod "$baseUrl/healthz"
```

Esperado:

```json
{"status":"ok"}
```

### Health protegido

```powershell
Invoke-RestMethod "$baseUrl/api/health" -Headers $headers
```

Verifique:

- `status` igual a `ok`.
- `app` igual a `observa`.
- Uma ou mais conexões.
- Registros de custo e métricas maiores que zero.
- `auth_mode` igual a `local` no primeiro uso.

### Proteção sem chave

```powershell
try {
  Invoke-RestMethod "$baseUrl/api/health"
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

Esperado: HTTP `401`.

## 6. Testar a interface web completa

Abra `http://localhost:3000`. Quando solicitado, informe a API key.

### 6.1 Overview

Rota: `/`

1. Confirme o custo total dos últimos 30 dias.
2. Confira quantidade de produtos, providers e alertas.
3. Valide o gráfico de tendência diária.
4. Confira custos por provider, produto e squad.
5. Compare o total da tela com `GET /api/costs/summary`.

Esperado: os cards e gráficos devem estar preenchidos pelo `mock-demo`.

### 6.2 Products

Rota: `/products`

1. Confira nome, squad, tribe, custo, serviços e recursos.
2. Abra um produto, por exemplo `hiperlocal`.
3. Valide custos por provider e serviço.
4. Confira inventário e métricas vinculadas ao produto.

API equivalente:

```powershell
Invoke-RestMethod "$baseUrl/api/products" -Headers $headers
Invoke-RestMethod "$baseUrl/api/products/hiperlocal" -Headers $headers
```

### 6.3 Ecosystem maps

Rota: `/maps`

1. Alterne entre os produtos.
2. Arraste e aplique zoom no grafo.
3. Confirme nós de frontend, API, worker, banco e dependências.
4. Verifique se as conexões mudam ao selecionar outro produto.

API equivalente:

```powershell
Invoke-RestMethod "$baseUrl/api/ecosystem?product=hiperlocal" -Headers $headers
```

### 6.4 Inventory

Rota: `/inventory`

1. Confira tipo, nome, provider, região, status e produto.
2. Abra produtos através dos links da primeira coluna.
3. Compare a quantidade com `GET /api/resources`.
4. Identifique recursos sem produto ou labels.

```powershell
Invoke-RestMethod "$baseUrl/api/resources" -Headers $headers
Invoke-RestMethod "$baseUrl/api/resources?untagged=true" -Headers $headers
```

### 6.5 Governance

Rota: `/governance`

#### Aplicar tag

1. Selecione um recurso sem mapeamento.
2. Informe `owner` como tag.
3. Informe `platform-team` como valor.
4. Clique em **Aplicar na cloud**.
5. Recarregue a página e confirme que o recurso saiu da lista quando estiver completamente mapeado.

No conector mock, a ação simula o write-back e atualiza o catálogo local. Na AWS, EC2 recebe a
tag real quando `dry_run=false` e a credencial possui permissão.

#### Criar agendamento

1. Selecione um recurso.
2. Dê um nome para a política.
3. Mantenha `America/Sao_Paulo`.
4. Defina hora para ligar e desligar.
5. Opcionalmente defina a data limite.
6. Crie a política.

Esperado: a política aparece em **Políticas ativas** com badge `dry-run`.

#### Aprovar ou rejeitar ação

1. Execute o avaliador pelo endpoint ou CLI, conforme a seção 10.
2. Volte à tela Governance.
3. Localize a ação pendente.
4. Clique em **Aprovar**.
5. Confirme status `simulated` para política `dry-run`.
6. Crie outra ação e clique em **Rejeitar**.
7. Confirme status `rejected`.

### 6.5.1 Budgets

Rota: `/budgets`

1. Crie um budget para um produto existente, como `hiperlocal`.
2. Use um valor baixo em ambiente demo para atingir o limite.
3. Selecione resposta `Solicitar desligamento`.
4. Informe o owner e um UID de recurso do Inventory.
5. Clique em **Sincronizar e avaliar**.
6. Confirme evento crítico e ação pendente na tela Governance.
7. Aprove a ação e confirme status `simulated` quando a regra estiver em dry-run.
8. Crie regras `Notificar` e `Ignorar` e compare os eventos gerados.

### 6.6 Dashboards

Rota: `/dashboards`

1. Confirme os dashboards disponíveis.
2. Abra cada card.
3. Verifique gráficos, listas, KPIs e status.
4. Confirme que uma rota dinâmica `/dashboards/{id}` é aberta sem erro.

```powershell
$dashboards = Invoke-RestMethod "$baseUrl/api/dashboards" -Headers $headers
$dashboards
Invoke-RestMethod "$baseUrl/api/dashboards/$($dashboards[0].id)" -Headers $headers
```

### 6.7 APM & Infra

Rota: `/observability`

Valide por produto:

- Latência P95.
- Taxa de erro.
- Requests por minuto.
- CPU.
- Conexões e CPU do banco.

```powershell
Invoke-RestMethod "$baseUrl/api/observability" -Headers $headers
Invoke-RestMethod "$baseUrl/api/metrics/series?name=apm.latency_p95_ms&product=hiperlocal" -Headers $headers
```

### 6.8 Logs

Rota: `/logs`

1. Filtre por produto.
2. Filtre por severidade.
3. Filtre por source.
4. Pesquise texto livre.
5. Confirme que limpar filtros restaura a listagem.

```powershell
Invoke-RestMethod "$baseUrl/api/logs?limit=20&product=hiperlocal&severity=error" -Headers $headers
Invoke-RestMethod "$baseUrl/api/logs?q=timeout" -Headers $headers
```

### 6.9 Traces

Rota: `/traces`

1. Confira trace ID, produto, serviço, duração e status.
2. Abra um trace.
3. Valide o waterfall e os spans.
4. Confirme destaque para spans com erro.

```powershell
Invoke-RestMethod "$baseUrl/api/traces?limit=10" -Headers $headers
```

### 6.10 Monitors

Rota: `/monitors`

Confira nome, tipo, status, produto, query e origem:

```powershell
Invoke-RestMethod "$baseUrl/api/monitors" -Headers $headers
```

### 6.11 RUM & Synthetics

Rota: `/rum`

Confira sessões, LCP, erros JavaScript, crash-free, views principais e disponibilidade dos testes:

```powershell
Invoke-RestMethod "$baseUrl/api/rum" -Headers $headers
Invoke-RestMethod "$baseUrl/api/synthetics" -Headers $headers
```

### 6.12 GCP Monitoring

Rota: `/gcp`

Confira o projeto exibido, séries e tipos de métricas:

```powershell
Invoke-RestMethod "$baseUrl/api/gcp/monitoring" -Headers $headers
```

Essa tela usa dados demonstrativos até que uma fonte compatível forneça os sinais.

### 6.13 Alerts

Rota: `/alerts`

1. Confira severidade, categoria, produto e status.
2. Verifique alertas de custo, APM, banco, infraestrutura e recomendações.
3. Compare alertas abertos com o KPI da Overview.

```powershell
Invoke-RestMethod "$baseUrl/api/alerts" -Headers $headers
Invoke-RestMethod "$baseUrl/api/alerts?status=open" -Headers $headers
```

### 6.14 Connections

Rota: `/connections`

1. Confira o catálogo agrupado por categoria.
2. Abra `Mock Demo`.
3. Teste a conexão.
4. Salve com o nome `Teste manual`.
5. Execute Sync.
6. Confira data, status e mensagem da última sincronização.
7. Exclua a conexão criada manualmente.

Não exclua a conexão `Demo Full Platform` durante os primeiros testes.

### 6.15 Authentication

Rota: `/settings/auth`

1. Confirme modo `local`.
2. Verifique formulários Google e GitLab.
3. Salve mantendo modo local.
4. Recarregue e confirme persistência.

Não ative OIDC antes de configurar client ID, client secret, issuer e redirect URI corretamente.

## 7. Testar CRUD de conexões pela API

### Catálogo

```powershell
Invoke-RestMethod "$baseUrl/api/connectors" -Headers $headers
```

### Testar o mock sem salvar

```powershell
$body = @{
  connector_id = "mock-demo"
  config = @{ days = 7 }
  secrets = @{}
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "$baseUrl/api/connections/test" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

### Criar, sincronizar, editar e excluir

```powershell
$createBody = @{
  name = "Mock via API"
  connector_id = "mock-demo"
  config = @{ days = 7; profile = "full" }
  secrets = @{}
} | ConvertTo-Json -Depth 5

$connection = Invoke-RestMethod "$baseUrl/api/connections" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $createBody

$connection
$connectionId = $connection.id

Invoke-RestMethod "$baseUrl/api/connections/$connectionId/sync" `
  -Method Post -Headers $headers

$patchBody = @{ name = "Mock renomeado" } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/connections/$connectionId" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $patchBody

Invoke-RestMethod "$baseUrl/api/connections/$connectionId" `
  -Method Delete -Headers $headers
```

Esperado: credenciais nunca aparecem na resposta da API.

## 8. Testar custos, produtos e sinais pela API

```powershell
Invoke-RestMethod "$baseUrl/api/demo/seed" -Method Post -Headers $headers
Invoke-RestMethod "$baseUrl/api/costs/summary?days=30" -Headers $headers
Invoke-RestMethod "$baseUrl/api/costs/trend?days=30" -Headers $headers
Invoke-RestMethod "$baseUrl/api/products" -Headers $headers
Invoke-RestMethod "$baseUrl/api/resources" -Headers $headers
Invoke-RestMethod "$baseUrl/api/observability" -Headers $headers
```

Valide:

- Valores numéricos não negativos.
- Providers presentes no resumo.
- Tendência ordenada por data.
- Recursos associados aos produtos.
- Métricas com timestamp, unidade e valor.

## 9. Testar tags e labels com segurança

Escolha um recurso:

```powershell
$resource = (Invoke-RestMethod "$baseUrl/api/resources" -Headers $headers)[0]
$resource | ConvertTo-Json -Depth 6
$resourceUid = $resource.uid
```

### Preview sem alterar

```powershell
$tagPreview = @{
  tags = @{ owner = "platform-team"; cost_center = "cc-100" }
  dry_run = $true
  write_back = $true
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "$baseUrl/api/resources/$resourceUid/tags" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $tagPreview
```

Esperado: `dry_run=true` e recurso sem alteração persistida.

### Atualizar apenas o catálogo local

```powershell
$tagLocal = @{
  tags = @{ owner = "platform-team"; product = "observa" }
  dry_run = $false
  write_back = $false
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "$baseUrl/api/resources/$resourceUid/tags" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $tagLocal
```

### Write-back no provider

Use somente com mock ou AWS EC2 previamente autorizado:

```powershell
$tagCloud = @{
  tags = @{ owner = "platform-team" }
  dry_run = $false
  write_back = $true
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "$baseUrl/api/resources/$resourceUid/tags" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $tagCloud
```

Para AWS, confirme a tag também no console EC2.

## 10. Testar políticas, agendamentos e aprovações

### Criar política determinística

Use um horário próximo ou o campo `at` no avaliador:

```powershell
$resource = (Invoke-RestMethod "$baseUrl/api/resources" -Headers $headers)[0]

$policyBody = @{
  name = "Teste de desligamento"
  resource_ids = @($resource.uid)
  selector = @{}
  timezone = "UTC"
  weekdays = @(0,1,2,3,4,5,6)
  start_time = "07:00"
  stop_time = "20:00"
  expiration_action = "stop"
  enabled = $true
  require_approval = $true
  dry_run = $true
} | ConvertTo-Json -Depth 6

$policy = Invoke-RestMethod "$baseUrl/api/automation/policies" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $policyBody

$policy
```

### Avaliar o horário agendado

```powershell
$runBody = @{ at = "2026-09-17T20:00:00Z" } | ConvertTo-Json
$run = Invoke-RestMethod "$baseUrl/api/automation/run-due" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $runBody
$run
```

Esperado: uma ação `stop` com status `pending_approval`.

Execute novamente com o mesmo timestamp:

```powershell
Invoke-RestMethod "$baseUrl/api/automation/run-due" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $runBody
```

Esperado: nenhuma ação duplicada para o mesmo minuto.

### Aprovar

```powershell
$actionId = $run.created[0].id
Invoke-RestMethod "$baseUrl/api/automation/actions/$actionId/approve" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
```

Esperado: status `simulated`, pois a política está em `dry-run`.

### Rejeitar

Crie outra ação para outro minuto e execute:

```powershell
$actions = Invoke-RestMethod "$baseUrl/api/automation/actions?status=pending_approval" -Headers $headers
$rejectBody = @{ reason = "Teste de rejeição" } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/automation/actions/$($actions[0].id)/reject" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $rejectBody
```

### Alterar ou remover política

```powershell
$disableBody = @{ enabled = $false } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/automation/policies/$($policy.id)" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $disableBody

Invoke-RestMethod "$baseUrl/api/automation/policies/$($policy.id)" `
  -Method Delete -Headers $headers
```

### Testar data limite

Crie uma política com `expires_at` no passado e execute `run-due`. A ação configurada em
`expiration_action` deve ser criada independentemente do horário recorrente.

### Testar budgets e forecast

```powershell
$budgetBody = @{
  name = "Budget hiperlocal"
  scope_type = "product"
  scope_value = "hiperlocal"
  amount = 100
  currency = "BRL"
  window_days = 30
  warning_threshold = 0.8
  critical_threshold = 1.0
  response_mode = "approval"
  owner = "squad-hiperlocal"
  resource_ids = @($resource.uid)
  dry_run = $true
  enabled = $true
} | ConvertTo-Json -Depth 6

$budget = Invoke-RestMethod "$baseUrl/api/budgets" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $budgetBody

Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"

Invoke-RestMethod "$baseUrl/api/budgets/events?rule_id=$($budget.id)" -Headers $headers
```

Execute a avaliação duas vezes no mesmo dia e confirme que o segundo ciclo não duplica o evento.

## 11. Testar o scheduler operacional

O endpoint abaixo deve ser chamado uma vez por minuto:

```powershell
Invoke-RestMethod "$baseUrl/api/automation/run-due" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
```

Exemplo de cron Linux:

```cron
* * * * * curl -sS -X POST http://localhost:8080/api/automation/run-due \
  -H "X-Observa-Api-Key: SUA_CHAVE" -H "Content-Type: application/json" -d '{}'
```

Em produção, use Kubernetes CronJob, EventBridge Scheduler, Cloud Scheduler ou equivalente.

## 12. Testar o CLI

### Instalar em modo editável

```powershell
cd "C:\Users\thiag\Downloads\PROJECTS_TGR_TECHNOLOGY\observa"
python -m pip install -e .\apps\cli
$env:OBSERVA_URL = "http://localhost:8080"
$env:OBSERVA_API_KEY = $apiKey
observa --help
```

### Inventário

```powershell
observa resources
observa resources --untagged
observa resources --product hiperlocal
observa --json resources --untagged
```

### Tags

Preview:

```powershell
observa tag 1 --set owner=platform --set cost_center=cc-100
```

Aplicação local:

```powershell
observa tag 1 --set owner=platform --apply --local-only
```

Write-back:

```powershell
observa tag 1 --set owner=platform --apply
```

### Políticas

```powershell
observa policies list
observa policies create "Horário de homologação" `
  --selector environment=staging `
  --timezone America/Sao_Paulo `
  --start 07:00 `
  --stop 20:00
```

Por recurso:

```powershell
observa policies create "Expiração temporária" `
  --resource 1 `
  --expires-at 2026-12-31T23:59:00-03:00
```

### Ações

```powershell
observa run-due --at 2026-09-17T20:00:00Z
observa actions list
observa actions list --status pending_approval
observa actions approve act_ID
observa actions reject act_ID --reason "Ambiente ainda necessário"
```

### Budgets

```powershell
observa budgets create "Budget hiperlocal" `
  --scope product --value hiperlocal --amount 5000 `
  --warning 80 --critical 100 --response approval `
  --owner squad-hiperlocal --resource 12
observa budgets list
observa budgets evaluate
observa budgets monitor
observa budgets events
```

Esperado: os resultados devem ser equivalentes aos endpoints REST.

## 13. Testar o aplicativo mobile

### Instalar e iniciar

```powershell
cd "C:\Users\thiag\Downloads\PROJECTS_TGR_TECHNOLOGY\observa\apps\mobile"
npm.cmd install
npm.cmd start
```

Escolha Android, iOS ou Expo Go.

### URL correta da API

- Android Emulator: `http://10.0.2.2:8080`
- iOS Simulator: `http://localhost:8080`
- Dispositivo físico: `http://IP_DA_MAQUINA:8080`

No dispositivo físico, computador e celular devem estar na mesma rede. Libere a porta `8080`
no firewall apenas para a rede privada.

### Checklist mobile

1. Informe URL e API key.
2. Toque em **Conectar**.
3. Confira custo, variação e alertas.
4. Puxe a tela para atualizar.
5. Confira recursos sem mapeamento.
6. Gere uma ação pendente pela API ou CLI.
7. Atualize a tela.
8. Aprove a ação e confirme que ela desapareceu dos pendentes.
9. Gere outra ação e rejeite.
10. Reinicie o aplicativo e confirme que a API key continua armazenada com SecureStore.

## 14. Testar conectores reais

Use a tela **Connections** para todos os conectores:

1. Selecione o conector.
2. Preencha campos de configuração.
3. Informe os segredos.
4. Clique em **Test connection**.
5. Salve apenas após o teste retornar sucesso.
6. Clique em **Sync**.
7. Confira `last_sync_status` e `last_sync_message`.
8. Valide os dados na tela correspondente.

Consulte `docs/CONNECTORS.md` para campos e status de cada integração.

### AWS Cost Explorer e EC2

Capacidades atuais: `cost`, `inventory`, `tags:write` e `power:write`.

Valide nesta ordem:

1. `Test connection` com STS.
2. Sync do Cost Explorer.
3. Inventário EC2.
4. Preview de tag.
5. Aplicação de uma tag não destrutiva.
6. Política `dry-run` de stop/start.
7. Somente em conta de laboratório, ação real de stop/start.

Permissões mínimas típicas:

- `sts:GetCallerIdentity`
- `ce:GetCostAndUsage`
- `ec2:DescribeInstances`
- `ec2:CreateTags`
- `ec2:StartInstances`
- `ec2:StopInstances`

Restrinja ações aos ARNs e tags permitidos pela organização.

### GCP Billing

Capacidade atual: custos via tabela de exportação do Cloud Billing no BigQuery.

1. Configure `project_id`.
2. Configure `billing_table` como `project.dataset.table`.
3. Informe o JSON da service account ou use ADC.
4. Teste a conexão.
5. Sincronize.
6. Confira provider `gcp` em Overview e Products.

Write-back de labels e power actions ainda não estão implementados nesse conector.

### Azure Cost Management

Capacidade atual: custos por subscription.

1. Configure `subscription_id`.
2. Informe tenant ID, client ID e client secret.
3. Teste a obtenção do token.
4. Sincronize.
5. Confira provider `azure` nos custos.

Write-back de tags e power actions ainda não estão implementados nesse conector.

### Observabilidade e SaaS

Para Datadog, New Relic, Grafana Cloud, Elastic, Prometheus, Kubernetes, Splunk, Sentry,
PagerDuty, Opsgenie, GitHub, GitLab, Bitbucket, Cloudflare, DigitalOcean, Vercel, Netlify,
MongoDB Atlas, Stripe, Snowflake, Linode e OCI:

1. Confirme as capacidades mostradas no card.
2. Use credencial somente leitura inicialmente.
3. Teste a conexão.
4. Sincronize.
5. Procure os sinais nas telas Inventory, Overview, Products, APM, Logs ou Alerts.
6. Confirme que remover a conexão também remove os dados sincronizados por ela.

## 15. Testar autenticação

### Modo local

```powershell
Invoke-RestMethod "$baseUrl/api/auth/me" -Headers $headers
Invoke-RestMethod "$baseUrl/api/auth/settings" -Headers $headers
```

Esperado: `mode=local`.

### Persistência de configuração

```powershell
$authBody = @{
  mode = "local"
  providers = @{}
} | ConvertTo-Json -Depth 5

Invoke-RestMethod "$baseUrl/api/auth/settings" `
  -Method Put -Headers $headers -ContentType "application/json" -Body $authBody
```

### OIDC Google ou GitLab

Antes de ativar:

1. Cadastre a aplicação no provider.
2. Use callback `http://localhost:8080/auth/callback/google` ou `/gitlab`.
3. Configure client ID, client secret e issuer na UI.
4. Ative apenas um provider primeiro.
5. Abra uma janela anônima.
6. Confirme redirecionamento, callback e identidade em `/api/auth/me`.
7. Confirme que o client secret não é retornado em texto puro.

## 16. Validar persistência no SQLite

O banco local fica em `data/observa.db`. Faça backup antes de inspeções manuais:

```powershell
Copy-Item .\data\observa.db .\data\observa.backup.db
```

Uma forma de listar contagens usando Python:

```powershell
@'
import sqlite3

db = sqlite3.connect("data/observa.db")
for table in (
    "connections", "cost_records", "resources", "metrics", "alerts",
    "automation_policies", "action_runs", "audit_events",
):
    count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")
'@ | python -
```

Valide que:

- Sincronizar o mesmo recurso mantém seu `uid`.
- Tags locais permanecem após uma nova sincronização quando o provider não devolve labels.
- Políticas apontam para recursos estáveis.
- Aprovações e rejeições criam eventos de auditoria.

## 17. Executar os testes automatizados

### API e conectores

No Windows, usando o ambiente virtual já criado:

```powershell
cd "C:\Users\thiag\Downloads\PROJECTS_TGR_TECHNOLOGY\observa"
$env:PYTHONPATH = "$PWD\apps\api;$PWD\packages\connectors;$PWD\apps\cli"
& .\apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests packages\connectors\tests -q
```

Resultado esperado atual: todos os testes passam.

### Web

```powershell
npm.cmd --prefix apps\web run typecheck
npm.cmd --prefix apps\web run lint
npm.cmd --prefix apps\web run build
```

O lint pode mostrar warnings preexistentes de navegação, mas não deve mostrar erros.

### Mobile

```powershell
npm.cmd --prefix apps\mobile run typecheck
```

### CLI

```powershell
$env:PYTHONPATH = "$PWD\apps\cli"
python -m observa_cli.main --help
```

## 18. Testes de falha e segurança

Execute também os cenários negativos:

| Cenário | Resultado esperado |
|---|---|
| API sem chave | HTTP 401 |
| Connector ID inexistente | HTTP 400 |
| Connection ID inexistente | HTTP 404 |
| Resource UID inexistente | HTTP 404 |
| Política sem recurso e sem selector | HTTP 400 |
| Timezone inválido | HTTP 400 |
| Aprovar ação já executada | HTTP 409 |
| Write-back não suportado | HTTP 409 |
| Credencial cloud inválida | teste de conexão com `ok=false` |
| Sync com provider indisponível | conexão marcada como `failed` |
| Execução em dry-run | nenhum recurso real alterado |

Nunca teste desligamento real em produção. Use uma conta sandbox, recurso descartável e janela de
mudança aprovada.

## 19. Resetar o ambiente

### Docker, preservando dados

```powershell
docker compose down
docker compose up -d
```

### Docker, removendo todos os dados do Observa

```powershell
docker compose down -v
docker compose up -d --build
```

O segundo comando remove banco, API key, chave de criptografia e conexões. Use somente quando
quiser começar do zero.

### Reseed do demo

```powershell
Invoke-RestMethod "$baseUrl/api/demo/seed" -Method Post -Headers $headers
```

## 20. Checklist final de aceite

- [ ] API pública responde em `/healthz`.
- [ ] API protegida rejeita chamadas sem chave.
- [ ] Mock Demo sincroniza custos, recursos e métricas.
- [ ] Overview apresenta KPIs e gráficos.
- [ ] Products e detalhes carregam corretamente.
- [ ] Ecosystem map permite zoom e navegação.
- [ ] Inventory lista recursos.
- [ ] Governance aplica tags locais e mock.
- [ ] Política recorrente cria ação no horário correto.
- [ ] Data de expiração cria ação.
- [ ] Execução repetida no mesmo minuto não duplica ação.
- [ ] Aprovação em dry-run termina como `simulated`.
- [ ] Rejeição termina como `rejected`.
- [ ] Dashboards, APM, Logs, Traces, Monitors, RUM, GCP e Alerts carregam.
- [ ] CRUD de Connections funciona.
- [ ] Configuração de autenticação persiste sem expor segredos.
- [ ] CLI reproduz inventário, tags, políticas e aprovações.
- [ ] Mobile exibe custos, recursos e aprovações.
- [ ] Testes Python passam.
- [ ] Web passa em typecheck e build.
- [ ] Mobile passa em typecheck.

## 21. Limitações atuais relevantes aos testes

- Write-back de tags e start/stop real estão implementados para AWS EC2.
- GCP e Azure atualmente coletam custos, mas ainda não executam mutações em recursos.
- O app mobile está focado em consulta e aprovação; criação de políticas fica na Web e CLI.
- O scheduler é acionado externamente através de `/api/automation/run-due`.
- Algumas telas profundas usam o dataset demonstrativo enquanto seus conectores específicos não
  estiverem configurados.

## 22. Referência rápida de endpoints

Rotas públicas:

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/` | Informações básicas da aplicação |
| GET | `/healthz` | Liveness probe |
| GET | `/auth/mode` | Modo de autenticação usado pelo login gate |
| GET | `/auth/authorize/{provider}` | Iniciar login OIDC |
| GET | `/auth/callback/{provider}` | Receber callback OIDC |

Rotas protegidas pela API key ou sessão:

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/api/health` | Saúde e contadores |
| POST | `/api/demo/seed` | Recriar dataset demonstrativo |
| GET | `/api/auth/me` | Identidade atual |
| GET | `/api/auth/settings` | Ler configuração de autenticação |
| PUT | `/api/auth/settings` | Salvar configuração de autenticação |
| GET | `/api/connectors` | Catálogo de conectores |
| GET | `/api/connections` | Listar conexões |
| POST | `/api/connections` | Criar conexão |
| PATCH | `/api/connections/{conn_id}` | Editar conexão |
| DELETE | `/api/connections/{conn_id}` | Excluir conexão e dados associados |
| POST | `/api/connections/test` | Testar credencial sem salvar |
| POST | `/api/connections/{conn_id}/sync` | Sincronizar uma conexão |
| GET | `/api/costs/summary` | Resumo de custos |
| GET | `/api/costs/trend` | Série diária de custos |
| GET | `/api/budgets` | Listar budgets |
| POST | `/api/budgets` | Criar budget |
| PATCH | `/api/budgets/{rule_id}` | Editar budget |
| DELETE | `/api/budgets/{rule_id}` | Excluir budget |
| POST | `/api/budgets/evaluate` | Avaliar custo real e projetado |
| POST | `/api/budgets/monitor` | Sincronizar custos e avaliar budgets |
| GET | `/api/budgets/events` | Histórico de eventos de budget |
| GET | `/api/products` | Catálogo de produtos |
| GET | `/api/products/{slug}` | Detalhes do produto |
| GET | `/api/resources` | Inventário de recursos |
| PATCH | `/api/resources/{resource_uid}/tags` | Preview ou aplicação de tags |
| GET | `/api/automation/policies` | Listar políticas |
| POST | `/api/automation/policies` | Criar política |
| PATCH | `/api/automation/policies/{policy_id}` | Editar política |
| DELETE | `/api/automation/policies/{policy_id}` | Excluir política |
| POST | `/api/automation/run-due` | Avaliar políticas vencidas ou no horário |
| GET | `/api/automation/actions` | Listar ações |
| POST | `/api/automation/actions/{action_id}/approve` | Aprovar e executar/simular ação |
| POST | `/api/automation/actions/{action_id}/reject` | Rejeitar ação |
| GET | `/api/observability` | Resumo APM e infraestrutura |
| GET | `/api/metrics/series` | Série de uma métrica |
| GET | `/api/alerts` | Alertas consolidados |
| GET | `/api/ecosystem` | Grafo de dependências |
| GET | `/api/dashboards` | Catálogo de dashboards |
| GET | `/api/dashboards/{dash_id}` | Detalhes do dashboard |
| GET | `/api/monitors` | Monitores |
| GET | `/api/logs` | Logs pesquisáveis |
| GET | `/api/traces` | Traces distribuídos |
| GET | `/api/gcp/monitoring` | Visão de métricas GCP |
| GET | `/api/rum` | Resumo de Real User Monitoring |
| GET | `/api/synthetics` | Testes sintéticos |

O Swagger em `http://localhost:8080/docs` permite executar todas as rotas protegidas após usar o
header `X-Observa-Api-Key` nas requisições.

## 23. Cenários completos das novas features de budget

Esta seção deve ser executada depois do smoke test, com o `mock-demo` sincronizado. Cada cenário
possui um identificador para registrar evidências em uma planilha, issue ou ferramenta de QA.

### 23.1 Preparação comum

```powershell
cd "C:\Users\thiag\Downloads\PROJECTS_TGR_TECHNOLOGY\observa"
$baseUrl = "http://localhost:8080"
$apiKey = (Get-Content .\data\api_key -Raw).Trim()
$headers = @{ "X-Observa-Api-Key" = $apiKey }
Invoke-RestMethod "$baseUrl/api/demo/seed" -Method Post -Headers $headers
$resources = Invoke-RestMethod "$baseUrl/api/resources" -Headers $headers
$hiperlocalResource = $resources | Where-Object product -eq "hiperlocal" | Select-Object -First 1
$hiperlocal = Invoke-RestMethod "$baseUrl/api/products/hiperlocal" -Headers $headers
```

Se estiver usando Docker, preencha `$apiKey` manualmente com a chave exibida nos logs.

Função auxiliar:

```powershell
function New-ObservaBudget {
  param(
    [string]$Name,
    [string]$ScopeType,
    [string]$ScopeValue,
    [double]$Amount,
    [string]$ResponseMode = "notify",
    [string]$Owner = "",
    [int[]]$ResourceIds = @(),
    [int]$WindowDays = 30,
    [double]$Warning = 0.8,
    [double]$Critical = 1.0,
    [bool]$DryRun = $true
  )

  $body = @{
    name = $Name
    scope_type = $ScopeType
    scope_value = $ScopeValue
    amount = $Amount
    currency = "BRL"
    window_days = $WindowDays
    warning_threshold = $Warning
    critical_threshold = $Critical
    response_mode = $ResponseMode
    owner = $(if ($Owner) { $Owner } else { $null })
    resource_ids = $ResourceIds
    dry_run = $DryRun
    enabled = $true
  } | ConvertTo-Json -Depth 6

  Invoke-RestMethod "$baseUrl/api/budgets" `
    -Method Post -Headers $headers -ContentType "application/json" -Body $body
}
```

### 23.2 Matriz resumida

| ID | Cenário | Resultado principal |
|---|---|---|
| BUD-001 | Valores padrão | Janela 30 dias e thresholds 80/100% |
| BUD-002 | Abaixo do limite | Nível `normal`, sem evento |
| BUD-003 | Forecast preventivo | Warning antes do teto |
| BUD-004 | Limite crítico | Evento `critical` |
| BUD-005 | Escopo produto | Custos filtrados por produto |
| BUD-006 | Escopo provider/cloud | Custos filtrados por provider |
| BUD-007 | Escopo conta/projeto | Custos filtrados por account |
| BUD-008 | Escopo recurso | Custos filtrados por resource ID |
| BUD-009 | Monitor completo | Sync antes da avaliação |
| BUD-010 | Falha parcial de sync | Outras conexões continuam |
| BUD-011 | Resposta notify | Alerta sem ação |
| BUD-012 | Resposta approval | Ação preventiva pendente |
| BUD-013 | Resposta ignore | Evento ignorado sem alerta/ação |
| BUD-014 | Owner obrigatório | Criação rejeitada sem owner |
| BUD-015 | Recurso não mapeado | Evento `needs_mapping` |
| BUD-016 | Aprovação dry-run | Ação termina `simulated` |
| BUD-017 | Rejeição | Ação termina `rejected` |
| BUD-018 | Deduplicação diária | Sem evento duplicado |
| BUD-019 | Warning evolui para critical | Novo evento, mesma ação pendente |
| BUD-020 | Regra desabilitada | Regra não avaliada |
| BUD-021 | Atualização e exclusão | CRUD persistente |
| BUD-022 | Janela customizada | Forecast muda conforme dias |
| BUD-023 | Interface web | Criação, monitoramento e histórico |
| BUD-024 | CLI | Mesmas operações da API |
| BUD-025 | Mobile | Aprovação e rejeição remotas |
| BUD-026 | Alertas | Budget aparece na central |
| BUD-027 | Auditoria | Regra, evento e decisão registrados |
| BUD-028 | Segurança | API key, validações e dry-run |
| BUD-029 | Scheduler | Monitoramento recorrente |
| BUD-030 | AWS real controlada | Stop somente após aprovação |
| BUD-031 | GCP/Azure | Detecta custo e sinaliza falta de adapter |

### BUD-001 — Validar valores padrão

```powershell
$rule = New-ObservaBudget -Name "Defaults" -ScopeType product `
  -ScopeValue hiperlocal -Amount 999999
$rule | ConvertTo-Json -Depth 5
```

Esperado:

- `window_days=30`.
- `warning_threshold=0.8`.
- `critical_threshold=1.0`.
- `currency=BRL`.
- `dry_run=true`.
- `enabled=true`.

### BUD-002 — Custo abaixo do limite

```powershell
$rule = New-ObservaBudget -Name "Normal" -ScopeType product `
  -ScopeValue hiperlocal -Amount 999999
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$result.rules | Where-Object rule_id -eq $rule.id
```

Esperado: nível `normal`, `usage_pct` menor que `0.8` e nenhum evento novo para a regra.

### BUD-003 — Forecast aciona proteção preventiva

Use o custo atual para posicionar o consumo em aproximadamente 90%:

```powershell
$amount = $hiperlocal.total_brl / 0.9
$rule = New-ObservaBudget -Name "Forecast preventivo" -ScopeType product `
  -ScopeValue hiperlocal -Amount $amount -ResponseMode approval `
  -Owner "squad-hiperlocal" -ResourceIds @($hiperlocalResource.uid)
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-21"}'
$event = $result.created | Where-Object rule_id -eq $rule.id
$event
```

Esperado:

- Nível `warning`.
- Status `pending_approval`.
- Uma ação `stop` criada antes de 100%.
- `projected_cost` considerado junto com `actual_cost`.

### BUD-004 — Ultrapassar limite crítico

```powershell
$rule = New-ObservaBudget -Name "Critical" -ScopeType product `
  -ScopeValue hiperlocal -Amount 1
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-22"}'
$result.created | Where-Object rule_id -eq $rule.id
```

Esperado: nível `critical`, `usage_pct >= 1` e alerta de severidade alta.

### BUD-005 — Budget por produto

```powershell
$rule = New-ObservaBudget -Name "Produto hiperlocal" -ScopeType product `
  -ScopeValue hiperlocal -Amount 5000
Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
```

Compare `actual_cost` com `total_brl` retornado por `/api/products/hiperlocal`. Pequenas diferenças
só são aceitáveis se as janelas consultadas forem diferentes.

### BUD-006 — Budget por cloud/provider

```powershell
$summary = Invoke-RestMethod "$baseUrl/api/costs/summary?days=30" -Headers $headers
$rule = New-ObservaBudget -Name "Cloud GCP" -ScopeType provider `
  -ScopeValue gcp -Amount ($summary.by_provider.gcp / 0.9)
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$result.rules | Where-Object rule_id -eq $rule.id
```

Esperado: custo calculado apenas para registros cujo provider é `gcp`.

### BUD-007 — Budget por conta ou projeto cloud

No demo, `account=demo-org`:

```powershell
$rule = New-ObservaBudget -Name "Conta demo" -ScopeType account `
  -ScopeValue demo-org -Amount 100
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$result.rules | Where-Object rule_id -eq $rule.id
```

Repita com `scope_type=project`. Ambos usam o campo normalizado `account` nos custos. Em GCP real,
use o project ID exportado no billing; em Azure, use a subscription normalizada pelo conector.

### BUD-008 — Budget por recurso

O conector precisa produzir `cost_records.resource_id`. Crie a regra usando o identificador cloud,
não apenas o UID interno:

```powershell
$resource = $resources | Select-Object -First 1
$rule = New-ObservaBudget -Name "Recurso individual" -ScopeType resource `
  -ScopeValue $resource.id -Amount 100
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$result.rules | Where-Object rule_id -eq $rule.id
```

Esperado no demo atual: custo zero quando não existe alocação de billing por recurso. Isso deve ser
tratado como lacuna de dados, não como prova de custo zero. Em um conector real com resource IDs,
compare o valor com o relatório nativo da cloud.

### BUD-009 — Monitor sincroniza antes de avaliar

```powershell
$result = Invoke-RestMethod "$baseUrl/api/budgets/monitor" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$result.synced
$result.failed
$result.evaluation
```

Esperado:

- `synced` contém conexões habilitadas com capacidade `cost`.
- A avaliação ocorre depois das sincronizações.
- O resultado inclui regras e eventos novos.

### BUD-010 — Falha parcial de sincronização

1. Crie uma conexão real com credencial propositalmente inválida em ambiente de teste.
2. Mantenha o Mock Demo habilitado.
3. Execute `/api/budgets/monitor`.

Esperado:

- A conexão inválida aparece em `failed`.
- O Mock Demo aparece em `synced`.
- A avaliação ainda é executada com os dados disponíveis.
- O monitor não encerra todo o ciclo por falha de um único provider.

### BUD-011 — Modo notify

```powershell
$rule = New-ObservaBudget -Name "Somente notificar" -ScopeType product `
  -ScopeValue hiperlocal -Amount 1 -ResponseMode notify
Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-23"}'
```

Esperado: evento `notified`, alerta criado e nenhuma action ID.

### BUD-012 — Modo approval

```powershell
$rule = New-ObservaBudget -Name "Aprovação preventiva" -ScopeType product `
  -ScopeValue hiperlocal -Amount 1 -ResponseMode approval `
  -Owner "squad-hiperlocal" -ResourceIds @($hiperlocalResource.uid)
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-24"}'
$event = $result.created | Where-Object rule_id -eq $rule.id
```

Esperado: evento `pending_approval` e action ID visível em Governance, CLI e mobile.

### BUD-013 — Modo ignore

```powershell
$rule = New-ObservaBudget -Name "Exceção aprovada" -ScopeType provider `
  -ScopeValue gcp -Amount 1 -ResponseMode ignore
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-25"}'
$event = $result.created | Where-Object rule_id -eq $rule.id
```

Esperado: status `ignored`, sem action IDs e sem alerta novo, mas com evento histórico.

### BUD-014 — Owner obrigatório para aprovação

```powershell
try {
  New-ObservaBudget -Name "Sem owner" -ScopeType product `
    -ScopeValue hiperlocal -Amount 100 -ResponseMode approval
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

Esperado: HTTP `400` com mensagem informando que `owner` é obrigatório.

### BUD-015 — Custo sem recursos mapeados

O demo possui custo Datadog, mas não inventário Datadog elegível para stop:

```powershell
$rule = New-ObservaBudget -Name "Datadog sem mapping" -ScopeType provider `
  -ScopeValue datadog -Amount 1 -ResponseMode approval -Owner "finops"
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-26"}'
$result.created | Where-Object rule_id -eq $rule.id
```

Esperado: status `needs_mapping`, sem desligamento e alerta indicando necessidade de mapear recursos.

### BUD-016 — Aprovar em dry-run

```powershell
$rule = New-ObservaBudget -Name "Aprovação dry-run" -ScopeType product `
  -ScopeValue hiperlocal -Amount 1 -ResponseMode approval `
  -Owner "squad-hiperlocal" -ResourceIds @($hiperlocalResource.uid)
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-28"}'
$event = $result.created | Where-Object rule_id -eq $rule.id
$actionId = $event.action_ids[0]
$approved = Invoke-RestMethod "$baseUrl/api/automation/actions/$actionId/approve" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
$approved
```

Esperado: status `simulated`; o status real do recurso não deve mudar.

### BUD-017 — Rejeitar desligamento

```powershell
$rule = New-ObservaBudget -Name "Rejeição justificada" -ScopeType product `
  -ScopeValue hiperlocal -Amount 1 -ResponseMode approval `
  -Owner "squad-hiperlocal" -ResourceIds @($hiperlocalResource.uid)
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" `
  -Body '{"at":"2026-09-29"}'
$event = $result.created | Where-Object rule_id -eq $rule.id
$actionId = $event.action_ids[0]
$rejectBody = @{ reason = "Campanha ativa; exceção aprovada pelo owner" } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/automation/actions/$actionId/reject" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $rejectBody
```

Esperado: status `rejected`, justificativa persistida e nenhuma ação no provider.

### BUD-018 — Deduplicação no mesmo dia

```powershell
$body = '{"at":"2026-09-27"}'
$first = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $body
$second = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

Esperado: a segunda execução retorna a regra como `deduplicated=true` e não cria outro evento para
a mesma combinação de regra, data e nível.

### BUD-019 — Evolução warning para critical

1. Crie uma regra cujo consumo fique entre warning e critical.
2. Avalie usando uma data fixa.
3. Reduza `amount` com `PATCH /api/budgets/{rule_id}`.
4. Avalie novamente na mesma data.

```powershell
$patch = @{ amount = 1 } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/budgets/$($rule.id)" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $patch
```

Esperado:

- Um evento warning e outro critical, pois os níveis são diferentes.
- A ação pendente existente é reutilizada.
- Não há spam de aprovações para o mesmo recurso.

### BUD-020 — Regra desabilitada

```powershell
$patch = @{ enabled = $false } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/budgets/$($rule.id)" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $patch
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
```

Esperado: o ID da regra desabilitada não aparece em `result.rules`.

### BUD-021 — Atualizar e excluir

```powershell
$patch = @{ amount = 7000; owner = "novo-owner" } | ConvertTo-Json
$updated = Invoke-RestMethod "$baseUrl/api/budgets/$($rule.id)" `
  -Method Patch -Headers $headers -ContentType "application/json" -Body $patch
Invoke-RestMethod "$baseUrl/api/budgets/$($rule.id)" `
  -Method Delete -Headers $headers
```

Esperado: valores atualizados persistem; após DELETE, a regra não aparece em `GET /api/budgets`.

### BUD-022 — Janela de 7 dias versus 30 dias

Crie duas regras idênticas, alterando apenas `window_days`:

```powershell
$seven = New-ObservaBudget -Name "Janela 7d" -ScopeType product `
  -ScopeValue hiperlocal -Amount 5000 -WindowDays 7
$thirty = New-ObservaBudget -Name "Janela 30d" -ScopeType product `
  -ScopeValue hiperlocal -Amount 5000 -WindowDays 30
$result = Invoke-RestMethod "$baseUrl/api/budgets/evaluate" `
  -Method Post -Headers $headers -ContentType "application/json" -Body "{}"
```

Esperado: `actual_cost`, `observed_days` e forecast refletem suas respectivas janelas.

### BUD-023 — Interface web

1. Abra `/budgets`.
2. Crie regras para produto, projeto, recurso e provider.
3. Confira validação de owner para aprovação.
4. Clique em **Sincronizar e avaliar**.
5. Confira custo real, projetado, percentual, nível e status.
6. Abra `/alerts` e confirme alertas de budget.
7. Abra `/governance` e confirme aprovações pendentes.
8. Exclua uma regra e confirme remoção da lista.

### BUD-024 — CLI

```powershell
observa budgets create "CLI provider" --scope provider --value gcp `
  --amount 5000 --warning 80 --critical 100 --response notify
observa budgets list
observa budgets monitor
observa budgets events
observa --json budgets events
```

Para aprovação:

```powershell
observa budgets create "CLI approval" --scope product --value hiperlocal `
  --amount 100 --response approval --owner squad-hiperlocal `
  --resource $($hiperlocalResource.uid)
observa budgets monitor
observa actions list --status pending_approval
```

### BUD-025 — Aplicativo mobile

1. Gere uma ação de budget pendente.
2. Abra o app e atualize com pull-to-refresh.
3. Confira aumento do contador de alertas.
4. Confira a ação com motivo iniciado por `Budget`.
5. Aprove uma ação dry-run e confirme que ela desaparece dos pendentes.
6. Gere outra ação e rejeite com o app.
7. Confirme os estados na API.

### BUD-026 — Central de alertas

```powershell
$alerts = Invoke-RestMethod "$baseUrl/api/alerts" -Headers $headers
$alerts | Where-Object category -eq "budget"
```

Esperado:

- Warning usa severidade `medium`.
- Critical usa severidade `high`.
- Approval pendente usa status `pending`.
- Modo ignore não cria alerta.

### BUD-027 — Auditoria no banco

```powershell
@'
import json
import sqlite3

conn = sqlite3.connect("data/observa.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT * FROM audit_events WHERE event_type LIKE 'budget.%' ORDER BY id DESC LIMIT 20"
).fetchall()
for row in rows:
    print(row["created_at"], row["event_type"], row["subject"], json.loads(row["payload_json"]))
'@ | python -
```

Esperado: eventos para criação/alteração de regras e criação de budget events.

### BUD-028 — Segurança e validações

Valide individualmente:

- Requisição sem API key retorna 401.
- `amount <= 0` retorna 422 ou 400.
- `window_days=0` retorna 422.
- `warning_threshold > critical_threshold` retorna 400.
- `scope_type` desconhecido retorna 400.
- `response_mode` desconhecido retorna 400.
- Approval sem owner retorna 400.
- Regra nova permanece em dry-run por padrão.
- Resource UID inexistente não executa ação.

### BUD-029 — Scheduler recorrente

Configure o scheduler para chamar `/api/budgets/monitor`, não apenas `/api/budgets/evaluate`:

```cron
*/5 * * * * curl -sS -X POST http://observa-api:8080/api/budgets/monitor \
  -H "X-Observa-Api-Key: SUA_CHAVE" -H "Content-Type: application/json" -d '{}'
```

Teste por pelo menos três ciclos:

1. Primeiro ciclo sincroniza e cria evento.
2. Segundo ciclo deduplica.
3. Após alterar o custo/threshold, o terceiro ciclo cria o novo nível quando aplicável.

Registre duração, quantidade de conexões sincronizadas e falhas parciais.

### BUD-030 — AWS EC2 real em conta sandbox

Pré-condições:

- Instância descartável.
- Janela de mudança autorizada.
- Backup ou recriação conhecida.
- Credencial limitada ao ARN da instância.

Fluxo:

1. Crie conexão AWS e sincronize.
2. Confirme EC2 no Inventory.
3. Crie budget approval com UID da instância.
4. Mantenha `dry_run=true` e aprove a primeira ação.
5. Confirme status `simulated` e instância ainda ligada.
6. Somente após validação, crie outra regra via CLI com `--apply`.
7. Gere e aprove a ação.
8. Confirme no console AWS que a instância parou.
9. Confirme status `executed` e auditoria.

Nunca faça esse cenário diretamente em produção.

### BUD-031 — GCP e Azure sem adapter de desligamento

1. Configure GCP Billing ou Azure Cost Management.
2. Sincronize custos.
3. Crie budget por project/account/provider.
4. Avalie e confirme custo/forecast.
5. Use response `approval` sem resource IDs mapeados.

Esperado: detecção e alerta funcionam; evento fica `needs_mapping` ou a ação falha de forma segura
se o conector não suporta power action. O Observa não deve desconectar billing automaticamente.

### 23.3 Evidências recomendadas

Para cada ID, salve:

- Data e hora.
- Ambiente e commit testado.
- Payload enviado.
- Resposta HTTP.
- Screenshot da Web ou mobile quando aplicável.
- Estado anterior e posterior do recurso.
- Registro em `budget_events`, `action_runs`, `alerts` e `audit_events`.
- Resultado `Pass`, `Fail` ou `Blocked` com justificativa.

### 23.4 Limpeza dos cenários

Liste e remova apenas as regras criadas para testes:

```powershell
$rules = Invoke-RestMethod "$baseUrl/api/budgets" -Headers $headers
$rules | Select-Object id,name,scope_type,scope_value

# Exemplo individual:
Invoke-RestMethod "$baseUrl/api/budgets/ID_DA_REGRA" `
  -Method Delete -Headers $headers
```

Os eventos e a auditoria devem ser preservados como evidência. Para apagar todo o ambiente local,
use o procedimento de reset completo da seção 19.

## 24. Companies, tenancies, privacidade e remediação

### 24.1 Preparação

```powershell
$baseUrl = "http://localhost:8080"
$apiKey = Get-Content .\data\api_key -Raw
$admin = @{ "X-Observa-Api-Key" = $apiKey.Trim() }

$company = Invoke-RestMethod "$baseUrl/api/companies" -Method Post -Headers $admin `
  -ContentType "application/json" -Body '{"name":"Empresa QA","slug":"empresa-qa"}'
$prod = Invoke-RestMethod "$baseUrl/api/tenancies" -Method Post -Headers $admin `
  -ContentType "application/json" `
  -Body (@{ company_id=$company.id; name="Produção"; slug="producao" } | ConvertTo-Json)
$sandbox = Invoke-RestMethod "$baseUrl/api/tenancies" -Method Post -Headers $admin `
  -ContentType "application/json" `
  -Body (@{ company_id=$company.id; name="Sandbox"; slug="sandbox" } | ConvertTo-Json)
$prodHeaders = $admin + @{
  "X-Observa-Company-ID" = $company.id
  "X-Observa-Tenancy-ID" = $prod.id
}
$sandboxHeaders = $admin + @{
  "X-Observa-Company-ID" = $company.id
  "X-Observa-Tenancy-ID" = $sandbox.id
}
```

### MT-001 — Company com múltiplas tenancies

```powershell
Invoke-RestMethod "$baseUrl/api/companies" -Headers $admin
Invoke-RestMethod "$baseUrl/api/tenancies?company_id=$($company.id)" -Headers $admin
```

Esperado: a company aparece uma vez e contém as tenancies Produção e Sandbox com IDs diferentes.

### MT-002 — Isolamento de conexões

```powershell
Invoke-RestMethod "$baseUrl/api/connections" -Method Post -Headers $prodHeaders `
  -ContentType "application/json" `
  -Body '{"name":"Mock Prod","connector_id":"mock-demo","config":{"days":7}}'
$prodConnections = Invoke-RestMethod "$baseUrl/api/connections" -Headers $prodHeaders
$sandboxConnections = Invoke-RestMethod "$baseUrl/api/connections" -Headers $sandboxHeaders
```

Esperado: `Mock Prod` existe somente em `$prodConnections`; Sandbox permanece vazia.

### MT-003 — Isolamento de custos, recursos e budgets

Sincronize a conexão na Produção e consulte os mesmos endpoints nas duas tenancies:

```powershell
$connectionId = $prodConnections[0].id
Invoke-RestMethod "$baseUrl/api/connections/$connectionId/sync" -Method Post -Headers $prodHeaders
Invoke-RestMethod "$baseUrl/api/costs/summary" -Headers $prodHeaders
Invoke-RestMethod "$baseUrl/api/costs/summary" -Headers $sandboxHeaders
Invoke-RestMethod "$baseUrl/api/resources" -Headers $sandboxHeaders
Invoke-RestMethod "$baseUrl/api/budgets" -Headers $sandboxHeaders
```

Esperado: dados sincronizados somente em Produção; nenhuma linha vaza para Sandbox.

### MT-004 — Company e tenancy incompatíveis

Envie o ID da tenancy com o ID de outra company.

Esperado: HTTP `409` e nenhum dado no corpo da resposta.

### MT-005 — Tenancy inexistente

```powershell
$invalid = $admin + @{ "X-Observa-Tenancy-ID" = "tnt_inexistente" }
try { Invoke-RestMethod "$baseUrl/api/resources" -Headers $invalid } catch { $_.Exception.Response.StatusCode.value__ }
```

Esperado: HTTP `404` sem fallback silencioso para a tenancy padrão.

### MT-006 — OIDC sem membership não descobre company

1. Autentique um usuário OIDC ainda não cadastrado.
2. Execute `GET /api/companies` com o token de sessão.
3. Tente acessar a tenancy informando os headers manualmente.

Esperado: a company não aparece na listagem e o acesso direto retorna HTTP `403`.

### MT-007 — Membership explícita

Com a chave de plataforma ou um owner, autorize o `subject` exibido por `/api/auth/me`:

```powershell
$body = @{
  subject = "google:SUBJECT_IMUTAVEL"
  email = "owner@empresa.example"
  role = "owner"
} | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/companies/$($company.id)/members" `
  -Method Put -Headers $admin -ContentType "application/json" -Body $body
```

Esperado: após novo acesso, o usuário lista apenas companies autorizadas e acessa suas tenancies.

### MT-008 — Viewer é somente leitura

Cadastre outro subject com role `viewer`. Com o token desse usuário:

- `GET /api/costs/summary` deve retornar `200`.
- `POST /api/connections` deve retornar `403`.
- `POST /api/budgets/evaluate` deve retornar `403`.
- `POST /api/remediations/{id}/approve` deve retornar `403`.

### MT-009 — Operator não aprova remediação

O role `operator` pode ingerir logs e executar análise, mas a aprovação/rejeição de uma correção
deve retornar HTTP `403`. Repita como `owner` ou `admin` e confirme HTTP `200`.

### MT-010 — Seletor Web

1. Abra **Platform → Organizations**.
2. Crie uma company e duas tenancies.
3. Use o seletor lateral para alternar entre elas.
4. Crie uma conexão somente em uma tenancy.

Esperado: cada tela recarrega no contexto selecionado e a conexão não aparece na outra tenancy.

### MT-011 — CLI com contexto

```powershell
$env:OBSERVA_URL = $baseUrl
$env:OBSERVA_API_KEY = $apiKey.Trim()
observa companies list
observa tenancies list --company $company.id
observa --company-id $company.id --tenancy-id $prod.id resources
```

Esperado: os comandos de dados usam exclusivamente a tenancy informada.

### MT-012 — Mobile com contexto

1. Informe API URL, API key, Company ID e Tenancy ID na tela de conexão.
2. Confira o contexto no topo do app.
3. Valide custos, aprovações e remediações sugeridas.

Esperado: o app envia os dois headers em toda requisição e não mistura ambientes.

### REM-001 — Ingestão privada de logs

```powershell
$logs = @{
  connection_id = "qa-agent"
  logs = @(
    @{ ts="2026-09-23T10:00:00Z"; severity="ERROR"; source="app"; product="observa"; service="api"; message="upstream timeout calling billing" },
    @{ ts="2026-09-23T10:01:00Z"; severity="ERROR"; source="app"; product="observa"; service="api"; message="upstream timeout calling billing" }
  )
} | ConvertTo-Json -Depth 5
Invoke-RestMethod "$baseUrl/api/logs/ingest" -Method Post -Headers $prodHeaders `
  -ContentType "application/json" -Body $logs
```

Esperado: duas linhas em Produção e zero linhas em Sandbox.

### REM-002 — Análise local e sugestão

```powershell
$analysis = Invoke-RestMethod "$baseUrl/api/remediations/analyze" -Method Post `
  -Headers $prodHeaders -ContentType "application/json" -Body '{"dry_run":true}'
$proposal = $analysis.proposals | Where-Object title -Like '*observa/api*' | Select-Object -First 1
$proposal
```

Esperado: status `suggested`, diagnóstico e recomendação, sem credenciais ou logs brutos no payload.

### REM-003 — Aprovação dry-run

```powershell
Invoke-RestMethod "$baseUrl/api/remediations/$($proposal.id)/approve" `
  -Method Post -Headers $prodHeaders -ContentType "application/json" -Body '{}'
```

Esperado: status `simulated`; nenhum webhook, pipeline ou aplicação é alterado.

### REM-004 — Rejeição e aprendizado

Rejeite uma nova proposta e envie feedback `false_positive`. Execute a análise novamente.

Esperado: o mesmo fingerprint deixa de ser sugerido naquela tenancy, mas continua independente nas
outras tenancies.

### REM-005 — Correção real aprovada

1. Configure uma conexão `onprem-custom` com `remediation_url` em ambiente sandbox.
2. Analise com `dry_run=false` e `executor_connection_id` dessa conexão.
3. Confirme que nada acontece antes da aprovação.
4. Aprove como owner/admin.

Esperado: o endpoint privado recebe somente ID, título, diagnóstico, recomendação e ação estruturada;
não recebe log bruto, token ou secrets. O resultado fica `applied` ou `failed` e gera auditoria.

### SEC-001 — Busca por segredos e dados de cliente no repositório

```powershell
git grep -n -I -E "(BEGIN PRIVATE KEY|client_secret.{0,10}=|api[_-]?key.{0,10}=|bearer [A-Za-z0-9_-]{20,})"
git status --short
```

Esperado: nenhum segredo real, banco `.db`, diretório `data/`, `.env` ou credencial versionada.

### SEC-002 — Tentativa de enumeração

Com token sem membership, tente IDs válidos e inválidos em `/api/context`, `/api/resources`,
`/api/logs`, `/api/remediations` e `/api/connections`.

Esperado: `403` para company não autorizada, `404` para tenancy inexistente e nenhum metadado do
cliente na resposta.

## 25. Mapa Vivo e assistente contextual

Arquitetura, contrato da API, controles de privacidade e troubleshooting detalhados estão em
`docs/MAPA_VIVO.md`.

### MAP-001 — Carregamento da topologia

1. Acesse `http://localhost:3000/maps`.
2. Selecione o produto `hiperlocal`.
3. Confira os contadores de componentes, conexões e integrações externas.
4. Use zoom, redução e ajuste automático do mapa.

Esperado: nós e conexões retornados pela API aparecem no canvas sem sobreposição crítica, com
legenda por tipo e painel do primeiro componente selecionado.

### MAP-002 — Inspeção de componente

1. Selecione um nó do mapa.
2. Confira produto, camada, entradas, saídas, tipo e identificador.
3. Clique em uma dependência direta no painel lateral.

Esperado: o nó relacionado passa a ser selecionado, suas conexões ficam destacadas e o painel é
atualizado sem nova requisição ou mistura de tenancy.

### MAP-003 — Troca de produto

1. Troque `hiperlocal` por `platform` no seletor.
2. Aguarde a sincronização.
3. Repita a inspeção de nós.

Esperado: o mapa anterior desaparece durante o carregamento e somente a topologia de `platform`
fica visível após a resposta.

### MAP-004 — Pergunte ao Observa

1. Clique em **Pergunte ao Observa**.
2. Confira o produto e componente exibidos em **Contexto atual**.
3. Escolha uma pergunta sugerida ou escreva uma pergunta.
4. Pressione `Esc` para fechar o assistente.

Esperado: a resposta informa entradas e saídas usando apenas a topologia local, declara que nenhum
dado foi enviado para IA externa e que nenhuma alteração foi executada.

### MAP-005 — Responsividade e teclado

1. Teste a tela em larguras de `1440px`, `1024px`, `768px` e `390px`.
2. Navegue por seletor, controles, dependências e assistente usando `Tab` e `Shift+Tab`.
3. Verifique foco visível e legibilidade dos textos.

Esperado: o inspetor passa para baixo do canvas em telas menores, o botão do assistente permanece
acessível e nenhum controle essencial fica cortado.

### AUTH-001 — Chave local expirada ou inválida

1. Salve uma API key inválida no navegador e recarregue `/maps`.
2. Confira que a interface protegida não permanece visível.
3. Informe a chave atual em `data/api_key` e desbloqueie.

Esperado: a credencial inválida é removida, o formulário de acesso reaparece e a aplicação só é
liberada após `/api/health` validar a nova chave.

### MAP-006 — Integridade do contrato da topologia

```powershell
$apiKey = (Get-Content .\data\api_key -Raw).Trim()
$headers = @{ "X-Observa-Api-Key" = $apiKey }
$ecosystem = Invoke-RestMethod `
  "http://localhost:8080/api/ecosystem?product=hiperlocal" `
  -Headers $headers

$nodeIds = @($ecosystem.nodes | ForEach-Object { $_.id })
$duplicateIds = @($nodeIds | Group-Object | Where-Object Count -gt 1)
$invalidEdges = @($ecosystem.edges | Where-Object {
  $_.source -notin $nodeIds -or $_.target -notin $nodeIds
})

$duplicateIds.Count
$invalidEdges.Count
```

Esperado: os dois contadores retornam `0`; nenhum nó possui ID duplicado e nenhuma aresta aponta
para componente inexistente.

### MAP-007 — Assistente não chama serviços externos

1. Abra as ferramentas de desenvolvimento do navegador na aba **Network**.
2. Limpe as requisições registradas.
3. Abra **Pergunte ao Observa** e envie uma pergunta.
4. Filtre por `fetch` e `xhr`.

Esperado: nenhuma chamada adicional para domínio externo ou endpoint de IA é criada; a resposta é
calculada no navegador a partir do payload já carregado.

### MAP-008 — Isolamento de company e tenancy

1. Crie duas companies, cada uma com pelo menos uma tenancy.
2. Troque o contexto ativo no seletor lateral.
3. Em **Network**, abra a requisição de `/api/ecosystem`.
4. Confira `X-Observa-Company-ID` e `X-Observa-Tenancy-ID`.
5. Repita o teste com um usuário sem membership na company selecionada.

Esperado: os headers correspondem ao contexto ativo; o backend rejeita contexto não autorizado e
nunca retorna nomes, IDs ou relações pertencentes a outra organização.

Observação: enquanto `/api/ecosystem` usar `demo_platform.py`, este cenário valida autenticação e
propagação de contexto. A validação completa do filtro persistido deve ser obrigatória quando a
topologia real dos conectores substituir o provedor demonstrativo.

### MAP-009 — Modo somente leitura

1. Selecione diferentes nós e dependências.
2. Use zoom, ajuste automático e movimentação do canvas.
3. Faça perguntas no assistente.
4. Consulte auditoria, propostas de remediação e recursos do provider.

Esperado: nenhuma tag, regra, recurso, proposal ou configuração é criada ou alterada. O mapa e o
assistente local operam somente em leitura.

### MAP-010 — Falha controlada da API

1. Com a página aberta, pare temporariamente a API.
2. Troque o produto selecionado.
3. Observe a mensagem de erro.
4. Reinicie a API e selecione novamente o produto.

Esperado: a topologia anterior não é misturada com a nova seleção, a interface exibe erro sem
mostrar dados de outro contexto e volta a carregar após a recuperação da API.
