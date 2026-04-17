import typing as ty

from rest_lib.descriptor.function_field import FunctionField
from rest_lib.entity.function_type_base import FunctionTypeBase


class FunctionRelationField(FunctionField):
    """
    Descriptor usado por FunctionType (insert/update) para declarar campos de
    relacionamento que apontam para outros FunctionType. O tipo esperado deve ser
    declarado via typing annotations.
    """

    def __init__(self, type_field_name: str | None = None, description: str = ""):
        super().__init__(type_field_name=type_field_name, description=description)
        self.related_type: ty.Optional[ty.Type[FunctionTypeBase]] = None
        self.multiple: bool = False

    def configure_related_type(self, annotation: ty.Any, field_name: str):
        """
        Analisa a anotação do campo para identificar o tipo relacionado e
        se trata-se de um relacionamento 1x1 ou 1xN.
        """

        related_annotation, multiple = self._extract_related_annotation(annotation)
        if related_annotation is None:
            raise ValueError(
                f"É necessário anotar o campo '{field_name}' com um FunctionType válido."
            )

        if not issubclass(related_annotation, FunctionTypeBase):
            raise ValueError(
                f"O campo '{field_name}' deve ser anotado com uma classe que herde de FunctionTypeBase."
            )

        self.related_type = related_annotation
        self.multiple = multiple

    def _extract_related_annotation(self, annotation: ty.Any):
        origin = ty.get_origin(annotation)
        args = ty.get_args(annotation)

        if origin is ty.Union:
            non_none_args = [arg for arg in args if arg is not type(None)]  # noqa: E721
            if len(non_none_args) == 1:
                return self._extract_related_annotation(non_none_args[0])
            return (None, False)

        if origin in (list, ty.List):
            if not args:
                return (None, True)
            return (args[0], True)

        return (annotation, False)
