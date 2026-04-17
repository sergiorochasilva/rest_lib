# [DTO](src/rest_lib/dto/dto_base.py)
`DTOBase` é uma classe abstrata que representa um Data Transfer Object (DTO) usado para transferir dados entre a camada de apresentação e a camada de serviço de uma aplicação. É especialmente útil em operações onde uma entidade de banco de dados precisa ser convertida em um formato adequado para interações com a interface do usuário.

## Atributos:
- `resume_fields: Set[str]` - Conjunto de campos que devem ser incluídos na visualização resumida do DTO.
- `partition_fields: Set[str]` - Conjunto de campos utilizados para particionamento de dados.
- `fields_map: Dict[str, DTOField]` - Dicionário mapeando nomes de atributos do DTO para configurações de campos correspondentes.
- `list_fields_map: dict` - Dicionário mapeando nomes de atributos do DTO para configurações de campos de lista.
- `field_filters_map: Dict[str, DTOFieldFilter]` - Dicionário mapeando nomes de atributos do DTO para configurações de filtros de campo.
- `pk_field: str` - Nome do campo chave primária na entidade associada ao DTO.
- `fixed_filters: Dict[str, Any]` - Dicionário contendo filtros fixos que devem ser aplicados ao recuperar dados da base de dados.
- `conjunto_type: ConjuntoType` - Tipo de conjunto utilizado para junções de dados relacionados.
- `conjunto_field: str` - Nome do campo utilizado para junções de dados relacionados.
- `escape_validator: bool` - Indica se a validação de dados deve ser ignorada.
- `uniques: Dict[str, Set[str]]` - Dicionário mapeando nomes de campos únicos para um conjunto de valores únicos.
- `candidate_keys: List[str]` - Lista de nomes de campos que juntos formam uma chave candidata única.
- `etag_fields: Set[str]` - Conjunto de campos usados para gerar o ETag em GET unitario.
- `etag_type: Literal["RAW", "DATE", "HASH"]` - Tipo de ETag usado na comparacao e geracao do header.

## Métodos:
- `__init__(self, entity: Union[EntityBase, dict] = None, escape_validator: bool = False, generate_default_pk_value: bool = True, **kwargs)` -> None: Construtor da classe DTOBase que inicializa um objeto DTOBase com base em uma entidade ou um dicionário de dados, permitindo determinar se a validação deve ser ignorada e se o valor da PK deve ser gerado se não for fornecido.
- `convert_to_entity(self, entity_class: EntityBase, none_as_empty: bool = False)` -> EntityBase - Converte o DTO para uma instância da entidade associada.
- `convert_to_dict(self, fields: Dict[str, List[str]] = None, just_resume: bool = False)` -> Dict - Converte o DTO para um dicionário, permitindo especificar campos para inclusão e se deve ser uma visualização resumida.
