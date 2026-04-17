# Como implementamos telemetria de uso das APIs Nasajon?

## O que é telemetria e por que usamos?

Telemetria é a coleta automática de dados sobre o uso dos sistemas. Esses dados ajudam a responder perguntas essenciais para o negócio e o desenvolvimento, tais como:

- **Quantificar o uso de cada rota** (quantas requisições cada rota recebeu).
- **Identificar quem mais consome** (clientes com maior volume de chamadas em determinada API).
- **Destacar APIs mais críticas** (as que mais recebem requisições ou são essenciais para o negócio).
- **Priorizar melhorias e evoluções nas funcionalidades** (focar onde há mais demanda).
- **Viabilizar cobrança por faixa de uso** (criar planos baseados no volume de requisições).

Com esses dados, conseguimos tomar decisões técnicas e comerciais baseadas em métricas confiáveis e reais.

## Como funciona (nossa arquitetura)?

A telemetria da Nasajon segue os padrões da ferramenta **OpenTelemetry**, porém simplificada através da nossa própria biblioteca interna **RestLib**.

Você pode ver a especificação arquitetura aprovada [aqui](https://github.com/Nasajon/Arquitetura/blob/master/RFCs/aprovados/telemetria_web.md).

### Processo detalhado:

1. Você decora uma rota da API utilizando um decorator especial (`@OpenTelemetry`).
2. A biblioteca extrai automaticamente dados da requisição HTTP.
3. Esses dados se tornam métricas etiquetadas (labels).
4. As métricas são enviadas a um contador do OpenTelemetry.
5. Os dados coletados ficam disponíveis para consulta pelo Prometheus e Grafana.

---

## Como implementar na prática?

### 1. Importe o decorator:
```
from rest_lib.decorator.opentelemetry import OpenTelemetry
```
### 2. Decorar a rota da sua API:
Exemplo completo com DTO:
```
@application.route(LIST_POST_ROUTE, methods=['GET'])
@OpenTelemetry(
    dto_class=ClienteDTO,                        # DTO que define campos extras para métricas
    route=LIST_POST_ROUTE,                       # Rota sendo monitorada
    metric_name="cliente",                       # Nome da métrica
    counter_name="cliente",                      # Nome do contador
    description_counter="requisições clientes",  # Descrição (opcional)
)
@ListRoute(
    url=LIST_POST_ROUTE,
    http_method='GET',
    dto_class=ClienteDTO,
    entity_class=ClienteEntity
)
def get_clientes(request, response):
    return response
```

Exemplo completo sem DTO (uso básico):
```
@application.route(GET_ROUTE, methods=['GET'])
@OpenTelemetryBase(
    route=GET_ROUTE,
    metric_name="ping",
    counter_name="ping",
)
def get_ping():
    return (json_dumps({"msg": "Pong!"}), 200, {})
```

## Dados coletados:

| Label               | Descrição                                       |
|---------------------|-------------------------------------------------|
| `route`             | Rota acessada na API                            |
| `method`            | Método HTTP (GET, POST, PUT, DELETE, etc.)      |
| `status_code`       | Código HTTP da resposta                         |
| `tenant`            | Campo padrão para identificação do tenant, mas pode ser renomeado para outro campo personalizado                   |
| `grupo_empresarial` | Campo padrão indicando o grupo empresarial, também pode ser renomeado para outro campo personalizado     |
| `time_grouping`     | Agrupamento temporal, o qual utiliza, por padrão, a semana do ano, pode ser alterado para o mês do ano              |

## Como coletar campos extras?

Para coletar campos personalizados, use o parâmetro `metric_label=True` no DTO, exemplo:
```
class ClienteDTO(DTOBase):
    cliente: str = DTOField(..., metric_label=True)
```
Os campos marcados com `metric_label=True` são extraídos automaticamente pelo decorator e incluídos nas métricas geradas.
