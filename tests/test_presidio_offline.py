"""Presidio no debe hacer llamadas HTTP (tldextract / publicsuffix.org)."""
import app.detection.presidio_layer as presidio_layer
import app.detection.presidio_offline as presidio_offline_mod


def test_tldextract_offline_blocks_network(monkeypatch):
    presidio_offline_mod._configured = False
    presidio_offline_mod.configure_offline_tldextract()

    import requests

    def _blocked(*_args, **_kwargs):
        raise AssertionError("tldextract intentó acceso de red")

    monkeypatch.setattr(requests, "get", _blocked)

    import tldextract

    result = tldextract.extract("usuario@juzgado.gov.ar")
    assert result.domain
    assert result.suffix


def test_presidio_analyze_email_text_no_network(monkeypatch):
    presidio_layer._analyzer = None
    presidio_layer._init_error = None
    presidio_offline_mod._configured = False

    presidio_offline_mod.configure_offline_tldextract()

    import requests

    monkeypatch.setattr(requests, "get", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("red")))

    text = "Contacto: maria.garcia@poderjudicial.gob.ar y DNI 27.353.518"
    items = presidio_layer.detect_presidio(text)
    emails = [x for x in items if x.cat == "EMAIL"]
    assert not emails  # Presidio ya no detecta email; regex lo haría en pipeline
