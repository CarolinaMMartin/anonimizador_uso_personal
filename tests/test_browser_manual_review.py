r"""Opt-in real-browser regressions with synthetic DOCX input and actual downloads.

PowerShell: $env:ANON_BROWSER_TESTS='1'; .\.venv\Scripts\python.exe -m pytest
tests/test_browser_manual_review.py -q
Requires Playwright and an installed browser (ANON_BROWSER_CHANNEL, default msedge).
The live app runs on an ephemeral loopback port; no APIs or DOM are mocked.
Set ANON_BROWSER_BASE_URL=http://127.0.0.1:PORT to test an already running
disposable portable process instead. Its owner must stop that process after
the suite: the application has no API for deleting whole sessions.
"""
import io
import os
import socket
import threading
import time

import pdfplumber
import pytest
from docx import Document

pytestmark = pytest.mark.skipif(
    os.environ.get('ANON_BROWSER_TESTS') != '1',
    reason='Opt-in browser suite: set ANON_BROWSER_TESTS=1',
)


@pytest.fixture(scope='module')
def live_app():
    external_url = os.environ.get('ANON_BROWSER_BASE_URL', '').strip().rstrip('/')
    if external_url:
        from urllib.parse import urlsplit

        parsed = urlsplit(external_url)
        assert parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1'), \
            'ANON_BROWSER_BASE_URL must identify a disposable local application'
        assert parsed.path in ('', '/') and not parsed.query and not parsed.fragment
        yield external_url
        return

    import uvicorn
    from app.main import app

    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, 'Local app did not start'
        try:
            yield f'http://127.0.0.1:{port}'
        finally:
            server.should_exit = True
            thread.join(timeout=10)


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        with playwright.chromium.launch(
            channel=os.environ.get('ANON_BROWSER_CHANNEL', 'msedge'), headless=True,
        ) as instance:
            print(f'\nReal browser: {instance.version}')
            yield instance


@pytest.fixture
def page(browser, live_app, tmp_path):
    # A portable keeps its sessions in another process. Do not pretend that
    # deleting IDs from the test interpreter would clean up the portable.
    store = None
    if not os.environ.get('ANON_BROWSER_BASE_URL', '').strip():
        from app.models.store import store

    with browser.new_context(viewport={'width': 1500, 'height': 1100}, accept_downloads=True) as context:
        page = context.new_page()
        errors = []
        sessions = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: sessions.append(response.json()['session_id'])
                if response.url.endswith('/api/upload') and response.ok else None)
        page.goto(live_app)
        try:
            yield page
            assert not errors, errors
        finally:
            page.screenshot(path=str(tmp_path / 'browser.png'), full_page=True)
            if store is not None:
                for sid in sessions:
                    store.delete(sid)


def load_document(page, text, *, analyze=True):
    from playwright.sync_api import expect

    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    with page.expect_response(lambda r: r.url.endswith('/api/upload')) as uploaded:
        page.locator('#fileInput').set_input_files({
            'name': 'sintetico.docx',
            'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'buffer': buffer.getvalue(),
        })
    assert uploaded.value.ok
    if not analyze:
        expect(page.locator('#analyzeBtn')).to_be_enabled()
        return uploaded.value.json()
    for checkbox in page.locator('#catChecks input').all():
        checkbox.uncheck()
    page.locator('#catChecks input[data-cat="EMAIL"]').check()
    with page.expect_response(lambda r: r.url.endswith('/api/analyze'), timeout=60000) as analyzed:
        page.locator('#analyzeBtn').click()
    assert analyzed.value.ok, analyzed.value.text()
    assert analyzed.value.json()['detections'] == []
    expect(page.locator('#workspace')).to_be_visible()
    expect(page.locator('#docPreview')).to_have_text(text, use_inner_text=False)
    return uploaded.value.json()


