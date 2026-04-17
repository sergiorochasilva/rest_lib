from typing import Any, Callable, Dict, List

from rest_lib.dto.dto_base import DTOBase

from .service_base_insert import ServiceBaseInsert


class ServiceBaseUpdate(ServiceBaseInsert):

    def update(
        self,
        dto: DTOBase,
        id: Any,
        aditional_filters: Dict[str, Any] = None,
        custom_before_update: Callable = None,
        custom_after_update: Callable = None,
        upsert: bool = False,
        manage_transaction: bool = True,
        function_name: str | None = None,
        retrieve_after_update: bool = False,
        custom_json_response: bool = False,
        retrieve_fields=None,
    ) -> DTOBase:
        return self._save(
            insert=False,
            dto=dto,
            manage_transaction=manage_transaction,
            partial_update=False,
            id=id,
            aditional_filters=aditional_filters,
            custom_before_update=custom_before_update,
            custom_after_update=custom_after_update,
            upsert=upsert,
            function_name=function_name,
            retrieve_after_insert=retrieve_after_update,
            custom_json_response=custom_json_response,
            retrieve_fields=retrieve_fields,
        )

    def update_list(
        self,
        dtos: List[DTOBase],
        aditional_filters: Dict[str, Any] = None,
        custom_before_update: Callable = None,
        custom_after_update: Callable = None,
        upsert: bool = False,
        manage_transaction: bool = True,
        function_name: str | None = None,
        retrieve_after_update: bool = False,
        custom_json_response: bool = False,
        retrieve_fields=None,
    ) -> List[DTOBase]:
        _lst_return = []
        try:
            if manage_transaction:
                self._dao.begin()

            for dto in dtos:
                _return_object = self._save(
                    insert=False,
                    dto=dto,
                    manage_transaction=False,
                    partial_update=False,
                    id=getattr(dto, dto.pk_field),
                    aditional_filters=aditional_filters,
                    custom_before_update=custom_before_update,
                    custom_after_update=custom_after_update,
                    upsert=upsert,
                    function_name=function_name,
                    retrieve_after_insert=retrieve_after_update,
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
