# DTOSQLJoinField

Esse tipo de field representa um campo cujo valor é preenchido por meio de Join com outra entidade (impactando diretamente na consulta SQL gerada no banco de dados). E, portanto, deve ser usado com temperança (visto que impacta na velocidade das queries).

Além de permitir a recuperação de dados de outras entidades, esse tipo de field também pode ser usado como filtro, viabilizando casos de uso como listagem dos Rateios Padrão de um determinado Grupo Empresarial, sendo que filtrando pelo código do grupo (mesmo que na tabela de rateio só conste o ID do grupo relacionado).

_Obs.: Por hora, a query gerada não considera os campos de particinamento no join. Portanto deve-se ter cuidado com seu uso em bancos multi-tenant._

## Sintaxe básica:

Segue exemplo simples onde se deseja pegar o campo "id" do Grupo Empresarial (que nesse caso é o Código), e trazê-lo para o DTO corrente:

```py
from rest_lib.descriptor.dto_sql_join_field import DTOSQLJoinField, DTOJoinFieldType

grupo_empresarial: str = DTOSQLJoinField(
    dto_type=GrupoEmpresarialERP3DTO,
    entity_type=GrupoEmpresarialERP3Entity,
    related_dto_field="id",
    relation_field="grupo_empresarial_id",
    entity_relation_owner=EntityRelationOwner.SELF,
    join_type=DTOJoinFieldType.INNER,
    resume=False,
)
```

Abaixo, segue as descições das propriedades disponíveis (destacando-se os campos principais):

* **dto_type:** Classe do DTO relacionado (cuja entidade se deseja fazer join, e para o qual se apontará o campo a ser utilizado).
* **entity_type:** Classe da Entity relacionada (cuja entidade se deseja fazer join).
* **related_dto_field:** Nome do campo, no DTO relacionado, a ser copiado para o campo do DTO corrente.
* **relation_field:** Nome do campo, usado na query, para correlacionar as entidades (correspondente ao campo usado no "on" de um "join").
* **entity_relation_owner:** Indica qual entidade contém o campo que aponta o relacionamento (se for EntityRelationField.OTHER, implica que a entidade apontada pela classe de DTO passada no decorator, é que contem o campo; se for o EntityRelationField.SELF, indica que o próprio DTO que contém o campo).
* **join_type:** Indica o tipo de Join a ser realizado na query (LEFT, INNER ou FULL).
* not_null: O campo não poderá ser None, ou vazio, no caso de strings.
* resume: O campo será usado como resumo, isto é, será sempre rotornado num HTTP GET que liste os dados (mesmo que não seja solicitado por meio da query string "fields").
* validator: Função que recebe o valor (a ser atribuído), e retorna o mesmo valor após algum tipo de tratamento (como adição ou remoção, automática, de formatação).
* use_default_validator: Flag indicando se o validator padrão deve ser aplicado à propriedade (esse validator padrão verifica o tipo de dados passado, e as demais verificações recebidas no filed, como, por exemplo, valor máximo, mínio, not_null, etc).