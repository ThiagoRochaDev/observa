# Sistema visual web do Observa

O sistema visual v1 é aplicado pelo shell global e pelos estilos compartilhados. Toda rota renderizada dentro de `app/layout.tsx` recebe a mesma navegação, contexto organizacional, tipografia, superfícies e componentes básicos.

## Estrutura global

```text
Faixa de contexto (28px)
├── Company / tenancy / ambiente
└── Aviso operacional

Sidebar (232px em desktop)
├── Marca Observa
├── Navegação agrupada
└── Usuário e papéis

Área principal
├── Header (52px)
│   ├── Seletor de contexto
│   ├── Busca global
│   └── Política de IA externa
└── Conteúdo da rota
```

Em viewports menores que `1000px`, a sidebar entra no modo compacto com ícones. O conteúdo das páginas continua rolando de forma independente.

## Contexto e segurança

- A faixa superior permanece visível em todas as rotas.
- O código `PROD`, `HML` ou `DEV` é derivado da tenancy ativa.
- Produção usa destaque vermelho e aviso sobre ações reais.
- A troca de contexto acontece em modal, sem aplicar a escolha durante a navegação.
- Ao confirmar, `company_id` e `tenancy_id` são persistidos e a aplicação é recarregada para limpar filtros e estados locais.
- O header informa quando IA externa está desativada.

O frontend comunica contexto, mas a autorização e o isolamento continuam obrigatoriamente no backend.

## Tokens principais

| Token | Uso |
| --- | --- |
| `--bg` | fundo geral |
| `--bg-card` | cards, tabelas e painéis |
| `--border` | divisores e contornos |
| `--text` | texto principal |
| `--text-muted` | descrições e metadados |
| `--accent` | seleção e ações neutras |
| `--success` | saudável, economia e sucesso |
| `--warning` | atenção e anomalia |
| `--danger` | risco, falha e produção |
| `--purple` | IA e recomendação |

Gradientes não fazem parte do sistema v1. Sombras são reservadas para modais e overlays. Raios são de `4px` em badges, `7px` em campos e botões, `10px` em cards e `12px` em modais.

## Tipografia

- Interface: Geist.
- Código, IDs, atalhos e valores técnicos: Geist Mono.
- Base: `13px`.
- Números usam alinhamento tabular.
- Títulos de página usam peso semibold e tracking negativo discreto.

## Componentes compartilhados

### Cards

Use `.card`. O componente recebe superfície sólida, borda, raio de `10px` e estado hover sem deslocamento ou sombra decorativa.

### Grids

- `.grid.grid-2`: duas colunas.
- `.grid.grid-3`: três colunas.
- `.grid.grid-4`: quatro colunas.
- Abaixo de `1180px`, grids de três e quatro colunas passam para duas.
- Abaixo de `720px`, todos passam para uma coluna.

### Tabelas

Use `.table`. Cabeçalhos são compactos, uppercase e separados por borda. Linhas usam divisores discretos e realce sólido no hover. Em telas pequenas, a tabela mantém largura mínima e pode rolar horizontalmente.

### Formulários

Use `.form` para espaçamento. Inputs, selects e textareas compartilham fundo inset, borda e foco azul visível. Não coloque credenciais em placeholders, valores iniciais ou documentação.

### Botões

- `.btn`: ação neutra.
- `.btn.btn-primary`: ação principal.
- `.btn-danger`: ação destrutiva ou de risco.
- `.button.primary` e `.button.secondary`: variantes usadas em dialogs.

Status e ações devem sempre incluir texto; cor isolada não é suficiente.

### Badges

Use `.badge` com os modificadores `.ok`, `.low`, `.medium`, `.high` ou `.fail`. Badges são compactos, possuem borda e texto descritivo.

## Rotas cobertas

O shell e os componentes compartilhados são aplicados a:

- Visão geral;
- Produtos e detalhes;
- Mapa do ecossistema;
- Inventário;
- Budgets;
- Governança;
- Dashboards e detalhes;
- APM e infraestrutura;
- Logs;
- Traces;
- Monitores;
- RUM e sintéticos;
- GCP Monitoring;
- Alertas;
- Remediações;
- Conexões;
- Companies e tenancies;
- Autenticação e segurança.

## Arquivos principais

- `apps/web/app/layout.tsx`: idioma e fontes globais.
- `apps/web/components/Shell.tsx`: faixa de contexto, sidebar, header e modal.
- `apps/web/app/globals.css`: tokens e estilos compartilhados.
- `apps/web/components/EcosystemMap.tsx`: experiência especializada do Mapa Vivo.

## Marketplace de conexões

A rota `/connections` usa um navegador de integrações inspirado em gerenciadores de plugins, sem
copiar identidade visual de terceiros. O fluxo é dividido entre **Catálogo** e **Instalados**, com:

- busca textual por nome, descrição, categoria ou capacidade;
- filtro lateral por categoria e contagem de conectores;
- cards com ícones locais das plataformas, descrição e capacidades;
- indicador visual de conector já instalado;
- painel lateral de configuração, teste e salvamento;
- lista separada para sincronizar ou remover conexões existentes;
- aviso de isolamento por company e tenancy.

Os ícones são SVGs incorporados ao frontend e não fazem requisições a CDNs. Secrets nunca são
preenchidos novamente na interface e devem permanecer criptografados no backend.

O catálogo diferencia dois níveis de integração:

- **Integração nativa**: o Observa se comunica diretamente com a API oficial da ferramenta.
- **Via API Adapter**: um adapter controlado pelo cliente converte a ferramenta para os contratos
  canônicos de custos, recursos, métricas e logs do Observa.

Conectores via adapter usam ícones monogramados locais, teste de saúde, bearer token opcional e
ingestão por `GET /observa/pull`. O adapter permanece no ambiente do cliente, permitindo integrar
ferramentas SaaS, open source, legadas ou internas sem enviar credenciais para terceiros.

## Regras para novas telas

1. Renderize a rota dentro do layout raiz existente.
2. Reutilize `.page-title`, `.page-sub`, `.card`, `.grid`, `.table`, `.form`, `.btn` e `.badge`.
3. Não crie uma segunda sidebar ou outro seletor de tenancy.
4. Não use gradientes decorativos.
5. Não use apenas cor para representar estado.
6. Preserve foco visível e navegação por teclado.
7. Não mantenha dados da tenancy anterior após troca de contexto.
8. Não mostre secrets, tokens ou credenciais.
9. Valide em desktop, modo compacto e mobile.
10. Execute typecheck e lint antes de publicar.
