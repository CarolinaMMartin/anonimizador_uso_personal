"""Cabeceras HTTP para descargas."""
from urllib.parse import quote


def content_disposition_attachment(filename: str) -> str:
    """Content-Disposition compatible con ASCII y UTF-8 (RFC 5987)."""
    safe = filename.replace('"', "'").replace("\r", "").replace("\n", "")
    ascii_name = safe.encode("ascii", "ignore").decode().strip() or "documento"
    encoded = quote(safe, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
