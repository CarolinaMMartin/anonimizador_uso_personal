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

    return status
