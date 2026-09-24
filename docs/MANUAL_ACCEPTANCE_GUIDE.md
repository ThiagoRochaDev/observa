# Guia completo de uso e homologação manual do Observa

Este documento é o roteiro principal para usar e testar o Observa depois de uma
alteração ou antes de uma demonstração. Ele cobre todas as telas web, fluxos de
governança, CLI, mobile, API, MCP, conectores, isolamento multiempresa e controles
operacionais.

Use somente dados de demonstração ou contas de homologação. Nunca grave tokens,
credenciais, nomes de clientes, logs reais ou identificadores de cloud em prints,
vídeos, issues ou relatórios públicos.

## 1. Preparação do ambiente

### 1.1 Subir API e web

Com Docker:

```powershell
docker compose up -d --build
docker compose ps
```

Ou use os processos locais já configurados:

```powershell
curl.exe http://127.0.0.1:8080/healthz
curl.exe http://127.0.0.1:8080/readyz
```

Resultado esperado:

- Web disponível em `http://localhost:3000`.
- `/healthz` retorna `status=ok`.
- `/readyz` retorna `status=ready`, `control=ok` e `tenant=ok`.

### 1.2 Obter a chave local sem colocá-la em logs

Docker:

```powershell
$env:OBSERVA_API_KEY = (docker compose exec -T api cat /data/api_key).Trim()
```

Execução local:

```powershell
$env:OBSERVA_API_KEY = (Get-Content data/api_key -Raw).Trim()
```

Não execute `Write-Host $env:OBSERVA_API_KEY`, não coloque a chave em URL e não a
inclua em screenshots. Na web, informe-a somente na tela local protegida.

### 1.3 Confirmar o contexto de demonstração

Na barra superior, selecione:

- Company: `TGR Technology`.
- Tenancy: `Default`.

O cabeçalho deve mostrar que o contexto está isolado. Todos os dados vistos a
seguir pertencem somente à tenancy selecionada.

### 1.4 Rodar a validação automatizada inicial

```powershell
python -m pytest apps/api/tests packages/connectors/tests -q
cd apps/web
npm run lint
npm run typecheck
npm run build
cd ../mobile
npm run typecheck
```

Resultado esperado: todos os testes e builds terminam sem erro. Avisos de lint ou
depreciação devem ser registrados, mas não confundidos com falhas.

## 2. Login local e shell global

### OBS-WEB-001 — Chave inválida

1. Abra `http://localhost:3000` em janela anônima.
2. Informe um valor propositalmente inválido.
3. Clique em **Acessar plataforma**.

Resultado esperado: acesso negado, nenhuma tela protegida é exibida e nenhum dado
da API aparece no navegador.

### OBS-WEB-002 — Chave válida

1. Informe a chave obtida em `1.2`.
2. Clique em **Acessar plataforma**.

Resultado esperado: a Visão geral é carregada; a chave não aparece na URL, no
header visual ou nas respostas exibidas.

### OBS-WEB-003 — Busca global de serviços

1. Clique no campo **Qual serviço você deseja acessar?**.
2. Digite `conexões`, `logs`, `budgets`, `mapa` e `companies`, um termo por vez.
3. Use as setas e `Enter` para abrir uma sugestão.
4. Repita usando clique.

Resultado esperado: as sugestões mostram a tela e sua descrição; `Enter` e clique
navegam para a mesma rota; a busca substitui a necessidade de localizar a opção
manualmente no menu lateral.

### OBS-WEB-004 — Troca de company e tenancy

1. Abra o seletor de contexto no header.
2. Escolha outra tenancy de homologação, se existir.
3. Observe Overview, Inventory e Connections.
4. Volte para `TGR Technology / Default`.

Resultado esperado: cada troca recarrega dados somente do novo contexto. Uma
tenancy vazia não pode mostrar conexões, recursos ou custos da tenancy anterior.

## 3. Visão geral — `/`

### OBS-WEB-010 — KPIs FinOps

1. Abra **Visão geral**.
2. Confira `Total 30d`, `Produtos`, `Providers` e `Alertas abertos`.
3. Clique em **ver alertas**.

Resultado esperado: os valores são numéricos, coerentes com o dataset demo, e o
link abre `/alerts`.

### OBS-WEB-011 — Gráficos e agrupamentos

1. Volte para a Visão geral.
2. Confira **Tendência diária**, **Por provider**, **Por produto** e **Por squad**.
3. Compare o total dos agrupamentos com o custo consolidado.

