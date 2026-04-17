# Forçando a variável de ambiente ENV
import os

os.environ["ENV"] = "erp_sql"
os.environ["CRYPT_KEY"] = ""

import argparse
import base64
import sys

from rest_lib.controller.command_router import CommandRouter
from rest_lib.util import json_util


def codifica_ansi_base64(value: str):
    ansi_bytes = value.encode("cp1252")
    base64_bytes = base64.b64encode(ansi_bytes)
    return base64_bytes.decode("utf-8")


def internal_main(
    command: str,
    host: str,
    password: str,
    port: str,
    name: str,
    user: str,
    json: str,
    print_plain: bool = False,
):
    # Ajustando as variáveis de conexão com o banco de dados
    os.environ["DATABASE_HOST"] = host
    os.environ["DATABASE_PASS"] = password
    os.environ["DATABASE_PORT"] = port
    os.environ["DATABASE_NAME"] = name
    os.environ["DATABASE_USER"] = user
    os.environ["DATABASE_DRIVER"] = "POSTGRES"

    # Tratando das entradas
    command = command
    entrada = json_util.json_loads(json)

    # Processando a chamada
    try:
        # Desempacotando os parâmetros da chamada
        url_pars = entrada.get("url_pars")
        query_args = entrada.get("query_args")
        body = entrada.get("body")

        # Validando a entrada
        if url_pars is None or not isinstance(url_pars, dict):
            raise ValueError("Faltando parâmetro 'url_pars' (ou tipo incorreto).")
        if query_args is None or not isinstance(query_args, dict):
            raise ValueError("Faltando parâmetro 'query_args' (ou tipo incorreto).")
        if body is None or not isinstance(body, dict):
            raise ValueError("Faltando parâmetro 'body' (ou tipo incorreto).")

        # Recuperando a rota certa para chamar
        route = CommandRouter.get_instance().get(command)

        # Chamando a rota
        resp_body, resp_status, _ = route.func(
            **url_pars,
            query_args=query_args,
            body=body,
        )

        # Formatando a saída
        if resp_body is not None and resp_body.strip() != "":
            response = {"status": resp_status, "body": json_util.json_loads(resp_body)}
        else:
            response = {"status": resp_status, "body": {}}

    except Exception as e:
        response = {"status": 500, "body": f"Erro desconhecido: {e}"}

    # Codificando a saída em ansi e depois em base64
    saida = json_util.json_dumps(response)

    # Imprimindo a saída
    if print_plain:
        print(saida)
    else:
        print(codifica_ansi_base64(saida))

    if response["status"] >= 200 and response["status"] < 300:
        sys.exit(0)
    else:
        sys.exit(1)


def main():
    # Inicializando a lógica interna
    try:
        # Initialize parser
        parser = argparse.ArgumentParser(
            description="""
Utilitário para execução de APIs do RestLib por linha de comando.
"""
        )

        # Adding optional argument
        parser.add_argument(
            "-t",
            "--host",
            help="Host do banco de dados.",
        )

        parser.add_argument(
            "-p",
            "--port",
            help="Porta do banco de dados.",
        )

        parser.add_argument(
            "-s",
            "--password",
            help="Senha do banco de dados.",
        )

        parser.add_argument(
            "-n",
            "--name",
            help="Nome do banco de dados.",
        )

        parser.add_argument(
            "-u",
            "--user",
            help="Usuário do banco de dados.",
        )

        parser.add_argument(
            "-c",
            "--command",
            help="Identificador do comando a ser executado (exemplo 'list_empresa_erp3').",
        )

        parser.add_argument(
            "-j",
            "--json",
            help="""JSON de entrada do comando, seguindo formato:
{
    "url_pars": {
        str: any
    },
    "query_args": {
        str: any
    },
    "body": {
        str: any
    }
}

Onde:
- "url_pars": Representa os parâmetros que seria passados no path da chamada chamada HTTP (na parte da URL antes do "&").
- "query_args": Representa os parâmetros que seria passados por meio da própria URL, numa chamada HTTP (na parte que vem após o "&").
- "body": Representa o corpo da chamada HTTP.
""",
        )

        # Read arguments from command line
        args = parser.parse_args()

        # Desempacotando os dados
        json = base64.b64decode(args.json).decode(encoding="cp1252")
        json = json

        # Iniciando a execução
        internal_main(
            args.command,
            args.host,
            args.password,
            args.port,
            args.name,
            args.user,
            json,
        )
    except Exception as e:
        print(f"Erro fatal não identificado. Mensagem original do erro {e}")
        sys.exit(5)
