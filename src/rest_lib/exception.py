class DTOConfigException(Exception):
    pass


class DTOListFieldConfigException(Exception):
    pass


class ERPException(Exception):
    mope_code: str
    message: str

    def __init__(self, mope_code: str, message: str):
        super().__init__(f"{mope_code} - {message}")
        self.mope_code = mope_code
        self.message = message


class PaginationException(ERPException):
    def __init__(self, msg: str):
        super().__init__(
            "0000-E001",
            f'Erro nos parâmetros requisitados para paginação: {msg}',
        )


class MissingParameterException(Exception):
    _parameter_name: str

    def __init__(self, parameter_name: str):
        super().__init__(f"Missing parameter: {parameter_name}")
        self._parameter_name = parameter_name


class DataOverrideParameterException(Exception):
    _parameter_name: str

    def __init__(self, parameter_name: str, more_generic_parameter_name: str):
        super().__init__(
            f"Para filtrar por {parameter_name} é necessário passar também o parâmetro {more_generic_parameter_name}"
        )
        self._parameter_name = parameter_name


class NotFoundException(Exception):
    pass


class ConflictException(Exception):
    pass


class AfterRecordNotFoundException(Exception):
    pass


class PostgresFunctionException(Exception):
    pass
