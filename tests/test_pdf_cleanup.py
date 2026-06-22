from app.extraction.pdf_cleanup import clean_pdf_text, merge_lines_to_paragraphs


def test_clean_page_footer():
    raw = "Texto legal.\n1 | P á g i n a\n\nMás texto."
    out = clean_pdf_text(raw)
    assert "Página" not in out or "P á g i n a" not in out
    assert "Texto legal" in out
    assert "Más texto" in out


def test_merge_wrapped_lines():
    raw = "En su funcionamiento destaca la ejecución\n\nparticular por la cual, en forma coordinada,"
    out = merge_lines_to_paragraphs(raw)
    assert "funcionamiento destaca" in out
    assert "particular por la cual" in out
    assert out.count("\n\n") == 0
