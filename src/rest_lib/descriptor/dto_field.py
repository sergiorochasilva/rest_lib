import typing
import uuid

from decimal import Decimal
from typing import Any

from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.util.type_validator_util import TypeValidatorUtil


class DTOFieldFilter:
    def __init__(
        self, name: str = None, operator: FilterOperator = FilterOperator.EQUALS
    ):
        self.name = name
        self.operator = operator
        self.field_name = None

    def set_field_name(self, field_name: str):
        self.field_name = field_name


class DTOAutoIncrementField:
    def __init__(
        self,
        sequence_name: typing.Union[str, None],
        template: typing.Union[str, None],
        group: typing.Union[typing.List[str], None],
        start_value: typing.Union[int, None] = 1,
        db_managed: typing.Union[bool, None] = False,
    ):
        self.sequence_name = sequence_name
        self.template = template
        self.group = group
        self.start_value = start_value
        self.db_managed = db_managed

        if db_managed:
            self.sequence_name = None
            self.template = None
            self.group = None
            self.start_value = None
        else:
            if not sequence_name:
                raise ValueError(
                    "sequence_name must be provided for auto increment field."
                )
            if not template:
                raise ValueError("template must be provided for auto increment field.")
            if not group or len(group) == 0:
                raise ValueError(
                    "group must contain at least one field for auto increment field."
                )