Resultado esperado: gráficos carregam sem erro, legendas são legíveis e produtos
sem mapeamento não são atribuídos silenciosamente a outro owner.

## 4. Produtos — `/products` e `/products/{slug}`

### OBS-WEB-020 — Catálogo de produtos

1. Abra **Produtos**.
2. Verifique nome, squad, custo, serviços e recursos.
3. Escolha um produto com custo e abra seu nome.

Resultado esperado: a listagem é ordenada e o clique abre o detalhe correto.

### OBS-WEB-021 — Detalhe do produto

1. Confira os KPIs e gráficos do produto.
2. Compare custo, recursos e serviços com a linha da listagem anterior.
3. Abra referências relacionadas, quando disponíveis.

Resultado esperado: o slug da URL representa o produto selecionado e nenhum dado
de outro produto é agregado sem identificação.

## 5. Mapa Vivo — `/maps`

### OBS-WEB-030 — Topologia

1. Abra **Mapa do ecossistema**.
2. Selecione um produto.
3. Use zoom, pan e controles de enquadramento.
4. Clique em um serviço e depois em um recurso conectado.

Resultado esperado: nós e arestas permanecem legíveis; o item selecionado abre o
inspetor; dependências upstream/downstream são destacadas sem alterar dados.

### OBS-WEB-031 — Pergunte ao Observa

1. Com um nó selecionado, abra **Pergunte ao Observa**.
2. Faça uma pergunta sobre custo, dependências ou risco daquele componente.
3. Troque o componente e repita.

Resultado esperado: a resposta usa o produto e componente atuais como contexto.
Na configuração local, a análise não envia topologia para IA externa e não executa
ações de infraestrutura.

### OBS-WEB-032 — Isolamento do mapa

1. Troque para uma tenancy vazia.
2. Abra novamente o mapa.

Resultado esperado: a topologia anterior não permanece em cache como se
pertencesse à nova tenancy.

## 6. Inventário — `/inventory`

### OBS-WEB-040 — Listagem e filtros

1. Abra **Inventário**.
2. Filtre por provider, tipo, região, status e produto, conforme disponível.
3. Procure recursos sem produto ou owner.

Resultado esperado: filtros reduzem a tabela corretamente e o total acompanha o
resultado visível.

### OBS-WEB-041 — Tags e labels

1. Escolha um recurso sem mapeamento.
2. Abra a ação de tags pela tela de Governança ou pelo fluxo disponível.
3. Adicione `product=homologacao` e `owner=finops-test` em dry-run.
4. Confirme a prévia e depois aplique somente no catálogo local.
5. Se o conector suportar write-back e a conta for de homologação, repita com
   escrita no provider.

Resultado esperado: dry-run não altera o recurso; aplicação local atualiza o
catálogo; write-back só ocorre quando explicitamente solicitado e permitido.

## 7. Budgets — `/budgets`

### OBS-WEB-050 — Budget somente notificação

1. Crie um budget `Teste notify`.
2. Selecione escopo `product`, informe um produto demo e valor baixo.
3. Use janela de 30 dias, warning 80%, critical 100% e resposta `notify`.
4. Salve e execute a avaliação.

Resultado esperado: surge evento de warning/critical quando aplicável, sem ação de
desligamento.

### OBS-WEB-051 — Budget com aprovação

1. Crie `Teste approval` com resposta `approval` e mantenha dry-run ativo.
2. Associe recursos demo quando o formulário permitir.
3. Execute **Monitorar**.
4. Abra Governança e localize a ação pendente.
5. Aprove a ação simulada.

Resultado esperado: o excesso gera pedido de aprovação; nada é desligado antes da
aprovação; em dry-run, a aprovação termina como simulação auditável.

### OBS-WEB-052 — Budget ignorado

1. Crie `Teste ignore` com resposta `ignore`.
2. Avalie o budget.

Resultado esperado: o evento é registrado, mas nenhuma ação ou aprovação é criada.

### OBS-WEB-053 — Deduplicação

1. Avalie duas vezes o mesmo budget no mesmo período.
2. Compare os eventos.

Resultado esperado: o mesmo threshold não produz ações duplicadas.

### OBS-WEB-054 — Limpeza

Exclua os budgets `Teste notify`, `Teste approval` e `Teste ignore`.

Resultado esperado: regras desaparecem sem remover eventos históricos ou auditoria
que devam ser preservados.

## 8. Governança — `/governance`

