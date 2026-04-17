import logging
import os

from flask import Flask

try:
    from opentelemetry import metrics as _otel_metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
except ModuleNotFoundError:
    _otel_metrics = None
    MeterProvider = None
    PeriodicExportingMetricReader = None
    OTLPMetricExporter = None

# Lendo variáveis de ambiente
APP_NAME = os.getenv("APP_NAME", "rest_lib")
MOPE_CODE = os.getenv("MOPE_CODE")
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 20))
DATABASE_DRIVER = os.getenv("DATABASE_DRIVER", "POSTGRES")
USE_SQL_RETURNING_CLAUSE = (
    os.getenv(
        "USE_SQL_RETURNING_CLAUSE",
        "false" if DATABASE_DRIVER.upper() == "MYSQL" else "true",
    ).lower()
    == "true"
)

DATABASE_HOST = os.getenv("DATABASE_HOST", "")
DATABASE_PASS = os.getenv("DATABASE_PASS", "")
DATABASE_PORT = os.getenv("DATABASE_PORT", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "")
DATABASE_USER = os.getenv("DATABASE_USER", "")
ENV_MULTIDB = os.getenv("ENV_MULTIDB", "false").lower()

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 1))

CLOUD_SQL_CONN_NAME = os.getenv("CLOUD_SQL_CONN_NAME", "")
ENV = os.getenv("ENV", "")

REST_LIB_AUTO_INCREMENT_TABLE = os.getenv(
    "REST_LIB_AUTO_INCREMENT_TABLE", "seq_control"
)


def get_logger():
    """Retorna o logger padrao da aplicacao."""
    return logging.getLogger(APP_NAME)


if ENV_MULTIDB == "true":
    get_logger().warning(
        "Atenção! Todas as propriedades (colunas) do tipo tenant serão ignoradas nos DTOs."
    )


class _NoOpCounter:
    """Counter no-op usado quando telemetria esta indisponivel."""

    def add(self, value, attributes):
        """Ignora envio de metrica quando OpenTelemetry nao esta ativo."""
        return None


class _NoOpMeter:
    """Meter no-op usado quando telemetria esta indisponivel."""

    def create_counter(self, name, description=""):
        """Retorna um counter no-op para manter compatibilidade."""
        return _NoOpCounter()


class _NoOpMetrics:
    """Facade no-op para manter a interface minima de metricas."""

    @staticmethod
    def get_meter(metric_name):
        """Retorna meter no-op para chamadas de instrumentacao."""
        return _NoOpMeter()


def _configure_metrics():
    """Configura e retorna o provider de metricas, com fallback no-op."""
    if _otel_metrics is None:
        get_logger().warning("OpenTelemetry nao instalado; telemetria desabilitada.")
        return _NoOpMetrics()

    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "otel-collector.prometheus-otel:4317")
    try:
        otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
        reader = PeriodicExportingMetricReader(otlp_exporter)
        provider = MeterProvider(metric_readers=[reader])
        _otel_metrics.set_meter_provider(provider)
        return _otel_metrics
    except Exception:
        get_logger().exception(
            "Falha ao configurar OpenTelemetry; telemetria desabilitada."
        )
        return _NoOpMetrics()


# Interface de metricas consumida pelos decorators da rest_lib.
metrics = _configure_metrics()

application = Flask("app")
