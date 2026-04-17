# [HealthCheck](../../src/rest_lib/healthcheck_config.py)
A classe `HealthCheckConfig` oferece uma configuração para verificação da saúde em uma aplicação Flask. Verificando o status do banco de dados e do servidor RabbitMQ. Parâmetro obrigatório na inicialização é o _flask_application_, outros parâmetros como: _injector_factory_class_, _app_name_, _rabbitmq_host_, _rabbitmq_http_port_, _rabbitmq_user_, _rabbitmq_pass_, serão recuperados das variáveis de ambiente e/ou nulos. Na `config` por padrão os parâmetros _check_database_ e _check_rabbit_mq_ virão True e False, podendo ser ajustados na chamada.

**Exemplo:**
```
#importando a classe
from rest_lib.healthcheck_config import HealthCheckConfig

HealthCheckConfig(
    flask_application=application
).config(check_database=True, check_rabbit_mq=False)
```