### OBS-WEB-060 — Recursos sem mapeamento

1. Abra **Governança**.
2. Confira a área de recursos sem produto/owner.
3. Selecione um recurso e teste o mapeamento em dry-run.

Resultado esperado: a tela diferencia claramente simulação, alteração local e
write-back no provider.

### OBS-WEB-061 — Política de horário

1. Crie política `Expediente homologação`.
2. Selecione um recurso demo.
3. Defina timezone, dias úteis, hora de início e parada.
4. Mantenha **Exigir aprovação** e **Dry-run** ativos.
5. Salve e execute **Run due** com horário determinístico, se disponível.

Resultado esperado: uma ação agendada é criada apenas quando horário e seletor
coincidem; ela aguarda aprovação.

### OBS-WEB-062 — Data limite

1. Crie política `Expiração homologação`.
2. Defina `expires_at` no passado ou próximo minuto.
3. Selecione ação de expiração `stop`.
4. Execute a avaliação.

Resultado esperado: surge ação de parada pendente, nunca execução silenciosa.

### OBS-WEB-063 — Aprovar e rejeitar

1. Aprove uma ação dry-run.
2. Rejeite outra informando motivo.

Resultado esperado: status e mensagem são atualizados; a rejeição não chama o
provider; ambas aparecem na trilha de auditoria.

### OBS-WEB-064 — Proteção contra ação real

Não desative dry-run fora de uma conta exclusiva de homologação. Quando testar
ação real, use um recurso descartável, confirme owner e janela, capture aprovação
e verifique o estado diretamente no provider.

## 9. Conexões — `/connections`

### OBS-WEB-070 — Catálogo

1. Abra **Conexões**.
2. Alterne entre **Catálogo** e **Instaladas**.
3. Pesquise `GitHub`, `AWS`, `GCP`, `Datadog`, `MCP` e uma ferramenta adapter.
4. Teste filtros de categoria.

Resultado esperado: cards exibem ícone, categoria, sinais coletados e badge
`Integração nativa` ou `Via API Adapter`.

### OBS-WEB-071 — Formulário e proteção de segredos

1. Abra o card GitHub.
2. Confira campos, instruções e link de obtenção de credencial.
3. Feche e reabra o drawer.

Resultado esperado: layout permanece centralizado e responsivo; segredos salvos
nunca são reexibidos em texto puro.

### OBS-WEB-072 — Mock Demo

1. Abra `Mock Demo`.
2. Salve com nome `Mock homologação`.
3. Clique em **Testar conexão**.
4. Clique em **Sincronizar**.
5. Verifique Overview, Products, Inventory, Logs e Alerts.

Resultado esperado: teste e sync concluem; dados aparecem nas telas corretas; a
conexão fica na aba Instaladas.

### OBS-WEB-073 — Atualizar, desabilitar e excluir

1. Renomeie a conexão de homologação.
2. Desabilite-a e confirme que rotinas globais não a sincronizam.
3. Reabilite, sincronize e exclua.

Resultado esperado: cada ação afeta somente a conexão da tenancy atual.

### OBS-WEB-074 — API Adapter

1. Suba um endpoint de homologação que implemente health e `/observa/pull`.
2. Escolha qualquer card marcado `Via API Adapter`.
3. Informe base URL, paths e bearer token temporário.
4. Teste antes de salvar e depois sincronize.

Resultado esperado: payload canônico cria somente os sinais declarados; token não
aparece em logs, respostas ou listagens.

### OBS-WEB-075 — Conector MCP

1. Escolha o conector MCP.
2. Informe a URL Streamable HTTP de um servidor de homologação.
3. Descubra as tools.
4. Configure a tool permitida e teste.
5. Sincronize payload canônico de custos/recursos/métricas/logs.

Resultado esperado: somente a tool configurada é chamada; falha de protocolo ou
payload inválido não persiste dados parciais.

### OBS-WEB-076 — Cloud real

1. Use conta/projeto temporário e credencial de leitura com menor privilégio.
2. Teste a conexão sem salvar.
3. Salve na tenancy de homologação e sincronize.
4. Compare amostra de custos/recursos com o console do provider.
5. Revogue a credencial ao concluir.

Resultado esperado: diferença conhecida é explicada por janela, moeda ou atraso do
provider; nenhum recurso de outra conta aparece.

## 10. Dashboards — `/dashboards` e `/dashboards/{id}`

### OBS-WEB-080 — Catálogo de dashboards

