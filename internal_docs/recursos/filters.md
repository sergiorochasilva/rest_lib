# [Filter](../../src/rest_lib/entity/filter.py)
A classe `Filter` é uma representação de um filtro que pode ser aplicado a uma consulta em um banco de dados, ou a uma coleção de dados. Um filtro é composto por um FilterOperator e um valor que será usado para realizar a comparação.

Por padrão, todos os campos declarados num DTO (pelos descritores DTOField e DTOSQLJoinField) são passíveis de filtro, bastando adicionar na URL de GET: ```<nome_do_campo>=<valor>```. Mas, esse tipo de filtro está restrito à comparação de igualdade.

Por meio da declaração de filtros, é possível criar novos filtros que trabalhem com outros tipos de operadores, cumprindo assim o Guidelines interno, que padroniza filtros sem operadores explícitos.

## Tipos de Operadores (enumerado FilterOperator)
```
EQUALS = "equals"
DIFFERENT = "diferent"
GREATER_THAN = "greater_than"
LESS_THAN = "less_than"
GREATER_OR_EQUAL_THAN = "greater_or_equal_than"
LESS_OR_EQUAL_THAN = "less_or_equal_than"
LIKE = "like"
ILIKE = "ilike"
NOT_NULL = "not_null"
```

**Exemplo:**
```
from rest_lib.entity.filter import Filter, FilterOperator

Filter(FilterOperator.GREATER_THAN, 'criado_apos')
```