from typing import Dict, List

from rest_lib.descriptor.conjunto_type import ConjuntoType
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.filter import Filter

from .dao_base_util import DAOBaseUtil

class DAOBaseConjuntos(DAOBaseUtil):

    def _make_conjunto_sql(
        self,
        conjunto_type: ConjuntoType,
        entity: EntityBase,
        filters: Dict[str, List[Filter]],
        conjunto_field: str = None,
    ):
        tabela_conjunto = f"ns.conjuntos{conjunto_type.name.lower()}"
        cadastro = conjunto_type.value

        # Motando os parâmetros de conjuntos para a query
        valores_filtro_codigo = []
        valores_filtro_id = []
        for filtro in filters[conjunto_field]:
            if self.is_valid_uuid(filtro.value):
                valores_filtro_id.append(filtro.value)
            else:
                valores_filtro_codigo.append(filtro.value)

        conjunto_map = {
            "conjunto_cadastro": cadastro,
            "grupo_empresarial_conjunto_codigo": tuple(valores_filtro_codigo),
            "grupo_empresarial_conjunto_id": tuple(valores_filtro_id),
        }

        query_grupo = ""
        if valores_filtro_codigo and valores_filtro_id:
            query_grupo = "and (gemp0.codigo in :grupo_empresarial_conjunto_codigo or gemp0.grupoempresarial in :grupo_empresarial_conjunto_id)"
        elif valores_filtro_codigo:
            query_grupo = "and gemp0.codigo in :grupo_empresarial_conjunto_codigo"
        elif valores_filtro_id:
            query_grupo = "and gemp0.grupoempresarial in :grupo_empresarial_conjunto_id"

        with_conjunto = f"""
            with grupos_conjuntos as (
                select
                    gemp0.grupoempresarial as grupo_empresarial_pk,
                    gemp0.codigo as grupo_empresarial_codigo,
                    est_c0.conjunto
                from ns.gruposempresariais gemp0
                join ns.empresas emp0 on (emp0.grupoempresarial = gemp0.grupoempresarial {query_grupo})
                join ns.estabelecimentos est0 on (est0.empresa = emp0.empresa)
                join ns.estabelecimentosconjuntos est_c0 on (
                    est_c0.estabelecimento = est0.estabelecimento
                    and est_c0.cadastro = :conjunto_cadastro
                )
                group by gemp0.grupoempresarial, gemp0.codigo, est_c0.conjunto
            )
            """

        join_conjuntos = f"""
            join {tabela_conjunto} as cr0 on (t0.{entity.get_pk_field()} = cr0.registro)
            join grupos_conjuntos as gc0 on (gc0.conjunto = cr0.conjunto)
            """

        fields_conjunto = """
            gc0.grupo_empresarial_pk,
            gc0.grupo_empresarial_codigo,
            gc0.conjunto as conjunto,
            """

        del filters[conjunto_field]

        return join_conjuntos, with_conjunto, fields_conjunto, conjunto_map

    def insert_relacionamento_conjunto(
        self,
        id: str,
        conjunto_field_value: str,
        conjunto_type: ConjuntoType = None,
    ):
        # Recuperando o conjunto correspondente ao grupo_empresarial
        tabela_conjunto = f"ns.conjuntos{conjunto_type.name.lower()}"
        cadastro = conjunto_type.value
        query_grupo = ""

        if self.is_valid_uuid(conjunto_field_value):
            data = {
                "conjunto_cadastro": cadastro,
                "grupo_empresarial_conjunto_id": conjunto_field_value,
            }
            query_grupo = "and gemp0.grupoempresarial = :grupo_empresarial_conjunto_id"
        else:
            data = {
                "conjunto_cadastro": cadastro,
                "grupo_empresarial_conjunto_codigo": conjunto_field_value,
            }
            query_grupo = "and gemp0.codigo = :grupo_empresarial_conjunto_codigo"

        sql = f"""
        select
            gemp0.grupoempresarial as grupo_empresarial_pk,
            est_c0.conjunto
        from ns.gruposempresariais gemp0
        join ns.empresas emp0 on (emp0.grupoempresarial = gemp0.grupoempresarial {query_grupo})
        join ns.estabelecimentos est0 on (est0.empresa = emp0.empresa)
        join ns.estabelecimentosconjuntos est_c0 on (
            est_c0.estabelecimento = est0.estabelecimento
            and est_c0.cadastro = :conjunto_cadastro
        )
        group by gemp0.grupoempresarial, est_c0.conjunto
        """
        resp = self._db.execute_query(sql, **data)

        if len(resp) > 1:
            raise Exception(
                f"A biblioteca rest_lib ainda não suporta inserção de registros onde há mais de um conjunto, de um mesmo tipo ({cadastro}), num mesmo grupo_empresarial ({conjunto_field_value})."
            )

        if len(resp) < 1:
            raise Exception(
                f"Não foi encontrado um conjunto correspondente ao grupo empresarial {conjunto_field_value}, para o tipo de cadastro {cadastro}."
            )

        # Inserindo o relacionamento com o conjunto
        sql = f"""
        insert into {tabela_conjunto} (conjunto, registro) values (:conjunto, :registro)
        """

        data = {"conjunto": resp[0]["conjunto"], "registro": id}
        self._db.execute(sql, **data)

    def delete_relacionamento_conjunto(
        self,
        id: str,
        conjunto_type: ConjuntoType = None,
    ):
        # Resolvendo a tabela de conjunto
        tabela_conjunto = f"ns.conjuntos{conjunto_type.name.lower()}"

        # Removendo o relacionamento com o conjunto
        sql = f"""
        delete from {tabela_conjunto} where registro = :registro
        """

        self._db.execute(sql, registro=id)

    def delete_relacionamentos_conjunto(
        self,
        ids: List[str],
        conjunto_type: ConjuntoType = None,
    ):
        # Resolvendo a tabela de conjunto
        tabela_conjunto = f"ns.conjuntos{conjunto_type.name.lower()}"

        # Removendo o relacionamento com o conjunto
        sql = f"""
        delete from {tabela_conjunto} where registro in :registro
        """

        self._db.execute(sql, registro=tuple(ids))
