import re
from typing import Any, Dict, List, Tuple

from rest_lib.util.json_util import convert_to_dumps, json_loads

from rest_lib.dao.dao_base_util import DAOBaseUtil
from rest_lib.descriptor.function_relation_field import FunctionRelationField
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.exception import PostgresFunctionException


class _FunctionSQLBuilder:
    def __init__(self, root_object: FunctionTypeBase):
        self._root_object = root_object
        self.declarations: List[str] = []
        self.assignments: List[str] = []
        self.values_map: Dict[str, Any] = {}
        self._var_index = 0
        self._declared_vars = {"VAR_TIPO"}

    def build(self) -> Tuple[List[str], List[str], Dict[str, Any]]:
        self._assign_composite(
            target_var="VAR_TIPO",
            instance=self._root_object,
            base_prefix="root",
        )
        return self.declarations, self.assignments, self.values_map

    def _assign_composite(
        self,
        target_var: str,
        instance: FunctionTypeBase,
        base_prefix: str,
    ):
        fields_map = instance.get_fields_map()

        for field_name, descriptor in fields_map.items():
            value = getattr(instance, field_name, None)
            if value is None:
                continue

            type_field_name = descriptor.get_type_field_name()
            field_prefix = f"{base_prefix}_{type_field_name}"

            if isinstance(descriptor, FunctionRelationField):
                self._assign_relation_field(
                    parent_var=target_var,
                    target_field_name=type_field_name,
                    descriptor=descriptor,
                    value=value,
                    base_prefix=field_prefix,
                )
                continue

            placeholder = self._add_value(field_prefix, value)
            self.assignments.append(
                f"{target_var}.{type_field_name} = {placeholder};"
            )

    def _assign_relation_field(
        self,
        parent_var: str,
        target_field_name: str,
        descriptor: FunctionRelationField,
        value,
        base_prefix: str,
    ):
        related_type = descriptor.related_type
        if related_type is None:
            raise ValueError(
                f"O campo '{descriptor.name}' não possui um InsertFunctionType relacionado configurado."
            )

        target_attr = f"{parent_var}.{target_field_name}"
        type_name = related_type.type_name

        if descriptor.multiple:
            if value is None:
                items = []
            else:
                if not isinstance(value, (list, tuple)):
                    raise ValueError(
                        f"O campo '{descriptor.name}' deveria ser uma lista de '{related_type.__name__}'."
                    )
                items = list(value)
            self.assignments.append(f"{target_attr} = ARRAY[]::{type_name}[];")

            for idx, child in enumerate(items):
                if not isinstance(child, related_type):
                    raise ValueError(
                        f"Os itens de '{descriptor.name}' devem ser instâncias de '{related_type.__name__}'."
                    )
                child_prefix = f"{base_prefix}_{idx}"
                child_var = self._new_var(child_prefix)
                self.declarations.append(f"{child_var} {type_name};")
                self._assign_composite(
                    target_var=child_var,
                    instance=child,
                    base_prefix=child_prefix,
                )
                self.assignments.append(
                    f"{target_attr} = array_append({target_attr}, {child_var});"
                )
            return

        if not isinstance(value, related_type):
            raise ValueError(
                f"O campo '{descriptor.name}' deve ser uma instância de '{related_type.__name__}'."
            )

        child_var = self._new_var(base_prefix)
        self.declarations.append(f"{child_var} {type_name};")
        self._assign_composite(
            target_var=child_var,
            instance=value,
            base_prefix=base_prefix,
        )
        self.assignments.append(f"{target_attr} = {child_var};")

    def _add_value(self, base_name: str, value) -> str:
        placeholder_name = self._next_placeholder_name(base_name)
        self.values_map[placeholder_name] = convert_to_dumps(value)
        return f":{placeholder_name}"

    def _next_placeholder_name(self, base_name: str) -> str:
        sanitized = self._sanitize_identifier(base_name.lower())
        if sanitized == "":
            sanitized = "field"

        candidate = sanitized
        suffix = 1
        while candidate in self.values_map:
            candidate = f"{sanitized}_{suffix}"
            suffix += 1
        return candidate

    def _new_var(self, base_name: str) -> str:
        sanitized = self._sanitize_identifier(base_name)
        if sanitized == "":
            sanitized = "var"
        candidate = f"VAR_{sanitized.upper()}"
        while candidate in self._declared_vars:
            self._var_index += 1
            candidate = f"VAR_{sanitized.upper()}_{self._var_index}"
        self._declared_vars.add(candidate)
        return candidate

    @staticmethod
    def _sanitize_identifier(identifier: str) -> str:
        return re.sub(r"[^0-9a-zA-Z_]", "_", identifier or "")


