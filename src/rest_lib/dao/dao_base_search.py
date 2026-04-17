import datetime
import decimal
import re
import uuid

import unidecode

from typing import Any, Dict, List, Tuple

from rest_lib.entity.entity_base import EntityBase

from .dao_base_conjuntos import DAOBaseConjuntos


class DAOBaseSearch(DAOBaseConjuntos):
    """
    Extensão de DAOBase com suporte a busca textual genérica (``search``).

    Implementa construção de SQL para busca em múltiplos campos, incluindo
    campos relacionais via subquery ``exists``.
    """

    def _wrap_search_condition(self, condition_sql: str, field_spec: Dict[str, Any]) -> str:
        """
        Envolve uma condição de busca em ``exists`` quando o campo é relacional.

        Args:
            condition_sql (str): Condição base de busca (ex.: ``t1.nome ilike :p``).
            field_spec (Dict[str, Any]): Metadados do campo de busca.

        Returns:
            str: Condição SQL original ou envolvida em subquery ``exists``.
        """
        if field_spec.get("relation_mode") != "exists":
            return condition_sql

        relation_table = field_spec.get("relation_table")
        relation_alias = field_spec.get("relation_alias")
        relation_parent_field = field_spec.get("relation_parent_field")
        relation_child_field = field_spec.get("relation_child_field")
        relation_join_sql = field_spec.get("relation_join_sql") or ""

        if (
            relation_table is None
            or relation_alias is None
            or relation_parent_field is None
            or relation_child_field is None
        ):
            return condition_sql

        return f"""
        exists (
            select 1
            from {relation_table} as {relation_alias}
            {relation_join_sql}
            where {relation_alias}.{relation_child_field} = t0.{relation_parent_field}
              and ({condition_sql})
        )
        """.strip()

    def _normalize_search_field_spec(
        self,
        search_field: Any,
        idx: int,
        base_entity: EntityBase,
    ) -> Dict[str, Any] | None:
        """
        Normaliza a especificação de um campo de busca.

        Args:
            search_field (Any): Campo bruto (string ou dicionário de metadados).
            idx (int): Índice da iteração para composição de aliases.
            base_entity (EntityBase): Entidade principal da consulta.

        Returns:
            Dict[str, Any] | None: Especificação normalizada com alias e entity_field.
            Retorna ``None`` quando a especificação for inválida.
        """
        if isinstance(search_field, str):
            spec = {
                "field": search_field,
                "table_alias": "t0",
            }
            entity_obj = base_entity
        elif isinstance(search_field, dict):
            spec = dict(search_field)
            entity_class = spec.get("entity_class")
            if entity_class is None:
                entity_obj = base_entity
            else:
                entity_obj = entity_class()

            if spec.get("relation_mode") == "exists" and not spec.get("relation_alias"):
                spec["relation_alias"] = f"sr_{idx}"
        else:
            return None

        field_name = spec.get("field")
        if field_name is None:
            return None

        entity_field = entity_obj.fields_map.get(field_name)
        if entity_field is None:
            return None

        table_alias = spec.get("table_alias") or spec.get("relation_alias") or "t0"
        spec["table_alias"] = table_alias
        spec["entity_field"] = entity_field
        return spec

    def _make_search_sql(
        self,
        search_query: str,
        search_fields: List[Any],
        entity: EntityBase,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Monta a parte da cláusula where referente ao parâmetro search, bem como o mapa de
        valores para realizar a pesquisa (passando para a execução da query).

        Retorna uma tupla, onde a primeira posição é o mapa de valores, e a segunda a cláusula sql.
        """

        search_map: Dict[str, Any] = {}
        search_where = ""

        date_pattern = r"(\d\d)/(\d\d)/((\d\d\d\d)|(\d\d))"
        int_pattern = r"(\d+)"
        float_pattern = r"(\d+((,|\.)\d+)?)"

        if search_fields is not None and search_query is not None:
            search_conditions: List[str] = []

            for idx, raw_field in enumerate(search_fields):
                spec = self._normalize_search_field_spec(raw_field, idx, entity)
                if spec is None:
                    continue

                field_name = spec["field"]
                table_alias = spec["table_alias"]
                entity_field = spec["entity_field"]
                field_ref = f"{table_alias}.{field_name}"
                safe_field_name = re.sub(r"[^0-9a-zA-Z_]", "_", field_name)
                search_str = search_query
                cont = -1

                if (
                    entity_field.expected_type is datetime.datetime
                    or entity_field.expected_type is datetime.date
                ):
                    # Tratando da busca de datas
                    received_floats = re.findall(date_pattern, search_str)
                    for received_float in received_floats:
                        cont += 1

                        dia = int(received_float[0])
                        mes = int(received_float[1])
                        ano = received_float[2]
                        if len(ano) < 4:
                            ano = f"20{ano}"
                        ano = int(ano)

                        try:
                            data_obj = datetime.date(ano, mes, dia)
                        except Exception:
                            continue

                        key = f"shf_{safe_field_name}_{cont}"
                        raw_condition = f"{field_ref} = :{key}"
                        search_conditions.append(
                            self._wrap_search_condition(raw_condition, spec)
                        )
                        search_map[key] = data_obj

                elif entity_field.expected_type is int:
                    # Tratando da busca de inteiros
                    search_str = re.sub(date_pattern, "", search_str)
                    received_ints = re.findall(int_pattern, search_str)

                    for received_int in received_ints:
                        cont += 1
                        valor = int(received_int[0])
                        valor_min = int(valor * 0.9)
                        valor_max = int(valor * 1.1)

                        key_min = f"shf_{safe_field_name}_{cont}_min"
                        key_max = f"shf_{safe_field_name}_{cont}_max"
                        raw_condition = (
                            f"({field_ref} >= :{key_min} and {field_ref} <= :{key_max})"
                        )
                        search_conditions.append(
                            self._wrap_search_condition(raw_condition, spec)
                        )
                        search_map[key_min] = valor_min
                        search_map[key_max] = valor_max

                elif entity_field.expected_type in [float, decimal.Decimal]:
                    # Tratando da busca de floats e decimais
                    search_str = re.sub(date_pattern, "", search_str)
                    received_floats = re.findall(float_pattern, search_str)

                    for received_float in received_floats:
                        cont += 1
                        valor = float(received_float[0].replace(",", "."))
                        valor_min = valor * 0.9
                        valor_max = valor * 1.1

                        key_min = f"shf_{safe_field_name}_{cont}_min"
                        key_max = f"shf_{safe_field_name}_{cont}_max"
                        raw_condition = (
                            f"({field_ref} >= :{key_min} and {field_ref} <= :{key_max})"
                        )
                        search_conditions.append(
                            self._wrap_search_condition(raw_condition, spec)
                        )
                        search_map[key_min] = valor_min
                        search_map[key_max] = valor_max

                elif entity_field.expected_type in [str, uuid, uuid.UUID]:
                    # Tratando da busca de strings e UUIDs
                    for palavra in search_str.split(" "):
                        if palavra == "":
                            continue

                        cont += 1
                        key = f"shf_{safe_field_name}_{cont}"
                        raw_condition = (
                            f"upper(unaccent(CAST({field_ref} AS varchar))) "
                            f"like upper(unaccent(:{key}))"
                        )
                        search_conditions.append(
                            self._wrap_search_condition(raw_condition, spec)
                        )
                        search_map[key] = f"%{unidecode.unidecode(palavra)}%"

            if len(search_conditions) > 0:
                search_buffer = "\n                or ".join(search_conditions)
                search_where = f"""
            and (
                false
                or {search_buffer}
            )
            """

        return search_map, search_where
