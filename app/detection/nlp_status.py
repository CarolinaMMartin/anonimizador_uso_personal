"""Diagnóstico de capas NLP."""
from app.config import ENABLE_PRESIDIO, ENABLE_SPACY


def get_nlp_layers_status() -> dict:
    status = {
        "presidio": {"enabled": ENABLE_PRESIDIO, "available": False},
        "spacy": {"enabled": ENABLE_SPACY, "available": False},
    }

    if ENABLE_PRESIDIO:
        try:
            from app.detection.presidio_layer import presidio_status

            status["presidio"].update(presidio_status())
        except Exception as e:
            status["presidio"]["error"] = str(e)

    if ENABLE_SPACY:
        try:
            from app.detection.spacy_layer import spacy_status

            status["spacy"].update(spacy_status())
        except Exception as e:
            status["spacy"]["error"] = str(e)

    from app.detection.dictionaries import get_apellidos, get_nombres
    from app.detection.regex_catalog import load_catalog_patterns

    status["dictionaries"] = {}
    for name, load in (("nombres", get_nombres), ("apellidos", get_apellidos),
                       ("regex", load_catalog_patterns)):
        try:
            values = load()
            status["dictionaries"][name] = {"available": bool(values), "count": len(values)}
        except (OSError, ValueError, TypeError) as exc:
            status["dictionaries"][name] = {"available": False, "error": str(exc)}

    return status
