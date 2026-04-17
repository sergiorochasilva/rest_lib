# APIs Desktop

A partir da versão 2.9.0, o RestLib tem suporte ao empacotamento de APIs em arquivo executável (CLI: Command Line Interface), com o objetivo de viabilizar uma arquitetura de implementação onde um mesmo código fonte python passa ser usado tanto para distribuição como API Rest normal, como para uso vinha linha de comando (sem necessidade de nenhum tpo de refatoração).

## Ideia Básica
Em resumo, a biblioteca foi adaptada para que todas as rotas genéricas (ListRoute, GetRoute, PostRoute, PutRoute e PatchRoute) possam ser executadas por meio da passagem de parâmetros que representem as três formas de entrada de dados nas APIs HTTP. A saber:

* **url_pars:** Dados contidos no path da URL.
* **query_args:** Dados contidos após o caracter "?" da URL (passados como query string, do tipo `par x valor`).
* **body:** Dados contidos no corpo da requisição (json).

A ideia básica então é que, na execução da API empacotada como CLI, é necessário passar um parâmetro do tipo JSON, o qual deve ser construído da seguinte maneira:

```json
{
    "url_pars": {...},
    "query_args": {...},
    "body": {...}
}
```

Assim, a aplicação CLI será capaz de dispensar o uso dos recursos do Flask, e passará os dados, necessários à execução do código fonte, direto pelo dicionário passado na entrada.

## Parâmetros da linha de comando

Além do JSON com as entradas, o CLI também precisará receber parâmetros com as informações necessárias para a conexão com o BD, e, é claro, uma string de indentificação do comando em si a ser executado (isso é, da rota REST a ser chamada). Os parâmetros de entrada suportados, portanto, serão:

* **-t ou --host:** IP ou nome do servidor de banco de dados.
* **-p ou --port:** Porta do servidor de banco de dados.
* **-n ou --name:** Nome do banco de dados.
* **-u ou --user:** Usuário para conexão com banco de dados.
* **-s ou --password:** Senha para conexão com o banco de dados.
* **-c ou --command:** Identificador do comando a ser executado (exemplo 'list_empresa_erp3').
* **-j ou --json:** Json das entradas (conforme explicado antes).

Um exemplo de linha de comando completa seria:

> dados-mestre.exe --command list_fornecedores_erp3 --host localhost --password mysecretpassword --name nasajon --port 5490 --user projeto --json eyJ1cmxfcGFycyI6e30sICJxdWVyeV9hcmdzIjp7ImZpZWxkcyI6ImVuZGVyZWNvcyIsICJncnVwb19lbXByZXNhcmlhbCI6Ik5BU0FKT04ifSwgImJvZHkiOnt9fQ==

### Parâmetro command

Tradicionalmente, para criação de uma rota com o RestLib, é necessário decorar um método python com um dos decorators de rotas genéricas: _ListRoute, GetRoute, PostRoute, PutRoute ou PatchRoute_.

Portanto, para simplificar a implementação, o próprio nome dos métodos sendo decorados será usado como valor para o parâmetro command. Por exemplo, na declaração da rota de recuperação de uma empresa, pelo ID, mostrado abaixo, o parâmetro a ser passado seria `--command get_empresa_erp3`:

```python
@application.route(f"{ROUTE}/<id>", methods=["GET"])
@auth.requires_api_key_or_access_token()
@multi_database()
@GetRoute(
    url=f"{ROUTE}/<id>",
    http_method="GET",
    dto_class=EmpresaERP3DTO,
    entity_class=EmpresaERP3Entity,
    injector_factory=InjectorFactoryMultibanco,
)
def get_empresa_erp3(_, response):
    return response
```

### Parâmetro json

Embora já tenhamos exmplicado esse parâmetro na seção de "Ideia Básica", vale dar um exemplo compatível com o exemplo de recuperação de uma empresa, da seção imediatamente acima:

```json
{
    "url_pars": {"id": "13485926000166"},
    "query_args": {"fields":"enderecos", "grupo_empresarial":"NASAJON"},
    "body":{}
}
```

Nesse caso, estaríamos recuperando a empresa com ID "13485926000166", trazendo a propriedade "enderecos" (mesmo que esta não esteja no resumo da entidade), e filtrando os dados pelo grupo_empresarial "NASAJON".

## Passo a passo para usar o recurso (na implementação de novas APIs/CLI)

Esse passo a passo pressupõe que sua aplicação já utiliza o RestLib para expôr APIs Rest.

1. Atualize a versão do NsjRestLib do seu projeto, no mínimo para `rest_lib==2.9.0`.
2. Atualize a versão do MultiDatabaseLib para, no mínimo: `nsj-multi-database-lib==1.1.0`.
3. Crie um arquivo `cli.py` em sua aplicação, conforme o exemplo abaixo. Esse arquivo será o ponto de entrada para execução de sua aplicação em linha de comando:

```python
# Importando o "cli" padrão no RestLib
from rest_lib.cli import main

# TODO Esse import precisa ser por projeto (para que todas as rotas sejam declaradas)
from nasajon import wsgi

if __name__ == "__main__":
    main()
```

Note que o import do `wsgi` (ponto de entrada de sua aplicação Flask), deve ser feito no seu `cli.py` customizado, isso porque é no wsgi que todos os controllers são importados, e, portanto, as rotas são declaradas (no caso, registradas para execução como comando).

