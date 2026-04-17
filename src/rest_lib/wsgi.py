# Importando arquivos de configuração
import rest_lib.db_pool_config
from rest_lib.settings import application

# Configurando o healthcheck
from rest_lib.healthcheck_config import HealthCheckConfig

HealthCheckConfig(flask_application=application).config(True)

import tests.cliente_controller
import tests.classificacao_financeira_controller
import tests.cliente_byfunction_controller

if __name__ == "__main__":
    application.run(port=5000)
