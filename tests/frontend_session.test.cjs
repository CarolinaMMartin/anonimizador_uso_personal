// Behavioral regressions for session/save/export races, using Node's built-in VM.
// The DOM and server are simulated; this does not replace a browser/portable test.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json' },
});

function createApp(handler = async () => json({})) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      id, hidden: true, value: '', textContent: '', innerHTML: '', dataset: {}, listeners: {},
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      style: { setProperty() {}, getPropertyValue() { return ''; } },
      addEventListener(event, callback) { this.listeners[event] = callback; },
      querySelectorAll() { return []; },
      setAttribute() {}, focus() {}, select() {}, click() {}, append() {}, contains() { return true; },
    });
    return elements.get(id);
  }
  const storage = { getItem() { return null; }, setItem() {} };
  const sandbox = {
    console, setTimeout, clearTimeout, AbortController, DOMException, URL,
    sessionStorage: storage, localStorage: storage,
    confirm: () => true, navigator: {},
    fetch: (url, options) => url === '/health' ? Promise.resolve(json({})) : handler(url, options),
    window: { addEventListener() {}, getSelection: () => null },
    document: {
      getElementById: element, querySelectorAll: () => [],
      querySelector: () => ({ value: 'cat' }), addEventListener() {},
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(readFileSync(join(__dirname, '../frontend/app.js'), 'utf8') + `
    globalThis.controls = {
      sessionFetch, flushPendingSaves, scheduleDetectionPatch, openEditorPanel,
      renderPreviewLocal, loadPreview, beginRequest, endRequest, resetDocumentState,
      runManualDetectionAndMaybeGroup, buildMarkdownExport, assertEditorCurrent,
      assignDetectionToCluster,
      looksSimilarDetection, joinSimilarDetections, ignoreSimilarDetections,
      toBrowserOffset, toDocumentOffset,
      setDocument(text) { docText = text; detections = []; },
      setReview(rows, groups) { detections = rows; clusters = groups; },
      init(id = 'A') {
        resetDocumentState(); sessionId = id;
        docText = 'JUAN PEREZ solicita que se rechace la demanda';
        detections = [{ id: 0, cat: 'PERSONA', original: 'JUAN PEREZ', placeholder: '[PERSONA_1]',
          enabled: true, positions: [{ start: 0, end: 10 }], cluster_id: null }];
      },
      select(text = 'JUAN PEREZ', cat = 'PERSONA') {
        const start = docText.indexOf(text);
        pendingSelection = { start, end: start + text.length, text };
        $('selCat').value = cat;
      },
      edit(patch) { Object.assign(detections[0], patch); scheduleDetectionPatch(0, patch); },
      mode(mode) { viewMode = mode; },
      docText: () => docText,
      detections: () => JSON.parse(JSON.stringify(detections)),
      busy: () => activeAbort !== null,
      pendingCount: () => pendingPatches.size + pendingSaves.size,
      filename(value) { currentDocName = value; },
      editor(value) { $('editorText').value = value; editorSnapshot.dirty = true; },
      errors: () => saveErrors.size,
    };
  `, sandbox);
  sandbox.controls.init();
  return { app: sandbox.controls, element, sandbox };
}

test('analyze without categories keeps the current review and makes no request', async () => {
  const calls = [];
  const { app, element } = createApp(async (url) => { calls.push(url); return json({}); });
  const before = app.detections();
  element('editorText').value = 'edición conservada';
  await element('analyzeBtn').listeners.click();
  assert.deepEqual(calls, []);
  assert.deepEqual(app.detections(), before);
  assert.equal(element('editorText').value, 'edición conservada');
  assert.equal(app.busy(), false);
});

test('field changes are combined and editor waits for a slow PATCH', async () => {
  const calls = [];
  const server = { id: 0, cat: 'PERSONA', original: 'JUAN PEREZ', placeholder: '[PERSONA_1]',
    enabled: true, positions: [{ start: 0, end: 10 }] };
  const { app, element } = createApp(async (url, options) => {
    calls.push(url);
    if (options.method === 'PATCH') {
      await delay(100);
      Object.assign(server, JSON.parse(options.body));
      return json({ detections: [server], clusters: [] });
    }
    if (url === '/api/export/preview') {
      assert.equal(server.enabled, false);
      assert.equal(server.placeholder, '[CORREGIDO]');
      return json({ text: 'texto verificado' });
    }
    return json({});
  });
  app.edit({ enabled: false });
  app.edit({ placeholder: '[CORREGIDO]' });
  await app.openEditorPanel();
  assert.deepEqual(calls, ['/api/detections/0', '/api/export/preview']);
  assert.equal(element('editorText').value, 'texto verificado');
  assert.equal(app.pendingCount(), 0);
});

test('flush waits for an already started PATCH even after its debounce timer fired', async () => {
  let finish;
  let started = false;
  const { app } = createApp(async () => {
    started = true;
    await new Promise((resolve) => { finish = resolve; });
    return json({});
  });
  app.edit({ placeholder: '[CORREGIDO]' });
  await delay(470);
  assert.equal(started, true);
  let flushed = false;
  const flush = app.flushPendingSaves().then(() => { flushed = true; });
  await delay(20);
  assert.equal(flushed, false);
  finish();
  await flush;
  assert.equal(flushed, true);
});

test('failed saves prevent editor/export preparation', async () => {
  const calls = [];
  const { app, element } = createApp(async (url) => {
    calls.push(url);
    return json({ detail: 'falló el guardado' }, 500);
  });
  app.edit({ placeholder: '[CORREGIDO]' });
  await app.openEditorPanel();
  assert.deepEqual(calls, ['/api/detections/0']);
  assert.equal(element('editorPanel').hidden, true);
  assert.equal(app.errors(), 1);
});

test('a later edit retries all fields from a failed save', async () => {
  const payloads = [];
  const { app } = createApp(async (_url, options) => {
    payloads.push(JSON.parse(options.body));
    return payloads.length === 1 ? json({ detail: 'guardado fallido' }, 500) : json({});
  });
  app.edit({ enabled: false });
  await assert.rejects(app.flushPendingSaves(), /sin guardar/);
  app.edit({ placeholder: '[CORREGIDO]' });
  await app.flushPendingSaves();
  assert.equal(payloads[1].enabled, false);
  assert.equal(payloads[1].placeholder, '[CORREGIDO]');
  assert.equal(app.errors(), 0);
});

test('manual API failure creates no local detection and reports an error', async () => {
  const { app, element } = createApp(async () => json({ detail: 'falló la detección' }, 500));
  app.select();
  const before = app.detections();
  await app.runManualDetectionAndMaybeGroup(false);
  assert.deepEqual(app.detections(), before);
  assert.equal(element('toast').textContent, 'falló la detección');
  assert.equal(element('toast').className, 'toast show error');
});

test('failed group assignment leaves the server-backed state unchanged', async () => {
  const { app, element } = createApp(async () => json({ detail: 'falló el grupo' }, 500));
  await app.assignDetectionToCluster(0, '__new__');
  assert.equal(app.detections()[0].cluster_id, null);
  assert.equal(element('toast').className, 'toast show error');
});

test('changing documents clears pending edits and never patches the new session', async () => {
  const calls = [];
  const { app, element } = createApp(async (url) => { calls.push(url); return json({}); });
  app.edit({ enabled: false });
  app.init('B');
  await app.flushPendingSaves();
  await delay(470);
  assert.deepEqual(calls, []);
  assert.equal(element('editorText').value, '');
  assert.equal(element('editorPanel').hidden, true);
  assert.equal(element('exportPanel').hidden, true);
});

test('late responses and JSON reads are rejected after changing documents', async () => {
  let finish;
  const { app } = createApp(async () => {
    await new Promise((resolve) => { finish = resolve; });
    return json({ session: 'A' });
  });
  const pending = app.sessionFetch('/api/preview?session_id=A');
  app.init('B');
  finish();
  await assert.rejects(pending, (error) => error.name === 'AbortError');
});

test('response JSON cannot be consumed after reset', async () => {
  const { app } = createApp(async () => json({ session: 'A' }));
  const response = await app.sessionFetch('/api/preview?session_id=A');
  app.init('B');
  await assert.rejects(response.json(), (error) => error.name === 'AbortError');
});

test('an old request finalizer cannot clear the new cancellation controller', () => {
  const { app } = createApp();
  const old = app.beginRequest();
  const latest = app.beginRequest();
  assert.equal(old.aborted, true);
  assert.equal(app.endRequest(old), false);
  assert.equal(app.busy(), true);
  assert.equal(app.endRequest(latest), true);
});

test('preview keeps the original immutable across repeated edits in anonymous mode', async () => {
  const { app, element } = createApp(async (url) => {
    assert.match(url, /mode=orig$/);
    return json({ text: 'JUAN PEREZ solicita que se rechace la demanda', highlights: [] });
  });
  app.mode('anon');
  await app.loadPreview();
  assert.equal(element('docPreview').textContent, '[PERSONA_1] solicita que se rechace la demanda');
  app.edit({ placeholder: '[X]' });
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '[X] solicita que se rechace la demanda');
  assert.equal(app.docText(), 'JUAN PEREZ solicita que se rechace la demanda');
  app.resetDocumentState();
});

