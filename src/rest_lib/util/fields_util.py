from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List, Optional, Set

FieldsTree = Dict[str, Any]


def _compose_path(parts: List[str], leaf: str) -> str:
    path_parts = [p for p in parts if p]
    if leaf:
        path_parts.append(leaf)
    return ".".join(path_parts)


def split_fields_expression(expression: Optional[str]) -> List[str]:
    """
    Converte a expressão de fields (usada na query string) em uma lista de caminhos
    no formato separado por ponto (ex: ["contatos.nome", "contatos.telefones.numero"]).
    """
    if expression is None:
        return []

    stack: List[str] = []
    token: List[str] = []
    paths: List[str] = []

    def flush() -> None:
        nonlocal token

        name = "".join(token).strip()
        if not name:
            token = []
            return

        path = _compose_path(stack, name)
        if path:
            paths.append(path)

        token = []

    for char in expression:
        if char == "(":
            name = "".join(token).strip()
            if not name:
                token = []
                continue

            stack.append(name)
            token = []
        elif char == ")":
            flush()
            if stack:
                stack.pop()
        elif char == ",":
            flush()
        else:
            token.append(char)

    flush()

    return paths


def build_fields_tree(paths: Iterable[str]) -> FieldsTree:
    """
    Constrói uma estrutura em árvore a partir de uma lista de caminhos separados por ponto.
    A estrutura resultante segue o padrão:

    {
        "root": {"contatos"},
        "contatos": {
            "root": {"nome", "telefones"},
            "telefones": {
                "root": {"numero"}
            }
        }
    }
    """
    tree: FieldsTree = {"root": set()}

    for raw_path in paths:
        if raw_path is None:
            continue

        path = raw_path.strip()
        if not path:
            continue

        parts = [part for part in path.split(".") if part]
        if not parts:
            continue

        _add_path(tree, parts)

    return tree


def _add_path(tree: FieldsTree, parts: List[str]) -> None:
    head, *tail = parts

    root_set = tree.setdefault("root", set())
    if not isinstance(root_set, set):
        raise TypeError("root entry must be a set of field names.")

    root_set.add(head)

    if not tail:
        return

    child = tree.get(head)
    if not isinstance(child, dict):
        child = {"root": set()}
        tree[head] = child

    _add_path(child, tail)


def parse_fields_expression(expression: Optional[str]) -> FieldsTree:
    """
    Converte a expressão textual dos fields em uma estrutura de árvore.
    """
    paths = split_fields_expression(expression)
    return build_fields_tree(paths)


def merge_fields_tree(target: FieldsTree, source: FieldsTree) -> None:
    """
    Mescla a árvore de fields "source" dentro de "target".
    """
    target_root = target.setdefault("root", set())
    source_root = source.get("root", set())

    if not isinstance(target_root, set):
        raise TypeError("root entry must be a set of field names.")
    if not isinstance(source_root, set):
        raise TypeError("root entry must be a collection of field names.")

    target_root |= source_root

    for key, value in source.items():
        if key == "root":
            continue

        if not isinstance(value, dict):
            raise TypeError("expected nested dict for related field")

        child = target.get(key)
        if not isinstance(child, dict):
            child = {"root": set()}
            target[key] = child

        merge_fields_tree(child, value)


def normalize_fields_tree(fields: Optional[Dict[str, Any]]) -> FieldsTree:
    """
    Normaliza uma estrutura de fields possivelmente no formato antigo
    (dict de sets) para a estrutura em árvore.
    """
    if fields is None:
        return {"root": set()}

    if not isinstance(fields, dict):
        raise TypeError("fields must be a dict mapping field names to sets/dicts")

    result: FieldsTree = {}
    for key, value in fields.items():
        if key == "root":
            result["root"] = _ensure_set(value)
            continue

        if isinstance(value, dict):
            result[key] = normalize_fields_tree(value)
        else:
            result[key] = {"root": _ensure_set(value)}

    result.setdefault("root", set())
    return result


def extract_child_tree(fields: FieldsTree, field_name: str) -> FieldsTree:
    """
    Recupera (sem modificar a estrutura original) a subárvore referente ao campo informado.
    Retorna uma árvore vazia caso o campo não esteja presente.
    """
    value = fields.get(field_name)

    if value is None:
        return {"root": set()}

    if isinstance(value, dict):
        return copy.deepcopy(value)

    return {"root": _ensure_set(value)}


def clone_fields_tree(fields: FieldsTree) -> FieldsTree:
    """
    Retorna uma cópia profunda da árvore de fields.
    """
    return copy.deepcopy(fields)


def _ensure_set(value: Any) -> Set[str]:
    if isinstance(value, set):
        return set(value)
    if isinstance(value, list) or isinstance(value, tuple):
        return set(value)
    raise TypeError("expected a collection of field names")