class DTOField:
    _ref_counter = 0

    description: str

    def __init__(
        self,
        type: object = None,
        not_null: bool = False,
        resume: bool = False,
        min: int = None,
        max: int = None,
        validator: typing.Callable = None,
        strip: bool = False,
        entity_field: str = None,
        filters: typing.List[DTOFieldFilter] = None,
        pk: bool = False,
        use_default_validator: bool = True,
        default_value: typing.Union[typing.Callable, typing.Any] = None,
        partition_data: bool = False,
        convert_to_entity: typing.Callable = None,
        convert_from_entity: typing.Callable = None,
        unique: str = None,
        candidate_key: bool = False,
        search: bool = True,
        read_only: bool = False,
        no_update: bool = False,
        metric_label: bool = False,
        auto_increment: dict[str, any] = {},
        description: str = "",
        use_integrity_check: bool = True,
        insert_function_field: str = None,
        update_function_field: str = None,
        convert_to_function: typing.Callable = None,
        get_function_field: str = None,
        delete_function_field: str = None,
    ):
        """
        -----------
        Parameters:
        -----------

        - type: Tipo esperado para a propriedade. Se for do tipo enum.Enum, o valor recebido, para atribuição à propriedade, será convertido para o enumerado.

        - not_null: O campo não poderá ser None, ou vazio, no caso de strings.

        - resume: O campo será usado como resumo, isto é, será sempre rotornado num HTTP GET que liste os dados (mesmo que não seja solicitado por meio da query string "fields").

        - min: Menor valor permitido (ou menor comprimento, para strings).

        - max: Maior valor permitido (ou maior comprimento, para strings).

        - validator: Função que recebe o valor (a ser atribuído), e retorna o mesmo valor após algum tipo de tratamento (como adição ou remoção, automática, de formatação).

        - strip: O valor da string sofrerá strip (remoção de espaços no início e no fim), antes de ser guardado (só é útil para strings).

        - entity_field: Nome da propriedade equivalente na classe de entity (que reflete a estruturua do banco de dados).

        - insert_function_field: Nome do campo correspondente no InsertFunctionType utilizado para inserts por função (default: o próprio nome do campo no DTO).

        - update_function_field: Nome do campo correspondente no UpdateFunctionType utilizado para updates por função (default: herdado de insert_function_field ou o próprio nome do campo no DTO).

        - get_function_field: Nome do campo correspondente no Get/ListFunctionType utilizado para consultas por função (default: o próprio nome do campo no DTO).

        - delete_function_field: Nome do campo correspondente no DeleteFunctionType utilizado para exclusões por função (default: o próprio nome do campo no DTO).

        - filters: Lista de filtros adicionais suportados para esta propriedade (adicionais, porque todos as propriedades, por padrão, suportam filtros de igualdade, que podem ser passados por meio de uma query string, com mesmo nome da proriedade, e um valor qualquer a ser comparado).
            Essa lista de filtros consiste em objetos do DTOFieldFilter (veja a documentação da classe para enteder a estrutura de declaração dos filtros).

        - pk: Flag indicando se o campo corresponde à chave da entidade corresponednte.

        - use_default_validator: Flag indicando se o validator padrão deve ser aplicado à propriedade (esse validator padrão verifica o tipo de dados passado, e as demais verificações recebidas no filed, como, por exemplo, valor máximo, mínio, not_null, etc).

        - default_value: Valor padrão de preenchimento da propriedade, caso não se receba conteúdo para a mesma (podendo ser um valor estático, ou uma função a ser chamada no preenchimento).

        - partition_data: Flag indicando se esta propriedade participa dos campos de particionamento da entidade, isto é, campos sempre usados nas queries de listagem gravação dos dados, inclusíve para recuperação de entidades relacionadas.

        - convert_to_entity: Função para converter o valor contido no DTO, para o(s) valor(es) a serem gravados no objeto de entidade (durante a conversão). É útil para casos onde não há equivalência um para um entre um campo do DTO e um da entidade.
            (por exemplo, uma chave de cnpj que pode ser guardada em mais de um campo do BD). Outro caso de uso, é quando um campo tem formatação diferente entre o DTO e a entidade, carecendo de conversão customizada.
            A função recebida deve suportar os parâmetros (dto_value: Any, dto: DTOBase), e retornar um Dict[str, Any], como uma coleção de chaves e valores a serem atribuídos na entidade.

        - convert_to_function: Função para converter o valor do DTO antes de popular o InsertFunctionType. Recebe (value_do_campo, dict_com_valores_do_dto) e deve retornar um dicionário cujas chaves são os campos do InsertFunctionType e os valores correspondentes (permite mapear/derivar múltiplos campos). Se None, o valor é copiado diretamente.

        - convert_from_entity: Função para converter o valor contido na Entity, para o(s) valor(es) a serem gravados no objeto DTO (durante a conversão). É útil para casos onde não há equivalência um para um entre um campo do DTO e um da entidade
            (por exemplo, uma chave de cnpj que pode ser guardada em mais de um campo do BD). Outro caso de uso, é quando um campo tem formatação diferente entre o DTO e a entidade, carecendo de conversão customizada.
            A função recebida deve suportar os parâmetros (entity_value: Any, entity_fields: Dict[str, Any]), e retornar um Dict[str, Any], como uma coleção de chaves e valores a serem atribuídos no DTO.

        - unique: Permite indicar um nome de chave de unicidade. Cada chave de unicidade é considerada no momento de uma inserção no BD (impedindo duplicações indesejadas).

        - candidate_key: Permite indicar que este campo se trata de uma chave candidata (útil para operações unitárias, como GTE e DELETE, pois estas irão verificar se o tipo do dado recebido bate com a PK, ou com as chaves candidatas, para resolver como fará a query).

        - search: Indica que esse campo é passível de busca, por meio do argumento "search" passado num GET List, como query string (por hora, apenas pesquisas simples, por meio de operador like, estão implementadas).

        - read_only: Permite declarar propriedades que estão disponíveis no GET (list ou unitário), mas que não poderão ser usadas para gravação (POST, PUT ou PATCH).

        - no_update: Permite declarar propriedades que estão disponíveis no GET e POST, mas que não poderão ser usadas para atualização (PUT ou PATCH). Este campo é ignorado em upsert.

        - metric_label: Permite indicar quais campos serão enviados como métricas para o OpenTelemetry Collector.

        - auto_increment: Dicionário para controle de campos com auto incremento de valores. O padrão do dicionário é:
            {
                "sequence_name": "NOME_DA_SEQUENCIA",
                "template": "{seq}",
                "group": ["field1", "field2", ...],
                "start_value": 1,
                "db_managed": False
            }

            Onde:
                - "sequence_name": Nome da sequência de auto incremento (que será combinado com os campos de agrupamento, mas serve para impedir conflito com outras sequências num mesmo DTO).
                - "template": Indica o formato padrão do campo que sofrerá o auto incremento; seguindo o padrão do python, e, podendo conter:
                  - Qualquer coisa fixa.
                  - Placeholder "{seq}" (que controla onde entrará a numeração automática)
                  - Qualquer outro nome de DTOField, passado como placeholder, para substituição automatica.
                  - Como segue o padrão python, sintaxes como "{seq:04d}" são aceitas (formatando, no exemplo, o número com 4 dígitos, e zeros à esquerda).
                - "group": Indica a lista de campos utilizados para resolver o próximo número da sequencia de autoincremento (o próximo número será o maior do grupo + 1).
                - Para que esse tipo de comportamento funcione corretamente, é necessário que a variável de ambiente "REST_LIB_AUTO_INCREMENT_TABLE" seja declarada com o nome da tabela de controle do auto incremento, a qual deve seguir o DDL:
                    CREATE TABLE seq_control (
                        seq_name VARCHAR PRIMARY KEY,
                        current_value INTEGER NOT NULL,
                        unique (seq_name)
                    );
                - Os campos de particionamento de dados sempre entram (automaticamente), no agrupamento de auto incremento.
                - "start_value": Valor inicial da sequência de auto incremento (opcional, default 1).
                - "db_managed": Flag que indica se o auto incremento é gerenciado pelo banco de dados (default False, ou seja, o auto incremento é gerenciado pelo código).
                    Se for True, todas as outras propriedades são ignoradas, porque o valor será gerencia pelo BD (só faz sentido para campos inteiros).
        - description: Descrição deste campo na documentação.

        - use_integrity_check: Se o campo deve ser usado na geração de hash de registro para a api de verificação de integridade (ver IntegrityCheckRoute).
        """
        self.name = None
        self.description = description
        self.expected_type = type
        self.not_null = not_null
        self.resume = resume
        self.min = min
        self.max = max
        self.validator = validator
        self.strip = strip
        self.entity_field = entity_field
        self.insert_function_field = insert_function_field
        self.update_function_field = update_function_field
        self.get_function_field = get_function_field
        self.delete_function_field = delete_function_field
        self.filters = filters
        self.pk = pk
        self.use_default_validator = use_default_validator
        self.default_value = default_value
        self.partition_data = partition_data
        self.convert_to_entity = convert_to_entity
        self.convert_to_function = convert_to_function
        self.convert_from_entity = convert_from_entity
        self.unique = unique
        self.candidate_key = candidate_key
        self.search = search
        self.read_only = read_only
        self.no_update = no_update
        self.metric_label = metric_label

        self.auto_increment = None
        if auto_increment:
            start_value = auto_increment.get("start_value", 1)
            self.auto_increment = DTOAutoIncrementField(
                sequence_name=auto_increment.get("sequence_name"),
                template=auto_increment.get("template", "{seq}"),
                group=auto_increment.get("group"),
                start_value=start_value,
                db_managed=auto_increment.get("db_managed", False),
            )

        self.use_integrity_check = use_integrity_check

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        try:
            if self.validator is None:
                if self.use_default_validator:
                    value = self.validate(self, value, instance)
            else:
                if self.use_default_validator:
                    value = self.validate(self, value, instance)
                try:
                    value = self.validator(self, value, instance)
                except TypeError:
                    value = self.validator(self, value)
        except ValueError as e:
            if not (
                "escape_validator" in instance.__dict__
                and instance.__dict__["escape_validator"] == True
            ):
                raise

        instance.__dict__[self.storage_name] = value

    def validate(self, dto_field: "DTOField", value, instance):
        """
        Default validator (ckecking default constraints: not null, type, min, max and enum types).
        """

        # Checking not null constraint
        if (
            self.not_null
            and (
                value is None
                or (
                    isinstance(value, str)
                    and len(value.strip() if dto_field.strip else value) <= 0
                )
            )
            and (
                not dto_field.pk
                or (
                    "generate_default_pk_value" in instance.__dict__
                    and instance.__dict__["generate_default_pk_value"]
                )
            )
        ):
            raise ValueError(f"O campo {self.storage_name} deve estar preenchido.")

        # Checking type constraint
        # TODO Ver como suportar typing
        if (
            self.expected_type is not None
            and not isinstance(value, self.expected_type)
            and value is not None
        ):
            value = TypeValidatorUtil.validate(self, value)

        # Checking min constraint
        if self.min is not None:
            if isinstance(value, str) and (len(value) < self.min):
                raise ValueError(
                    f"O campo {self.storage_name} deve conter no mínimo {self.min} caracteres. Valor recebido: {value}."
                )
            elif (
                isinstance(value, int)
                or isinstance(value, float)
                or isinstance(value, Decimal)
            ) and (value < self.min):
                raise ValueError(
                    f"O campo {self.storage_name} deve ser maior ou igual a {self.min}. Valor recebido: {value}."
                )

        # Checking min constraint
        if self.max is not None:
            if isinstance(value, str) and (len(value) > self.max):
                raise ValueError(
                    f"O campo {self.storage_name} deve conter no máximo {self.max} caracteres. Valor recebido: {value}."
                )
            elif (
                isinstance(value, int)
                or isinstance(value, float)
                or isinstance(value, Decimal)
            ) and (value > self.max):
                raise ValueError(
                    f"O campo {self.storage_name} deve ser menor ou igual a {self.max}. Valor recebido: {value}."
                )

        # Striping strings (if desired)
        if isinstance(value, str) and self.strip:
            value = value.strip()

        return value

    def get_entity_field_name(self) -> str:
        """
        Retorna o nome correspondente do field no entity
        (o qual é o nome do field no DTO por padrão, ou o nome que for
        passado no parâmetro "entity_field" no construtor).
        """

        if self.entity_field is not None:
            return self.entity_field
        else:
            return self.name

    def get_insert_function_field_name(self) -> str:
        """
        Retorna o nome correspondente do field no InsertFunctionType
        (o qual é o nome do field no DTO por padrão, ou o nome que for
        passado no parâmetro "insert_function_field" no construtor).
        """

        if self.insert_function_field is not None:
            return self.insert_function_field
        else:
            return self.name

    def get_update_function_field_name(self) -> str:
        """
        Retorna o nome correspondente do field no UpdateFunctionType, caindo no
        mapeamento de insert (ou no próprio nome do campo) quando não houver
        configuração específica.
        """

        if self.update_function_field is not None:
            return self.update_function_field
        return self.get_insert_function_field_name()

    def get_function_field_name(self, operation: str) -> str:
        if operation in ("get", "list"):
            if self.get_function_field is not None:
                return self.get_function_field
            return self.name
        if operation == "delete":
            if self.delete_function_field is not None:
                return self.delete_function_field
            return self.name
        if operation == "update":
            return self.get_update_function_field_name()
        return self.get_insert_function_field_name()

    def get_metric_labels(dto_class, request, tenant, grupo_empresarial):
        """
        Retorna os campos que possuem metric_label=True,
        incluindo sempre tenant e grupo_empresarial se existirem no DTO.
        """
        metric_fields = {}

        if hasattr(dto_class, tenant):
            metric_fields[tenant] = request.args.get(tenant, "")
        if hasattr(dto_class, grupo_empresarial):
            metric_fields[grupo_empresarial] = request.args.get(grupo_empresarial, "")

        if hasattr(dto_class, "metric_fields"):
            for field_name in dto_class.metric_fields:
                metric_fields[field_name] = request.args.get(field_name, "")

        json_data = request.get_json(silent=True) or {}

        if json_data:
            for field_name in metric_fields:
                if not metric_fields[field_name] and field_name in json_data:
                    metric_fields[field_name] = json_data.get(field_name, "")

        return metric_fields

    def get_null_value(self):
        """
        Retorna o valor nulo esperado para o campo (para quando for necessário representar, no BD,
        com um valor, mas, o campos mesmo assim deve ser entedido como vazio - isso só faz sentido para campos do tipo not_null,
        mas que precisem de um valor a ser ignorado).

        Caso de uso de exemplo: Tabelas de configuração, onde pode-se ter uma configuração global (com valor 0 na coluna tenant),
        e a sobrescreita da mesma configuração por tenant.
        """

        if self.expected_type is None:
            return None
        elif self.expected_type == uuid.UUID:
            return uuid.UUID(int=0)
        elif self.expected_type == str:
            return ""
        elif self.expected_type == int:
            return 0
        elif self.expected_type == float:
            return 0.0
        elif self.expected_type == Decimal:
            return Decimal(0)
        else:
            return None
