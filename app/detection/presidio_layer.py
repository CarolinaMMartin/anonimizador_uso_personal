"""Capa Presidio (MVP2) - analyzer con NLP en español y recognizers AR.

Requiere (ver https://microsoft.github.io/presidio/installation/):
  pip install presidio-analyzer presidio-anonymizer spacy
  python -m spacy download es_core_news_md
"""
import logging

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.detection.regex_ar import RawItem

logger = logging.getLogger(__name__)

_analyzer: AnalyzerEngine | None = None
_init_error: str | None = None

SPACY_MODEL_ES = "es_core_news_md"

# Entidades estándar Presidio que mapeamos a nuestras categorías
# Etiquetas sueltas que Presidio a veces marca por contexto (no son PII real)
SKIP_SURFACES = frozenset(
    {
        "cuit", "cuil", "dni", "tel", "teléfono", "telefono", "email",
        "correo", "expediente", "expte", "juzgado", "fiscalía", "fiscalia",
    }
)


CAT_MAP = {
    "DNI": "DNI",
    "CUIT": "CUIT",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "TELEFONO",
    "PERSON": "PERSONA",
    "LOCATION": "DOMICILIO",
    "ORGANIZATION": "ORGANISMO",
    "NRP": "PERSONA",
}


def _build_analyzer() -> AnalyzerEngine:
    """AnalyzerEngine con spaCy en español + recognizers custom AR."""
    from app.detection.presidio_offline import (
        configure_offline_tldextract,
        strip_network_email_recognizer,
    )
    from app.runtime_paths import spacy_model_dir

    configure_offline_tldextract()

    bundled = spacy_model_dir()
    model_entry: dict[str, str] = (
        {"lang_code": "es", "model_name": str(bundled)}
        if bundled is not None
        else {"lang_code": "es", "model_name": SPACY_MODEL_ES}
    )

    configuration = {
        "nlp_engine_name": "spacy",
        "models": [model_entry],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    dni_pattern = Pattern(
        name="dni_ar",
        regex=r"\b\d{1,2}\.\d{3}\.\d{3}\b",
        score=0.9,
    )
    cuit_pattern = Pattern(
        name="cuit_ar",
        regex=r"\b\d{2}[-\s]?\d{8}[-\s]?\d\b",
        score=0.9,
    )
    expt_pattern = Pattern(
        name="expediente_ar",
        regex=r"\b(?:expediente|expte\.?|causa)\s*(?:n[°ºo]?\.?)?\s*[:#]?\s*[A-Z0-9\-\/\.]{4,25}",
        score=0.75,
    )

    recognizers = [
        PatternRecognizer(
            supported_entity="DNI",
            patterns=[dni_pattern],
            supported_language="es",
            context=["dni", "documento", "identidad", "imputado", "denunciante"],
        ),
        PatternRecognizer(
            supported_entity="CUIT",
            patterns=[cuit_pattern],
            supported_language="es",
            context=["cuit", "cuil", "afip"],
        ),
        PatternRecognizer(
            supported_entity="EXPEDIENTE",
            patterns=[expt_pattern],
            supported_language="es",
            context=["expediente", "causa", "autos", "juzgado"],
        ),
    ]

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["es"],
    )
    strip_network_email_recognizer(analyzer)
    for rec in recognizers:
        analyzer.registry.add_recognizer(rec)

    return analyzer


def _get_analyzer() -> AnalyzerEngine:
    global _analyzer, _init_error
    if _analyzer is not None:
        return _analyzer
    if _init_error is not None:
        raise RuntimeError(_init_error)
    try:
        _analyzer = _build_analyzer()
        logger.info("Presidio Analyzer inicializado (es / %s)", SPACY_MODEL_ES)
        return _analyzer
    except Exception as e:
        _init_error = str(e)
        logger.warning(
            "Presidio no disponible: %s. Ejecutá: pip install presidio-analyzer spacy && "
            "python -m spacy download %s",
            e,
            SPACY_MODEL_ES,
        )
        raise


def presidio_status() -> dict:
    """Estado de la capa para healthcheck / diagnóstico."""
    if _analyzer is not None:
        return {"available": True, "model": SPACY_MODEL_ES}
    if _init_error:
        return {"available": False, "error": _init_error}
    try:
        _get_analyzer()
        return {"available": True, "model": SPACY_MODEL_ES}
    except Exception as e:
        return {"available": False, "error": str(e)}


def detect_presidio(text: str) -> list[RawItem]:
    analyzer = _get_analyzer()
    # Presidio recomienda chunks en textos muy largos
    chunk_size = 100_000
    items: list[RawItem] = []
    offset = 0
    while offset < len(text):
        chunk = text[offset : offset + chunk_size]
        results = analyzer.analyze(
            text=chunk,
            language="es",
            # EMAIL: regex AR + catálogo (Presidio EmailRecognizer usa tldextract → red)
            entities=["DNI", "CUIT", "PERSON", "PHONE_NUMBER"],
        )
        for r in results:
            if r.score < 0.75:
                continue
            cat = CAT_MAP.get(r.entity_type, "OTRO")
            if r.entity_type == "EXPEDIENTE":
                cat = "EXPEDIENTE"
            surface = chunk[r.start : r.end].strip()
            if len(surface) < 3:
                continue
            if surface.lower() in SKIP_SURFACES:
                continue
            from app.detection.filters import is_valid_detection

            if not is_valid_detection(cat, surface, text, r.start + offset):
                continue
            items.append(
                RawItem(
                    cat=cat,
                    original=surface,
                    start=r.start + offset,
                    end=r.end + offset,
                    source_layer="presidio",
                )
            )
        offset += chunk_size
    return items