1. Abra **Dashboards**.
2. Confira os cards de visão executiva, APM, infraestrutura e logs.
3. Abra cada dashboard.

Resultado esperado: título, widgets e métricas correspondem ao card escolhido.

### OBS-WEB-081 — Widgets

1. Verifique gráficos, KPIs, tabelas, estados vazios e legendas.
2. Redimensione a janela para desktop menor.

Resultado esperado: nenhum widget sobrepõe outro e valores permanecem legíveis.

## 11. Aplicações e infraestrutura — `/observability`

### OBS-WEB-090 — Saúde por produto

1. Abra **Aplicações e infra**.
2. Confira séries ativas, produtos monitorados e alertas.
3. Compare p95, error rate, RPM, CPU e conexões de banco por produto.

Resultado esperado: produtos presentes correspondem aos sinais sincronizados; não
há divisão por zero ou valor `NaN`.

## 12. Logs — `/logs`

### OBS-WEB-100 — Exploração

1. Abra **Logs**.
2. Pesquise texto existente.
3. Filtre severity, source e product.
4. Limpe os filtros.

Resultado esperado: tabela, total e paginação refletem a consulta; labels e trace
ID não vazam dados de outra tenancy.

### OBS-WEB-101 — Ingestão via API

```powershell
$headers = @{
  "X-Observa-Api-Key" = $env:OBSERVA_API_KEY
  "Content-Type" = "application/json"
}
$body = @{
  connection_id = "manual-test"
  logs = @(@{
    ts = (Get-Date).ToUniversalTime().ToString("o")
    severity = "ERROR"
    source = "acceptance-guide"
    message = "timeout connecting to database in acceptance test"
    product = "homologacao"
    service = "api"
    labels = @{ synthetic = "true" }
  })
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/api/logs/ingest -Headers $headers -Body $body
```

Resultado esperado: log aparece somente na tenancy selecionada pelos headers. Para
tenancy não default, inclua também `X-Observa-Company-ID` e
`X-Observa-Tenancy-ID`.

## 13. Traces — `/traces`

### OBS-WEB-110 — Waterfall distribuído

1. Abra **Traces**.
2. Escolha um trace com múltiplos spans.
3. Compare duração total, serviço, status e barras do waterfall.

Resultado esperado: spans respeitam ordem temporal e erros ficam destacados.

## 14. Monitores — `/monitors`

### OBS-WEB-120 — Estado das regras

1. Abra **Monitores**.
2. Compare estados `OK`, `WARN` e `ALERT`.
3. Confira mensagem, produto e última avaliação.

Resultado esperado: contadores superiores batem com a tabela.

## 15. RUM e sintéticos — `/rum`

### OBS-WEB-130 — Experiência do usuário

1. Abra **RUM e sintéticos**.
2. Confira sessões, LCP, erros JS, crash-free, uptime e checks.

Resultado esperado: unidades e percentuais são exibidos corretamente; ausência de
dados reais usa estado vazio, não valores inventados.

## 16. GCP Monitoring — `/gcp`

### OBS-WEB-140 — Métricas GCP

1. Abra **GCP Monitoring**.
2. Selecione projeto/recurso quando disponível.
3. Confira séries de CPU, memória, banco e Cloud Run/GKE.

Resultado esperado: filtros não misturam projetos e a tela permanece funcional
com Mock Demo e conector GCP real.

## 17. Alertas — `/alerts`

### OBS-WEB-150 — Caixa unificada

1. Abra **Alertas**.
2. Filtre severity, categoria, produto e status.
3. Compare alertas FinOps, infraestrutura e aplicação.

Resultado esperado: cada linha mostra origem, severidade, produto e detecção; o
contador lateral acompanha os alertas abertos.

## 18. Remediações — `/remediations`

### OBS-WEB-160 — Análise de erro

1. Garanta que o log sintético de `OBS-WEB-101` existe.
2. Abra **Remediações**.
3. Clique em analisar logs.
4. Leia diagnóstico, evidência e recomendação.

Resultado esperado: proposta é criada em dry-run e não modifica código ou
infraestrutura automaticamente.

### OBS-WEB-161 — Aprovação e feedback

1. Aprove uma proposta em dry-run.
2. Rejeite outra com motivo.
3. Registre feedback de sucesso/falha quando disponível.

Resultado esperado: execução real exige papel admin e aprovação explícita; feedback
fica associado à proposta e não é compartilhado entre clientes.

## 19. Autenticação — `/settings/auth`

