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
