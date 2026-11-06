"""Límites de campos rotulados en formularios y comprobantes."""
import re


FIELD_LABEL_RE = re.compile(
    r"\b(?:"
    r"apellidos?\s+y\s+nombres?(?:\s*/\s*raz[oó]n\s+social)?"
    r"|nombres?\s+y\s+apellidos?"
    r"|raz[oó]n\s+social"
    r"|fecha\s+(?:de\s+)?(?:emisi[oó]n|vencimiento|nacimiento|inicio|pago|notificaci[oó]n|presentaci[oó]n)"
    r"|inicio\s+de\s+actividades"
    r"|domicilio\s+(?:comercial|fiscal|legal|real|electr[oó]nico)"
    r"|condici[oó]n\s+(?:frente\s+al\s+iva|de\s+venta)"
    r"|punto\s+de\s+venta"
    r"|per[ií]odo\s+facturado(?:\s+(?:desde|hasta))?"
    r"|(?:tipo|n[uú]mero|nro\.?)\s+de\s+(?:documento|comprobante|factura|identificaci[oó]n)"
    r"|comp(?:robante)?\.?\s*(?:nro\.?|n[°º])"
    r"|precio\s+unitario|cantidad|subtotal|importe\s+total"
    r"|(?:cuit|cuil|dni|tel[eé]fono|celular|correo|email|domicilio|nombre|apellido)\s*[:|]"
    r")(?!\w)",
    re.IGNORECASE,
)


def field_value_end(text: str, start: int, end: int) -> int:
    label = FIELD_LABEL_RE.search(text, start, end)
    if not label:
        return end
    boundary = label.start()
    while boundary > start and text[boundary - 1].isspace():
        boundary -= 1
    return boundary
