import re
from typing import Optional, Tuple


DEFAULT_RESP_HEADERS = {"Content-Type": "application/json; charset=utf-8"}


def _extract_postgres_code_and_message(exc: Exception) -> Tuple[Optional[str], str]:
    """
    Extrai SQLSTATE e mensagem de erro de excecoes SQLAlchemy/pg8000.

    Args:
        exc: Excecao original capturada na camada de controller/DAO.

    Returns:
        Tupla (sqlstate, mensagem). Quando nao houver codigo identificado,
        sqlstate sera None.
    """
    orig = getattr(exc, "orig", None)

    if orig is None:
        return None, str(exc)

    code = None
    message = str(orig)

    if hasattr(orig, "pgcode"):
        code = getattr(orig, "pgcode")

    if code is None and hasattr(orig, "sqlstate"):
        code = getattr(orig, "sqlstate")

    if isinstance(orig, dict):
        code = code or orig.get("C") or orig.get("code")
        message = orig.get("M") or orig.get("message") or message
        detail = orig.get("D")
        if detail:
            message = f"{message}. {detail}"
        return code, message

    args = getattr(orig, "args", None)
    if args:
        first = args[0]
        if isinstance(first, dict):
            code = code or first.get("C") or first.get("code")
            message = first.get("M") or first.get("message") or message
            detail = first.get("D")
            if detail:
                message = f"{message}. {detail}"
            return code, message

        if isinstance(first, str):
            if code is None:
                match = re.search(r"'C':\s*'([0-9A-Z]+)'", first)
                if match:
                    code = match.group(1)
            if not message:
                message = first

    return code, message


def map_db_exception_to_http(exc: Exception) -> Optional[Tuple[int, str]]:
    """
    Mapeia erros de banco para status HTTP e mensagem de API.

    Args:
        exc: Excecao do banco (ex.: IntegrityError/ProgrammingError).

    Returns:
        Tupla (status_http, mensagem) quando houver mapeamento.
        Retorna None quando o codigo SQLSTATE nao estiver mapeado.
    """
    code, db_message = _extract_postgres_code_and_message(exc)

    if code == "23503":
        return 409, f"Violacao de chave estrangeira: {db_message}"
    if code == "23505":
        return 409, f"Violacao de unicidade: {db_message}"
    if code in ("23502", "22P02"):
        return 400, f"Dados invalidos para persistencia: {db_message}"

    return None
