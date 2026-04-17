import os
import base64
import requests

from healthcheck import HealthCheck

from rest_lib.injector_factory_base import NsjInjectorFactoryBase


class HealthCheckConfig:
    def __init__(
        self,
        flask_application,
        injector_factory_class: NsjInjectorFactoryBase = None,
        app_name: str = None,
        rabbitmq_host: str = None,
        rabbitmq_http_port: int = None,
        rabbitmq_user: str = None,
        rabbitmq_pass: str = None,
    ):
        self._flask_application = flask_application
        self._injector_factory_class = injector_factory_class or NsjInjectorFactoryBase
        self._app_name = app_name or os.getenv('APP_NAME')
        self._rabbitmq_host = rabbitmq_host or os.getenv('RABBITMQ_HOST')
        self._rabbitmq_http_port = rabbitmq_http_port or int(
            os.getenv('RABBITMQ_HTTP_PORT', 15672))
        self._rabbitmq_user = rabbitmq_user or os.getenv(
            'RABBITMQ_USER', 'guest')
        self._rabbitmq_pass = rabbitmq_pass or os.getenv(
            'RABBITMQ_PASS', 'guest')

    def check_database(self):
        with self._injector_factory_class() as factory:
            sql = "SELECT 1"

            factory.db_adapter().execute_query(sql)

            return True, "Banco de dados OK"

    def check_rabbit_mq(self):
        rabbit_url = f"{self._rabbitmq_host}:{self._rabbitmq_http_port}/api/healthchecks/node"
        if rabbit_url[0:4] != 'http':
            rabbit_url = 'http://' + rabbit_url

        credentials = f"{self._rabbitmq_user}:{self._rabbitmq_pass}"
        credentials = credentials.encode('utf8')
        credentials = base64.b64encode(credentials)
        credentials = credentials.decode('utf8')

        headers = {
            "Authorization": f"Basic {credentials}"
        }

        response = requests.get(rabbit_url, headers=headers)

        if response.status_code == 200:
            return True, "RabbitMQ OK"
        else:
            return False, f"Falha de comunicação com o RabbitMQ"

    def config(
        self,
        check_database: bool = True,
        check_rabbit_mq: bool = False
    ):

        health = HealthCheck()

        # Adicionando a validação de banco de dados
        if check_database:
            health.add_check(self.check_database)

        # Adicionando a validação do RabbitMQ
        if check_rabbit_mq:
            health.add_check(self.check_rabbit_mq)

        # Registrando a rota do HealthCheck
        if self._app_name is not None:
            self._flask_application.add_url_rule(f"/{self._app_name}/healthcheck", "healthcheck",
                                                 view_func=lambda: health.run())
        else:
            self._flask_application.add_url_rule(f"/healthcheck", "healthcheck",
                                                 view_func=lambda: health.run())