class DAOBaseSaveByFunction(DAOBaseUtil):
    def _sql_function_type(
        self,
        function_object: FunctionTypeBase,
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Retorna as declarações adicionais, atribuições e mapa de valores
        necessários para preencher o type usado na função configurada.
        """

        builder = _FunctionSQLBuilder(function_object)
        return builder.build()

    def insert_by_function(
        self,
        function_object: FunctionTypeBase,
        function_name: str,
        custom_json_response: bool = False,
    ):
        """
        Insere a entidade utilizando uma função de banco declarada por meio de um FunctionType.
        """

        return self._execute_function(
            function_object,
            function_name=function_name,
            block_label="DOINSERT",
            action_label="inserindo",
            custom_json_response=custom_json_response,
        )

    def update_by_function(
        self,
        function_object: FunctionTypeBase,
        function_name: str,
        custom_json_response: bool = False,
    ):
        """
        Atualiza a entidade utilizando uma função de banco declarada por meio de um FunctionType.
        """

        return self._execute_function(
            function_object,
            function_name=function_name,
            block_label="DOUPDATE",
            action_label="atualizando",
            custom_json_response=custom_json_response,
        )

    def _execute_function(
        self,
        function_object: FunctionTypeBase,
        function_name: str,
        block_label: str,
        action_label: str,
        custom_json_response: bool = False,
    ):
        if function_object is None:
            raise ValueError(
                "É necessário informar um objeto do tipo FunctionTypeBase para o processamento por função."
            )

        function_type_class = function_object.__class__
        if not function_name:
            raise ValueError(
                f"É necessário informar o nome da função para {function_type_class.__name__}."
            )

        (
            relation_declarations,
            assignments,
            values_map,
        ) = self._sql_function_type(function_object)

        declarations_sql = "\n".join(
            f"    DECLARE {declaration}" for declaration in relation_declarations
        )

        assignments_sql = "\n".join(f"        {line}" for line in assignments)

        sql = f"""
        DO ${block_label}$
            DECLARE VAR_TIPO {function_type_class.type_name};
{declarations_sql if declarations_sql else ''}
            DECLARE VAR_RETORNO RECORD;
        BEGIN
{assignments_sql}

            VAR_RETORNO = {function_name}(VAR_TIPO);
            PERFORM set_config('retorno.bloco', VAR_RETORNO.mensagem::varchar, true);
        END ${block_label}$;

        SELECT current_setting('retorno.bloco', true)::jsonb as retorno;
        """

        rowcount, returning = self._db.execute_batch(sql, **values_map)

        if rowcount <= 0 or len(returning) <= 0:
            raise Exception(
                f"Erro {action_label} {function_type_class.__name__} no banco de dados"
            )

        returning = returning[0]["retorno"]

        if returning["codigo"].lower().strip() != "ok":
            returning_tipo = returning.get("tipo")
            if returning_tipo:
                msg = f"{returning_tipo}: {returning.get('mensagem')}"
            else:
                msg = returning.get('mensagem')

            raise PostgresFunctionException(msg)

        if custom_json_response:
            return self._extract_custom_response(returning)

        return function_object

    def _extract_custom_response(self, returning: dict) -> object:
        if not isinstance(returning, dict):
            return returning

        payload = returning.get("mensagem")
        if payload is None:
            return returning

        if isinstance(payload, str):
            try:
                return json_loads(payload)
            except Exception:
                return payload

        return payload
