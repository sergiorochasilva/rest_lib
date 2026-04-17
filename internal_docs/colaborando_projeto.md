# Colaborando com o projeto

## Montando o ambiente de desenvolvimento
* Instalar todas as dependências do projeto.
```
pip install -r requirements.txt
```
* Subir o container do banco de testes, para cada teste pode ou não rodar o script contido no `global.sql`, basta configurar no `pre_setup` conforme necessidade.
``` 
docker-compose up -d postgres 
```
* Na configuração do Debug (launch.json), configure o Flask e o Pytest. Certifique-se de que o Flask esteja em execução para o Pytest funcionar corretamente.
```
    {
        "name": "Python: Flask",
        "type": "python",
        "request": "launch",
        "module": "flask",
        "env": {
            "FLASK_APP": "src/rest_lib/wsgi.py",
            "FLASK_DEBUG": "1"
        },
        "args": [
            "run",
            "--no-debugger",
            "--no-reload"
        ],
        "jinja": true,
        "justMyCode": true
    },
    {
        "name": "Pytest",
        "type": "python",
        "request": "launch",
        "module": "pytest",
        "args": [
            "-s",
            "tests/api/casos_de_teste"
        ]
    }
```

## Sobreescrevendo a dependência de seu projeto local, para utilizar o repositório clonado (e facilitar o teste de suas alterações)
A ideia aqui, é que, quando queremos melhorar o RestiLib, é bom testar os efeitos em nosso projeto. Mas, se tivermos que subir uma nova versão a cada ajuste, será um trabalho improdutivo, e que irá gerar versões demais.

Para rodar a biblioteca localmente, após a configuração da sua aplicação principal, siga os passos:

1. Clone a biblioteca:
`git clone git@github.com:Nasajon/rest_lib.git`
2. Desinstale a biblioteca no seu ambiente virtual da aplicação:
`pip uninstall rest-lib`
3. Na variável de ambiente PYTHONPATH localizado no .env da aplicação principal, coloque o caminho da biblioteca após o caminho da aplicação, entre :
`PYTHONPATH=/home/@work/dados-mestre-api:/home/@work/rest_lib/src`

## Criação dos testes
Para a criação dos casos de testes de forma automática pode seguir o exemplo ["Criação de caso de teste"](https://github.com/Nasajon/nsj-rest-test-util#cria%C3%A7%C3%A3o-de-caso-de-teste).

Neste contexto, foram desenvolvidos testes para entidade de clientes ([DELETE](tests/api/casos_de_teste/clientes/delete/test_clientes_delete.py), [GET](tests/api/casos_de_teste/clientes/get/test_clientes_get.py), [POST](tests/api/casos_de_teste/clientes/post/test_clientes_post.py) e [PUT](tests/api/casos_de_teste/clientes/put/test_clientes_put.py)).

## Testes Automatizados

Para executar os testes autoatizados já implementados, utilize o comando:

```sh
pytest -s tests/api/casos_de_teste
```

Obs.: Também disponível no makefile.

Abaixo, segue a estrutura dos testes automatizados disponíveis na própria biblioteca (casos simples, para não regressão do básico da ferramenta):

```
src/
│...
├── tests/
│   ├── api/
│   │   ├── casos_de_teste/
│   │   │   ├── clientes/
│   │   │   │   ├── delete/
│   │   │   │   │   ├── entradas_json/
│   │   │   │   │   │   ├── exemplo1_204.json
│   │   │   │   │   ├── saidas_json/
│   │   │   │   │   │   ├── exemplo1_204.json
│   │   │   │   │   ├── test_clientes_delete.py
│   │   │   │   ├── get/
│   │   │   │   │   ├── entradas_json/
│   │   │   │   │   │   ├── exemplo1_200.json
│   │   │   │   │   ├── saidas_json/
│   │   │   │   │   │   ├── exemplo1_200.json
│   │   │   │   │   ├── test_clientes_get.py
│   │   │   │   ├── post/
│   │   │   │   │   ├── entradas_json/
│   │   │   │   │   │   ├── exemplo1_201.json
│   │   │   │   │   ├── saidas_json/
│   │   │   │   │   │   ├── exemplo1_201.json
│   │   │   │   │   ├── test_clientes_post.py
│   │   │   │   ├── put/
│   │   │   │   │   ├── entradas_json/
│   │   │   │   │   │   ├── exemplo1_204.json
│   │   │   │   │   ├── saidas_json/
│   │   │   │   │   │   ├── exemplo1_204.json
│   │   │   │   │   ├── test_clientes_put.py
│   │   │   ├── dump_sql/
│   │   │   │   ├── global.sql             
```
