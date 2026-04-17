from rest_lib.dto.dto_base import DTOBase


class AfterInsertUpdateData:
    def __init__(self) -> None:
        self.received_dto: DTOBase
