class EntityField:
    _ref_counter = 0

    description: str

    def __init__(
        self,
        type: object = None,
        description: str = "",
    ):
        """
        -----------
        Parameters:
        -----------

        - update_type_field: Nome do campo no tipo usado para atualização via função no BD.
        - description: Descrição deste campo na documentação.
        """
        self.name: str | None = None
        self.expected_type = type
        self.description = description

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        instance.__dict__[self.storage_name] = value
