import uuid

from rest_lib.decorator.insert_function_type import InsertFunctionType
from rest_lib.decorator.update_function_type import UpdateFunctionType
from rest_lib.decorator.list_function_type import ListFunctionType
from rest_lib.decorator.get_function_type import GetFunctionType
from rest_lib.decorator.delete_function_type import DeleteFunctionType
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
    ListFunctionTypeBase,
    GetFunctionTypeBase,
    DeleteFunctionTypeBase,
)


@InsertFunctionType(
    type_name="teste.tclassificacaofinanceiranovo",
)
class ClassificacaoFinanceiraInsertType(InsertFunctionTypeBase):
    id: uuid.UUID = FunctionField(type_field_name="idclassificacao")
    codigo: str = FunctionField()
    descricao_func: str = FunctionField(type_field_name="descricao")
    codigocontabil: str = FunctionField()
    resumo: str = FunctionField()
    natureza: int = FunctionField()
    paiid: uuid.UUID = FunctionField(type_field_name="classificacaopai")
    grupoempresarial: uuid.UUID = FunctionField()
    transferencia: bool = FunctionField()
    repasse_deducao: bool = FunctionField()
    rendimentos: bool = FunctionField()


@UpdateFunctionType(
    type_name="teste.tclassificacaofinanceiraalterar",
)
class ClassificacaoFinanceiraUpdateType(UpdateFunctionTypeBase):
    classificacao: uuid.UUID = FunctionField()
    classificacaopai: uuid.UUID = FunctionField()
    grupoempresarial: uuid.UUID = FunctionField()
    codigo: str = FunctionField()
    descricao: str = FunctionField()
    codigocontabil: str = FunctionField()
    resumo: str = FunctionField()
    situacao: int = FunctionField()
    natureza: int = FunctionField()
    transferencia: bool = FunctionField()
    repasse_deducao: bool = FunctionField()
    rendimentos: bool = FunctionField()


@ListFunctionType(type_name="teste.tclassificacaofinanceiralist")
class ClassificacaoFinanceiraListType(ListFunctionTypeBase):
    id: uuid.UUID = FunctionField(type_field_name="classificacao")
    codigo: str = FunctionField()
    descricao: str = FunctionField(type_field_name="descricao_func")
    grupoempresarial: uuid.UUID = FunctionField(
        pk=True, type_field_name="grupo_empresarial"
    )


@GetFunctionType(type_name="teste.tclassificacaofinanceiraget")
class ClassificacaoFinanceiraGetType(GetFunctionTypeBase):
    classificacao: uuid.UUID = FunctionField(pk=True)
    codigo: str = FunctionField()
    descricao_func: str = FunctionField()
    grupo_empresarial: uuid.UUID = FunctionField()


@DeleteFunctionType(type_name="teste.tclassificacaofinanceiraexcluir")
class ClassificacaoFinanceiraDeleteType(DeleteFunctionTypeBase):
    classificacao: uuid.UUID = FunctionField(pk=True)
    grupo_empresarial: uuid.UUID = FunctionField()
