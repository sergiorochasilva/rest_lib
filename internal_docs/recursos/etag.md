# ETag em GET unitario

Este recurso adiciona suporte a ETag nas rotas de GET por ID.

Arquivos relacionados:
- [get_route](src/rest_lib/controller/get_route.py)
- [route_base](src/rest_lib/controller/route_base.py)
- [dto_decorator](src/rest_lib/decorator/dto.py)
- [dto](src/rest_lib/dto/dto_base.py)

## Como habilitar
- Configure o decorator `DTO` com `etag_fields` e, se necessario, `etag_type`.
- Por padrao (`etag_fields=True`), o ETag usa os campos de resumo (`resume_fields`).
- Para adicionar campos extras, passe um `set[str]` em `etag_fields`.
- Para desabilitar o ETag, use `etag_fields=False`.
- `etag_type` suporta:
  - `HASH` (default): concatena os valores e aplica SHA-256.
  - `RAW`: usa a concatenacao direta dos valores.
  - `DATE`: exige exatamente um campo e compara por data (ISO 8601).

Exemplo:
```python
from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.dto.dto_base import DTOBase

@DTO(etag_fields={"version", "updated_at"}, etag_type="HASH")
class ClienteDTO(DTOBase):
    id: int = DTOField(pk=True)
    version: str = DTOField()
    updated_at: datetime.datetime = DTOField()
```

## Resposta com ETag
- Quando o campo configurado possui valor, o GET por ID inclui o header `ETag`.
- O header e sempre retornado como weak etag, com prefixo `W/`.
- O valor e sempre retornado entre aspas e com escape de `"`.

## If-None-Match
- Se o header `If-None-Match` contem o valor atual, a rota retorna `304` com corpo vazio e header `ETag`.
- Se nao houver match, retorna `200` com o payload completo e `ETag` atualizado.
- O header aceita multiplos valores entre aspas, separados por virgula, e suporta valores com `W/` (weak etag).
- Quando `etag_type` e `HASH`, o valor esperado no `If-None-Match` e o hash calculado.

## Observacoes de execucao
- Para comparar o ETag, o `RouteBase.handle_if_none_match` faz uma leitura rasa com `fields={'root': {pk_field} | etag_fields}` e sem expands.
- Os campos de ETag sao sempre incluidos no conjunto de fields, mesmo quando nao sao solicitados na query.
- O header `ETag` e adicionado via `RouteBase.add_etag_header_if_needed` quando `etag_fields` nao esta vazio.