4. Crie um arquivo `build-cli.bat` na raiz do seu repositório, com conteúdo como segue (ajuste nome e path conforme sua aplicação):

```bat
pip install pyinstaller==6.3.0
pyinstaller --hidden-import=pg8000 --onefile --name "dados-mestre" --paths=./.venv/Lib/site-packages ./nasajon/cli.py
```

5. Execute o arquivo `build-cli.bat` (cuidado para rodar dentro de um venv, para não instalar o pyinstaller no ambiente python global de sua máquina):

> .\build-cli.bat

**Obs.: Se você utilizar venv, é necessário estar com o venv ativo, e todas os requirements instalados nomesmo, para rodar o comando acima.**

## Funcionamento interno

Conforme explicado superficilamente na introdução, o RestLib foi melhorado para registrar as rotas declaradas como comandos, bem como para conter uma implementação genérica do tipo CLI (Command Line Interface), de tal modo que seja possível invocar qualquer das rotas definidas em controller, como um ponto de entrada via linha de comando. Contudo, como se dá internamente o registro dessas rotas?

Nesta sessão, vamos apresentar, resumidamente, como se dá o registro e a execução das rotas via CLI:

### Registro das rotas como comandos

1. Ao registrar uma nova rota, conforme o padrão do RestLib, ter-se-á um código semelhante ao que se segue:

```python
@application.route(f"{ROUTE}/<id>", methods=["GET"]) # Não faz parte do RestLib, mas sim do Flask
@auth.requires_api_key_or_access_token() # Não faz parte do RestLib, mas sim do nsj-flask-auth
@multi_database() # Não faz parte do RestLib, mas sim do nsj-multi-database-lib
@GetRoute(
    url=f"{ROUTE}/<id>",
    http_method="GET",
    dto_class=EmpresaERP3DTO,
    entity_class=EmpresaERP3Entity,
    injector_factory=InjectorFactoryMultibanco,
)
def get_empresa_erp3(_, response):
    return response
```

2. Ao se utilizar um dos decoradores de rota do RestLib (ListRoute, GetRoute, PostRoute, PutRoute e PatchRoute), a biblioteca, internamente, irá registrar a rota com o nome do método (no exemplo acima `get_empresa_erp3`), como um `CommandRoute` no singleton `CommandRouter` (ver método `__call__` da classe `RouteBase`).
3. Assim, cada `CommandRoute` registrado fica indexado num dict, interno ao singleton, por meio do nome do método. E, cada `CommandRoute` contém uma referência para a função a ser executada, bem como para o objeto de `RouteBase`, do próprio RestLib, que contém os metados da rota criada.

### Execução das rotas como comandos

1. Ao se executar o método `main` do módulo `rest_lib.cli`, esse método irá procurar pelos argumentos da linha de comando, bem como decodificar o json recebido em formato base64.
2. Em seguida, já no método `internal_main`, as variáveis de ambiente abaixo serão forçosamente sobrescritas:

* `ENV = erp_sql`
* `DATABASE_HOST = <valor do parâmetro --host>`
* `DATABASE_PASS = <valor do parâmetro --password>`
* `DATABASE_PORT = <valor do parâmetro --port>`
* `DATABASE_NAME = <valor do parâmetro --name>`
* `DATABASE_USER = <valor do parâmetro --user>`
* `DATABASE_DRIVER = POSTGRES`

3. O método a ser executado, é recuperado por meio do valor do parâmetro `--command`, a partir do singleton `CommandRouter`.
4. O método, previamente registrado, é então executado conforme o código abaixo:

```python
resp_body, resp_status, _ = route.func(
    **url_pars,
    query_args=query_args,
    body=body,
)
```

Note que as partes do json de entrada são passadas de tal modo que:

* **url_pars:** Os parâmetros de URL são todos passados como argumentos diretos do método de execução da rota (conforme rege o próprio padrão do Flask).
* **query_args:** Os argumentos passados como query string são passados num dict, e, cada implementação interna das rotas genéricas do RestLib foi refatorada para utilizar essa parâmetro, em lugar do `request.args` do Flask (apenas quando a variável de ambiente ENV for igual a `erp_sql`).
* **body:** O corpo da requisição é passado num dict, e, cada implementação interna das rotas genéricas do RestLib foi refatorada para utilizar esse dict, em lugar do `request.json` do Flask (apenas quando a variável de ambiente ENV for igual a `erp_sql`).

5. A retorno do método executado é tratado, de modo que qualquer http status entre 200 e 300 resulta numa saída 0, e qualquer outro status resulta em saída 1.
6. Adicionalmente, o corpo da resposta em si é impresso como stdout do CLI (em formato base64).

## Dúvidas diversas?

### Por que se optou pelo uso do formato base64 no json de entrada e no json de saída?

Acontece que o padrão base64 (super simplificando) transforma cada 6 bits de um byte em um caracter novo (na verdade, cada 3 bytes se tornam em quatro), resultando apenas em caracteres simples e passíveis de impressão em texto (um tipo de ASCII6).

Isso gera um desperdício de cerca de 8 bits, a cada 3 bytes (cerca de 33% de aumento). Mas também resulta numa string simples e segura, sem caracteres especiais, nem nehuma necessidade de escape complexo. Simplificando as tratativas de transporte dos dados na entrada da linha de comando, e na saída da execução.