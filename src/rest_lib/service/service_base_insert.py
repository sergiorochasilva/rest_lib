from typing import Any, Callable, Dict, List

from rest_lib.dto.dto_base import DTOBase

from .service_base_save import ServiceBaseSave


class ServiceBaseInsert(ServiceBaseSave):

    def insert(
        self,
        dto: DTOBase,
        aditional_filters: Dict[str, Any] = None,
        custom_before_insert: Callable = None,
        custom_after_insert: Callable = None,
        retrieve_after_insert: bool = False,
        manage_transaction: bool = True,
        function_name: str | None = None,
        custom_json_response: bool = False,
        retrieve_fields=None,
    ) -> DTOBase:
        return self._save(
            insert=True,
            dto=dto,
            manage_transaction=manage_transaction,
            partial_update=False,
            aditional_filters=aditional_filters,
            custom_before_insert=custom_before_insert,
            custom_after_insert=custom_after_insert,
            retrieve_after_insert=retrieve_after_insert,
            function_name=function_name,
            custom_json_response=custom_json_response,
            retrieve_fields=retrieve_fields,
        )

    def insert_list(
        self,
        dtos: List[DTOBase],
        aditional_filters: Dict[str, Any] = None,
        custom_before_insert: Callable = None,
        custom_after_insert: Callable = None,
        retrieve_after_insert: bool = False,
        manage_transaction: bool = True,
        function_name: str | None = None,
        custom_json_response: bool = False,
        retrieve_fields=None,
    ) -> List[DTOBase]:
        _lst_return = []
        try:
            if manage_transaction:
                self._dao.begin()

            for dto in dtos:
                _return_object = self._save(
                    insert=True,
                    dto=dto,
                    manage_transaction=False,
                    partial_update=False,
                    aditional_filters=aditional_filters,
                    custom_before_insert=custom_before_insert,
                    custom_after_insert=custom_after_insert,
                    retrieve_after_insert=retrieve_after_insert,
                    function_name=function_name,
                    custom_json_response=custom_json_response,
                    retrieve_fields=retrieve_fields,
                )

                if _return_object is not None:
                    _lst_return.append(_return_object)

        except:
            if manage_transaction:
                self._dao.rollback()
            raise
        finally:
            if manage_transaction:
                self._dao.commit()

        return _lst_return