### OBS-WEB-170 — Configuração local

1. Abra **Authentication**.
2. Confirme modo `local`.
3. Verifique que client secrets existentes não são exibidos.

Resultado esperado: valores sensíveis ficam mascarados/ausentes.

### OBS-WEB-171 — OIDC de homologação

1. Cadastre aplicação Google ou GitLab com callback de homologação.
2. Informe client ID, secret, issuer e habilite o provider.
3. Troque para OIDC somente depois de validar callback e conta admin.
4. Saia e faça login.

Resultado esperado: state inválido/expirado é recusado; sessão válida recebe
permissões do membership configurado, não acesso global automático.

## 20. Companies e tenancies — `/settings/organizations`

### OBS-WEB-180 — Criar company e duas tenancies

1. Crie company `Acceptance Corp`.
2. Crie tenancies `Production` e `Sandbox` dentro dela.
3. Adicione um usuário OIDC viewer e outro operator, se disponível.

Resultado esperado: slugs e IDs são únicos; papéis aparecem corretamente.

### OBS-WEB-181 — Isolamento forte

1. Na tenancy Production, crie conexão Mock Demo e sincronize.
2. Troque para Sandbox.
3. Abra Connections, Inventory, Budgets, Logs e Remediations.

Resultado esperado: Sandbox continua vazia. Se qualquer dado de Production
aparecer, interrompa a homologação e trate como incidente crítico.

### OBS-WEB-182 — RBAC

1. Entre como viewer e tente criar conexão, budget e política.
2. Entre como operator e repita.
3. Entre como admin e teste aprovação de remediação.

Resultado esperado: viewer lê, mas não altera; operator gerencia recursos da
tenancy; admin aprova ações privilegiadas; usuário sem membership não descobre a
company.

## 21. CLI

Configure o ambiente sem imprimir a chave:

```powershell
$env:OBSERVA_URL = "http://127.0.0.1:8080"
$env:OBSERVA_COMPANY_ID = "cmp_default"
$env:OBSERVA_TENANCY_ID = "tnt_default"
```

### OBS-CLI-001 — Consultas

```powershell
observa companies list
observa tenancies list --company cmp_default
observa resources --untagged
observa budgets list
observa policies list
observa actions list
observa remediations list
```

Resultado esperado: saída tabular legível; `--json` retorna JSON válido para
automação.

### OBS-CLI-002 — Tags em dry-run

```powershell
observa tag <RESOURCE_UID> --set product=homologacao --set owner=finops-test
```

Resultado esperado: nenhuma alteração real sem `--apply`.

### OBS-CLI-003 — Policy e aprovação

```powershell
observa policies create "CLI homologação" --resource <RESOURCE_UID> --timezone America/Sao_Paulo --stop 20:00
observa run-due
observa actions list --status pending_approval
observa actions approve <ACTION_ID>
```

Resultado esperado: policy nasce em dry-run e exige aprovação por padrão.

### OBS-CLI-004 — Budget

```powershell
observa budgets create "CLI budget" --scope product --value homologacao --amount 10 --response approval
observa budgets evaluate
observa budgets events
```

Resultado esperado: regra, evento e eventual aprovação aparecem na tenancy correta.

## 22. Mobile

### OBS-MOB-001 — Build e configuração

```powershell
cd apps/mobile
npm ci
npm run typecheck
npm start
```

1. Abra no Expo Go ou em build interno.
2. Configure URL da API acessível pelo dispositivo e chave de homologação.
3. Selecione company/tenancy.

Resultado esperado: segredo fica no Secure Store, não em logs ou AsyncStorage
aberto.

### OBS-MOB-002 — Fluxos principais

1. Confira custo e alertas.
2. Abra aprovações pendentes.
3. Aprove uma ação dry-run e rejeite outra.
4. Abra remediações sugeridas.

Resultado esperado: alterações aparecem também na web e CLI da mesma tenancy.

### OBS-MOB-003 — Publicação interna

1. Configure `projectId` com `eas init`.
2. Execute o workflow mobile com `submit=false`.
3. Instale Android/iOS em dispositivos de homologação.
4. Só use `submit=true` depois dos testes e documentos de privacidade.

## 23. MCP exposto pelo Observa

### OBS-MCP-001 — Descoberta de tools

Faça POST autenticado em `/mcp` com protocolo suportado e método `tools/list`.

Resultado esperado: aparecem somente tools read-only:

