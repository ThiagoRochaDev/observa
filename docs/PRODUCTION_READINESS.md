# Preparação enterprise e produção

Este documento separa controles implementados no repositório de atividades que
dependem da infraestrutura, das credenciais e da homologação de cada cliente.

## Estado atual

| Área | Estado | Evidência |
|---|---|---|
| Rate limiting | Implementado por instância | `SecurityMiddleware`, headers `RateLimit-*` e teste automatizado |
| Limite de payload e headers seguros | Implementado | HTTP 413, `nosniff`, `DENY`, `no-referrer`, `no-store` |
| Segredos externos em produção | Obrigatório | startup falha sem as três variáveis protegidas |
| Liveness e readiness | Implementado | `/healthz` e `/readyz` |
| Backup e restore | Implementado para SQLite | snapshot consistente, checksums, retenção e teste de round-trip |
| Backup agendado no Kubernetes | Implementado | CronJob diário e PVC separado |
| Alta disponibilidade web | Implementado | duas réplicas, HPA e PDB |
| Alta disponibilidade da API | Bloqueado por SQLite | uma réplica e estratégia `Recreate` para evitar corrupção |
| Teste de carga | Implementado | script sem dependências com SLO de erro e p95 |
| E2E em clouds reais | Harness implementado | execução depende de credenciais privadas do cliente |
| Auditoria de dependências/SAST | Implementado em CI | `pip-audit`, Bandit e `npm audit` |
| Pentest externo | Pendente | deve ser executado por equipe independente no ambiente homologado |
| Release CLI | Pipeline implementado | publicação depende de Trusted Publishing no PyPI |
| Release mobile | Pipeline implementado | build/submit depende de Expo, Apple e Google Play |
| Adapters dos clientes | Contrato pronto | implementação nativa depende de API, escopo e credenciais de cada cliente |

## Perfil Docker de produção

Gere os segredos fora do repositório e injete-os pelo secret manager da
plataforma. Não grave os valores no `.env` de uma máquina compartilhada.

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
```

Variáveis obrigatórias:

- `OBSERVA_API_KEY`: no mínimo 32 caracteres aleatórios.
- `OBSERVA_SECRETS_KEY`: chave Fernet válida usada para criptografar credenciais.
- `OBSERVA_SESSION_SECRET`: no mínimo 32 caracteres aleatórios para sessões.
- `CORS_ORIGINS`: JSON com os origins públicos permitidos ou `[]` quando o
  reverse proxy publica web e API no mesmo origin.

O perfil desativa seed de demonstração e documentação OpenAPI, remove
capabilities Linux, ativa filesystem somente leitura e adiciona healthchecks.

## Kubernetes

Antes de aplicar `deploy/kubernetes/observa.yaml`, crie `observa-secrets` pelo
secret manager do cluster (External Secrets, Sealed Secrets, Vault ou equivalente)
com estas chaves:

```text
OBSERVA_API_KEY
OBSERVA_SECRETS_KEY
OBSERVA_SESSION_SECRET
```

Depois:

```bash
kubectl apply -f deploy/kubernetes/observa.yaml
kubectl -n observa rollout status deployment/observa-api
kubectl -n observa rollout status deployment/observa-web
kubectl -n observa get pods,pdb,hpa,cronjob
```

O HPA da web requer Metrics Server. A API permanece com uma réplica porque os
bancos por tenancy são SQLite em um PVC `ReadWriteOnce`. Não aumente `replicas`
até migrar o repositório de dados para PostgreSQL ou outro banco transacional
compartilhado e substituir o rate limiter em memória por Redis/API Gateway.

## Backup e recuperação de desastre

Backup manual:

```bash
python scripts/backup.py --data-dir data --output-dir backups --retention 14
```

Restauração com a API parada:

```bash
python scripts/restore.py backups/observa-AAAAMMDDTHHMMSSZ --data-dir data-restored
```

O backup contém bancos, não contém chaves. As chaves do secret manager precisam
ser preservadas separadamente; sem a mesma `OBSERVA_SECRETS_KEY`, credenciais já
criptografadas não podem ser recuperadas. O PVC de backup protege contra falha do
pod, mas não contra perda do cluster. Configure replicação off-site, retenção
imutável e um exercício trimestral de restore em outro cluster.

## Teste de carga

```bash
python scripts/load_test.py \
  --api-key "$OBSERVA_API_KEY" \
  --requests 1000 \
  --concurrency 25 \
  --max-error-rate 0.01 \
  --max-p95-ms 750
```

Execute contra uma tenancy sintética, nunca contra ações de desligamento reais.
O script retorna código diferente de zero quando o erro ou p95 ultrapassa o SLO.
Para volume distribuído, execute-o de múltiplos runners e monitore CPU, memória,
I/O do volume e saturação do banco.

## Homologação em clouds reais

O workflow `Live connector smoke test` usa um GitHub Environment chamado
`live-connectors`. Configure nele:

- `OBSERVA_LIVE_URL` e `OBSERVA_LIVE_API_KEY`.
- `OBSERVA_LIVE_CONNECTOR_PAYLOAD`, JSON com `config` e `secrets`.

O job chama somente `/api/connections/test`; não persiste a credencial. Crie uma
conta de homologação com menor privilégio e execute um conector por vez. Depois,
faça uma sincronização controlada pela UI e valide custos, recursos e escopo da
tenancy antes de habilitar automações.

## Releases

### CLI

1. Configure Trusted Publishing do projeto `observa-cli` no PyPI para o workflow
   `release-cli.yml` e environment `pypi`.
2. Atualize a versão em `apps/cli/pyproject.toml`.
3. Crie uma tag `cli-vX.Y.Z`.
4. Instale o artefato publicado em uma máquina limpa e execute `observa --help`.

### Mobile

1. Execute `eas init` em `apps/mobile` e substitua `SET_WITH_EAS_INIT`.
2. Configure `EXPO_TOKEN` e as credenciais Apple/Google no EAS.
3. Rode manualmente `Build and submit mobile` primeiro com `submit=false`.
4. Valide o build em distribuição interna.
5. Só depois rode com `submit=true` e conclua revisão, privacidade e ficha das lojas.

## Pentest e go-live

Antes do go-live, uma equipe independente deve testar autenticação, autorização
entre companies/tenancies, SSRF nos conectores, armazenamento de segredos,
injeção, supply chain, rate limiting distribuído e fluxos de aprovação. Corrija
achados críticos/altos, repita o teste e guarde o relatório fora do repositório.

O aceite final também exige: restore testado em outro ambiente, observabilidade
do próprio Observa, runbooks de incidente, contatos de plantão, RPO/RTO aprovados,
termos de retenção de dados e revisão dos adapters específicos do cliente.
