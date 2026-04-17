class FunctionField:
    """
    Descriptor responsável por representar um campo do type usado em funções no banco
    de dados (insert/update). Mantém metadados mínimos seguindo o mesmo padrão das
    demais declarações da biblioteca.

    `binding_source` permite preencher o campo a partir de uma origem externa ao
    DTO, como `args.<nome>` na query string da request atual.
    """

    _ref_counter = 0

    def __init__(
        self,
        type_field_name: str | None = None,
        description: str = "",
        pk: bool = False,
        binding_source: str | None = None,
    ):
        self.type_field_name = type_field_name
        self.description = description
        self.expected_type = None
        self.pk = pk
        self.binding_source = binding_source
        self.name: str | None = None

        self.storage_name = (
            f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        )
        self.__class__._ref_counter += 1

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance.__dict__.get(self.storage_name)

    def __set__(self, instance, value):
        instance.__dict__[self.storage_name] = value

    def get_type_field_name(self) -> str:
        if self.type_field_name:
            return self.type_field_name
        return self.name

    def get_binding_source(self) -> str | None:
        return self.binding_source
