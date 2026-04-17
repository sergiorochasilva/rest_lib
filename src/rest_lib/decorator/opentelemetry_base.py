import functools
from flask import request
from rest_lib.settings import get_logger, metrics
from rest_lib.util.time_grouping import TimeGrouping, get_time_grouping


class OpenTelemetryBase:
    def __init__(
        self,
        route: str,
        metric_name: str,
        counter_name: str,
        description_counter: str = "",
        tenant_field: str = "tenant",
        grupo_empresarial_field: str = "grupo_empresarial",
        time_grouping: TimeGrouping = TimeGrouping.WEEK_OF_YEAR,
        extra_fields: dict = None,
    ):
        self.route = route
        self.metric_name = metric_name
        self.counter_name = counter_name
        self.description_counter = description_counter
        self.tenant_field = tenant_field
        self.grupo_empresarial_field = grupo_empresarial_field
        self.time_grouping = time_grouping
        self.extra_fields = extra_fields or {}
        self.logger = get_logger()

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            try:
                status_code = response[1] if isinstance(response, tuple) and len(response) > 1 else ""

                metric_data = {
                    "route": self.route,
                    "method": request.method,
                    "status_code": str(status_code),
                    self.time_grouping.value: get_time_grouping(self.time_grouping.name),
                    self.tenant_field: request.headers.get(self.tenant_field, ""),
                    self.grupo_empresarial_field: request.headers.get(self.grupo_empresarial_field, ""),
                    **self.extra_fields
                }

                self._send_telemetry(metric_data)
            except Exception as e:
                self.logger.exception(f"Falha ao enviar métricas: {e}")    
            return response

        return wrapper

    def _send_telemetry(self, metric_data):
        meter = metrics.get_meter(self.metric_name)
        counter = meter.create_counter(
            name=self.counter_name,
            description=self.description_counter,
        )
        self.logger.debug(
            f"[TelemetryBase] Enviando métrica - counter: {self.counter_name} - dados: {metric_data}"
        )
        counter.add(1, metric_data)