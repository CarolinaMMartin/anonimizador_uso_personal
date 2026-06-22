"""Presidio sin llamadas de red (tldextract / publicsuffix.org).

Presidio valida emails con tldextract, que por defecto puede intentar descargar
https://publicsuffix.org/list/public_suffix_list.dat (issue Presidio #1205).

Mitigación:
  1. tldextract en modo offline con snapshot embebido del paquete.
  2. EmailRecognizer removido del registry (emails los detecta regex AR).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_configured = False


def configure_offline_tldextract() -> None:
    """Fuerza tldextract a usar solo el snapshot local, sin HTTP."""
    global _configured
    if _configured:
        return

    import tldextract.tldextract as tldextract_core

    offline = tldextract_core.TLDExtract(
        suffix_list_urls=(),
        cache_dir=None,
        fallback_to_snapshot=True,
    )
    tldextract_core.TLD_EXTRACTOR = offline
    _configured = True
    logger.info("tldextract configurado offline (sin publicsuffix.org)")


def strip_network_email_recognizer(analyzer) -> None:
    """Quita EmailRecognizer: los emails los cubre regex AR + catálogo."""
    before = len(analyzer.registry.recognizers)
    analyzer.registry.remove_recognizer("EmailRecognizer")
    removed = before - len(analyzer.registry.recognizers)
    if removed:
        logger.info("Presidio: EmailRecognizer removido (%d); emails vía regex", removed)