- `observa_context`.
- `observa_cost_summary`.
- `observa_inventory`.
- `observa_products`.
- `observa_alerts`.

### OBS-MCP-002 — Isolamento

1. Chame `observa_context` em duas tenancies.
2. Consulte inventory e costs em ambas.
3. Omita/forje headers de contexto.

Resultado esperado: contexto válido é obrigatório; dados não atravessam tenancy;
o MCP não retorna credenciais nem oferece desligamento/remediação.

## 24. Segurança HTTP

### OBS-SEC-001 — Autenticação

1. Chame `/api/health` sem chave.
2. Repita com chave inválida e válida.

Resultado esperado: HTTP 401, HTTP 401 e HTTP 200, respectivamente.

### OBS-SEC-002 — Headers

Confira na resposta autenticada:

- `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`.
- `X-Content-Type-Options: nosniff`.
- `X-Frame-Options: DENY`.
- `Referrer-Policy: no-referrer`.
- `Cache-Control: no-store`.

### OBS-SEC-003 — Rate limit

1. Em ambiente isolado, reduza `RATE_LIMIT_REQUESTS`.
2. Reinicie a API e faça chamadas em sequência.

Resultado esperado: HTTP 429 com `Retry-After`; probes continuam disponíveis.

### OBS-SEC-004 — Payload máximo

1. Reduza `MAX_REQUEST_BODY_BYTES` em homologação.
2. Envie payload maior.

Resultado esperado: HTTP 413 antes de processar o corpo.

## 25. Backup e recuperação

### OBS-OPS-001 — Backup

```powershell
python scripts/backup.py --data-dir data --output-dir backups --retention 14
```

Resultado esperado: diretório com bancos e `manifest.json`; nenhuma chave ou
credencial é copiada.

### OBS-OPS-002 — Restore

```powershell
python scripts/restore.py backups/<BACKUP> --data-dir data-restored
```

1. Use os mesmos segredos externos do ambiente original.
2. Inicie instância isolada apontando para `data-restored`.
3. Verifique companies, tenancies, conexões, budgets e auditoria.

Resultado esperado: checksums válidos e dados restaurados; arquivo adulterado é
recusado.

## 26. Carga e disponibilidade

### OBS-OPS-010 — Carga curta

```powershell
python scripts/load_test.py --api-key $env:OBSERVA_API_KEY --requests 1000 --concurrency 25 --max-error-rate 0.01 --max-p95-ms 750
```

Resultado esperado: erro e p95 abaixo dos limites definidos para o ambiente.

### OBS-OPS-011 — Kubernetes

1. Aplique o manifest após criar `observa-secrets` no secret manager.
2. Confirme API ready, duas réplicas web, PDB, HPA e CronJob.
3. Remova um pod web e confirme continuidade.
4. Execute manualmente o CronJob de backup e valide o artefato.

Resultado esperado: web continua disponível. Não aumente a API acima de uma
réplica enquanto o storage for SQLite.

## 27. Vídeo completo

Para revisar rapidamente todas as áreas, abra:

`docs/demo/observa-complete-walkthrough.mp4`

Para regenerar com dados demo:

```powershell
$env:OBSERVA_DEMO_API_KEY = (Get-Content data/api_key -Raw).Trim()
python scripts/capture_demo.py
python scripts/render_demo_video.py
Remove-Item Env:OBSERVA_DEMO_API_KEY
```

Resultado esperado: 27 cenas, aproximadamente 89 segundos, H.264, 1440×900,
sem token ou credencial visível.

## 28. Evidências e aceite final

Para cada cenário, registre:

- ID do cenário.
- Data, versão/commit e ambiente.
- Company e tenancy de homologação.
- Resultado `PASS`, `FAIL` ou `BLOCKED`.
- Evidência sem segredo: screenshot, resposta sanitizada ou ID interno.
- Defeito associado e reteste.

O release pode ser aceito quando:

- Todos os cenários críticos de autenticação, RBAC e isolamento passam.
- Nenhuma ação destrutiva ocorre sem approval e escopo explícitos.
- Custos e recursos reais foram comparados com pelo menos uma cloud de homologação.
- Backup foi restaurado em outro diretório/ambiente.
- Testes automatizados, build web/mobile/CLI e carga passam.
- Achados críticos/altos de auditoria e pentest estão resolvidos.
- Credenciais temporárias foram revogadas.

Pentest independente, publicação em lojas e homologação de clouds reais continuam
dependendo de contas, credenciais e aprovações externas ao repositório.
