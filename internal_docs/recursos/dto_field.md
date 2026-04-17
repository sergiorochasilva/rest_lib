# DTOField
A classe `DTOField` representa uma propriedade de um objeto DTO e define várias configurações para essa propriedade, como tipo esperado, validações, formatações, entre outras. As validações personalizadas são acessadas em [DTOFieldValidators](src/rest_lib/descriptor/dto_field_validators.py). A classe `DTOFieldFilter` representa um filtro que pode ser aplicado a uma propriedade DTO para consultas.

## Parâmetros:
- `type [object = None]`: Tipo esperado para a propriedade. Se for do tipo enum.Enum, o valor recebido será convertido para o enumerado.
- `not_null [bool = False]`: Indica se o campo não pode ser None ou vazio (no caso de strings).
- `resume [bool = False]`: Indica se o campo será usado como resumo, sempre retornado em consultas GET que listam os dados.
- `min [int = None]`: Menor valor permitido (ou menor comprimento, para strings).
- `max [int = None]`: Maior valor permitido (ou maior comprimento, para strings).
- `validator [typing.Callable = None]`: Função que valida o valor da propriedade antes de atribuí-lo.
- `strip [bool = False]`: Indica se espaços no início e no fim de strings devem ser removidos.
- `entity_field [str = None]`: Nome da propriedade equivalente na classe de entidade.
- `filters [typing.List[DTOFieldFilter] = None]`: Lista de filtros adicionais suportados para esta propriedade.
- `pk [bool = False]`: Indica se o campo é a chave primária da entidade.
- `use_default_validator [bool = True]`: Indica se o validador padrão deve ser aplicado à propriedade.
- `default_value [typing.Union[typing.Callable, typing.Any] = None]`: Valor padrão de preenchimento da propriedade, caso não seja fornecido.
- `partition_data [bool = False]`: Indica se esta propriedade participa dos campos de particionamento da entidade.
- `convert_to_entity [typing.Callable = None]`: Função para converter o valor do DTO para o valor da entidade.
- `convert_from_entity [typing.Callable = None]`: Função para converter o valor da entidade para o valor do DTO.
- `unique [str = None]`: Nome de chave de unicidade, usado para evitar duplicações no banco de dados.
- `candidate_key [bool = False]`: Indica se este campo é uma chave candidata.
- `search [bool = True]`: Indica que esse campo é passível de busca, por meio do argumento "search" passado num GET List, como query string (por hora, apenas pesquisas simples, por meio de operador like, estão implementadas).
- `read_only [bool = False]`: Permite declarar propriedades que estão disponíveis no GET (list ou unitário), mas que não poderão ser usadas para gravação (POST, PUT ou PATCH).
- `metric_label [bool = False]`: Permite indicar quais campos serão enviados como métricas para o OpenTelemetry Collector, como padrão sempre será enviado o tenant e grupo_empresarial.

**Exemplo:**
```
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators

cliente: str = DTOField(resume=True, not_null=True, strip=True, min=11, max=60, 
    validator=DTOFieldValidators().validate_cpf_or_cnpj)
criado_em: datetime.datetime = DTOField(
        resume=True,
        filters=[
            DTOFieldFilter('criado_apos', FilterOperator.GREATER_THAN),
            DTOFieldFilter('criado_antes', FilterOperator.LESS_THAN),
        ],
        default_value=datetime.datetime.now
    )
```
