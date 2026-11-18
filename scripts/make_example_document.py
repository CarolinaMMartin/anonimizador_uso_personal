"""Genera el escrito judicial de ejemplo, totalmente ficticio.

Uso:
  python scripts/make_example_document.py

Salida: docs/ejemplos/escrito_ficticio.docx

Sirve para las notas de certificación de Microsoft Store, para las capturas de
la ficha y como prueba manual. Ningún dato corresponde a una persona, causa o
domicilio reales: los DNI usan un rango no emitido (99 millones), el número de
expediente lleva un año futuro, el juzgado no existe y el correo usa el
dominio reservado ``.invalid``. Los CUIT/CUIL tienen dígito verificador
correcto solo para que el detector los reconozca.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "ejemplos" / "escrito_ficticio.docx"

NOTICE = "DOCUMENTO DE EJEMPLO. Todos los nombres, números y domicilios son ficticios."
TITLE = "PROMUEVE DEMANDA POR DAÑOS Y PERJUICIOS"
PARAGRAPHS = (
    "Señor Juez:",
    "Marcelina Aurora Quintanilla Ordóñez, DNI 99.812.345, CUIL 27-99704218-8, "
    "de nacionalidad argentina, nacida el 14 de marzo de 1984, con domicilio real "
    "en Pasaje Las Calandrias 9876, piso 7, departamento B, Ciudad Autónoma de "
    "Buenos Aires, por derecho propio, con el patrocinio letrado del Dr. Fermín "
    "Leandro Echagüe Bustos, abogado, T° 912 F° 345 C.P.A.C.F., CUIT "
    "20-99812345-4, constituyendo domicilio procesal en Avenida Los Aromos 5432, "
    "oficina 12, de esta Ciudad, y domicilio electrónico en "
    "fermin.echague@estudio-ejemplo.invalid, teléfono (011) 5555-0147, en los "
    "autos caratulados «QUINTANILLA ORDÓÑEZ, MARCELINA AURORA c/ VILLAFAÑE "
    "COSTAS, EUSEBIO RAMIRO s/ DAÑOS Y PERJUICIOS», Expediente N° 987654/2099, "
    "en trámite ante el Juzgado Nacional de Primera Instancia en lo Civil N° 999, "
    "a V.S. respetuosamente digo:",
    "I. OBJETO",
    "Que vengo a promover demanda por daños y perjuicios contra Eusebio Ramiro "
    "Villafañe Costas, DNI 99.704.218, con domicilio en calle Los Tilos 8765, "
    "localidad de Los Sauces, provincia de Buenos Aires, y contra "
    "Transportes Rumbo Ficticio S.A., CUIT 30-99901234-1, con domicilio en "
    "Avenida Los Ceibos 7654 de Los Sauces, por la suma de pesos "
    "cuatro millones quinientos mil ($ 4.500.000), con más sus intereses y costas.",
    "II. HECHOS",
    "El 3 de febrero de 2099, aproximadamente a las 18:30 horas, la señora "
    "Quintanilla Ordóñez circulaba en bicicleta por Pasaje Las Calandrias cuando "
    "fue embestida por un camión dominio AB 123 CD, conducido por el señor "
    "Villafañe Costas y de propiedad de Transportes Rumbo Ficticio S.A.",
    "Como consecuencia del hecho, la actora fue atendida en el Sanatorio "
    "del Sur por el Dr. Baltasar Ignacio Urquiaga Montiel, M.N. "
    "987.654, quien diagnosticó fractura de muñeca izquierda. El hecho fue "
    "presenciado por la señora Dorotea Inés Zabaleta Arrieta, DNI 99.655.432, "
    "con domicilio en calle Los Tilos 8770 de Los Sauces.",
    "III. PRUEBA",
    "Se ofrece como prueba documental la historia clínica N° 554433 y, como "
    "testimonial, la declaración de Dorotea Inés Zabaleta Arrieta. Los gastos "
    "médicos fueron abonados desde la cuenta CBU 9990001100022200033344 a "
    "nombre de Marcelina Aurora Quintanilla Ordóñez.",
    "IV. PETITORIO",
    "Por lo expuesto, a V.S. solicito que se me tenga por presentada y por "
    "parte, que se corra traslado de la demanda a Eusebio Ramiro Villafañe "
    "Costas y a Transportes Rumbo Ficticio S.A., y que oportunamente se haga "
    "lugar a la demanda en todas sus partes.",
    "Proveer de conformidad, SERÁ JUSTICIA.",
    "Marcelina Aurora Quintanilla Ordóñez — Dr. Fermín Leandro Echagüe Bustos",
)


def document_paragraphs() -> list[str]:
    """Texto completo del ejemplo, en el orden en que queda en el archivo."""
    return [NOTICE, TITLE, *PARAGRAPHS]


def build(output: Path = OUTPUT) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    notice = document.add_paragraph()
    notice.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = notice.add_run(NOTICE)
    run.italic = True
    run.font.size = Pt(10)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(TITLE).bold = True

    for text in PARAGRAPHS:
        paragraph = document.add_paragraph()
        is_heading = text[:1] in "IV" and ". " in text[:5] and text.isupper()
        if is_heading:
            paragraph.add_run(text).bold = True
        else:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.add_run(text)

    properties = document.core_properties
    properties.title = "Escrito judicial de ejemplo (datos ficticios)"
    properties.author = "Anonimizador de uso personal"
    properties.last_modified_by = "Anonimizador de uso personal"
    properties.comments = NOTICE
    properties.created = properties.modified = datetime(2026, 1, 1)

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output


if __name__ == "__main__":
    print(build())
