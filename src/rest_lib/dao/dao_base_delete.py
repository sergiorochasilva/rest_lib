from typing import Dict, List

from rest_lib.entity.filter import Filter
from rest_lib.exception import NotFoundException

from .dao_base_util import DAOBaseUtil

class DAOBaseDelete(DAOBaseUtil):

    def list_ids(self, filters: Dict[str, List[Filter]]):
        """
        Lista os IDs encontrados, de acordo com os filtros recebidos.
        """

        # Retorna None, se não receber filtros
        if filters is None or len(filters) <= 0:
            return None

        # Montando uma entity fake
        entity = self._entity_class()

        # Recuperando o campo de chave primária
        pk_field = entity.get_pk_field()

        # Organizando o where dos filtros
        filters_where, filter_values_map = self._make_filters_sql(filters)

        # Montando a query
        sql = f"""
        select {pk_field} from {entity.get_table_name()} as t0 where true {filters_where}
        """

        # Executando a query
        resp = self._db.execute_query(sql, **filter_values_map)

        # Retornando em formato de lista de IDs
        if resp is None:
            return None
        else:
            return [item[pk_field] for item in resp]

    def delete(self, filters: Dict[str, List[Filter]]):
        """
        Exclui registros de acordo com os filtros recebidos.
        """

        # Retorna None, se não receber filtros
        if filters is None or len(filters) <= 0:
            raise NotFoundException(
                f"{self._entity_class.__name__} não encontrado. Filtros: {filters}"
            )

        # Montando uma entity fake
        entity = self._entity_class()

        # Organizando o where dos filtros
        filters_where, filter_values_map = self._make_filters_sql(filters, False)

        # CUIDADO PARA NÂO EXCLUIR O QUE NÃO DEVE
        if filters_where is None or filters_where.strip() == "":
            raise NotFoundException(
                f"{self._entity_class.__name__} não encontrado. Filtros: {filters}"
            )

        # Montando a query
        sql = f"""
        delete from {entity.get_table_name()} as t0 where {filters_where}
        """

        # Executando a query
        rowcount, _ = self._db.execute(sql, **filter_values_map)

        # Verificando se houve alguma deleção
        if rowcount <= 0:
            raise NotFoundException(
                f"{self._entity_class.__name__} não encontrado. Filtros: {filters}"
            )
