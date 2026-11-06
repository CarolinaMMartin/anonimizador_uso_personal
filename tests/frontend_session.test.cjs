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
      assignDetectionToCluster, absorbClusterInto, changeClusterCategory, clustersForCategory, clusterCard, confirmClusterById,
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
      editRow(id, patch) { Object.assign(detections.find(d => d.id === id), patch); scheduleDetectionPatch(id, patch); },
      mode(mode) { viewMode = mode; },
      docText: () => docText,
      detections: () => JSON.parse(JSON.stringify(detections)),
      clusters: () => JSON.parse(JSON.stringify(clusters)),
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

test('saved group labels update every visible occurrence without switching preview mode', async () => {
  const text = 'Ana Ruiz declaró. A. Ruiz volvió.';
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Ana Ruiz', placeholder: '[PERSONA_1]',
      enabled: true, positions: [{ start: 0, end: 8 }] },
    { id: 1, cat: 'PERSONA', original: 'A. Ruiz', placeholder: '[PERSONA_1]',
      enabled: true, positions: [{ start: 18, end: 25 }] },
  ];
  const { app, element } = createApp(async (_url, options) => {
    const { placeholder } = JSON.parse(options.body);
    return json({ detections: rows.map((row) => ({ ...row, placeholder })), clusters: [] });
  });
  app.setDocument(text);
  app.setReview(rows, []);
  app.mode('anon');
  app.edit({ placeholder: '[TESTIGO]' });
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '[TESTIGO] declaró. [PERSONA_1] volvió.');
  await app.flushPendingSaves();
  assert.equal(element('docPreview').textContent, '[TESTIGO] declaró. [TESTIGO] volvió.');
});

test('latest manual choice covers the overlap without changing an unrelated occurrence', () => {
  const { app, element } = createApp();
  app.setDocument('abcdefg abcde');
  app.setReview([
    { id: 0, cat: 'PERSONA', placeholder: '[OLD]', enabled: true, manual_order: 0,
      positions: [{ start: 0, end: 5 }, { start: 8, end: 13 }] },
    { id: 1, cat: 'OTRO', placeholder: '[NEW]', enabled: true, manual_order: 2,
      positions: [{ start: 2, end: 7 }] },
  ], []);
  app.mode('anon');
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '[NEW] [OLD]');
});

test('flush dispatches the latest actions in B then A order after A B A edits', async () => {
  const calls = [];
  const { app } = createApp(async (url) => { calls.push(url); return json({}); });
  app.setReview([0, 1].map(id => ({ id, cat: 'PERSONA', placeholder: '[OLD]', enabled: true,
    positions: [{ start: 0, end: 4 }] })), []);
  app.editRow(0, { placeholder: '[A]' });
  app.editRow(1, { placeholder: '[B]' });
  app.editRow(0, { placeholder: '[A2]' });
  await app.flushPendingSaves();
  assert.deepEqual(calls, ['/api/detections/1', '/api/detections/0']);
});

test('an older response with identical text keeps the later group decision pending', async () => {
  const rows = [0, 1].map(id => ({ id, cat: 'PERSONA', original: id ? 'Ann' : 'Ana', placeholder: '[OLD]', enabled: true,
    cluster_id: 'g', cluster_confirmed: true, positions: [{ start: id * 4, end: id * 4 + 3 }] }));
  const releases = [];
  const bodies = [];
  const { app, element } = createApp(async (_url, options) => {
    bodies.push(JSON.parse(options.body));
    await new Promise(resolve => releases.push(resolve));
    return json({ detections: rows.map(row => ({ ...row, placeholder: '[SAME]', manual_order: bodies.length })),
      clusters: [{ cluster_id: 'g', cat: 'PERSONA', status: 'confirmed', placeholder: '[SAME]', surfaces: ['Ana', 'Ann'] }] });
  });
  app.setDocument('Ana Ann');
  app.setReview(rows, [{ cluster_id: 'g', cat: 'PERSONA', status: 'confirmed' }]);
  app.mode('anon');
  app.editRow(0, { placeholder: '[SAME]' });
  const saving = app.flushPendingSaves();
  while (!releases.length) await delay(1);
  app.editRow(0, { placeholder: '[DIFFERENT]' });
  app.editRow(0, { placeholder: '[SAME]' });
  releases[0]();
  while (releases.length < 2) await delay(1);
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '[SAME] [SAME]');
  assert.ok(app.detections().every(row => row.manual_order >= 3));
  releases[1]();
  await saving;
  assert.equal(bodies.length, 2);
  assert.equal(app.pendingCount(), 0);
});

