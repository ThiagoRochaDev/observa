# Simulador de custo de migração multicloud

O Observa compara o custo mensal estimado de workloads equivalentes em AWS, Google Cloud e
Microsoft Azure. A simulação pode partir de um recurso descoberto, um produto, uma conta/cloud
inteira ou uma arquitetura informada manualmente.

## Objetivo e segurança

- Normalizar consumo de compute, Kubernetes, container serverless, banco, load balancer, object
  storage e cache.
- Mapear cada componente para serviço e SKU equivalente de cada cloud.
- Expor todas as fórmulas, unidades e preços usados no cálculo.
- Comparar a estimativa com o custo observado nos últimos 30 dias, quando disponível.
- Salvar cenários dentro da tenancy ativa, sem compartilhar dados com outra empresa ou tenancy.
- Nunca executar uma migração ou alterar infraestrutura a partir do simulador.

O catálogo embutido `observa-reference-2026.10-v1` é deliberadamente identificado como
**referência**. Ele não substitui Pricing Calculator, catálogo oficial, contrato privado, impostos,
free tier, suporte, spot/preemptible, região, alta disponibilidade ou custo operacional da migração.

## Escopos

| Escopo | Entrada | Comportamento |
|---|---|---|
| Recurso | UID do inventário | Usa tipo e labels do recurso para inferir consumo |
| Produto | Slug do produto | Agrupa todos os recursos mapeados ao produto |
| Conta/cloud | `all`, provider, account, project ou subscription | Agrupa recursos compatíveis na tenancy |
| Arquitetura | Componentes e consumo | Permite estudar uma solução ainda não inventariada |

Quando labels como `vcpu`, `memory_gb`, `storage_gb`, `hours` e `egress_gb` não estão disponíveis,
o Observa aplica defaults editáveis e reduz a confiança do resultado. O aviso aparece na resposta.

## Interface web

1. Abra **FinOps e catálogo → Migração multicloud**.
2. Escolha **Recurso**, **Produto**, **Conta / cloud** ou **Arquitetura**.
3. Para uma arquitetura, adicione componentes e edite o consumo mensal em JSON.
4. Marque as clouds de destino, moeda, câmbio e compromisso de 0, 12 ou 36 meses.
5. Clique em **Comparar custos**.
6. Expanda cada serviço para conferir SKU, unidades, preço unitário e fórmula.
7. Informe um nome e clique em **Salvar cenário** para manter a análise na tenancy atual.

Exemplo de arquitetura LB + Cloud Run equivalente + bucket:

```json
[
  {"name":"Load balancer público","category":"load_balancer","usage":{"hours":730,"processed_gb":500}},
  {"name":"API serverless","category":"serverless_container","usage":{"vcpu":2,"memory_gb":4,"active_hours":220,"requests_million":15,"egress_gb":80}},
  {"name":"Bucket de arquivos","category":"object_storage","usage":{"storage_gb":750,"operations_10k":120,"egress_gb":90}}
]
```

## CLI

Use a API key e o contexto organizacional correto:

```powershell
$env:OBSERVA_API_KEY = (Get-Content data/api_key -Raw).Trim()
$env:OBSERVA_COMPANY_ID = "cmp_default"
$env:OBSERVA_TENANCY_ID = "tnt_default"
cd apps/cli
```

Comparar um produto:

```powershell
python -m observa_cli.main migration estimate --scope product --value observa
```

Comparar apenas AWS e Azure com compromisso de 12 meses:

```powershell
python -m observa_cli.main migration estimate --scope account --value all --target aws --target azure --commitment 12
```

Salvar uma arquitetura customizada:

```powershell
python -m observa_cli.main migration estimate --scope custom --architecture arquitetura.json --save "LB API Bucket"
python -m observa_cli.main migration scenarios
python -m observa_cli.main migration delete <SCENARIO_ID>
```

## API

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/api/migration/catalog` | Catálogo, categorias, rates e defaults |
| `POST` | `/api/migration/estimate` | Simulação sem persistência |
| `GET` | `/api/migration/scenarios` | Cenários da tenancy atual |
| `POST` | `/api/migration/scenarios` | Simula e salva; exige operator |
| `DELETE` | `/api/migration/scenarios/{id}` | Exclui; exige operator |

Todas as rotas exigem API key e contexto de company/tenancy. O banco de cada tenancy é separado
fisicamente pela camada de persistência do Observa.

## Evolução para preços oficiais

O contrato de cálculo já separa catálogo, consumo normalizado e resultado. Adapters futuros podem
importar AWS Price List, Google Cloud Billing Catalog, Azure Retail Prices e tabelas privadas do
cliente sem mudar os escopos ou a interface. A versão do catálogo usada fica gravada no cenário
para garantir auditabilidade e permitir recálculo posterior.
