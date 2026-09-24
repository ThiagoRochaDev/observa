# Mapa Vivo e assistente contextual

O Mapa Vivo apresenta a topologia técnica de um produto em uma visão navegável. Ele conecta serviços, recursos de cloud, bancos, workers e dependências externas sem misturar o contexto de empresas ou tenancies.

Este documento descreve o comportamento implementado, o fluxo entre frontend e backend, o contrato de dados, os controles de segurança, a operação local e os testes recomendados.

## 1. Objetivos

- Entender rapidamente como os componentes de um produto se relacionam.
- Identificar dependências de entrada e saída durante incidentes e análises de arquitetura.
- Exibir recursos externos e possíveis pontos de acoplamento.
- Oferecer uma base visual para futuras análises de custo, risco, disponibilidade e capacidade.
- Permitir perguntas contextuais sem enviar dados do cliente para serviços externos por padrão.

## 2. Como acessar

Com a API e o frontend ativos, abra:

```text
http://localhost:3000/maps
```

Se a aplicação solicitar uma chave local, use o conteúdo de `data/api_key`. A chave permanece no `localStorage` do navegador e é enviada no header `X-Observa-Api-Key` somente para a API configurada em `NEXT_PUBLIC_API_URL`.

Para iniciar com Docker:

```bash
cp .env.example .env
docker compose up -d --build
```

No Windows, quando o ambiente Python e as dependências web já estiverem instalados, os processos também podem ser iniciados separadamente:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Em outro terminal:

```powershell
cd apps/web
npm run dev
```

## 3. Jornada na interface

1. Escolha um produto no seletor superior.
2. Aguarde o carregamento da topologia.
3. Confira o resumo de componentes, conexões e integrações externas.
4. Clique em um nó para selecioná-lo.
5. Observe as conexões relacionadas destacadas e animadas.
6. Use o painel lateral para consultar produto, camada, entradas, saídas, tipo e identificador.
7. Clique em uma dependência direta para navegar até ela sem recarregar a API.
8. Use zoom, redução, ajuste automático e movimentação do canvas.
9. Abra **Pergunte ao Observa** para analisar o componente selecionado.
10. Pressione `Esc` ou o botão de fechar para sair do assistente.

## 4. Significado dos nós

| `kind` | Uso | Código visual |
| --- | --- | --- |
| `frontend` | Aplicação web ou cliente visual | `WEB` |
| `api` | API, gateway ou serviço síncrono | `API` |
| `worker` | Consumidor, job ou processamento assíncrono | `WRK` |
| `resource` | Banco, cache, cluster ou recurso de infraestrutura | `RES` |
| `external` | Serviço fora do limite do produto | `EXT` |
| `service` | Serviço genérico quando não existe classificação mais específica | `SVC` |

O texto **Mapeado** indica que o componente está presente na topologia recebida. Ele não representa health check, disponibilidade nem conformidade operacional.

## 5. Fluxo técnico

```text
Usuário
  -> /maps
  -> apps/web/app/maps/page.tsx
  -> api.ecosystem(product)
  -> GET /api/ecosystem?product=<slug>
  -> autenticação e contexto ativo
  -> payload de nós e conexões
  -> EcosystemMap
  -> layout Dagre + renderização React Flow
```

Responsabilidades principais:

- `apps/web/app/maps/page.tsx`: seleciona o produto, busca os dados e controla loading/erro.
- `apps/web/components/EcosystemMap.tsx`: calcula layout, desenha a topologia, mantém seleção, inspector e assistente.
- `apps/web/lib/api.ts`: adiciona chave, company e tenancy às requisições.
- `apps/api/app/presentation/api/router.py`: expõe `GET /api/ecosystem`.
- `apps/api/app/application/demo_platform.py`: fornece os payloads demonstrativos atuais.

## 6. Contrato da API

Requisição:

```http
GET /api/ecosystem?product=produto-exemplo
X-Observa-Api-Key: <chave-local>
X-Observa-Company-ID: <company-id>
X-Observa-Tenancy-ID: <tenancy-id>
```

Resposta simplificada:

```json
{
  "product": "produto-exemplo",
  "nodes": [
    {
      "id": "web",
      "label": "produto-web",
      "kind": "frontend",
      "tier": 0
    },
    {
      "id": "api",
      "label": "produto-api",
      "kind": "api",
      "tier": 1,
      "type": "service"
    }
  ],
  "edges": [
    {
      "source": "web",
      "target": "api",
      "label": "HTTPS"
    }
  ]
}
```

Regras do contrato:

- `product` identifica o produto exibido.
- `nodes[].id` deve ser único dentro do produto e da tenancy.
- `nodes[].label` é o nome apresentado ao usuário.
- `nodes[].kind` define a categoria e o estilo visual.
- `nodes[].tier` define a camada lógica; a interface mostra `tier + 1`.
- `nodes[].type` é opcional e detalha a tecnologia ou tipo de recurso.
- `edges[].source` e `edges[].target` devem apontar para IDs existentes.
- `edges[].label` é opcional e descreve protocolo ou relação.

## 7. Layout e interação

O Dagre organiza automaticamente a topologia da esquerda para a direita (`LR`). Os nós não podem ser arrastados ou conectados manualmente, evitando que uma alteração visual seja confundida com uma mudança real na arquitetura.

Ao selecionar um nó:

- arestas de entrada e saída recebem destaque;
- o inspector recalcula os contadores;
- dependências diretas se tornam atalhos navegáveis;
- a resposta anterior do assistente é limpa;
- nenhuma nova requisição é necessária para navegar entre dependências já carregadas.

O design responsivo move o inspector para baixo do canvas em telas menores. O botão do assistente permanece fixo e acessível.