test('editor preserves manual corrections on reopening and Markdown uses a neutral title', async () => {
  let previews = 0;
  const { app, element } = createApp(async () => {
    previews++;
    return json({ text: '[PERSONA_1] solicita una medida' });
  });
  await app.openEditorPanel();
  app.editor('Texto corregido');
  await app.openEditorPanel();
  assert.equal(previews, 1);
  assert.equal(element('editorText').value, 'Texto corregido');
  app.filename('JUAN PEREZ DNI 12345678.docx');
  assert.equal(app.buildMarkdownExport(), '# Documento anonimizado\n\nTexto corregido\n');
});

test('exportable draft is rejected when the detections change', async () => {
  const { app } = createApp(async () => json({ text: '[PERSONA_1]' }));
  await app.openEditorPanel();
  app.edit({ placeholder: '[CORREGIDO]' });
  assert.throws(() => app.assertEditorCurrent(), /revisión cambió/);
  assert.throws(() => app.buildMarkdownExport(), /revisión cambió/);
  app.resetDocumentState();
});

test('attribute quotes are escaped in actual rendered markup', async () => {
  const { app, element } = createApp();
  app.edit({ placeholder: '" autofocus onfocus="alert(1)' });
  app.mode('orig');
  app.renderPreviewLocal();
  assert.match(element('docPreview').innerHTML, /title="&quot; autofocus onfocus=&quot;alert\(1\)"/);
  app.resetDocumentState();
});

