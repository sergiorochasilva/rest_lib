from typing import Any, Dict, List

from rest_lib.util.json_util import json_loads

from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.entity.filter import Filter
from rest_lib.exception import DTOListFieldConfigException
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.service.service_base_partial_of import ServiceBasePartialOf


class ServiceBaseDelete(ServiceBasePartialOf):

    def delete(
        self,
        id: Any,
        additional_filters: Dict[str, Any] = None,
        custom_before_delete=None,
        function_params: Dict[str, Any] | None = None,
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> DTOBase:
        return self._delete(
            id,
            manage_transaction=True,
            additional_filters=additional_filters,
            custom_before_delete=custom_before_delete,
            function_params=function_params,
            function_object=function_object,
            function_name=function_name,
            custom_json_response=custom_json_response,
        )

    def delete_list(
        self,
        ids: list,
        additional_filters: Dict[str, Any] = None,
        function_params: Dict[str, Any] | None = None,
        function_object=None,
        function_name: str | None = None,
    ):
        _returns = {}
        for _id in ids:
            try:
                self._delete(
                    _id,
                    manage_transaction=True,
                    additional_filters=additional_filters,
                    function_params=function_params,
                    function_object=function_object,
                    function_name=function_name,
                )
            except Exception as e:
                _returns[_id] = e

        return _returns

    def _delete(
        self,
        id: str,
        manage_transaction: bool,
        additional_filters: Dict[str, Any] = None,
        custom_before_delete=None,
        function_params: Dict[str, Any] | None = None,
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> DTOBase:
        try:
            if manage_transaction:
                self._dao.begin()

            # Função para validar ou fazer outras consultas antes de deletar
            if custom_before_delete is not None:
                dto = self.get(id, additional_filters, None)
                custom_before_delete(self._dao._db, dto)

            fn_name = function_name
            # DELETE por função só deve ocorrer quando o nome da função
            # for informado explicitamente.
            if fn_name is not None:
                return self._delete_by_function(
                    id,
                    additional_filters,
                    function_params or {},
                    function_object,
                    function_name=fn_name,
                    custom_json_response=custom_json_response,
                )

            # Convertendo os filtros para os filtros de entidade
            entity_filters = {}
            if additional_filters is not None:
                entity_filters = self._create_entity_filters(additional_filters)

            # Resolve o campo de chave sendo utilizado
            entity_key_field, entity_id_value = self._resolve_field_key(
                id,
                additional_filters,
            )

            # Adicionando o ID nos filtros
            id_condiction = Filter(FilterOperator.EQUALS, entity_id_value)

            entity_filters[entity_key_field] = [id_condiction]

            # Tratando das propriedades de lista
            if len(self._dto_class.list_fields_map) > 0:
                self._delete_related_lists(id, additional_filters)

            # Excluindo os conjuntos (se necessário)
            if self._dto_class.conjunto_type is not None:
                self._dao.delete_relacionamento_conjunto(
                    id, self._dto_class.conjunto_type
                )

            # Excluindo a entity principal
            self._dao.delete(entity_filters)
            return None
        except:
            if manage_transaction:
                self._dao.rollback()
            raise
        finally:
            if manage_transaction:
                self._dao.commit()

    def _delete_list(
        self,
        ids: List[str],
        manage_transaction: bool,
        additional_filters: Dict[str, Any] = None,
        custom_before_delete=None,
        function_params: Dict[str, Any] | None = None,
        function_name: str | None = None,
    ) -> DTOBase:

        if not ids:
            return

        try:
            if manage_transaction:
                self._dao.begin()

            # Convertendo os filtros para os filtros de entidade
            entity_filters = {}
            if additional_filters is not None:
                entity_filters = self._create_entity_filters(additional_filters)

            entity_id_values = []
            for _id in ids:
                # Função para validar ou fazer outras consultas antes de deletar
                if custom_before_delete is not None:
                    dto = self.get(_id, additional_filters, None)
                    custom_before_delete(self._dao._db, dto)

                fn_name = function_name
                # DELETE por função só deve ocorrer quando o nome da função
                # for informado explicitamente.
                if fn_name is not None:
                    self._delete_by_function(
                        _id,
                        additional_filters,
                        function_params or {},
                        function_name=fn_name,
                    )
                    continue

                # Resolve o campo de chave sendo utilizado
                entity_key_field, entity_id_value = self._resolve_field_key(
                    _id,
                    additional_filters,
                )

                entity_id_values.append(entity_id_value)

                # Tratando das propriedades de lista
                if len(self._dto_class.list_fields_map) > 0:
                    self._delete_related_lists(_id, additional_filters)

            # Adicionando o ID nos filtros
            id_condiction = Filter(FilterOperator.IN, entity_id_values)

            entity_filters[entity_key_field] = [id_condiction]

            # Excluindo os conjuntos (se necessário)
            if self._dto_class.conjunto_type is not None:
                self._dao.delete_relacionamentos_conjunto(
                    ids, self._dto_class.conjunto_type
                )

            # Excluindo a entity principal
            self._dao.delete(entity_filters)
        except:
            if manage_transaction:
                self._dao.rollback()
            raise
        finally:
            if manage_transaction:
                self._dao.commit()

    def _delete_by_function(
        self,
        id: Any,
        additional_filters: Dict[str, Any] | None,
        function_params: Dict[str, Any],
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ):
        params: Dict[str, Any] = dict(function_params or {})
        if additional_filters:
            params.update(additional_filters)

        fn_name = function_name
        if not fn_name:
            raise ValueError("Nome da função DELETE não informado.")

        if function_object is not None:
            if isinstance(function_object, FunctionTypeBase):
                rows = self._dao._call_function_with_type(function_object, fn_name)
                return self._handle_custom_delete_response(
                    rows,
                    custom_json_response,
                )
            raise TypeError(
                "function_object deve ser um FunctionTypeBase em _delete_by_function."
            )

        # Chamada RAW (parâmetros simples)
        positional_values = []
        if id is not None:
            positional_values.append(id)
        rows = self._dao._call_function_raw(
            fn_name,
            positional_values,
            params,
        )
        return self._handle_custom_delete_response(rows, custom_json_response)

    def _handle_custom_delete_response(self, rows, custom_json_response: bool):
        if not custom_json_response:
            return None

        if not rows:
            return {}

        first_row = rows[0]
        if isinstance(first_row, dict) and "mensagem" in first_row:
            payload = first_row.get("mensagem")
            if isinstance(payload, str):
                try:
                    return json_loads(payload)
                except Exception:
                    return payload
            return payload

        return first_row

    def _delete_related_lists_old(self, id, additional_filters: Dict[str, Any] = None):
        # Handling each related list
        from .service_base import ServiceBase

        for _, list_field in self._dto_class.list_fields_map.items():
            # Getting service instance
            if list_field.service_name is not None:
                service = self._injector_factory.get_service_by_name(
                    list_field.service_name
                )
            else:
                service = ServiceBase(
                    self._injector_factory,
                    DAOBase(
                        self._injector_factory.db_adapter(), list_field.entity_type
                    ),
                    list_field.dto_type,
                    list_field.entity_type,
                )

            # Making filter to relation
            filters = {
                # TODO Adicionar os campos de particionamento de dados
                list_field.related_entity_field: id
            }

            # Getting related data
            related_dto_list = service.list(None, None, {"root": set()}, None, filters)

            # Excluindo cada entidade detalhe
            for related_dto in related_dto_list:
                # Checking if pk_field exists
                if list_field.dto_type.pk_field is None:
                    raise DTOListFieldConfigException(
                        f"PK field not found in class: {self._dto_class}"
                    )

                if list_field.dto_type.pk_field not in related_dto.__dict__:
                    raise DTOListFieldConfigException(
                        f"PK field not found in DTO: {self._dto_class}"
                    )

                # Recuperando o ID da entidade detalhe
                related_id = getattr(related_dto, list_field.dto_type.pk_field)

                # Chamando a exclusão recursivamente
                service._delete(
                    related_id,
                    manage_transaction=False,
                    additional_filters=additional_filters,
                )

    def _delete_related_lists(self, id, additional_filters: Dict[str, Any] = None):
        # Handling each related list
        from .service_base import ServiceBase

        for _, list_field in self._dto_class.list_fields_map.items():
            # Getting service instance
            if list_field.service_name is not None:
                service = self._injector_factory.get_service_by_name(
                    list_field.service_name
                )
            else:
                service = ServiceBase(
                    self._injector_factory,
                    DAOBase(
                        self._injector_factory.db_adapter(), list_field.entity_type
                    ),
                    list_field.dto_type,
                    list_field.entity_type,
                )

            # Making filter to relation
            filters = {
                # TODO Adicionar os campos de particionamento de dados
                list_field.related_entity_field: id
            }

            # Getting related data
            related_dto_list = service.list(None, None, {"root": set()}, None, filters)

            # Excluindo cada entidade detalhe
            related_ids = []
            for related_dto in related_dto_list:
                # Checking if pk_field exists
                if list_field.dto_type.pk_field is None:
                    raise DTOListFieldConfigException(
                        f"PK field not found in class: {self._dto_class}"
                    )

                if list_field.dto_type.pk_field not in related_dto.__dict__:
                    raise DTOListFieldConfigException(
                        f"PK field not found in DTO: {self._dto_class}"
                    )

                # Recuperando o ID da entidade detalhe
                related_ids.append(getattr(related_dto, list_field.dto_type.pk_field))

            # Chamando a exclusão
            service._delete_list(
                related_ids,
                manage_transaction=False,
                additional_filters=additional_filters,
            )
