import functools
from typing import Optional, Type

from rest_lib.descriptor.function_relation_field import FunctionRelationField
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.entity.function_type_base import FunctionTypeBase


class FunctionType:
    type_base_class: Type[FunctionTypeBase] = FunctionTypeBase

    def __init__(self, type_name: str) -> None:
        """
        Cria um decorator para declarar um *FunctionType* associado
        a um TYPE composto do banco de dados (PL/pgSQL).

        O parâmetro ``type_name`` deve conter o nome totalmente
        qualificado do TYPE no banco (por exemplo
        ``\"teste.tclassificacaofinanceiranovo\"``). Esse valor é
        copiado para o atributo de classe ``type_name`` da classe
        decorada, e é usado posteriormente pelo DAO para montar o
        bloco PL/pgSQL que instancia o TYPE e chama a função. O uso
        varia conforme a operação:

        - ``InsertFunctionType`` e ``UpdateFunctionType``:
          ``type_name`` indica o TYPE aceito pelas funções de
          INSERT/UPDATE (ex.: ``a_objeto teste.tminhafuncaoinsert``),
          permitindo que o Service construa um registro desse TYPE a
          partir do DTO e delegue a operação para a função PL/pgSQL.
        - ``GetFunctionType``, ``ListFunctionType`` e
          ``DeleteFunctionType``: ``type_name`` indica o TYPE usado
          como “objeto de parâmetros” das funções de GET/LIST/DELETE.
          Se a rota/serviço receber um FunctionType desse tipo, a
          chamada será feita via ``_call_function_with_type``; caso
          contrário, a chamada ocorre em modo RAW (parâmetros simples).

        Em resumo: ``type_name`` é **sempre** o nome do TYPE (não o
        nome da função) que será instanciado e passado como argumento
        para a função de banco.
        """
        if not type_name:
            raise ValueError("O parâmetro 'type_name' é obrigatório.")

        self.type_name = type_name

    def __call__(self, cls: Type[FunctionTypeBase]):
        functools.update_wrapper(self, cls)

        if not issubclass(cls, self.type_base_class):
            raise ValueError(
                f"Classes decoradas com @{self.__class__.__name__} devem herdar de {self.type_base_class.__name__}."
            )

        self._check_class_attribute(cls, "type_name", self.type_name)
        self._check_class_attribute(cls, "fields_map", {})
        self._check_class_attribute(cls, "_dto_function_mapping_cache", {})

        annotations = dict(getattr(cls, "__annotations__", {}) or {})

        for key, attr in cls.__dict__.items():
            descriptor: Optional[FunctionField] = None

            if isinstance(attr, (FunctionField, FunctionRelationField)):
                descriptor = attr
            elif key in annotations:
                descriptor = attr
                if not isinstance(attr, (FunctionField, FunctionRelationField)):
                    descriptor = FunctionField()

            if descriptor:
                descriptor.storage_name = key
                descriptor.name = key
                if key in annotations:
                    descriptor.expected_type = annotations[key]
                    if isinstance(descriptor, FunctionRelationField):
                        descriptor.configure_related_type(annotations[key], key)
                cls.fields_map[key] = descriptor

        pk_fields = [
            name
            for name, desc in getattr(cls, "fields_map", {}).items()
            if getattr(desc, "pk", False)
        ]
        if len(pk_fields) > 1:
            raise ValueError(
                f"FunctionType '{cls.__name__}' possui mais de um campo marcado como pk."
            )
        cls.pk_field_name = pk_fields[0] if pk_fields else None

        return cls

    def _check_class_attribute(self, cls: object, attr_name: str, value):
        if attr_name not in cls.__dict__:
            setattr(cls, attr_name, value)