test('similar actions follow backend groups instead of shared surnames or substrings', () => {
  const { app } = createApp();
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Ana Vorst', cluster_id: 'A' },
    { id: 1, cat: 'PERSONA', original: 'Anna Vorst', cluster_id: 'B' },
    { id: 2, cat: 'PERSONA', original: 'Vorst', cluster_id: null },
    { id: 3, cat: 'PERSONA', original: 'A. Vorst', cluster_id: 'A' },
    { id: 4, cat: 'EMPRESA', original: 'Ana Vorst SA', cluster_id: 'A' },
  ];
  app.setReview(rows, [{ cluster_id: 'A', cat: 'PERSONA', status: 'suggested' },
    { cluster_id: 'B', cat: 'PERSONA', status: 'confirmed' }]);
  assert.equal(app.looksSimilarDetection(rows[0], rows[1]), false);
  assert.equal(app.looksSimilarDetection(rows[0], rows[2]), false);
  assert.equal(app.looksSimilarDetection(rows[0], rows[3]), true);
  assert.equal(app.looksSimilarDetection(rows[0], rows[4]), false);
});

test('ignore similar disables only members of the chosen identity', async () => {
  const patches = [];
  const { app } = createApp(async (url, options) => {
    patches.push({ url, patch: JSON.parse(options.body) });
    return json({});
  });
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Ana Vorst', cluster_id: 'A', enabled: true, positions: [] },
    { id: 1, cat: 'PERSONA', original: 'Anna Vorst', cluster_id: 'B', enabled: true, positions: [] },
    { id: 2, cat: 'PERSONA', original: 'A. Vorst', cluster_id: 'A', enabled: true, positions: [] },
  ];
  app.setReview(rows, [{ cluster_id: 'A', cat: 'PERSONA', status: 'suggested' },
    { cluster_id: 'B', cat: 'PERSONA', status: 'suggested' }]);
  await app.ignoreSimilarDetections(0);
  assert.deepEqual(patches.map((p) => p.url), ['/api/detections/0', '/api/detections/2']);
  assert.equal(app.detections()[1].enabled, true);
});