test('pending choices remain newer when the server has advanced beyond visible orders', async () => {
  const rows = [0, 1].map(id => ({ id, cat: 'OTRO', original: 'Ana', placeholder: '[OLD]',
    enabled: true, manual_order: 0, positions: [{ start: 0, end: 3 }] }));
  const releases = [];
  let calls = 0;
  const { app, element } = createApp(async (_url, options) => {
    const call = calls++, body = JSON.parse(options.body);
    await new Promise(resolve => releases.push(resolve));
    rows[call] = { ...rows[call], placeholder: body.placeholder, manual_order: 100 + call };
    return json({ detections: rows, clusters: [] });
  });
  app.setDocument('Ana'); app.setReview(rows, []); app.mode('anon');
  app.editRow(0, { placeholder: '[A]' });
  const saving = app.flushPendingSaves();
  while (!releases.length) await delay(1);
  app.editRow(1, { placeholder: '[B]' });
  releases[0]();
  while (releases.length < 2) await delay(1);
  app.renderPreviewLocal();
  const previewWhilePending = element('docPreview').textContent;
  releases[1](); await saving;
  assert.equal(previewWhilePending, '[B]');
  assert.equal(element('docPreview').textContent, '[B]');
});

for (const [text, query, expected] of [
  ['Ana Ana; xAna Ana Ana', 'Ana Ana', [[0, 7], [14, 21]]],
  ['📄 Jose\u0301; José.', 'jose', [[2, 7], [9, 13]]],
  ['+١٢٣ ١٢٣ +² ²', '١٢٣', [[5, 8]]],
  ['123-456; 123.', '123', [[9, 12]]],
]) {
  test(`complete search posts exact Unicode boundaries: ${text}`, async () => {
    let body;
    const { app, element } = createApp(async (url, options) => {
      if (url === '/api/search-and-anonymize') { body = JSON.parse(options.body); return json({ detections: [] }); }
      return json({ text, highlights: [] });
    });
    app.setDocument(text);
    element('searchInput').value = query;
    await element('searchAnonBtn').listeners.click();
    assert.deepEqual(body.positions.map(p => [p.start, p.end]), expected);
  });
}

for (const partial of [false, true]) {
  test(`whole search and explicit partial option (${partial}) agree with posted positions`, async () => {
    const bodies = [];
    const text = 'Ana y Mariana; Ana@example.test; Ana.';
    const { app, element } = createApp(async (url, options) => {
      if (url === '/api/search-and-anonymize') {
        bodies.push(JSON.parse(options.body));
        return json({ detections: [] });
      }
      return json({ text, highlights: [] });
    });
    app.setDocument(text);
    element('searchInput').value = 'Ana';
    element('searchPartial').checked = partial;
    await element('searchAnonBtn').listeners.click();
    assert.equal(bodies[0].positions.length, partial ? 4 : 2);
    assert.equal(bodies[0].allow_partial, partial);
  });
}

