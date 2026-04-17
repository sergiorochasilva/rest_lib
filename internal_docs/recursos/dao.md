# [DAO](src/rest_lib/dao/dao_base.py)

`DAOBase` é uma classe genérica que serve como um Data Access Object (DAO) para simplificar o processo de interação com o banco de dados.

**Em geral, o usuário do RestLib não precisa se preocupar em escrever DAOs diretamente (ou mesmo customizá-los).**

## Métodos:
- `__init__`(self, db: DBAdapter2, entity_class: EntityBase) -> None: Construtor da classe DAOBase. Inicializa um objeto DAOBase com uma instância de DBAdapter2 e uma classe de entidade (EntityBase) associada.

- `begin(self)` -> None: Inicia uma nova transação no banco de dados.

- `commit(self)` -> None: Realiza commit na transação corrente no banco de dados, se houver uma transação em andamento. Não gera erro se não houver uma transação.

- `rollback(self)` -> None: Realiza rollback na transação corrente no banco de dados, se houver uma transação em andamento. Não gera erro se não houver uma transação.

- `in_transaction(self)` -> bool: Verifica se há uma transação em andamento no DBAdapter. Retorna True se houver uma transação, caso contrário, retorna False.

- `get(self, key_field: str, id: uuid.UUID, fields: List[str] = None, filters: Dict[str, List[Filter]] = None, conjunto_type: ConjuntoType = None, conjunto_field: str = None)` -> EntityBase: Retorna uma instância de entidade com base no seu ID. Aceita parâmetros opcionais para especificar campos específicos, filtros adicionais ou junções de conjuntos.

- `list(self, after: uuid.UUID, limit: int, fields: List[str], order_fields: List[str], filters: Dict[str, List[Filter]], conjunto_type: ConjuntoType = None, conjunto_field: str = None)` -> List[EntityBase]: Retorna uma lista paginada de entidades. Aceita parâmetros para especificar a partir de qual registro (after) começar a paginar, o número máximo de registros (limit), campos a serem incluídos, campos pelos quais ordenar (order_fields), filtros adicionais e junções de conjuntos.

- `insert_relacionamento_conjunto(self, id: str, conjunto_field_value: str, conjunto_type: ConjuntoType = None)` -> None: Insere um relacionamento com um conjunto para uma entidade específica com base no seu ID e no valor do campo de conjunto. Permite especificar o tipo de conjunto, caso necessário.

- `delete_relacionamento_conjunto(self, id: str, conjunto_type: ConjuntoType = None)` -> None: Remove um relacionamento com um conjunto para uma entidade específica com base no seu ID. Permite especificar o tipo de conjunto, caso necessário.

- `insert(self, entity: EntityBase)` -> EntityBase: Insere um objeto de entidade no banco de dados. Retorna a entidade inserida com os dados atualizados, incluindo a chave primária, se for gerada automaticamente pelo banco de dados.

- `update(self, key_field: str, key_value: Any, entity: EntityBase, filters: Dict[str, List[Filter]], partial_update: bool = False)` -> EntityBase: Atualiza um objeto de entidade no banco de dados com base no campo de chave, valor de chave, filtros e entidade fornecidos. Permite a opção partial_update para atualização parcial de campos. Retorna a entidade atualizada com os dados mais recentes do banco de dados.

- `list_ids(self, filters: Dict[str, List[Filter]])` -> Optional[List[Any]]: Lista os IDs das entidades que correspondem aos filtros fornecidos. Retorna uma lista de IDs ou None se não houver correspondência.

- `delete(self, filters: Dict[str, List[Filter]])` -> None: Exclui registros do banco de dados com base nos filtros fornecidos. Gera uma exceção NotFoundException se nenhum registro for encontrado para exclusão.

- `is_valid_uuid(self, value)` -> bool: Verifica se um valor é um UUID válido.