## 8. Pergunte ao Observa

O assistente contextual recebe somente o estado já presente no componente React:

- produto selecionado;
- componente selecionado;
- quantidade de entradas;
- quantidade de saídas;
- relações presentes no payload carregado.

Na implementação atual, a resposta é determinística e local. Não existe chamada para OpenAI, Claude ou outro provedor externo. Também não há execução de comando, alteração de recurso ou remediação automática.

Perguntas sugeridas:

- Quais são as dependências deste componente?
- Existe algum ponto único de falha?
- Que dados estão disponíveis para analisar custos?

As respostas atuais resumem a conectividade. Inferências avançadas de risco, custo ou causa raiz exigirão métricas adicionais e um motor de análise futuro.

## 9. Segurança e privacidade

### 9.1 Autenticação

Todas as rotas `/api` exigem `X-Observa-Api-Key` no modo local. A tela de acesso valida uma chave armazenada chamando `/api/health`. Em caso de `401`, a chave é removida e a interface protegida não é exibida.

### 9.2 Isolamento organizacional

O cliente HTTP inclui, quando definidos:

- `X-Observa-Company-ID`;
- `X-Observa-Tenancy-ID`.

Conectores reais e persistência de topologia devem sempre filtrar dados no backend pelo contexto autorizado. O frontend não deve ser tratado como fronteira de segurança.

### 9.3 Dados enviados para IA

Por padrão, nenhum dado do mapa é enviado para IA externa. Uma futura integração precisa:

1. ser habilitada explicitamente pelo owner;
2. usar um conector configurado para a tenancy ativa;
3. aplicar minimização e redação de dados;
4. impedir o envio de secrets, tokens, logs brutos ou credenciais;
5. registrar auditoria sem armazenar conteúdo sensível desnecessário;
6. exigir aprovação separada antes de qualquer ação real.

### 9.4 Ações de infraestrutura

O Mapa Vivo é somente leitura. Selecionar nós, navegar por dependências ou perguntar ao assistente não altera recursos. Desligamentos, resizing, tags e remediações devem usar os fluxos de governança, aprovação e auditoria do Observa.

## 10. Estado atual e evolução

O endpoint de topologia atual usa payloads demonstrativos definidos em `demo_platform.py`. Eles validam a experiência visual e o contrato, mas ainda não representam descoberta automática de todos os conectores.

Para produção, a evolução recomendada é:

1. normalizar entidades e relações coletadas por AWS, GCP, Azure, Kubernetes, GitLab e ferramentas de observabilidade;
2. persistir a topologia com `company_id`, `tenancy_id`, `product_id` e origem do conector;
3. rejeitar relações entre contextos não autorizados;
4. registrar data da última observação e confiança da relação;
5. correlacionar nós com custo, métricas, logs, ownership e tags;
6. substituir o provedor demonstrativo por um serviço de consulta tenant-scoped;
7. habilitar IA externa apenas por política explícita e com auditoria.

## 11. Testes rápidos

Teste de saúde autenticado:

```powershell
$apiKey = (Get-Content .\data\api_key -Raw).Trim()
$headers = @{ "X-Observa-Api-Key" = $apiKey }
Invoke-RestMethod http://localhost:8080/api/health -Headers $headers
```

Teste do payload:

```powershell
$ecosystem = Invoke-RestMethod `
  "http://localhost:8080/api/ecosystem?product=hiperlocal" `
  -Headers $headers

$ecosystem.product
$ecosystem.nodes.Count
$ecosystem.edges.Count
```

Validações esperadas:

- o produto retornado corresponde ao solicitado;
- IDs de nós não se repetem;
- todas as arestas apontam para nós existentes;
- a API rejeita chave ausente ou inválida;
- a troca de contexto não mistura dados entre tenancies;
- o assistente informa que a análise é local;
- nenhuma ação real é disparada pela tela.

Os cenários completos estão em `docs/TESTING_GUIDE.md`, seção **25. Mapa Vivo e assistente contextual**.

## 12. Solução de problemas

### Tela solicita autenticação repetidamente

- confirme que a API está disponível em `http://localhost:8080`;
- use a chave atual de `data/api_key`;
- verifique se `NEXT_PUBLIC_API_URL` aponta para a API correta;
- recarregue a página depois de reiniciar a API.

### Mapa não carrega

- abra `http://localhost:8080/docs` e confirme que `/api/ecosystem` está disponível;
- teste o endpoint pelo PowerShell usando o header de autenticação;
- confira o erro exibido pela própria página;
- confirme que o slug do produto existe no provedor de topologia.

### Canvas aparece vazio

- confirme que `nodes` possui itens;
- valide se todos os IDs são únicos;
- valide se `source` e `target` apontam para nós existentes;
- use o controle de ajuste automático do React Flow;
- procure erros de hidratação ou JavaScript no console do navegador.

### Frontend em desenvolvimento bloqueia `127.0.0.1`

Use `http://localhost:3000` durante o desenvolvimento ou configure `allowedDevOrigins` no Next.js para hosts adicionais confiáveis. Não libere origens amplas sem necessidade.

## 13. Critérios para produção

Antes de usar o Mapa Vivo com dados reais de clientes, confirme:

- autenticação forte ou SSO configurado;
- autorização aplicada no backend;
- company e tenancy obrigatórias nas consultas persistidas;
- credenciais criptografadas e fora dos logs;
- conectores com permissões mínimas e preferencialmente read-only;
- testes de isolamento e enumeração aprovados;
- auditoria de consultas e ações sensíveis;
- retenção e exclusão de dados definidas;
- nenhuma integração externa habilitada implicitamente;
- backup e procedimento de recuperação testados.
