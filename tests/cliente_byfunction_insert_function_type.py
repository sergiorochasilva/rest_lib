from rest_lib.decorator.insert_function_type import InsertFunctionType
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.descriptor.function_relation_field import FunctionRelationField
from rest_lib.entity.function_type_base import InsertFunctionTypeBase


@InsertFunctionType(
    type_name="teste.tendereco",
)
class ClienteByfunctionEnderecoInsertType(InsertFunctionTypeBase):
    tipologradouro: str = FunctionField()
    logradouro: str = FunctionField()
    numero: str = FunctionField()
    complemento: str = FunctionField()
    cep: str = FunctionField()
    bairro: str = FunctionField()
    tipo: int = FunctionField(type_field_name="tipo")
    enderecopadrao: int = FunctionField()
    referencia: str = FunctionField()
    uf: str = FunctionField()
    cidade: str = FunctionField()


@InsertFunctionType(
    type_name="teste.tclientenovo",
)
class ClienteByfunctionInsertType(InsertFunctionTypeBase):
    codigo: str = FunctionField()
    nome: str = FunctionField()
    nomefantasia: str = FunctionField()
    identidade: str = FunctionField()
    documento: str = FunctionField()
    inscricaoestadual: str = FunctionField()
    retemiss: bool = FunctionField()
    retemir: bool = FunctionField()
    retempis: bool = FunctionField()
    retemcofins: bool = FunctionField()
    retemcsll: bool = FunctionField()
    reteminss: bool = FunctionField()
    enderecos: list[ClienteByfunctionEnderecoInsertType] = (
        FunctionRelationField(type_field_name="endereco")
    )
