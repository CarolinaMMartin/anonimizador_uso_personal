"""Capa spaCy EntityRuler (MVP2) - complementa regex/Presidio."""
import logging
import re

from app.detection.regex_ar import RawItem

logger = logging.getLogger(__name__)

_nlp = None
_init_error: str | None = None
SPACY_MODEL_ES = "es_core_news_md"

JUDICIAL_RULER_PATTERNS = [
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "el"}, {"LOWER": "imputado"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "la"}, {"LOWER": "imputada"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "la"}, {"LOWER": "victima"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "la"}, {"LOWER": "víctima"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "el"}, {"LOWER": "denunciante"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "la"}, {"LOWER": "denunciante"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "el"}, {"LOWER": "testigo"}]},
    {"label": "ROL_JUDICIAL", "pattern": [{"LOWER": "la"}, {"LOWER": "fiscalia"}]},
    {"label": "ORGANISMO", "pattern": [{"LOWER": "juzgado"}, {"LOWER": "nacional"}]},
    {"label": "ORGANISMO", "pattern": [{"LOWER": "fiscalia"}, {"IS_ALPHA": True}]},
    # Nombre completo precedido por título profesional / de cortesía. Captura de 1 a 4
    # palabras capitalizadas para no cortar apellidos poco frecuentes
    # (ej. "Dra. María Andrea Piesco").
    {
        "label": "PERSONA",
        "pattern": [
            {
                "ORTH": {
                    "IN": [
                        "Dr.", "Dra.", "Dres.", "Sr.", "Sra.", "Srta.",
                        "Lic.", "Ing.", "Cdor.", "Cra.", "Arq.",
                    ]
                }
            },
            {"IS_ALPHA": True, "IS_TITLE": True, "OP": "{1,4}"},
        ],
    },
]


def _get_nlp():
    global _nlp, _init_error
    if _nlp is not None:
        return _nlp
    if _init_error is not None:
        raise RuntimeError(_init_error)
    try:
        import spacy

        from app.runtime_paths import spacy_model_dir

        bundled = spacy_model_dir()
        nlp = spacy.load(bundled if bundled else SPACY_MODEL_ES)
        if "entity_ruler" not in nlp.pipe_names:
            ruler = nlp.add_pipe("entity_ruler", before="ner")
            ruler.add_patterns(JUDICIAL_RULER_PATTERNS)
        _nlp = nlp
        logger.info("spaCy cargado: %s", SPACY_MODEL_ES)
        return _nlp
    except OSError as e:
        _init_error = (
            f"Modelo {SPACY_MODEL_ES} no instalado. "
            f"Ejecutá: python -m spacy download {SPACY_MODEL_ES}"
        )
        raise RuntimeError(_init_error) from e
    except Exception as e:
        _init_error = str(e)
        raise


def spacy_status() -> dict:
    if _nlp is not None:
        return {"available": True, "model": SPACY_MODEL_ES}
    if _init_error:
        return {"available": False, "error": _init_error}
    try:
        _get_nlp()
        return {"available": True, "model": SPACY_MODEL_ES}
    except Exception as e:
        return {"available": False, "error": str(e)}

LABEL_MAP = {
    "PER": "PERSONA",
    "PERSON": "PERSONA",
    "PERSONA": "PERSONA",
    "ORG": "ORGANISMO",
    "LOC": "DOMICILIO",
    "ROL_JUDICIAL": "OTRO",
    "ORGANISMO": "ORGANISMO",
}


def detect_spacy(text: str) -> list[RawItem]:
    nlp = _get_nlp()
    # Procesar en chunks para documentos largos
    max_len = nlp.max_length if hasattr(nlp, "max_length") else 1_000_000
    if len(text) > max_len:
        nlp.max_length = len(text) + 100

    doc = nlp(text[: min(len(text), 500_000)])
    items: list[RawItem] = []
    from app.detection.filters import is_valid_detection

    for ent in doc.ents:
        cat = LABEL_MAP.get(ent.label_, "OTRO")
        if cat == "OTRO":
            continue
        if not is_valid_detection(cat, ent.text, text, ent.start_char):
            continue
        items.append(
            RawItem(
                cat=cat,
                original=ent.text,
                start=ent.start_char,
                end=ent.end_char,
                source_layer="spacy",
            )
        )

    # Buscar nombre después de rol judicial
    rol_re = re.compile(
        r"\b(?:imputad[oa]|víctima|victima|denunciante|testig[oa])\s+"
        r"(?:[:,\.]?\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})",
        re.IGNORECASE,
    )
    for m in rol_re.finditer(text):
        if m.group(1):
            name = m.group(1)
            start = m.start() + m.group(0).index(name)
            items.append(
                RawItem(
                    cat="PERSONA",
                    original=name,
                    start=start,
                    end=start + len(name),
                    source_layer="spacy",
                )
            )
    return items