test('normalized search includes trailing combining marks in the original range', async () => {
  const bodies = [];
  const text = 'Jose\u0301';
  const { app, element } = createApp(async (url, options) => {
    if (url === '/api/search-and-anonymize') { bodies.push(JSON.parse(options.body)); return json({ detections: [] }); }
    return json({ text, highlights: [] });
  });
  app.setDocument(text);
  element('searchInput').value = 'José';
  await element('searchAnonBtn').listeners.click();
  assert.deepEqual(bodies[0].positions, [{ start: 0, end: 5, raw: text }]);
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

test('crossing detections highlight and anonymize their complete coverage without changing review positions', () => {
  const { app, element } = createApp();
  app.setDocument('📄 Juan Perez Gomez declaró.');
  app.setReview([
    { id: 0, cat: 'PERSONA', original: 'Juan Perez', placeholder: '[PERSONA_1]',
      enabled: true, positions: [{ start: 2, end: 12 }] },
    { id: 1, cat: 'PERSONA', original: 'Perez Gomez', placeholder: '[PERSONA_2]',
      enabled: true, positions: [{ start: 7, end: 18 }] },
  ], []);
  const before = app.detections();
  app.mode('orig');
  app.renderPreviewLocal();
  assert.match(element('docPreview').innerHTML, /^📄 <span[^>]+>Juan Perez Gomez<\/span> declaró\.$/);
  app.mode('anon');
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '📄 [PERSONA_1] declaró.');
  assert.deepEqual(app.detections(), before);
});

test('contained detections use the same full interval and placeholder in both preview modes', () => {
  const { app, element } = createApp();
  app.setDocument('Juan Perez Gomez declaró.');
  app.setReview([
    { id: 0, cat: 'PERSONA', original: 'Juan', placeholder: '[PERSONA_1]',
      enabled: true, positions: [{ start: 0, end: 4 }] },
    { id: 1, cat: 'PERSONA', original: 'Juan Perez Gomez', placeholder: '[PERSONA_2]',
      enabled: true, positions: [{ start: 0, end: 16 }] },
  ], []);
  app.mode('orig');
  app.renderPreviewLocal();
  assert.match(element('docPreview').innerHTML, /^<span[^>]+title="\[PERSONA_2\]">Juan Perez Gomez<\/span> declaró\.$/);
  app.mode('anon');
  app.renderPreviewLocal();
  assert.equal(element('docPreview').textContent, '[PERSONA_2] declaró.');
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

function misclassifiedReview() {
  const target = { cluster_id: 'person', cat: 'PERSONA', status: 'confirmed',
    placeholder: '[PERSONA_9]', canonical_label: '[PERSONA_9]', surfaces: ['Eliana Vorst'], confidence: 'alta' };
  const source = { cluster_id: 'company', cat: 'EMPRESA', status: 'suggested',
    surfaces: ['ELIANA VORST Fecha de Emisión'], confidence: 'alta' };
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Eliana Vorst', cluster_id: 'person',
      placeholder: '[PERSONA_9]', enabled: true, positions: [] },
    { id: 1, cat: 'EMPRESA', original: source.surfaces[0], cluster_id: 'company',
      placeholder: '[EMPRESA_1]', enabled: true, positions: [] },
  ];
  return { rows, target, source };
}

test('groups show an editable category and offer destinations from other categories', () => {
  const { app } = createApp();
  const { rows, target, source } = misclassifiedReview();
  app.setReview(rows, [source, target]);
  assert.deepEqual(Array.from(app.clustersForCategory('EMPRESA', 'company'), (c) => c.cluster_id), ['person']);
  const markup = app.clusterCard(source);
  assert.match(markup, /cluster-category-select/);
  assert.match(markup, /value="PERSONA"/);
  assert.match(markup, /value="EMPRESA" selected/);
  assert.match(markup, /Por revisar/);
  assert.doesNotMatch(markup, /conf-badge/);
});

test('manual merge across categories requires explicit choice and preserves the target replacement', async () => {
  const requests = [];
  const { rows, target, source } = misclassifiedReview();
  const { app, sandbox } = createApp(async (url, options) => {
    requests.push({ url, body: options.body && JSON.parse(options.body) });
    if (url.includes('/absorb')) return json({ clusters: [target], detections: rows.map((d) => ({ ...d,
      cat: 'PERSONA', cluster_id: 'person', placeholder: '[PERSONA_9]', cluster_confirmed: true })) });
    return json({ text: '', highlights: [] });
  });
  app.setReview(rows, [source, target]);
  sandbox.confirm = () => false;
  assert.equal(await app.absorbClusterInto('person', 'company'), false);
  assert.equal(requests.length, 0);
  assert.equal(app.detections()[1].cat, 'EMPRESA');
  let explanation = '';
  sandbox.confirm = (message) => { explanation = message; return true; };
  assert.equal(await app.absorbClusterInto('person', 'company'), true);
  assert.match(explanation, /EMPRESA a PERSONA/);
  assert.deepEqual(requests[0].body, { source_cluster_id: 'company', reclassify: true });
  assert.equal(app.detections()[1].placeholder, '[PERSONA_9]');
  assert.equal(app.detections()[1].cat, 'PERSONA');
});

test('category correction waits for the server and does not alter a failed review', async () => {
  const { rows, target, source } = misclassifiedReview();
  const { app } = createApp(async () => json({ detail: 'No se guardó la corrección' }, 500));
  app.setReview(rows, [source, target]);
  const before = app.detections();
  assert.equal(await app.changeClusterCategory('company', 'PERSONA'), false);
  assert.deepEqual(app.detections(), before);
  assert.equal(app.clusters()[0].cat, 'EMPRESA');
});

test('a corrected cluster refreshes detections, category and destination groups together', async () => {
  const { rows, target, source } = misclassifiedReview();
  const payloads = [];
  const { app } = createApp(async (url, options) => {
    if (options.method === 'PATCH') {
      payloads.push(JSON.parse(options.body));
      return json({ clusters: [{ ...source, cat: 'PERSONA' }, target], detections: rows.map((d) => ({ ...d,
        cat: 'PERSONA', placeholder: d.id === 1 ? '[PERSONA_10]' : d.placeholder })) });
    }
    return json({ text: '', highlights: [] });
  });
  app.setReview(rows, [source, target]);
  assert.equal(await app.changeClusterCategory('company', 'PERSONA'), true);
  assert.deepEqual(payloads, [{ cat: 'PERSONA' }]);
  assert.equal(app.detections()[1].cat, 'PERSONA');
  assert.equal(app.clusters()[0].cat, 'PERSONA');
});

test('single row assignment can explicitly correct its category', async () => {
  const { rows, target, source } = misclassifiedReview();
  const calls = [];
  const { app } = createApp(async (url, options) => {
    if (url === '/api/assign-cluster') {
      calls.push(JSON.parse(options.body));
      return json({ detections: rows.map((d) => ({ ...d, cat: 'PERSONA', cluster_id: 'person',
        placeholder: '[PERSONA_9]' })), clusters: [target] });
    }
    return json({ text: '', highlights: [] });
  });
  app.setReview(rows, [source, target]);
  assert.equal(await app.assignDetectionToCluster(1, 'person'), true);
  assert.equal(calls[0].reclassify, true);
  assert.equal(app.detections()[1].cat, 'PERSONA');
});

test('manual corrections render the new suggestions returned by the server', async () => {
  const group = { cluster_id: 'fresh', cat: 'PERSONA', status: 'suggested',
    surfaces: ['Eliana Vorst', 'Eliana'], confidence: 'media' };
  const rows = [
    { id: 0, cat: 'PERSONA', original: 'Eliana', placeholder: '[TESTIGO]', manual_placeholder: true,
      enabled: true, cluster_id: 'fresh', positions: [{ start: 0, end: 6 }] },
    { id: 1, cat: 'PERSONA', original: 'Eliana Vorst', placeholder: '[PERSONA_2]',
      enabled: true, cluster_id: 'fresh', positions: [{ start: 8, end: 20 }] },
  ];
  const { app, element } = createApp(async (url) => {
    if (url === '/api/manual-detection') return json({ detection: rows[1], detections: rows, clusters: [group] });
    return json({ text: 'Eliana. Eliana Vorst.', highlights: [] });
  });
  app.setDocument('Eliana. Eliana Vorst.');
  app.setReview([{ ...rows[0], cluster_id: null }], []);
  app.select('Eliana Vorst');
  await app.runManualDetectionAndMaybeGroup(false);
  assert.equal(app.clusters()[0].cluster_id, 'fresh');
  assert.match(element('clustersList').innerHTML, /Eliana Vorst/);
  assert.equal(app.detections()[0].placeholder, '[TESTIGO]');
  assert.equal(app.detections()[0].manual_placeholder, true);
});

function incorporationReview() {
  const { rows, target, source } = misclassifiedReview();
  source.cat = 'PERSONA';
  source.target_cluster_id = target.cluster_id;
  source.surfaces = ['Eliana'];
  rows[1] = { ...rows[1], cat: 'PERSONA', original: 'Eliana', placeholder: '[PERSONA_10]' };
  return { rows, target, source };
}

test('incorporation identifies its confirmed destination and cancellation makes no request', async () => {
  const calls = [];
  const { app, sandbox } = createApp(async (url) => { calls.push(url); return json({}); });
  const { rows, target, source } = incorporationReview();
  app.setReview(rows, [target, source]);
  const markup = app.clusterCard(source);
  assert.match(markup, /Incorporar a \[PERSONA_9\]/);
  assert.match(markup, /Incorporar al grupo/);
  assert.match(markup, /conservan su reemplazo actual/);
  assert.equal(app.looksSimilarDetection(rows[0], rows[1]), true);
  assert.equal(app.clustersForCategory('PERSONA', 'person').length, 0);
  sandbox.confirm = () => false;
  assert.equal(await app.confirmClusterById('company'), false);
  assert.deepEqual(calls, []);
  assert.equal(app.detections()[1].placeholder, '[PERSONA_10]');
  assert.equal(app.clusters().length, 2);
});

test('incorporation only replaces current labels after successful confirmation', async () => {
  const { rows, target, source } = incorporationReview();
  let succeeds = false;
  const { app } = createApp(async () => succeeds
    ? json({ cluster: target, clusters: [target], detections: rows.map((row) => ({ ...row,
      cluster_id: 'person', cluster_confirmed: true, placeholder: '[PERSONA_9]' })) })
    : json({ detail: 'No se pudo confirmar' }, 500));
  app.setReview(rows, [target, source]);
  await assert.rejects(app.confirmClusterById('company'), /No se pudo confirmar/);
  assert.equal(app.detections()[1].placeholder, '[PERSONA_10]');
  assert.equal(app.clusters().length, 2);
  succeeds = true;
  assert.equal(await app.confirmClusterById('company'), true);
  assert.deepEqual(Array.from(app.clusters(), (group) => group.cluster_id), ['person']);
  assert.equal(app.detections()[1].placeholder, '[PERSONA_9]');
});

test('incorporation response from an old document cannot overwrite a new review', async () => {
  const { rows, target, source } = incorporationReview();
  let release, started;
  const pendingRequest = new Promise((resolve) => { started = resolve; });
  const { app } = createApp(async () => {
    started();
    await new Promise((resolve) => { release = resolve; });
    return json({ cluster: target, clusters: [target], detections: rows });
  });
  app.setReview(rows, [target, source]);
  const confirmation = app.confirmClusterById('company');
  await pendingRequest;
  app.init('new-document');
  release();
  await assert.rejects(confirmation, (error) => error.name === 'AbortError');
  assert.equal(app.clusters().length, 0);
  assert.equal(app.detections()[0].original, 'JUAN PEREZ');
});
