def _convert_to(obj: object, new_dto_class):
    new_obj = new_dto_class()

    for attribute in new_obj.__dict__:
        if not hasattr(obj, attribute):
            continue

        attr_source = getattr(obj, attribute, None)
        attr_target = getattr(new_obj, attribute, None)

        if callable(attr_source) or callable(attr_target):
            continue

        setattr(new_obj, attribute, attr_source)

    return new_obj


def convert_to(obj: object, new_dto_class):
    """
    Converte objeto(s) para uma nova classe DTO copiando apenas
    atributos que existam no objeto de destino.
    """
    if isinstance(obj, list):
        return [_convert_to(item, new_dto_class) for item in obj]
    return _convert_to(obj, new_dto_class)
