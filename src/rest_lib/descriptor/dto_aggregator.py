import typing as ty


# pylint: disable-next=too-few-public-methods
class DTOAggregator:
    """
    Permite dividir um DTO em mais de uma classe, de modo que, no JSON de representação do mesmo,
    um objeto JSON aninhado será adicionado, representando o conteúdo da classe referenciada.

    No entanto, do ponto de vista da query, as propriedades de ambos os objetos vem de uma mesma entity,
    e de uma mesma tabela.

    Exemplo:

    class ClienteDTO(DTOBase):
        id: int = DTOField(pk=True)
        nome: str = DTOField()
        endereco: EnderecoDTO = DTOAggregator(EnderecoDTO)

    class EnderecoDTO(DTOBase):
        rua: str = DTOField()
        cidade: str = DTOField()

    class ClienteEntity(EntityBase):
        id: int
        nome: str
        rua: str
        cidade: str


    Gerando o seguinte JSON de saída:
    {
        "id": 1,
        "nome": "João",
        "endereco": {
            "rua": "Avenida Paulista",
            "cidade": "São Paulo"
        }
    }
    """

    _ref_counter: int = 0

    name: str
    storage_name: str
    expected_type: ty.Any
    not_null: bool

    description: str

    def __init__(self, description: str = '') -> None:
        """
        -----------
        Parameters:
        -----------

        - description: Descrição deste campo na documentação.
        """
        self.description = description

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1
