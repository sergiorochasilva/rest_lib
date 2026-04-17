import hashlib
import re
from typing import (
    Callable, Dict, List, Optional, Any, Type, Tuple, Set, Union, Literal
)
import datetime as dt

from rest_lib.controller.controller_util import DEFAULT_RESP_HEADERS
from rest_lib.controller.funtion_route_wrapper import FunctionRouteWrapper
from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import (
    DataOverrideParameterException,
    MissingParameterException,
    PaginationException,
)
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.service.service_base import ServiceBase
from rest_lib.util.fields_util import FieldsTree, parse_fields_expression


class RouteBase:
    """
    # Examplo de SubRotas

    Tendo um DTO Filho:
    ```python
    @DTO
    class FilhoDTO(DTOBAse):
        id: uuid.UUID = DTOField()
        id_pai: uuid.UUID = DTOField()
    ```
    E um DTO Pai:
    ```python
    @DTO
    class PaiDTO(DTOBAse):
        id: uuid.UUID = DTOField()
    ```
    O Controller seria:
    ```python
    @application.route('/pai/<id_pai>/filho/<id>', methods=['GET'])
    @ListRoute(
        url='/pai/<id_pai>/filho/<id>',
        http_method='GET',
        dto_class=FilhoDTO,
        entity_class=FilhoEntity
    )
    def lista_filhos(_, response):
        return response
    ```

    A parte da rota `<id_pai>` deve ser o nome do campo no FilhoDTO que faz FK com o PaiDTO,
    ou seja, se a relação do FilhoDTO com o PaiDTO é feita pelo campo `pai` a rota ficaria:
    `/pai/<pai>/filho/<id>`

    *Observacao*: No momento a subrota apenas suporta o campo FK no FilhoDTO, e nao usando
    o campos candidatos do PaiDTO.

    Se no PaiDTO conter um `DTOListField` pro FilhoDTO
    ```python
    @DTO
    class PaiDTO(DTOBAse):
        id: uuid.UUID = DTOField()
        filhos: ty.List[FilhoDTO] = DTOListField(
            dto_type=FilhoDTO,
            entity_type=FilhoEntity,
            relation_key_field='id',
            related_entity_field='id_pai',
        )
    ```
    No FilhoDTO o campo de relacionamento é desnecessário:
    ```python
    @DTO
    class FilhoDTO(DTOBAse):
        id: uuid.UUID = DTOField()
    ```
    O campo de relacionamento será criado automaticamente, usando o nome passado no
    atributo `related_entity_field`, nesse exemplo o campo de relacionamento teria o nome `id_pai`.

    E em torno na rota ficaria: `/pai/<id_pai>/filho/<id>`
    """

    url: str
    http_method: str
    registered_routes: List["RouteBase"] = []
    function_wrapper: FunctionRouteWrapper

    _injector_factory: NsjInjectorFactoryBase
    _service_name: str
    _handle_exception: Callable
    _dto_class: DTOBase
    _entity_class: EntityBase
    _dto_response_class: DTOBase

    def __init__(
        self,
        url: str,
        http_method: str,
        dto_class: DTOBase,
        entity_class: EntityBase,
        dto_response_class: DTOBase = None,
        injector_factory: NsjInjectorFactoryBase = NsjInjectorFactoryBase,
        service_name: str = None,
        handle_exception: Callable = None,
    ):
        super().__init__()

        self.url = url
        self.http_method = http_method
        self.__class__.registered_routes.append(self)

        self._injector_factory = injector_factory
        self._service_name = service_name
        self._handle_exception = handle_exception
        self._dto_class = dto_class
        self._entity_class = entity_class
        self._dto_response_class = dto_response_class

    def __call__(self, func):
        from rest_lib.controller.command_router import CommandRouter

        # Criando o wrapper da função
        self.function_wrapper = FunctionRouteWrapper(self, func)

        # Registrando a função para ser chamada via linha de comando
        CommandRouter.get_instance().register(
            func.__name__,
            self.function_wrapper,
            self,
        )

        # Retornando o wrapper para substituir a função original
        return self.function_wrapper

    def internal_handle_request(self, *args: Any, **kwargs: Any):
        """
        Centraliza a criação do injector factory e delega para handle_request.
        """

        with self._injector_factory() as factory:
            self.set_injector_factory(factory)
            response = self.handle_request(*args, **kwargs)

        return response

    def set_injector_factory(self, factory: NsjInjectorFactoryBase):
        self._request_injector_factory = factory

    def get_injector_factory(self):
        return getattr(self, "_request_injector_factory", None)

    def _get_service(self, factory: NsjInjectorFactoryBase) -> ServiceBase:
        """
        Return service instance, by service name or using NsjServiceBase.
        """

        if self._service_name is not None:
            return factory.get_service_by_name(self._service_name)
        else:
            return ServiceBase(
                factory,
                DAOBase(factory.db_adapter(), self._entity_class),
                self._dto_class,
                self._entity_class,
                self._dto_response_class,
            )

    @staticmethod
    def parse_fields(dto_class: DTOBase, fields: str) -> FieldsTree:
        """
        Converte a expressão de fields recebida (query string) em uma estrutura
        em árvore, garantindo que os campos de resumo do DTO sejam considerados.
        """

        fields_tree = parse_fields_expression(fields)
        fields_tree["root"] |= dto_class.resume_fields

        return fields_tree

    @staticmethod
    def parse_expands(_dto_class: DTOBase, expands: Optional[str]) -> FieldsTree:
        expands_tree = parse_fields_expression(expands)
        # expands_tree["root"] |= dto_class.resume_expands

        return expands_tree

    @staticmethod
    def parse_if_none_match(header: str) -> List[str]:
        """
        Extrai os valores do header If-None-Match, respeitando aspas e escapes.

        Exemplo:
        >>> RouteBase.parse_if_none_match('"abc", "a\\"b"')
        ['abc', 'a"b']
        >>> RouteBase.parse_if_none_match('"one" , "two" , "three"')
        ['one', 'two', 'three']
        >>> RouteBase.parse_if_none_match('"unterminated')
        []
        >>> RouteBase.parse_if_none_match('W/"weak", "strong"')
        ['weak', 'strong']
        """
        i: int = 0
        header_size: int = len(header)
        ret: List[str] = []
        while i < header_size:
            if header[i] == '"':
                i += 1
                buf: List[str] = []
                while i < header_size:
                    if header[i] == '\\':
                        i += 1
                        if i >= header_size:
                            # NOTE: Checking if header ends with '\'
                            break
                        buf.append(header[i])
                        i += 1
                        continue

                    if header[i] == '"':
                        # NOTE: Append buf here so that if the string is not
                        #           closed we do not add a incomplete value
                        i += 1
                        ret.append(''.join(buf))
                        break

                    buf.append(header[i])
                    i += 1
                    pass
                continue
            i += 1
            # NOTE: Intentionaly ignoring commas and spaces
            pass
        return ret

    @staticmethod
    def quote_and_escape_string(s: str) -> str:
        """
        Envolve a string entre aspas e escapa aspas internas.

        Exemplo:
        >>> RouteBase.quote_and_escape_string('a"b')
        '"a\\"b"'
        >>> RouteBase.quote_and_escape_string('plain')
        '"plain"'
        >>> RouteBase.quote_and_escape_string('')
        '""'
        """
        return '"' + str(s).replace('"', '\\"') + '"'

    @staticmethod
    def parse_filters_and_search(
        dto_class: DTOBase,
        args: Dict[str, Any],
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Extrai filtros e o termo de busca (search) dos argumentos da requisição.

        - ``extra_filters``: dicionário inicial de filtros (ex.: kwargs de rota).
        - Ignora parâmetros de paginação e seleção de campos.
        - Ignora campos de particionamento até que sejam validados abaixo.
        - Levanta ``MissingParameterException`` caso algum campo de particionamento não seja informado.
        """

        filters: Dict[str, Any] = dict(extra_filters or {})
        search_query: Optional[str] = None

        for arg in args:
            if arg.lower() == "search":
                search_query = args.get(arg)
                continue

            if arg in ["limit", "after", "offset", "fields", "expand", "order"]:
                continue

            if arg in dto_class.partition_fields:
                continue

            filters[arg] = args.get(arg)

        for field in dto_class.partition_fields:
            value = args.get(field)
            if value is None:
                raise MissingParameterException(field)

            filters[field] = value

        return filters, search_query

    @staticmethod
    def parse_order(
        dto_class: DTOBase,
        args: Dict[str, Any],
    ) -> Optional[List[str]]:
        """
        Extrai e valida o parâmetro ``order`` da query string.

        Formato esperado:
        ``order=<campo1> [asc|desc],<campo2> [asc|desc],...``

        Também aceita ``|`` como separador entre campo e direção.
        Quando direção não é informada, o padrão é ``asc``.
        """

        raw_order = args.get("order")
        if raw_order is None:
            return None

        raw_order_text = str(raw_order).strip()
        if raw_order_text == "":
            raise PaginationException("Parâmetro 'order' inválido.")

        partial_config = getattr(dto_class, "partial_dto_config", None)
        accepted_fields: Set[str] = set(dto_class.fields_map.keys())
        if partial_config is not None and partial_config.extension_fields is not None:
            accepted_fields |= set(partial_config.extension_fields)

        order_fields: List[str] = []
        chunks = [chunk.strip() for chunk in raw_order_text.split(",")]
        if any(chunk == "" for chunk in chunks):
            raise PaginationException("Parâmetro 'order' inválido.")

        pattern = re.compile(
            r"^(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)"
            r"(?:\s*(?:\||\s+)\s*(?P<direction>asc|desc))?$",
            re.IGNORECASE,
        )

        for chunk in chunks:
            match = pattern.match(chunk)
            if match is None:
                raise PaginationException(f"Trecho inválido em 'order': '{chunk}'.")

            field_name = match.group("field")
            direction = match.group("direction")

            if field_name not in accepted_fields:
                raise PaginationException(
                    f"Campo inválido em 'order': '{field_name}'."
                )

            if direction is None:
                order_fields.append(field_name)
            else:
                order_fields.append(f"{field_name} {direction.lower()}")

        return order_fields

    @staticmethod
    def handle_if_none_match(
        id_: Any,
        service: Any,
        dto_class: Type[DTOBase],
        header_val: Optional[str],
        fields: FieldsTree,
        # Data for service.get
        partition_fields: Any,
        function_params: Any,
        function_object: Any,
        function_name: Any,
    ) -> Tuple[FieldsTree, Optional[Any]]:
        """
        Avalia o header If-None-Match para GET por id.

        Faz uma busca rasa (PK + ETag) quando o DTO define
        ``etag_fields`` e o header foi informado. Se houver match,
        retorna uma resposta 304 com ETag e evita o GET completo.
        Sempre adiciona o campo ETag em ``fields`` para garantir o
        retorno do header em respostas 200.

        Exemplo:
        >>> class DummyDTO:
        ...     etag_fields = {"version"}
        ...     etag_type = "RAW"
        ...     pk_field = "id"
        >>> class DummyService:
        ...     def __init__(self, version):
        ...         self._version = version
        ...     def get(self, **kwargs):
        ...         class Obj:
        ...             def __init__(self, version):
        ...                 self.version = version
        ...         return Obj(self._version)
        >>> fields = {"root": set()}
        >>> fields, resp = RouteBase.handle_if_none_match(
        ...     id_="1",
        ...     service=DummyService("abc"),
        ...     dto_class=DummyDTO,
        ...     header_val='"abc"',
        ...     fields=fields,
        ...     partition_fields={},
        ...     function_params=None,
        ...     function_object=None,
        ...     function_name=None,
        ... )
        >>> resp[1]
        304
        >>> resp[2]["ETag"]
        'W/"abc"'
        >>> "version" in fields["root"]
        True
        """
        etag_header: Optional[str] = header_val
        etag_fields: Set[str] = dto_class.etag_fields
        if etag_header is None or len(etag_fields) == 0:
            return fields, None

        # NOTE: This is to make sure Etag is returned if the values do
        #           not match
        fields['root'].update(etag_fields)

        # NOTE: Doing a shallow fetch to save on IO to DB
        fetch_fields: FieldsTree = {
            'root': {dto_class.pk_field} | etag_fields
        }
        etag_dto = service.get(
            id=id_,
            partition_fields=partition_fields,
            fields=fetch_fields,
            expands={'root': set()},
            function_params=function_params,
            function_object=function_object,
            function_name=function_name,
            custom_json_response=False,
        )

        etag_value: str = RouteBase.get_etag_value(etag_dto)
        vals: List[str] = RouteBase.parse_if_none_match(etag_header)
        if not RouteBase.is_etag_value_in_list(
            dto_class.etag_type,
            etag_value,
            vals
        ):
            return fields, None

        headers: Dict[str, str] = {**DEFAULT_RESP_HEADERS}
        RouteBase.add_etag_header_if_needed(headers, etag_dto)
        return fields, ("", 304, headers)

    @staticmethod
    def is_etag_value_in_list(
        etag_type: Union[Literal["RAW"], Literal["DATE"], Literal["HASH"]],
        val: str,
        vals: List[str]
    ) -> bool:
        """
        Verifica se um valor de ETag bate com a lista informada.

        Exemplo:
        >>> RouteBase.is_etag_value_in_list("RAW", "abc", ["abc", "def"])
        True
        >>> RouteBase.is_etag_value_in_list("RAW", "abc", ["def"])
        False
        >>> RouteBase.is_etag_value_in_list(
        ...     "DATE",
        ...     "2024-01-02T00:00:00",
        ...     ["2024-01-01T00:00:00"],
        ... )
        True
        >>> RouteBase.is_etag_value_in_list(
        ...     "DATE",
        ...     "2024-01-01T00:00:00",
        ...     ["2024-01-02T00:00:00"],
        ... )
        False
        >>> RouteBase.is_etag_value_in_list("HASH", "abc", ["abc"])
        True
        >>> RouteBase.is_etag_value_in_list("HASH", "abc", ["def"])
        False
        """
        def _to_datetime(s: str) -> dt.datetime:
            try:
                return dt.datetime.fromisoformat(s)
            except:
                return dt.datetime.min
            pass

        if etag_type == "DATE":
            vald: dt.datetime = _to_datetime(val)
            for v in vals:
                if vald >= _to_datetime(v):
                    return True
                pass
            return False

        return val in vals

    @staticmethod
    def get_etag_value(dto: DTOBase) -> str:
        """
        Gera o valor do ETag a partir dos campos configurados no DTO.

        Exemplo:
        >>> class DummyDTO:
        ...     etag_fields = {"version"}
        ...     etag_type = "RAW"
        ...     def __init__(self, version):
        ...         self.version = version
        >>> RouteBase.get_etag_value(DummyDTO("v1"))
        'v1'
        >>> DummyDTO.etag_type = "HASH"
        >>> RouteBase.get_etag_value(DummyDTO("v1"))
        '3bfc269594ef649228e9a74bab00f042efc91d5acc6fbee31a382e80d42388fe'
        >>> DummyDTO.etag_type = "DATE"
        >>> RouteBase.get_etag_value(DummyDTO("2024-01-01T00:00:00"))
        '2024-01-01T00:00:00'
        """
        etag_value: str = ""
        for f in sorted(dto.etag_fields):
            etag_value += str(getattr(dto, f, None))
            pass
        if dto.etag_type == "HASH":
            return hashlib.sha256(etag_value.encode('utf-8')).hexdigest()
        return etag_value

    @staticmethod
    def add_etag_header_if_needed(
        headers: Dict[str, str],
        dto: DTOBase
    ) -> None:
        """
        Adiciona o header ETag (weak) se o DTO define ``etag_fields``.

        Modifica o dicionário ``headers`` in-place.

        Exemplo:
        >>> class DummyDTO:
        ...     etag_fields = {"version"}
        ...     etag_type = "RAW"
        ...     def __init__(self, version):
        ...         self.version = version
        >>> headers = {}
        >>> RouteBase.add_etag_header_if_needed(headers, DummyDTO("1"))
        >>> headers["ETag"]
        'W/"1"'
        """
        fields: Set[str] = dto.etag_fields
        if len(fields) == 0:
            return
        headers["ETag"] = "W/" + RouteBase.quote_and_escape_string(
            RouteBase.get_etag_value(dto)
        )
        pass

    def _validade_data_override_parameters(self, args):
        """
        Validates the data override parameters provided in the request arguments.

        This method ensures that if a field in the data override fields list has a value (received as args),
        the preceding field in the list must also have a value. If this condition is not met,
        a DataOverrideParameterException is raised.

        Args:
            args (dict): The request arguments containing the data override parameters.

        Raises:
            DataOverrideParameterException: If a field has a value but the preceding field does not.
        """
        for i in range(1, len(self._dto_class.data_override_fields)):
            field = self._dto_class.data_override_fields[-i]
            previous_field = self._dto_class.data_override_fields[-i - 1]

            value_field = args.get(field)
            previous_value_field = args.get(previous_field)

            # Ensure that if a field has a value, its preceding field must also have a value
            if value_field is not None and previous_value_field is None:
                raise DataOverrideParameterException(field, previous_field)

    @staticmethod
    def build_function_type_from_args(
        function_type_class: type[FunctionTypeBase],
        args: dict[str, any],
        id_value: any = None,
    ) -> FunctionTypeBase:
        """
        Constrói um FunctionType a partir dos args da requisição, incluindo a PK.
        """
        if function_type_class is None:
            return None
        return function_type_class.build_from_params(args or {}, id_value=id_value)

    @staticmethod
    def build_function_object_from_args(
        dto_class: type[DTOBase] | None,
        args: Dict[str, Any] | None,
        extra_params: Dict[str, Any] | None = None,
        id_value: Any | None = None,
    ) -> DTOBase | None:
        """
        Constrói um DTO de parâmetros a partir dos args da requisição,
        incluindo campos adicionais (particionamento / filtros) e, se
        configurado, a PK mapeada a partir de id_value.

        Se dto_class for None, retorna None.
        """
        if dto_class is None:
            return None

        dto_kwargs: Dict[str, Any] = dict(args or {})
        if extra_params:
            dto_kwargs.update(extra_params)

        pk_field = getattr(dto_class, "pk_field", None)
        if pk_field and id_value is not None and pk_field not in dto_kwargs:
            dto_kwargs[pk_field] = id_value

        return dto_class(**dto_kwargs)
