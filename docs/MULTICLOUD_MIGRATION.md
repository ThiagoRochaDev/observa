# Simulador de custo de migração multicloud

O Observa compara o custo mensal estimado de workloads equivalentes em AWS, Google Cloud,
Microsoft Azure e Oracle Cloud Infrastructure (OCI). A simulação pode partir de um recurso
descoberto, um produto, uma conta/cloud inteira ou uma arquitetura informada manualmente.

## Objetivo e segurança

- Normalizar consumo de compute, Kubernetes, container serverless, banco, load balancer, object
  storage e cache.
- Mapear cada componente para serviço e SKU equivalente de cada cloud.
- Expor todas as fórmulas, unidades e preços usados no cálculo.
- Comparar a estimativa com o custo observado nos últimos 30 dias, quando disponível.
- Salvar cenários dentro da tenancy ativa, sem compartilhar dados com outra empresa ou tenancy.
- Nunca executar uma migração ou alterar infraestrutura a partir do simulador.

Em produção, `MIGRATION_PRICING_MODE=official` torna obrigatório consultar e rastrear os catálogos
oficiais. O cálculo falha se algum provider, categoria ou métrica não possuir SKU mapeado; nunca há
fallback silencioso. Em desenvolvimento, `official_preferred` tenta o catálogo oficial e identifica
visivelmente qualquer fallback para o catálogo de referência.

As fontes suportadas são AWS Price List Bulk API, Google Cloud Billing Catalog API, Azure Retail
Prices API e OCI Public List Pricing API. Cada resultado oficial grava região, SKU/meter, unidade,
vigência, URL da fonte, `fetched_at` e `expires_at`. O cache padrão é de 24 horas e pode ser
renovado manualmente.

- AWS: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api.html
- GCP: https://cloud.google.com/billing/v1/how-tos/catalog-api
- Azure: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices
- OCI: https://docs.oracle.com/en-us/iaas/Content/Billing/Tasks/signingup_topic-Estimating_Costs.htm#Accessing_List_Pricing_for_OCI_Products

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
8. Marque **Exigir somente preços oficiais** para impedir fallback e use **Atualizar catálogos
   oficiais** para renovar o cache.

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

Comparar apenas AWS e Oracle Cloud com compromisso de 12 meses:

```powershell
python -m observa_cli.main migration estimate --scope account --value all --target aws --target oci --commitment 12
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
| `GET` | `/api/migration/pricing/config` | Regiões e status dos mapeamentos oficiais |
| `PUT` | `/api/migration/pricing/config` | Salva regiões e mapeamentos SKU; exige admin |
| `POST` | `/api/migration/pricing/refresh` | Atualiza preços e metadados oficiais |
| `POST` | `/api/migration/estimate` | Simulação sem persistência |
| `GET` | `/api/migration/scenarios` | Cenários da tenancy atual |
| `POST` | `/api/migration/scenarios` | Simula e salva; exige operator |
| `DELETE` | `/api/migration/scenarios/{id}` | Exclui; exige operator |

Todas as rotas exigem API key e contexto de company/tenancy. O banco de cada tenancy é separado
fisicamente pela camada de persistência do Observa.

## Configuração oficial de produção

Defina no runtime:

```dotenv
ENVIRONMENT=production
MIGRATION_PRICING_MODE=official
MIGRATION_PRICING_CACHE_HOURS=24
GCP_BILLING_CATALOG_API_KEY=<secret-manager>
```

Configure os SKUs exatos por tenancy com `PUT /api/migration/pricing/config`. O mapeamento associa
cada métrica normalizada a um identificador oficial. AWS requer `service_code`, `sku` e `unit`; GCP
requer `service_id` e `sku_id`; Azure aceita `meterId`, `skuId` ou a combinação exata de campos da
Retail Prices API; OCI requer `part_number` e aceita `model` (padrão `PAY_AS_YOU_GO`) e
`range_min` para preços em faixa. `multiplier` converte a unidade oficial para a unidade
normalizada quando preciso. Na OCI, use-o explicitamente quando um preço em OCPU precisar ser
normalizado para vCPU; para a maioria dos produtos x86, 1 OCPU equivale a 2 vCPUs.

```json
{
  "regions": {"aws":"sa-east-1","gcp":"southamerica-east1","azure":"brazilsouth","oci":"sa-saopaulo-1"},
  "mappings": {
    "azure": {
      "load_balancer": {
        "service": "Azure Load Balancer",
        "sku": "Standard",
        "metrics": {
          "lb_hour": {"meterId":"<METER_ID_OFICIAL>","multiplier":1}
        }
      }
    },
    "gcp": {
      "serverless_container": {
        "service": "Cloud Run",
        "sku": "regional",
        "metrics": {
          "vcpu_hour": {"service_id":"<SERVICE_ID>","sku_id":"<SKU_ID>"}
        }
      }
    },
    "aws": {
      "compute": {
        "service": "Amazon EC2",
        "sku": "m6i.large",
        "metrics": {
          "instance_hour": {"service_code":"AmazonEC2","sku":"<SKU>","unit":"Hrs"}
        }
      }
    },
    "oci": {
      "load_balancer": {
        "service": "OCI Load Balancer",
        "sku": "Flexible Load Balancer",
        "metrics": {
          "lb_hour": {"part_number":"<B_PART_NUMBER_OFICIAL>","model":"PAY_AS_YOU_GO","multiplier":1}
        }
      }
    }
  }
}
```

A API pública da OCI retorna preço de lista global em USD por B Part Number e não publica uma
data de vigência nesse payload; por isso, `effective_at` fica vazio e `fetched_at` registra a coleta. O Observa mantém
`sa-saopaulo-1` no resultado para registrar a região de destino da simulação, mas não inventa um
ajuste regional quando o catálogo público não o fornece. Configure todos os B Part Numbers usados
pelas métricas da arquitetura; em modo oficial, qualquer ausência encerra o cálculo com erro.

Os IDs devem ser obtidos do catálogo da conta/região alvo e revisados quando a arquitetura mudar.
Descontos privados não aparecem nos catálogos públicos; para eles, importe uma tabela contratual
aprovada como evolução do adapter, mantendo a mesma trilha de origem e vigência.

O modo oficial não aplica percentuais presumidos de compromisso. Nesta versão, selecionar 12 ou
36 meses preserva o preço do SKU mapeado e exibe um aviso. Para comparar reservas/savings plans,
cadastre cenários separados com os SKUs oficiais do termo correspondente.

## Evolução para preços contratuais

Os catálogos públicos oficiais já são suportados. O próximo nível é integrar AWS Private Pricing,
Google Cloud Pricing API vinculada à billing account, exports Azure e rate cards contratuais OCI.
Essas fontes devem sobrescrever somente SKUs correspondentes e manter origem, vigência e auditoria.
