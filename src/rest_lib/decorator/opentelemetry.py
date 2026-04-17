import functools
from flask import request
from rest_lib.dto.dto_base import DTOBase
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.decorator.opentelemetry_base import OpenTelemetryBase
from rest_lib.util.time_grouping import TimeGrouping

class OpenTelemetry:
    def __init__(
        self,
        dto_class: DTOBase,
        route: str,
        metric_name: str,
        counter_name: str,
        description_counter: str = "",
        tenant_field: str = "tenant",
        grupo_empresarial_field: str = "grupo_empresarial",
        time_grouping: TimeGrouping = TimeGrouping.WEEK_OF_YEAR,
    ):
        self.decorator = OpenTelemetryBase(
            route=route,
            metric_name=metric_name,
            counter_name=counter_name,
            description_counter=description_counter,
            tenant_field=tenant_field,
            grupo_empresarial_field=grupo_empresarial_field,
            time_grouping=time_grouping,
        )
        self.dto_class = dto_class
        self.tenant_field = tenant_field
        self.grupo_empresarial_field = grupo_empresarial_field

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metric_fields = DTOField.get_metric_labels(
                self.dto_class,
                request,
                self.tenant_field,
                self.grupo_empresarial_field,
            ) if self.dto_class else {}

            self.decorator.extra_fields = metric_fields

            return self.decorator(func)(*args, **kwargs)

        return wrapper