test('join similar confirms the proposed identity without absorbing another person', async () => {
  const calls = [];
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Ana Vorst', cluster_id: 'A', enabled: true, positions: [] },
    { id: 1, cat: 'PERSONA', original: 'Anna Vorst', cluster_id: 'B', enabled: true, positions: [] },
    { id: 2, cat: 'PERSONA', original: 'A. Vorst', cluster_id: 'A', enabled: true, positions: [] },
  ];
  const { app } = createApp(async (url) => {
    calls.push(url);
    if (url.includes('/confirm')) return json({
      cluster: { cluster_id: 'A', cat: 'PERSONA', status: 'confirmed', surfaces: ['Ana Vorst', 'A. Vorst'] },
      detections: rows.map((r) => ({ ...r, placeholder: r.cluster_id === 'A' ? '[PERSONA_10]' : '[PERSONA_2]' })),
    });
    return json({ text: 'texto ficticio', highlights: [] });
  });
  app.setReview(rows, [
    { cluster_id: 'A', cat: 'PERSONA', status: 'suggested', surfaces: ['Ana Vorst', 'A. Vorst'] },
    { cluster_id: 'B', cat: 'PERSONA', status: 'suggested', surfaces: ['Anna Vorst'] },
  ]);
  await app.joinSimilarDetections(0);
  assert.equal(calls.filter((url) => url.includes('/confirm')).length, 1);
  assert.equal(calls.some((url) => url.includes('assign-cluster')), false);
  assert.deepEqual([...app.detections()].map((d) => d.placeholder), ['[PERSONA_10]', '[PERSONA_2]', '[PERSONA_10]']);
});

test('Unicode positions keep preview highlights and replacements aligned', () => {
  const { app, element } = createApp();
  app.setDocument('📄 Campana 39. Fin.');
  app.setReview([{ id: 0, cat: 'DOMICILIO', original: 'Campana 39', placeholder: '[DOMICILIO_1]',
    enabled: true, positions: [{ start: 2, end: 12 }] }], []);
  app.mode('orig');
  app.renderPreviewLocal();
  assert.match(element('docPreview').innerHTML, /^📄 <span[^>]+>Campana 39<\/span>\. Fin\.$/);
  app.mode('anon');
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '📄 [DOMICILIO_1]. Fin.');
});

test('manual selection sends Unicode offsets and refreshes the actual accepted review', async () => {
  const text = '📄 Campana 39. Fin.';
  const row = { id: 0, cat: 'DOMICILIO', original: 'Campana 39', placeholder: '[DOMICILIO_1]',
    enabled: true, positions: [{ start: 2, end: 12 }] };
  const calls = [];
  const { app, element } = createApp(async (url, options) => {
    calls.push(url);
    if (url === '/api/manual-detection') {
      const body = JSON.parse(options.body);
      assert.equal(body.start, 2);
      assert.equal(body.end, 12);
      assert.equal(body.original, 'Campana 39');
      return json({ detection: row, detections: [row] });
    }
    return json({ text, highlights: [] });
  });
  app.setDocument(text);
  app.select('Campana 39', 'DOMICILIO');
  await app.runManualDetectionAndMaybeGroup(false);
  assert.deepEqual(calls, ['/api/manual-detection', '/api/preview?session_id=A&mode=orig']);
  assert.equal(app.detections()[0].original, 'Campana 39');
  app.mode('anon');
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '📄 [DOMICILIO_1]. Fin.');
});

test('search uses the latest query and Unicode offsets even before its debounce fires', async () => {
  const bodies = [];
  const { app, element } = createApp(async (url, options) => {
    if (url === '/api/search-and-anonymize') {
      bodies.push(JSON.parse(options.body));
      return json({ detections: [] });
    }
    return json({ text: '📄 Campana 39. Campana 39.', highlights: [] });
  });
  app.setDocument('📄 Campana 39. Campana 39.');
  element('searchInput').value = 'Campana 39';
  element('searchCat').value = 'DOMICILIO';
  await element('searchAnonBtn').listeners.click();
  assert.equal(bodies.length, 1);
  assert.deepEqual(bodies[0].positions, [
    { start: 2, end: 12, raw: 'Campana 39' },
    { start: 14, end: 24, raw: 'Campana 39' },
  ]);
});

test('changing document while manual selection waits for a save sends no selection to the new document', async () => {
  const calls = [];
  let finish, started;
  const saving = new Promise((resolve) => { started = resolve; });
  const { app } = createApp(async (url) => {
    calls.push(url);
    if (url === '/api/detections/0') {
      started();
      await new Promise((resolve) => { finish = resolve; });
    }
    return json({});
  });
  app.edit({ placeholder: '[CAMBIO]' });
  app.select();
  const pending = app.runManualDetectionAndMaybeGroup(false);
  await saving;
  app.init('B');
  finish();
  await pending;
  assert.deepEqual(calls, ['/api/detections/0']);
});