def select_range(page, text, start, end):
    """Drag across the rendered DOM, including nested highlight/search text nodes."""
    preview = page.locator('#docPreview')
    preview.scroll_into_view_if_needed()
    offsets = [len(text[:offset].encode('utf-16-le')) // 2 for offset in (start, end)]
    points = preview.evaluate("""(container, [start, end]) => {
      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
      const nodes = []; let length = 0;
      while (walker.nextNode()) {
        const node = walker.currentNode;
        nodes.push({node, start: length, end: length + node.length});
        length += node.length;
      }
      function rect(offset) {
        const item = nodes.find(n => n.start <= offset && offset < n.end);
        const range = document.createRange();
        range.setStart(item.node, offset - item.start);
        range.setEnd(item.node, offset - item.start + 1);
        return range.getBoundingClientRect();
      }
      const first = rect(start), last = rect(end - 1);
      return {x1: first.left + 0.1, y1: first.top + first.height / 2,
              x2: last.right - 0.1, y2: last.top + last.height / 2};
    }""", offsets)
    page.mouse.move(points['x1'], points['y1'])
    page.mouse.down()
    page.mouse.move(points['x2'], points['y2'], steps=8)
    page.mouse.up()
    assert page.evaluate('window.getSelection().toString()') == text[start:end]
    from playwright.sync_api import expect
    expect(page.locator('#selectionToolbar')).to_be_visible()


def add_selection(page, text, start, end, cat='PERSONA', *, allow_partial=False):
    from playwright.sync_api import expect

    select_range(page, text, start, end)
    expect(page.locator('#selPartial')).not_to_be_checked()
    if allow_partial:
        page.locator('#selPartial').check()
    page.locator('#selCat').select_option(cat)
    with page.expect_response(lambda r: r.url.endswith('/api/manual-detection')) as saved:
        page.locator('#selAnonOnlyBtn').click()
    response = saved.value
    assert response.ok, response.text()
    expect(page.locator('#selectionToolbar')).to_be_hidden()
    return response.request.post_data_json, response.json()


def assert_exports(page, expected, tmp_path, *, editor_text=None, prefix='sintetico'):
    from playwright.sync_api import expect

    page.locator('#viewAnon').click()
    expect(page.locator('#docPreview')).to_have_text(expected, use_inner_text=False)
    page.locator('#openEditorBtn').click()
    expect(page.locator('#editorText')).to_have_value(expected)
    if editor_text is not None:
        page.locator('#editorText').fill(editor_text)
    assert_editor_downloads(page, expected if editor_text is None else editor_text, tmp_path, prefix=prefix)


def assert_editor_downloads(page, expected, tmp_path, *, prefix='sintetico'):
    from playwright.sync_api import expect

    expect(page.locator('#editorText')).to_have_value(expected)
    for extension, button in [('docx', '#exportDocx'), ('pdf', '#exportPdf')]:
        with page.expect_response(lambda r: r.url.endswith('/api/export/' + extension)) as exported:
            with page.expect_download() as downloaded:
                page.locator(button).click()
        assert exported.value.ok, exported.value.text()
        assert exported.value.request.post_data_json['text'] == expected
        output = tmp_path / f'{prefix}.{extension}'
        downloaded.value.save_as(output)
        if extension == 'docx':
            actual = '\n'.join(p.text for p in Document(output).paragraphs)
        else:
            with pdfplumber.open(output) as pdf:
                actual = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        assert actual == expected


@pytest.mark.parametrize('separator', ['  ', '\t', '\n'], ids=['spaces', 'tab', 'linebreak'])
def test_selection_keeps_actual_dom_range(page, tmp_path, separator):
    text = f'Ana Ruiz; Ana{separator}Ruiz'
    load_document(page, text)
    start, end = text.rindex('Ana'), len(text)
    payload, data = add_selection(page, text, start, end)
    assert (payload['start'], payload['end'], payload['original']) == (start, end, text[start:end])
    assert any((p['start'], p['end']) == (start, end) for p in data['detection']['positions'])
    assert_exports(page, 'Ana Ruiz; ' + data['detection']['placeholder'], tmp_path)


@pytest.mark.parametrize('allow_partial', [False, True], ids=['complete', 'partial'])
def test_overlapping_manual_selection_reaches_downloads(page, tmp_path, allow_partial):
    text = '121212'
    load_document(page, text)
    payload, data = add_selection(page, text, 2, 6, 'OTRO', allow_partial=allow_partial)
    assert (payload['start'], payload['end']) == (2, 6)
    assert payload['allow_partial'] is allow_partial
    expected = ('' if allow_partial else '12') + data['detection']['placeholder']
    assert_exports(page, expected, tmp_path)


def test_group_label_updates_visible_variants_without_switching_view(page, tmp_path):
    from playwright.sync_api import expect

    text = 'Ana Ruiz declaró. A. Ruiz volvió.'
    load_document(page, text)
    _, first = add_selection(page, text, 0, len('Ana Ruiz'))
    start = text.index('A. Ruiz')
    _, second = add_selection(page, text, start, start + len('A. Ruiz'))
    first_id, second_id = first['detection']['id'], second['detection']['id']
    first_row = page.locator(f'#detBody tr[data-id="{first_id}"]')
    second_row = page.locator(f'#detBody tr[data-id="{second_id}"]')
    first_row.locator('.combo-trigger').click()
    with page.expect_response(lambda r: r.url.endswith('/api/assign-cluster')):
        first_row.locator('.combo-new').click()
    second_row.locator('.combo-trigger').click()
    with page.expect_response(lambda r: r.url.endswith('/api/assign-cluster')):
        second_row.locator('.combo-item:not(.combo-new)').first.click()
    page.locator('#tabClusters').click()
    with page.expect_response(lambda r: '/confirm?' in r.url):
        page.locator('button[data-action="confirm"]').click()
    page.locator('#tabDetections').click()
    page.locator('#viewAnon').click()
    label = first_row.locator('.placeholder-input')
    with page.expect_response(lambda r: '/api/detections/' in r.url and r.request.method == 'PATCH'):
        label.fill('[TESTIGO]')
    expect(second_row.locator('.placeholder-input')).to_have_value('[TESTIGO]')
    expected = '[TESTIGO] declaró. [TESTIGO] volvió.'
    expect(page.locator('#docPreview')).to_have_text(expected, use_inner_text=False)
    expect(label).to_be_focused()
    assert label.evaluate('(el) => [el.selectionStart, el.selectionEnd]') == [9, 9]
    page.locator('#tabClusters').click()
    with page.expect_response(lambda r: '/api/clusters/' in r.url and r.request.method == 'PATCH') as changed:
        page.locator('.cluster-category-select').select_option('DOMICILIO')
    assert changed.value.ok, changed.value.text()
    page.locator('#tabDetections').click()
    for row in (first_row, second_row):
        expect(row.locator('.cat-select')).to_have_value('DOMICILIO')
        expect(row.locator('.placeholder-input')).to_have_value('[TESTIGO]')
    assert_exports(page, expected, tmp_path)


def test_latest_overlap_decision_keeps_full_coverage_and_other_occurrences(page, tmp_path):
    from playwright.sync_api import expect

    text = 'Ana Ruiz volvió. Ana Ruiz declaró.'
    load_document(page, text)
    _, first = add_selection(page, text, 0, len('Ana Ruiz'))
    _, second = add_selection(page, text, 4, len('Ana Ruiz volvió'))
    first_det, second_det = first['detection'], second['detection']
    first_row = page.locator(f'#detBody tr[data-id="{first_det["id"]}"]')
    second_row = page.locator(f'#detBody tr[data-id="{second_det["id"]}"]')
    assert first_det['positions'] == [
        {'start': 0, 'end': 8, 'raw': 'Ana Ruiz'},
        {'start': 17, 'end': 25, 'raw': 'Ana Ruiz'},
    ]
    assert second_det['manual_order'] > first_det['manual_order']
    expect(first_row.locator('.placeholder-input')).to_have_value(first_det['placeholder'])
    expect(first_row.locator('.effective-replacement')).to_have_text(
        f'Aplicado por aparición: 1: {second_det["placeholder"]}; 2: {first_det["placeholder"]}',
    )
    assert_exports(page, f'{second_det["placeholder"]}. {first_det["placeholder"]} declaró.', tmp_path, prefix='solapamiento')

    page.locator('#closeEditorBtn').click()
    with page.expect_response(lambda r: f'/api/detections/{first_det["id"]}' in r.url and r.request.method == 'PATCH') as saved:
        first_row.locator('.placeholder-input').fill('[PERSONA_REVISADA]')
    assert saved.value.ok, saved.value.text()
    expected = '[PERSONA_REVISADA]. [PERSONA_REVISADA] declaró.'
    expect(page.locator('#docPreview')).to_have_text(expected, use_inner_text=False)
    expect(second_row.locator('.effective-replacement')).to_have_text('Aplicado por aparición: 1: [PERSONA_REVISADA]')
    with page.expect_response(lambda r: f'/api/detections/{first_det["id"]}' in r.url and r.request.method == 'PATCH') as reclassified:
        first_row.locator('.cat-select').select_option('DOMICILIO')
    assert reclassified.value.ok, reclassified.value.text()
    expect(first_row.locator('.placeholder-input')).to_have_value('[PERSONA_REVISADA]')
    assert_exports(page, expected, tmp_path, prefix='decision-editada')


def search_and_save(page):
    with page.expect_response(lambda r: r.url.endswith('/api/search-and-anonymize')) as saved:
        page.locator('#searchAnonBtn').click()
    response = saved.value
    assert response.ok, response.text()
    from playwright.sync_api import expect
    expect(page.locator('#searchInput')).to_have_value('')
    return response.request.post_data_json, response.json()


def test_search_complete_partial_and_unicode_positions_use_same_preview_matches(page):
    from playwright.sync_api import expect

    text = '📄 Jose\u0301; Jose\u0301. Mariana; Ana; Ana/otra; 123-456; 123.'
    load_document(page, text)
    page.locator('#openSearch').click()
    expect(page.locator('#searchPartial')).not_to_be_checked()
    for query in ('Jose', 'José'):
        page.locator('#searchInput').fill(query)
        expect(page.locator('#searchCount')).to_have_text('1 / 2')
        expect(page.locator('#docPreview .search-match')).to_have_text(['Jose\u0301', 'Jose\u0301'])
    payload, _ = search_and_save(page)
    assert payload['allow_partial'] is False
    assert payload['positions'] == [
        {'start': 2, 'end': 7, 'raw': 'Jose\u0301'},
        {'start': 9, 'end': 14, 'raw': 'Jose\u0301'},
    ]

    page.locator('#searchInput').fill('Ana')
    expect(page.locator('#searchCount')).to_have_text('1 / 1')
    expect(page.locator('#docPreview .search-match')).to_have_text(['Ana'])
    page.locator('#searchPartial').check()
    expect(page.locator('#searchCount')).to_have_text('1 / 3')
    expect(page.locator('#docPreview .search-match')).to_have_text(['ana', 'Ana', 'Ana'])
    payload, _ = search_and_save(page)
    assert payload['allow_partial'] is True
    expected_starts = [text.index('Mariana') + 4, text.index('Ana;'), text.index('Ana/otra')]
    assert [(p['start'], p['end']) for p in payload['positions']] == [(start, start + 3) for start in expected_starts]

    page.locator('#searchInput').fill('123')
    page.locator('#searchPartial').uncheck()
    expect(page.locator('#searchCount')).to_have_text('1 / 1')
    expect(page.locator('#docPreview .search-match')).to_have_text(['123'])
    page.locator('#searchPartial').check()
    expect(page.locator('#searchCount')).to_have_text('1 / 2')
    payload, _ = search_and_save(page)
    assert payload['allow_partial'] is True
    assert [(p['start'], p['end']) for p in payload['positions']] == [
        (text.index('123-456'), text.index('123-456') + 3), (text.rindex('123'), text.rindex('123') + 3),
    ]

    page.locator('#searchClose').click()
    select_range(page, text, text.index('Mariana') + 4, text.index('Mariana') + 7)
    expect(page.locator('#selPartial')).not_to_be_checked()
    page.locator('#selPartial').check()
    page.locator('#selCancelBtn').click()
    select_range(page, text, text.index('Ana;'), text.index('Ana;') + 3)
    expect(page.locator('#selPartial')).not_to_be_checked()
    page.locator('#selCancelBtn').click()
    load_document(page, 'Otro documento sin datos.')
    page.locator('#openSearch').click()
    expect(page.locator('#searchPartial')).not_to_be_checked()


def test_reviewed_empty_table_exports_editor_changes_and_empty_text(page, tmp_path):
    from playwright.sync_api import expect

    text = 'Texto sintético sin datos personales.'
    load_document(page, text)
    expect(page.locator('#detBody')).to_contain_text('Sin detecciones')
    assert_exports(page, text, tmp_path, editor_text='Texto corregido para compartir.', prefix='editor-corregido')
    page.locator('#editorText').fill('')
    assert_editor_downloads(page, '', tmp_path, prefix='editor-vacio')


def test_deleting_last_detection_regenerates_editor_and_downloads(page, tmp_path):
    from playwright.sync_api import expect

    text = 'Ana Ruiz declaró.'
    load_document(page, text)
    _, data = add_selection(page, text, 0, 8)
    assert_exports(page, data['detection']['placeholder'] + ' declaró.', tmp_path, prefix='antes-de-eliminar')
    page.locator('#closeEditorBtn').click()
    row = page.locator(f'#detBody tr[data-id="{data["detection"]["id"]}"]')
    with page.expect_response(lambda r: '/api/detections/' in r.url and r.request.method == 'DELETE') as deleted:
        row.locator('.delete-btn').click()
    assert deleted.value.ok, deleted.value.text()
    assert deleted.value.json()['detections'] == []
    expect(page.locator('#detBody')).to_contain_text('Sin detecciones')
    assert_exports(page, text, tmp_path, prefix='ultima-eliminada')


def test_just_uploaded_document_does_not_offer_export_before_review(page):
    from playwright.sync_api import expect

    load_document(page, 'Documento todavía sin revisar.', analyze=False)
    expect(page.locator('#workspace')).to_be_hidden()
    expect(page.locator('#exportPanel')).to_be_hidden()
    expect(page.locator('#editorPanel')).to_be_hidden()
