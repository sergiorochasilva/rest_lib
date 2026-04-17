### [EntityBase](src/rest_lib/entity/entity_base.py)
`EntityBase` é uma classe abstrata genérica para representar entidades no banco de dados. Ele fornece um modelo flexível para criar classes de entidade específicas. As subclasses devem herdar desta classe e implementar os métodos para configurar os detalhes da tabela no banco de dados.

<!-- #### Atributos:

- `fields_map (dict)`: Um dicionário que mapeia os nomes dos campos da entidade.
- `table_name (str)`: O nome correspondente da tabela no banco de dados.
- `default_order_fields (List[str])`: Uma lista de campos para ordenação em consultas.
- `pk_field (str)`: O nome do campo que representa a chave primária da entidade. -->

#### Métodos

- `get_table_name(self) -> str`: Método que deve ser implementado pela subclasse para retornar o nome da tabela associada à entidade no banco de dados.

- `get_default_order_fields(self) -> List[str]`: Método que deve ser implementado pela subclasse para retornar uma lista de campos para ordenação padrão quando não for especificada uma ordenação personalizada.

- `get_pk_field(self) -> str`: Método que deve ser implementado pela subclasse para retornar o nome do campo chave primária na tabela do banco de dados.

- `get_fields_map(self) -> dict`: Método que deve ser implementado pela subclasse para retornar um dicionário mapeando nomes de atributos para nomes de campos no banco de dados. 

- `get_insert_returning_fields(self) -> List[str]`: Método que pode ser implementado pela subclasse para retornar uma lista de campos que devem ser retornados após uma operação de inserção no banco de dados.

- `get_update_returning_fields(self) -> List[str]`: Método que pode ser implementado pela subclasse para retornar uma lista de campos que devem ser retornados após uma operação de atualização no banco de dados.


**Exemplo:**
TODO: Adicionar uso do decorator

```
from rest_lib.entity.entity_base import EntityBase

class ClienteEntity(EntityBase):
    id: str
    estabelecimento: str
    cliente: str

    def __init__(self) -> None:
        self.id: str = None
        self.estabelecimento: str = None
        self.cliente: str = None

    def get_table_name(self) -> str:
        return 'cliente'

    def get_pk_field(self) -> str:
        return 'id'

    def get_default_order_fields(self) -> List[str]:
        return ['estabelecimento', 'cliente', 'id']

    def get_fields_map(self) -> dict: #rever
        return {
            "estabelecimento": "estabelecimento",
            "cliente": "cliente"
        }
```
