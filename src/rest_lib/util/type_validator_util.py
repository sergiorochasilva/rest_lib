import datetime
import enum
import json
import re
import uuid
import yaml

from dateutil.relativedelta import relativedelta

from decimal import Decimal
from typing import Any

from pg8000 import PGInterval


class TypeValidatorUtil:
    @staticmethod
    def validate(obj, value):
        """
        Valida o value recebido, de acordo com o tipo esperado, e faz as conversões necessárias (se possível).
        """

        # Montando expressões regulares para as validações
        matcher_uuid = re.compile(
            "^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$"
        )
        matcher_datetime = re.compile(
            "^(\d\d\d\d)-(\d\d)-(\d\d)[T,t](\d\d):(\d\d):(\d\d)$"
        )
        matcher_date = re.compile("^(\d\d\d\d)-(\d\d)-(\d\d)$")

        matcher_time = re.compile("^(\d\d):(\d\d):(\d\d)$")

        matcher_duration = re.compile(
            r"^P"
            r"(?:(\d+)Y)?"  # anos
            r"(?:(\d+)M)?"  # meses
            r"(?:(\d+)D)?"  # dias
            r"(?:T"  # parte de tempo começa com T
            r"(?:(\d+)H)?"  # horas
            r"(?:(\d+)M)?"  # minutos
            r"(?:(\d+(?:\.\d+)?)S)?"  # segundos (aceita fração)
            r")?$"
        )

        # Validação direta de tipos
        erro_tipo = False
        if obj.expected_type is datetime.datetime and isinstance(value, str):
            match_datetime = matcher_datetime.search(value)
            match_date = matcher_date.search(value)

            if match_datetime:
                ano = int(match_datetime.group(1))
                mes = int(match_datetime.group(2))
                dia = int(match_datetime.group(3))
                hora = int(match_datetime.group(4))
                minuto = int(match_datetime.group(5))
                segundo = int(match_datetime.group(6))

                value = datetime.datetime(
                    year=ano,
                    month=mes,
                    day=dia,
                    hour=hora,
                    minute=minuto,
                    second=segundo,
                )
            elif match_date:
                ano = int(match_date.group(1))
                mes = int(match_date.group(2))
                dia = int(match_date.group(3))

                value = datetime.datetime(
                    year=ano, month=mes, day=dia, hour=0, minute=0, second=0
                )
            else:
                erro_tipo = True
        elif obj.expected_type is datetime.date and isinstance(value, str):
            match_date = matcher_date.search(value)

            if match_date:
                ano = int(match_date.group(1))
                mes = int(match_date.group(2))
                dia = int(match_date.group(3))

                value = datetime.date(year=ano, month=mes, day=dia)
            else:
                erro_tipo = True
        elif obj.expected_type is datetime.time and isinstance(value, str):
            match_time = matcher_time.search(value)
            if match_time:
                hor = int(match_time.group(1))
                min = int(match_time.group(2))
                sec = int(match_time.group(3))

                value = datetime.time(hour=hor, minute=min, second=sec)
            else:
                erro_tipo = True
        elif obj.expected_type is relativedelta and isinstance(value, str):
            match_time = matcher_duration.search(value)
            if match_time:
                yea, mon, day, hor, min, sec = match_time.groups()

                seconds = float(sec) if sec else 0.0
                seconds_int = int(seconds)
                microseconds = int(round((seconds - seconds_int) * 1000000))

                value = relativedelta(
                    days=int(day) if day else 0,
                    months=int(mon) if mon else 0,
                    years=int(yea) if yea else 0,
                    hours=int(hor) if hor else 0,
                    minutes=int(min) if min else 0,
                    seconds=seconds_int,
                    microseconds=microseconds,
                )
            else:
                erro_tipo = True
        elif obj.expected_type is relativedelta and isinstance(value, PGInterval):

            value = relativedelta(
                days=int(value.days) if value.days else 0,
                months=int(value.months) if value.months else 0,
                years=int(value.years) if value.years else 0,
                hours=int(value.hours) if value.hours else 0,
                minutes=int(value.minutes) if value.minutes else 0,
                seconds=int(value.seconds) if value.seconds else 0,
            )
        elif obj.expected_type is relativedelta and isinstance(
            value, datetime.timedelta
        ):
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            value = relativedelta(
                hours=int(hours), minutes=int(minutes), seconds=int(seconds)
            )
        elif isinstance(obj.expected_type, enum.EnumMeta):
            # Enumerados
            try:
                value = TypeValidatorUtil.convert_enum_from_entity(obj, value)
            except ValueError:
                raise ValueError(
                    f"{obj.storage_name} não é um {obj.expected_type.__name__} válido. Valor recebido: {value}."
                )
        elif obj.expected_type is bool and isinstance(value, int):
            # Booleanos
            # Converting int to bool (0 is False, otherwise is True)
            value = bool(value)
        elif obj.expected_type is bool and isinstance(value, str):
            # Booleanos
            # Converting str to bool
            value = value.lower() == "true"
        elif obj.expected_type is datetime.datetime and isinstance(
            value, datetime.date
        ):
            # Datetime
            # Assumindo hora 0, minuto 0 e segundo 0 (quanto é recebida uma data para campo data + hora)
            value = datetime.datetime(
                value.year, value.month, value.day, 0, 0, 0)
        elif obj.expected_type is datetime.date and isinstance(
            value, datetime.datetime
        ):
            # Date
            # Desprezando hora , minuto e segundo (quanto é recebida uma data + hora, para campo de data)
            value = datetime.date(value.year, value.month, value.day)
        elif obj.expected_type is datetime.time and isinstance(
            value, datetime.datetime
        ):
            # Time
            # Desprezando data (quanto é recebida uma data + hora, para campo de hora)
            value = datetime.time(value.hour, value.minute, value.second)
        elif obj.expected_type is uuid.UUID and isinstance(value, str):
            # UUID
            # Verificando se pode ser alterado de str para UUID
            match_uuid = matcher_uuid.search(value)

            if match_uuid:
                value = uuid.UUID(value)
            else:
                erro_tipo = True
        elif obj.expected_type is int:
            # Int
            try:
                value = int(value)
            except:
                erro_tipo = True
        elif obj.expected_type is float:
            # Float
            try:
                value = float(value)
            except:
                erro_tipo = True
        elif obj.expected_type is Decimal:
            # Decimal
            try:
                value = Decimal(str(value))
            except:
                erro_tipo = True
        elif obj.expected_type is str:
            # String
            if value is not None:
                try:
                    value = str(value)
                except:
                    erro_tipo = True
        elif obj.expected_type is dict and isinstance(value, str):
            try:
                value = json.loads(value)
            except:
                try:
                    value = yaml.safe_load(value)
                except:
                    erro_tipo = True

        else:
            erro_tipo = True

        if erro_tipo:
            raise ValueError(
                f"{obj.storage_name} deve ser do tipo {obj.expected_type.__name__}. Valor recebido: {value}."
            )

        return value

    @staticmethod
    def convert_enum_from_entity(obj, value: Any):
        lista_enum = list(obj.expected_type)

        # Se o enum estiver vazio
        if len(lista_enum) <= 0:
            return None

        # Verificando o tipo dos valores do enum
        if isinstance(lista_enum[0].value, tuple):
            for item in obj.expected_type:
                lista_valores = list(item.value)
                for valor in lista_valores:
                    # Testando se casa com o valor
                    if valor == value:
                        return item

                    # Se o valor for string, testa inclusive em caixa alta e baixa
                    if isinstance(value, str):
                        if valor == value.lower() or valor == value.upper():
                            return item
            raise ValueError
        else:
            # Tentando pelo valor do próprio enum (e testando os casos, se for str)
            if isinstance(value, str):
                try:
                    return obj.expected_type(value)
                except ValueError:
                    try:
                        return obj.expected_type(value.lower())
                    except ValueError:
                        return obj.expected_type(value.upper())
            else:
                return obj.expected_type(value)
