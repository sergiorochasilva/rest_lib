import time

from contextlib import contextmanager
from functools import wraps

from rest_lib.util.logger import get_logger


def log_time(func):
    """Decorator para monitoria de performance de métodos (via log)."""

    @wraps(func)  # preserva metadados da função original
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        fim = time.time()
        get_logger().debug(
            f"[GCFUtils LogTime] Tempo de execução de {func.__name__}: {fim - inicio:.4f} segundos"
        )
        return resultado

    return wrapper


@contextmanager
def log_time_context(name: str):
    inicio = time.perf_counter()
    try:
        yield
    finally:
        fim = time.perf_counter()
        get_logger().debug(
            f"[GCFUtils LogTime Context] Tempo de execução do contexto '{name}': {fim - inicio:.4f} segundos"
        )
