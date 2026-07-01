/* Anonimizador Judicial - Frontend */
const API = '';

let activeAbort = null;

function beginRequest() {
  activeAbort?.abort();
  activeAbort = new AbortController();
  return activeAbort.signal;
}

function endRequest() {
  activeAbort = null;
}

function setProcessBusy(busy, label) {
  const cancelBtn = $('cancelProcessBtn');
  const analyzeBtn = $('analyzeBtn');
  if (cancelBtn) cancelBtn.hidden = !busy;
  if (analyzeBtn) analyzeBtn.disabled = busy || !sessionId;
  if (busy && label) {
    $('loader1')?.classList.add('show');
  } else {
    $('loader1')?.classList.remove('show');
  }
}

async function cancelActiveProcess() {
  activeAbort?.abort();
  endRequest();
  setProcessBusy(false);
  if (sessionId) {
    try {
      await fetch(API + '/api/analyze/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (_) {
      /* servidor puede estar ocupado; igual liberamos la UI */
    }
  }
  showToast('Proceso detenido. Podés volver a analizar.', 'success');
}

// Mostrar estado del motor local
fetch(API + '/health')
  .then((r) => r.json())
  .then((data) => {
    const nlp = data.nlp_layers;
    const ver = data.app_version ? `v${data.app_version}` : '';
    const badge = document.getElementById('nlpBadge');
    if (badge && nlp) {
      const presidioOk = nlp.presidio?.available;
      const spacyOk = nlp.spacy?.available;
      const presidio = presidioOk ? 'Presidio' : 'Presidio off';
      const spacy = spacyOk ? 'spaCy' : 'spaCy off';
      badge.textContent = `100% local ${ver} · ${presidio} · ${spacy}`;
      badge.classList.remove('badge-ok', 'badge-warn', 'badge-error');
      if (!presidioOk || !spacyOk) {
        badge.classList.add('badge-warn');
        badge.title =
          (nlp.spacy?.error || '') +
          (nlp.presidio?.error ? '\n' + nlp.presidio.error : '') +
          '\n\nReiniciá la aplicación con INICIAR.bat. Si el problema sigue, volvé a extraer el ZIP completo.';
      } else {
        badge.classList.add('badge-ok');
        badge.title = 'Procesamiento local. PDF digital nativo (sin OCR). Formatos: Word y PDF.';
      }
    } else if (badge) {
      badge.textContent = 'Servidor desactualizado — reiniciá la aplicación';
      badge.classList.add('badge-error');
    }
  })
  .catch(() => {});

let sessionId = null;
let docText = '';
let currentDocName = '';
let detections = [];
let clusters = [];
let viewMode = 'orig';

const $ = (id) => document.getElementById(id);

let reviewTab = sessionStorage.getItem('anon_review_tab') || 'detections';

function updateReviewTabBadges() {
  const enabled = detections.filter((d) => d.enabled).length;
  const detBadge = $('tabDetCount');
  const clusterBadge = $('tabClusterCount');
  if (detBadge) {
    detBadge.textContent =
      detections.length > 0 ? `${enabled}/${detections.length}` : '0';
  }
  if (clusterBadge) {
    clusterBadge.textContent = String(clusters.length);
  }
}

function switchReviewTab(tab) {
  reviewTab = tab;
  sessionStorage.setItem('anon_review_tab', tab);
  document.querySelectorAll('.review-tab').forEach((btn) => {
    const active = btn.dataset.tab === tab;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  const detPanel = $('panelDetections');
  const clusterPanel = $('panelClusters');
  if (detPanel) {
    detPanel.classList.toggle('active', tab === 'detections');
    detPanel.hidden = tab !== 'detections';
  }
  if (clusterPanel) {
    clusterPanel.classList.toggle('active', tab === 'clusters');
    clusterPanel.hidden = tab !== 'clusters';
  }
}

function initReviewTabs() {
  document.querySelectorAll('.review-tab').forEach((btn) => {
    btn.addEventListener('click', () => switchReviewTab(btn.dataset.tab));
  });
  switchReviewTab(reviewTab);
}

function showToast(msg, type = '') {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.classList.remove('show'), 2800);
}

async function parseApiError(res) {
  try {
    const data = await res.json();
    const d = data.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  } catch {
    /* ignore */
  }
  if (res.status === 404) {
    return 'No encontrado: reiniciá INICIAR.bat, recargá la página y volvé a analizar el documento.';
  }
  return res.statusText || 'Error en el servidor';
}

function requireSession() {
  if (!sessionId) {
    showToast('Sesión perdida: cargá el documento de nuevo.', 'error');
    return false;
  }
  return true;
}

function setActiveStep(n) {
  document.querySelectorAll('.step').forEach((el) => {
    const step = parseInt(el.dataset.step, 10);
    el.classList.toggle('active', step <= n);
  });
}

let openComboRoot = null;

let selectionClusterId = '';

/** Desplegable + buscador para asignar a grupos */
function mountGroupPicker(
  root,
  { getItems, onPick, triggerLabel = 'Elegir grupo…', selectOnly = false }
) {
  root.innerHTML = '';
  root.className = 'combo';

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'combo-trigger';
  trigger.textContent = triggerLabel;

  const panel = document.createElement('div');
  panel.className = 'combo-panel';

  const search = document.createElement('input');
  search.type = 'search';
  search.className = 'combo-search';
  search.placeholder = 'Buscar grupo…';
  search.autocomplete = 'off';

  const menu = document.createElement('div');
  menu.className = 'combo-menu';
  menu.setAttribute('role', 'listbox');

  panel.append(search, menu);
  root.append(trigger, panel);

  let focusIdx = -1;

  function close() {
    root.classList.remove('open');
    if (openComboRoot === root) openComboRoot = null;
  }

  function renderList() {
    const q = search.value.trim().toLowerCase();
    const items = getItems().filter((it) => {
      if (!q) return true;
      return (it.label + ' ' + (it.meta || '')).toLowerCase().includes(q);
    });
    menu.innerHTML = '';
    focusIdx = -1;
    if (!items.length) {
      menu.innerHTML = '<div class="combo-empty">Sin coincidencias</div>';
      return;
    }
    items.forEach((it) => {
      const div = document.createElement('div');
      div.className = 'combo-item' + (it.special ? ' combo-new' : '');
      div.innerHTML = `${escapeHTML(it.label)}${it.meta ? `<small>${escapeHTML(it.meta)}</small>` : ''}`;
      div.addEventListener('mousedown', (e) => {
        e.preventDefault();
        if (selectOnly) {
          root.dataset.selected = it.value;
          const lbl = it.label.length > 32 ? it.label.slice(0, 32) + '…' : it.label;
          trigger.textContent = lbl;
          if (onPick) onPick(it);
        } else if (onPick) {
          onPick(it);
        }
        close();
        search.value = '';
      });
      menu.appendChild(div);
    });
  }

  function open() {
    if (openComboRoot && openComboRoot !== root) openComboRoot.classList.remove('open');
    root.classList.add('open');
    openComboRoot = root;
    renderList();
    setTimeout(() => search.focus(), 0);
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    if (root.classList.contains('open')) close();
    else open();
  });
  search.addEventListener('input', renderList);
  search.addEventListener('keydown', (e) => {
    const opts = menu.querySelectorAll('.combo-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusIdx = Math.min(focusIdx + 1, opts.length - 1);
      opts.forEach((o, i) => o.classList.toggle('focused', i === focusIdx));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusIdx = Math.max(focusIdx - 1, 0);
      opts.forEach((o, i) => o.classList.toggle('focused', i === focusIdx));
    } else if (e.key === 'Enter' && focusIdx >= 0 && opts[focusIdx]) {
      e.preventDefault();
      opts[focusIdx].dispatchEvent(new MouseEvent('mousedown'));
    } else if (e.key === 'Escape') {
      close();
    }
  });

  if (!root.dataset.boundClose) {
    root.dataset.boundClose = '1';
    document.addEventListener('click', (e) => {
      if (!root.contains(e.target)) close();
    });
  }

  return {
    trigger,
    open,
    close,
    getValue: () => root.dataset.selected || '',
  };
}

function selectionGroupItems() {
  const cat = $('selCat')?.value || 'PERSONA';
  const list = clusters
    .filter((c) => c.cat === cat || c.cat === 'PERSONA' || cat === 'PERSONA')
    .map((c) => ({
      value: c.cluster_id,
      label: clusterOption(c).label,
      meta: clusterOption(c).meta,
    }));
  list.push({ value: '__new__', label: 'Crear grupo nuevo', special: true });
  return list;
}

function initSelectionGroupPicker() {
  const host = $('selGroupPicker');
  if (!host) return;
  selectionClusterId = '';
  mountGroupPicker(host, {
    triggerLabel: 'Elegir grupo…',
    selectOnly: true,
    getItems: selectionGroupItems,
    onPick: (it) => {
      selectionClusterId = it.value;
    },
  });
}

function clustersForDetection(det) {
  return clusters.filter((c) => c.cat === det.cat || c.cat === 'PERSONA');
}

function isPlaceholderLike(s) {
  return typeof s === 'string' && /^\[[A-Z_]+(?:_\d+)?\]$/.test(s.trim());
}

function bestClusterSurface(c) {
  const surfaces = Array.isArray(c?.surfaces) ? c.surfaces.filter(Boolean) : [];
  if (!surfaces.length) return '';
  return [...surfaces].sort((a, b) => (b || '').length - (a || '').length)[0] || '';
}

function clusterDisplayLabel(c) {
  const canonical =
    c?.canonical_label && !isPlaceholderLike(c.canonical_label) ? c.canonical_label : '';
  const surface = bestClusterSurface(c);
  const main = canonical || surface || '';
  if (main) return main;
  return c?.placeholder || c?.cluster_id || 'Grupo';
}

function clusterOption(c) {
  const label = clusterDisplayLabel(c);
  const ph = c?.placeholder && isPlaceholderLike(c.placeholder) ? c.placeholder : c?.placeholder || '';
  const status = c?.status === 'confirmed' ? 'confirmado' : 'sugerido';
  const count = Array.isArray(c?.surfaces) ? c.surfaces.length : 0;
  const metaParts = [];
  if (c?.cat) metaParts.push(c.cat);
  if (ph) metaParts.push(ph);
  metaParts.push(status);
  if (count) metaParts.push(`${count} menciones`);
  return { value: c.cluster_id, label, meta: metaParts.join(' · ') };
}

function escapeHTML(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function getEnabledCategories() {
  return [...document.querySelectorAll('#catChecks input[data-cat]:checked')].map(
    (c) => c.dataset.cat
  );
}

function getLabelMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

// Upload
const uploadZone = $('uploadZone');
const fileInput = $('fileInput');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) handleFile(e.target.files[0]);
});

async function handleFile(file) {
  const form = new FormData();
  form.append('file', file);
  $('fileInfo').classList.add('show');
  $('fileInfo').innerHTML = 'Extrayendo texto…';
  const signal = beginRequest();
  setProcessBusy(true);
  try {
    const res = await fetch(API + '/api/upload', { method: 'POST', body: form, signal });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error al cargar');
    }
    const data = await res.json();
    sessionId = data.session_id;
    currentDocName = file.name || 'documento';
    $('fileInfo').innerHTML =
      `<strong>${escapeHTML(file.name)}</strong> · ${data.char_count.toLocaleString('es')} caracteres · ${data.paragraph_count} párrafos`;
    $('analyzeBtn').disabled = false;
    setActiveStep(2);
    showToast('Documento cargado', 'success');
  } catch (e) {
    if (e.name === 'AbortError') return;
    $('fileInfo').innerHTML = 'Error: ' + escapeHTML(e.message);
    showToast(e.message, 'error');
  } finally {
    endRequest();
    setProcessBusy(false);
  }
}

// Radio mode UI
document.querySelectorAll('input[name="mode"]').forEach((r) => {
  r.addEventListener('change', () => {
    document.querySelectorAll('.radio-option').forEach((o) => o.classList.remove('selected'));
    r.closest('.radio-option').classList.add('selected');
  });
});

// Analyze
$('analyzeBtn').addEventListener('click', async () => {
  if (!sessionId) return;
  const signal = beginRequest();
  setProcessBusy(true);
  try {
    const res = await fetch(API + '/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify({
        session_id: sessionId,
        label_mode: getLabelMode(),
        enabled_categories: getEnabledCategories(),
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en análisis');
    }
    const data = await res.json();
    detections = data.detections;
    clusters = data.clusters;
    renderStats(data.stats);
    renderTable();
    renderClusters();
    await loadPreview();
    $('statsRow').hidden = false;
    $('workspace').hidden = false;
    $('exportPanel').hidden = false;
    setActiveStep(3);
    const suggested = clusters.filter((c) => c.status === 'suggested');
    if (suggested.length > 0 && !sessionStorage.getItem('anon_clusters_tab_seen')) {
      switchReviewTab('clusters');
      sessionStorage.setItem('anon_clusters_tab_seen', '1');
    }
    showToast(`Análisis: ${detections.length} detecciones, ${clusters.length} grupos sugeridos`, 'success');
  } catch (e) {
    if (e.name === 'AbortError') return;
    showToast(e.message, 'error');
  } finally {
    endRequest();
    setProcessBusy(false);
  }
});

$('cancelProcessBtn')?.addEventListener('click', cancelActiveProcess);

const CAT_COLORS = {
  PERSONA: '#9f3343',
  DNI: '#8a4a19',
  CUIT: '#8a4a19',
  EMPRESA: '#4a1e78',
  EMAIL: '#256c5b',
  TELEFONO: '#24647a',
  DOMICILIO: '#7a476d',
  PATENTE: '#5a3d6e',
  EXPEDIENTE: '#0b2545',
  ORGANISMO: '#4a1e78',
  OTRO: '#445a84',
};

const CATEGORIES = [
  'PERSONA',
  'DNI',
  'CUIT',
  'EMPRESA',
  'EMAIL',
  'TELEFONO',
  'DOMICILIO',
  'PATENTE',
  'EXPEDIENTE',
  'ORGANISMO',
  'OTRO',
];

const saveTimers = new Map();

function normalizeForMatch(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/^(original|duplicado|triplicado|cuadruplicado|copia|anexo)\s+/i, '')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function tokensForMatch(value) {
  return normalizeForMatch(value)
    .split(' ')
    .filter((t) => t.length > 2 && !['de', 'del', 'la', 'las', 'los', 'y'].includes(t));
}

function looksSimilarDetection(a, b) {
  if (!a || !b || a.id === b.id || a.cat !== b.cat) return false;
  const na = normalizeForMatch(a.original);
  const nb = normalizeForMatch(b.original);
  if (!na || !nb) return false;
  if (na === nb || na.includes(nb) || nb.includes(na)) return true;
  if (a.cat !== 'PERSONA') {
    const da = na.replace(/\D/g, '');
    const db = nb.replace(/\D/g, '');
    return da && da === db;
  }
  const ta = tokensForMatch(a.original);
  const tb = tokensForMatch(b.original);
  const shared = ta.filter((t) => tb.includes(t));
  return shared.length >= 2 || (shared.length === 1 && Math.min(ta.length, tb.length) <= 2);
}

function categoryOptions(selected) {
  return CATEGORIES.map(
    (cat) => `<option value="${cat}" ${cat === selected ? 'selected' : ''}>${cat}</option>`
  ).join('');
}

async function saveDetectionPatch(detId, patch, { refresh = false, quiet = true } = {}) {
  if (!requireSession()) return false;
  try {
    const res = await fetch(API + `/api/detections/${detId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, ...patch }),
    });
    if (!res.ok) throw new Error(await parseApiError(res));
    const data = await res.json();
    detections = data.detections;
    clusters = data.clusters;
    renderStatsFromDetections();
    if (refresh) {
      renderTable();
      renderClusters();
      await loadPreview();
    }
    if (!quiet) showToast('Cambio guardado', 'success');
    return true;
  } catch (e) {
    showToast(e.message, 'error');
    return false;
  }
}

function scheduleDetectionPatch(detId, patch) {
  clearTimeout(saveTimers.get(detId));
  saveTimers.set(
    detId,
    setTimeout(() => {
      saveDetectionPatch(detId, patch);
      saveTimers.delete(detId);
    }, 450)
  );
}

async function flushPendingSaves() {
  if (!saveTimers.size) return;
  await new Promise((resolve) => setTimeout(resolve, 520));
}

function renderStats(stats) {
  const row = $('statsRow');
  row.innerHTML = '';
  for (const [cat, n] of Object.entries(stats)) {
    if (cat === 'TOTAL') continue;
    const color = CAT_COLORS[cat] || '#4b5563';
    row.innerHTML += `
      <div class="stat-card" style="--cat-color:${color}">
        <div class="stat-num">${n}</div>
        <div class="stat-label">${cat}</div>
      </div>`;
  }
  row.innerHTML += `
    <div class="stat-card" style="--cat-color:#4b5563">
      <div class="stat-num">${stats.TOTAL || detections.length}</div>
      <div class="stat-label">Total</div>
    </div>`;
}

function applyLocalClusterAssign(detId, clusterValue) {
  const d = detections.find((x) => x.id === detId);
  if (!d) return false;

  if (clusterValue === '__new__') {
    const newId = `local_${Date.now()}`;
    clusters.push({
      cluster_id: newId,
      cat: d.cat,
      canonical_label: null,
      placeholder: d.placeholder,
      surfaces: [d.original],
      mention_ids: [],
      confidence: 'media',
      status: 'suggested',
      reasons: ['manual'],
    });
    d.cluster_id = newId;
    return true;
  }

  const c = clusters.find((x) => x.cluster_id === clusterValue);
  if (!c) return false;
  if (!c.surfaces.includes(d.original)) c.surfaces.push(d.original);
  d.cluster_id = clusterValue;
  if (c.placeholder) d.placeholder = c.placeholder;
  return true;
}

async function assignDetectionToCluster(detId, clusterValue) {
  if (!clusterValue || !requireSession()) return;
  try {
    const res = await fetch(API + '/api/assign-cluster', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        detection_id: detId,
        cluster_id: clusterValue,
      }),
    });
    if (!res.ok) {
      if (applyLocalClusterAssign(detId, clusterValue)) {
        renderClusters();
        renderTable();
        renderPreviewLocal();
        showToast('Asignado localmente (reiniciá el servidor para guardar en sesión)', 'success');
        return;
      }
      throw new Error(await parseApiError(res));
    }
    const data = await res.json();
    clusters = data.clusters;
    detections = data.detections;
    renderClusters();
    renderTable();
    await loadPreview();
    clearTextSelection();
    showToast('Agregado al grupo', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderTable() {
  const tbody = $('detBody');
  updateReviewTabBadges();
  if (!detections.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="empty-state">Sin detecciones</td></tr>';
    return;
  }
  tbody.innerHTML = detections
    .map((d) => {
      const inCluster = d.cluster_id
        ? clusters.find((c) => c.cluster_id === d.cluster_id)
        : null;
      const clusterHint = inCluster
        ? `<span class="cluster-in-badge">● ${escapeHTML(clusterDisplayLabel(inCluster))}</span>`
        : '';
      return `
    <tr data-id="${d.id}" class="${d.enabled ? '' : 'row-disabled'}">
      <td><input type="checkbox" ${d.enabled ? 'checked' : ''} class="toggle-det" aria-label="Incluir"></td>
      <td>
        <select class="cat-select pill-${d.cat}" aria-label="Tipo de dato">
          ${categoryOptions(d.cat)}
        </select>
      </td>
      <td>
        ${escapeHTML(d.original)}<br>
        <small>${d.positions.length}×</small>${clusterHint}
        <div class="row-tools">
          <button type="button" class="link-action join-similar">Unir similares</button>
          <button type="button" class="link-action ignore-similar">Ignorar similares</button>
        </div>
      </td>
      <td><input class="placeholder-input" value="${escapeHTML(d.placeholder)}"></td>
      <td><div class="combo-host" data-det-id="${d.id}"></div></td>
      <td><button class="delete-btn" title="Eliminar" type="button">✕</button></td>
    </tr>`;
    })
    .join('');

  tbody.querySelectorAll('tr').forEach((tr) => {
    const id = parseInt(tr.dataset.id, 10);
    const d = detections.find((x) => x.id === id);
    tr.querySelector('.toggle-det').addEventListener('change', (e) => {
      d.enabled = e.target.checked;
      renderPreviewLocal();
      scheduleDetectionPatch(id, { enabled: d.enabled });
      renderStatsFromDetections();
    });
    tr.querySelector('.placeholder-input').addEventListener('input', (e) => {
      d.placeholder = e.target.value;
      d.manual_placeholder = true;
      renderPreviewLocal();
      scheduleDetectionPatch(id, { placeholder: d.placeholder });
    });
    tr.querySelector('.cat-select').addEventListener('change', async (e) => {
      d.cat = e.target.value;
      d.cluster_id = null;
      const ok = await saveDetectionPatch(id, { cat: d.cat }, { refresh: true, quiet: false });
      if (!ok) renderTable();
    });
    tr.querySelector('.join-similar').addEventListener('click', async () => {
      await joinSimilarDetections(id);
    });
    tr.querySelector('.ignore-similar').addEventListener('click', async () => {
      await ignoreSimilarDetections(id);
    });
    const comboHost = tr.querySelector('.combo-host');
    if (comboHost) {
      mountGroupPicker(comboHost, {
        triggerLabel: 'Asignar a grupo…',
        getItems: () => {
          const list = clustersForDetection(d).map((c) => clusterOption(c));
          list.push({ value: '__new__', label: 'Crear grupo nuevo', special: true });
          return list;
        },
        onPick: async (it) => {
          await assignDetectionToCluster(id, it.value);
        },
      });
    }
    tr.querySelector('.delete-btn').addEventListener('click', async () => {
      if (sessionId) {
        try {
          const res = await fetch(
            API + `/api/detections/${id}?session_id=${sessionId}`,
            { method: 'DELETE' }
          );
          if (res.ok) {
            const data = await res.json();
            detections = data.detections;
            clusters = data.clusters;
          } else {
            detections = detections.filter((x) => x.id !== id);
          }
        } catch {
          detections = detections.filter((x) => x.id !== id);
        }
      } else {
        detections = detections.filter((x) => x.id !== id);
      }
      renderTable();
      renderClusters();
      renderPreviewLocal();
    });
  });
}

async function ensureDetectionCluster(detId) {
  const det = detections.find((d) => d.id === detId);
  if (!det) return '';
  if (det.cluster_id) return det.cluster_id;
  await assignDetectionToCluster(detId, '__new__');
  const updated = detections.find((d) => d.id === detId);
  return updated?.cluster_id || '';
}

async function confirmClusterById(clusterId) {
  const res = await fetch(
    API + `/api/clusters/${encodeURIComponent(clusterId)}/confirm?session_id=${encodeURIComponent(sessionId)}`,
    { method: 'POST' }
  );
  if (!res.ok) throw new Error(await parseApiError(res));
  const data = await res.json();
  const idx = clusters.findIndex((c) => c.cluster_id === clusterId);
  if (idx >= 0) clusters[idx] = data.cluster;
  detections = data.detections;
}

async function joinSimilarDetections(detId) {
  if (!requireSession()) return;
  const det = detections.find((d) => d.id === detId);
  if (!det) return;
  const similar = detections.filter((other) => looksSimilarDetection(det, other));
  if (!similar.length) {
    showToast('No encontré filas similares para unir', 'error');
    return;
  }
  const targetCluster = await ensureDetectionCluster(detId);
  if (!targetCluster) return;
  try {
    for (const item of similar) {
      await assignDetectionToCluster(item.id, targetCluster);
    }
    await confirmClusterById(targetCluster);
  } catch (e) {
    showToast(e.message, 'error');
    return;
  }
  renderClusters();
  renderTable();
  await loadPreview();
  showToast(`Unidas ${similar.length + 1} variantes en un grupo`, 'success');
}

async function ignoreSimilarDetections(detId) {
  if (!requireSession()) return;
  const det = detections.find((d) => d.id === detId);
  if (!det) return;
  const targets = [det, ...detections.filter((other) => looksSimilarDetection(det, other))];
  for (const item of targets) {
    item.enabled = false;
    await saveDetectionPatch(item.id, { enabled: false });
  }
  renderTable();
  renderStatsFromDetections();
  renderPreviewLocal();
  showToast(`Ignoradas ${targets.length} filas similares`, 'success');
}

let clusterFilterQuery = '';

function applyClusterFilter() {
  const q = clusterFilterQuery.trim().toLowerCase();
  document.querySelectorAll('.cluster-card').forEach((card) => {
    const text = (card.dataset.search || '').toLowerCase();
    card.classList.toggle('hidden-by-filter', !!q && !text.includes(q));
  });
}

if ($('clusterFilter')) {
  $('clusterFilter').addEventListener('input', (e) => {
    clusterFilterQuery = e.target.value;
    applyClusterFilter();
  });
}

function renderClusters() {
  const el = $('clustersList');
  updateReviewTabBadges();
  const suggested = clusters.filter((c) => c.status === 'suggested');
  const confirmed = clusters.filter((c) => c.status === 'confirmed');

  if (!clusters.length) {
    el.innerHTML =
      '<div class="empty-state">No hay grupos sugeridos. Las menciones únicas aparecen solo en Detecciones.</div>';
    return;
  }

  let html = '';
  if (confirmed.length) {
    html += '<p class="section-label">Confirmados</p>';
    html += confirmed.map(clusterCard).join('');
  }
  if (suggested.length) {
    html += '<p class="section-label" style="margin-top:12px">Posibles entidades equivalentes</p>';
    html += suggested.map(clusterCard).join('');
  }
  el.innerHTML = html;
  applyClusterFilter();

  el.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => handleClusterAction(btn));
  });

  el.querySelectorAll('.combo-host-add').forEach((host) => {
    const cid = host.dataset.clusterId;
    const c = clusters.find((x) => x.cluster_id === cid);
    if (!c) return;
    mountGroupPicker(host, {
      triggerLabel: 'Sumar variante al grupo…',
      getItems: () =>
        detectionsNotInCluster(c).map((d) => ({
          value: String(d.id),
          label: d.original,
          meta: d.cat,
        })),
      onPick: async (it) => {
        await assignDetectionToCluster(parseInt(it.value, 10), cid);
      },
    });
  });

  el.querySelectorAll('.combo-host-merge').forEach((host) => {
    const sourceId = host.dataset.sourceId;
    const source = clusters.find((x) => x.cluster_id === sourceId);
    if (!source) return;
    mountGroupPicker(host, {
      triggerLabel: 'Unir con otro grupo…',
      getItems: () =>
        clusters
          .filter(
            (t) =>
              t.cluster_id !== sourceId &&
              (t.cat === source.cat || t.cat === 'PERSONA' || source.cat === 'PERSONA')
          )
          .map((t) => clusterOption(t)),
      onPick: async (it) => {
        await absorbClusterInto(it.value, sourceId);
      },
    });
  });
}

async function absorbClusterInto(targetId, sourceId) {
  if (!requireSession() || targetId === sourceId) return;
  try {
    const res = await fetch(
      API +
        `/api/clusters/${encodeURIComponent(targetId)}/absorb?session_id=${encodeURIComponent(sessionId)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_cluster_id: sourceId }),
      }
    );
    if (!res.ok) throw new Error(await parseApiError(res));
    const data = await res.json();
    clusters = data.clusters;
    detections = data.detections;
    renderClusters();
    renderTable();
    await loadPreview();
    showToast('Grupos unidos', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function detectionsNotInCluster(c) {
  const inCluster = new Set(c.surfaces.map((s) => s.trim().toLowerCase()));
  return detections.filter(
    (d) =>
      (d.cat === c.cat || c.cat === 'PERSONA') &&
      !inCluster.has(d.original.trim().toLowerCase()) &&
      !d.cluster_id
  );
}

function clusterCard(c) {
  const label = c.canonical_label || c.placeholder || `${c.cat} (pendiente)`;
  const statusClass = c.status === 'confirmed' ? 'confirmed' : '';
  const available = detectionsNotInCluster(c);
  const searchBlob = [label, c.placeholder, c.cat, ...c.surfaces].join(' ');
  return `
    <div class="cluster-card ${statusClass}" data-cluster-id="${c.cluster_id}" data-search="${escapeHTML(searchBlob)}">
      <h4>${escapeHTML(label)} <span class="conf-badge conf-${c.confidence}">${c.confidence}</span></h4>
      <div class="cluster-mentions">
        ${c.surfaces
          .map(
            (s) => `<div class="cluster-mention-row">
            <span class="cluster-mention-text">${escapeHTML(s)}</span>${
              c.surfaces.length > 1
                ? `<button type="button" class="cluster-mention-remove" data-action="remove-surface" data-id="${c.cluster_id}" data-surface="${escapeHTML(s)}" title="Quitar esta variante del grupo">✕</button>`
                : ''
            }
          </div>`
          )
          .join('')}
      </div>
      ${
        available.length
          ? `<div class="cluster-add-row">
        <div class="combo-host-add" data-cluster-id="${c.cluster_id}"></div>
      </div>`
          : ''
      }
      <div class="cluster-merge-row">
        <div class="combo-host-merge" data-source-id="${c.cluster_id}"></div>
      </div>
      <div class="cluster-actions">
        ${
          c.status !== 'confirmed'
            ? `<button class="btn btn-sm btn-success" data-action="confirm" data-id="${c.cluster_id}">Confirmar grupo</button>`
            : ''
        }
        <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${c.cluster_id}">Editar reemplazo</button>
        <button class="btn btn-sm btn-reject" data-action="reject" data-id="${c.cluster_id}">Rechazar</button>
      </div>
    </div>`;
}

async function handleClusterAction(btn) {
  const action = btn.dataset.action;
  const clusterId = btn.dataset.id;
  if (action === 'confirm') {
    try {
      const res = await fetch(
        API + `/api/clusters/${clusterId}/confirm?session_id=${sessionId}`,
        { method: 'POST' }
      );
      if (!res.ok) throw new Error((await res.json()).detail);
      const data = await res.json();
      const idx = clusters.findIndex((c) => c.cluster_id === clusterId);
      if (idx >= 0) clusters[idx] = data.cluster;
      detections = data.detections;
      renderClusters();
      renderTable();
      await loadPreview();
      showToast('Grupo confirmado', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  } else if (action === 'reject') {
    clusters = clusters.filter((c) => c.cluster_id !== clusterId);
    detections.forEach((d) => {
      if (d.cluster_id === clusterId) d.cluster_id = null;
    });
    renderClusters();
    renderTable();
    showToast('Grupo rechazado', 'success');
  } else if (action === 'edit') {
    const c = clusters.find((x) => x.cluster_id === clusterId);
    const val = prompt('Nuevo placeholder:', c?.placeholder || '');
    if (!val) return;
    try {
      const res = await fetch(
        API + `/api/clusters/${clusterId}?session_id=${sessionId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ placeholder: val }),
        }
      );
      if (!res.ok) throw new Error((await res.json()).detail);
      const data = await res.json();
      const idx = clusters.findIndex((c) => c.cluster_id === clusterId);
      if (idx >= 0) clusters[idx] = data.cluster;
      renderClusters();
      renderTable();
      await loadPreview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  } else if (action === 'remove-surface') {
    const surface = btn.dataset.surface;
    if (!surface || !requireSession()) return;
    try {
      const res = await fetch(
        API + `/api/clusters/${encodeURIComponent(clusterId)}/remove-surface?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ surface }),
        }
      );
      if (!res.ok) throw new Error(await parseApiError(res));
      const data = await res.json();
      clusters = data.clusters;
      detections = data.detections;
      renderClusters();
      renderTable();
      await loadPreview();
      showToast('Variante separada en su propio grupo', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  }
}

let lastPreviewHighlights = [];

async function loadPreview() {
  const res = await fetch(
    API + `/api/preview?session_id=${sessionId}&mode=${viewMode === 'anon' ? 'anon' : 'orig'}`
  );
  if (!res.ok) return;
  const data = await res.json();
  docText = data.text;
  if (viewMode === 'orig') {
    lastPreviewHighlights = Array.isArray(data.highlights) ? data.highlights : [];
    renderHighlighted(data.text, lastPreviewHighlights);
    if (window.searchTool) window.searchTool.refresh();
  } else {
    $('docPreview').textContent = data.text;
  }
}

function renderHighlighted(text, highlights, searchMatches, currentSearchIdx) {
  const detHls = Array.isArray(highlights) ? [...highlights] : [];
  detHls.sort((a, b) => a.start - b.start);
  // Dedup solapamientos entre detecciones (mantiene el primero que aparece).
  const cleanDet = [];
  let lastEnd = -1;
  for (const h of detHls) {
    if (h.start < lastEnd) continue;
    cleanDet.push(h);
    lastEnd = h.end;
  }
  const matches = Array.isArray(searchMatches) ? searchMatches : [];

  let html = '';
  let cursor = 0;
  for (const h of cleanDet) {
    if (cursor < h.start) {
      html += renderRangeWithSearch(text, cursor, h.start, matches, currentSearchIdx);
    }
    html +=
      `<span class="hl hl-${h.cat}" title="${escapeHTML(h.placeholder)}">` +
      renderRangeWithSearch(text, h.start, h.end, matches, currentSearchIdx) +
      `</span>`;
    cursor = h.end;
  }
  if (cursor < text.length) {
    html += renderRangeWithSearch(text, cursor, text.length, matches, currentSearchIdx);
  }
  $('docPreview').innerHTML = html;
}

// Renderiza [start, end) del texto sumando <mark> por cada coincidencia del buscador
// que caiga dentro; recorta coincidencias que se solapan parcialmente con el rango.
function renderRangeWithSearch(text, start, end, matches, currentSearchIdx) {
  if (!matches || !matches.length) {
    return escapeHTML(text.substring(start, end));
  }
  let out = '';
  let cur = start;
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    if (m.end <= start) continue;
    if (m.start >= end) break;
    const mStart = Math.max(m.start, start);
    const mEnd = Math.min(m.end, end);
    if (mStart > cur) {
      out += escapeHTML(text.substring(cur, mStart));
    }
    const cls =
      i === currentSearchIdx ? 'search-match search-match-current' : 'search-match';
    const idAttr = i === currentSearchIdx ? ' id="searchMatchCurrent"' : '';
    out += `<mark class="${cls}"${idAttr}>${escapeHTML(text.substring(mStart, mEnd))}</mark>`;
    cur = mEnd;
  }
  if (cur < end) {
    out += escapeHTML(text.substring(cur, end));
  }
  return out;
}

function renderPreviewLocal() {
  if (viewMode === 'anon') {
    const replacements = [];
    detections
      .filter((d) => d.enabled)
      .forEach((d) => {
        d.positions.forEach((p) => {
          replacements.push({ start: p.start, end: p.end, value: d.placeholder });
        });
      });
    replacements.sort((a, b) => b.start - a.start);
    let out = docText;
    replacements.forEach((r) => {
      out = out.substring(0, r.start) + r.value + out.substring(r.end);
    });
    $('docPreview').textContent = out;
  } else {
    loadPreview();
  }
}

$('viewOrig').addEventListener('click', () => {
  viewMode = 'orig';
  $('viewOrig').classList.add('active');
  $('viewAnon').classList.remove('active');
  loadPreview();
});
$('viewAnon').addEventListener('click', () => {
  viewMode = 'anon';
  $('viewAnon').classList.add('active');
  $('viewOrig').classList.remove('active');
  renderPreviewLocal();
});

// Export
function getExportFormat() {
  return {
    font_name: $('fmtFont')?.value || 'Times New Roman',
    font_size_pt: parseInt($('fmtSize')?.value || '12', 10),
    line_spacing: parseFloat($('fmtLine')?.value || '1.5'),
    margin_cm: parseFloat($('fmtMargin')?.value || '3'),
    margin_top_bottom_cm: 2.5,
    alignment: $('fmtAlign')?.value || 'justify',
  };
}

function applyEditorPreviewStyle() {
  const ta = $('editorText');
  if (!ta) return;
  const fmt = getExportFormat();
  ta.style.fontFamily = fmt.font_name === 'Times New Roman' ? '"Times New Roman", Times, serif' : fmt.font_name;
  ta.style.fontSize = `${fmt.font_size_pt}pt`;
  ta.style.lineHeight = String(fmt.line_spacing);
  ta.style.textAlign = fmt.alignment === 'justify' ? 'justify' : fmt.alignment;
}

async function downloadExport(url, filename, payloadExtra = {}) {
  if (!requireSession()) throw new Error('Sesión perdida: cargá el documento de nuevo.');
  await flushPendingSaves();
  const body = {
    session_id: sessionId,
    use_confirmed_only: false,
    ...payloadExtra,
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseApiError(res));
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function openEditorPanel() {
  $('loaderPreview').classList.add('show');
  $('openEditorBtn').disabled = true;
  try {
    const res = await fetch(API + '/api/export/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, use_confirmed_only: false }),
    });
    if (!res.ok) throw new Error(await parseApiError(res));
    const data = await res.json();
    $('editorText').value = data.text || '';
    applyEditorPreviewStyle();
    $('exportPanel').hidden = true;
    $('editorPanel').hidden = false;
    setActiveStep(4);
    $('editorText').focus();
    showToast('Revisá el texto antes de exportar', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    $('loaderPreview').classList.remove('show');
    $('openEditorBtn').disabled = false;
  }
}

function closeEditorPanel() {
  $('editorPanel').hidden = true;
  $('exportPanel').hidden = false;
  setActiveStep(3);
}

['fmtFont', 'fmtSize', 'fmtLine', 'fmtAlign', 'fmtMargin'].forEach((id) => {
  const el = $(id);
  if (el) el.addEventListener('change', applyEditorPreviewStyle);
});

$('openEditorBtn')?.addEventListener('click', openEditorPanel);
$('closeEditorBtn')?.addEventListener('click', closeEditorPanel);

$('exportDocx')?.addEventListener('click', async () => {
  $('loader2').classList.add('show');
  try {
    const text = $('editorText').value;
    const format = getExportFormat();
    await downloadExport(API + '/api/export/docx', 'documento_anonimizado.docx', { text, format });
    showToast('Word descargado', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    $('loader2').classList.remove('show');
  }
});

$('exportPdf')?.addEventListener('click', async () => {
  $('loaderPdf').classList.add('show');
  try {
    const text = $('editorText').value;
    const format = getExportFormat();
    await downloadExport(API + '/api/export/pdf', 'documento_anonimizado.pdf', { text, format });
    showToast('PDF descargado', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    $('loaderPdf').classList.remove('show');
  }
});

function buildMarkdownExport() {
  const text = $('editorText')?.value || '';
  const title = (currentDocName || 'documento').replace(/\.[^.]+$/, '').trim() || 'documento';
  return `# ${title}\n\n${text}\n`;
}

async function copyTextFallback(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.top = '-1000px';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  ta.setSelectionRange(0, ta.value.length);
  let ok = false;
  try {
    ok = document.execCommand('copy');
  } catch {
    ok = false;
  }
  document.body.removeChild(ta);
  return ok;
}

$('copyMdBtn')?.addEventListener('click', async () => {
  const md = buildMarkdownExport();
  if (!md.trim()) {
    showToast('No hay texto para copiar', 'error');
    return;
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(md);
      showToast('Markdown copiado al portapapeles', 'success');
      return;
    }
  } catch {
    /* cae al fallback */
  }
  const ok = await copyTextFallback(md);
  if (ok) showToast('Markdown copiado al portapapeles', 'success');
  else showToast('No se pudo copiar: seleccioná el texto manualmente', 'error');
});

$('exportCsv').addEventListener('click', async () => {
  try {
    await downloadExport(API + '/api/export/csv', 'equivalencias.csv');
    showToast('CSV descargado', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
});

// ——— Redimensionar paneles ———
function initSplitPane() {
  const pane = $('splitPane');
  const divider = $('splitDivider');
  const left = $('splitLeft');
  if (!pane || !divider || !left) return;

  const saved = localStorage.getItem('anon_split_pct');
  if (saved) left.style.setProperty('--split-left', saved);

  let dragging = false;

  function onMove(clientX) {
    const rect = pane.getBoundingClientRect();
    const pct = Math.min(78, Math.max(22, ((clientX - rect.left) / rect.width) * 100));
    const val = `${pct}%`;
    left.style.setProperty('--split-left', val);
    localStorage.setItem('anon_split_pct', val);
  }

  divider.addEventListener('mousedown', (e) => {
    dragging = true;
    divider.classList.add('dragging');
    e.preventDefault();
  });
  window.addEventListener('mousemove', (e) => {
    if (dragging) onMove(e.clientX);
  });
  window.addEventListener('mouseup', () => {
    dragging = false;
    divider.classList.remove('dragging');
  });
  divider.addEventListener('keydown', (e) => {
    const cur = parseFloat(left.style.getPropertyValue('--split-left')) || 46;
    if (e.key === 'ArrowLeft') onMove(pane.getBoundingClientRect().left + (pane.offsetWidth * (cur - 2)) / 100);
    if (e.key === 'ArrowRight') onMove(pane.getBoundingClientRect().left + (pane.offsetWidth * (cur + 2)) / 100);
  });
}

initSplitPane();
initReviewTabs();

// ——— Seleccionar texto y anonimizar (v1) ———
let pendingSelection = null;

function getSelectionInPreview() {
  const container = $('docPreview');
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount || !container) return null;
  const range = sel.getRangeAt(0);
  if (!container.contains(range.commonAncestorContainer)) return null;

  const pre = document.createRange();
  pre.selectNodeContents(container);
  pre.setEnd(range.startContainer, range.startOffset);
  const start = pre.toString().length;
  pre.setEnd(range.endContainer, range.endOffset);
  const end = pre.toString().length;
  const text = sel.toString().replace(/\s+/g, ' ').trim();
  if (text.length < 2) return null;

  let useStart = start;
  let useEnd = end;
  let useText = docText.slice(useStart, useEnd).trim();
  if (!useText || useText.length < 2) {
    useText = text;
    const idx = docText.toLowerCase().indexOf(useText.toLowerCase(), Math.max(0, start - 40));
    if (idx >= 0) {
      useStart = idx;
      useEnd = idx + useText.length;
    }
  } else if (useText !== text && text.length >= 2) {
    const idx = docText.toLowerCase().indexOf(text.toLowerCase(), Math.max(0, useStart - 40));
    if (idx >= 0) {
      useStart = idx;
      useEnd = idx + text.length;
      useText = docText.slice(useStart, useEnd).trim();
    }
  }
  if (useEnd <= useStart) useEnd = useStart + Math.max(useText.length, 2);
  return { start: useStart, end: useEnd, text: useText };
}

function showSelectionToolbar(sel) {
  pendingSelection = sel;
  const bar = $('selectionToolbar');
  const prev = $('selPreview');
  if (!bar || !prev) return;
  prev.textContent = sel.text.length > 48 ? sel.text.slice(0, 48) + '…' : sel.text;
  bar.hidden = false;
  initSelectionGroupPicker();
}

function hideSelectionToolbar() {
  pendingSelection = null;
  selectionClusterId = '';
  const bar = $('selectionToolbar');
  if (bar) bar.hidden = true;
}

function applyLocalManualDetection(cat, sel) {
  const text = sel.text.trim();
  if (!text) return null;
  const positions = [];
  const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(escaped, 'gi');
  let m;
  while ((m = re.exec(docText)) !== null) {
    positions.push({ start: m.index, end: m.index + m[0].length, raw: m[0] });
  }
  if (!positions.length) {
    positions.push({ start: sel.start, end: sel.end, raw: text });
  }
  const key = text.toLowerCase();
  let det = detections.find(
    (d) => d.cat === cat && d.original.trim().toLowerCase() === key
  );
  if (det) {
    const seen = new Set(det.positions.map((p) => `${p.start}-${p.end}`));
    positions.forEach((p) => {
      const k = `${p.start}-${p.end}`;
      if (!seen.has(k)) {
        det.positions.push(p);
        seen.add(k);
      }
    });
    return det;
  }
  const counters = {};
  detections.forEach((d) => {
    counters[d.cat] = (counters[d.cat] || 0) + 1;
  });
  counters[cat] = (counters[cat] || 0) + 1;
  const mode = getLabelMode();
  const ph =
    mode === 'gen'
      ? `[${cat === 'PERSONA' ? 'NOMBRE' : cat}]`
      : `[${cat}_${counters[cat]}]`;
  const newId = detections.length ? Math.max(...detections.map((d) => d.id)) + 1 : 0;
  det = {
    id: newId,
    cat,
    original: text,
    placeholder: ph,
    enabled: true,
    positions,
    cluster_id: null,
    user_added: true,
  };
  detections.push(det);
  return det;
}

function clearTextSelection() {
  hideSelectionToolbar();
  const sel = window.getSelection();
  if (sel) sel.removeAllRanges();
}

async function runManualDetectionAndMaybeGroup(assignToGroup) {
  if (!pendingSelection) {
    showToast('Seleccioná texto en la vista previa (modo Original)', 'error');
    return;
  }
  if (!requireSession()) return;
  const cat = $('selCat').value;
  if (pendingSelection.end <= pendingSelection.start) {
    showToast('Selección inválida', 'error');
    return;
  }
  if (pendingSelection.text.length < 2) {
    showToast('Seleccioná al menos 2 caracteres', 'error');
    return;
  }

  const groupId = assignToGroup ? selectionClusterId : '';
  if (assignToGroup && !groupId) {
    showToast('Elegí un grupo en el desplegable (o Crear grupo nuevo)', 'error');
    return;
  }

  const sel = { ...pendingSelection };

  try {
    let det = null;
    const res = await fetch(API + '/api/manual-detection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        cat,
        start: sel.start,
        end: sel.end,
        original: sel.text,
      }),
    });
    if (!res.ok) {
      det = applyLocalManualDetection(cat, sel);
      if (!det) throw new Error(await parseApiError(res));
      detections = [...detections];
    } else {
      const data = await res.json();
      detections = data.detections;
      det = data.detection;
    }

    if (groupId && det) {
      await assignDetectionToCluster(det.id, groupId);
      return;
    }

    clearTextSelection();
    renderTable();
    renderStatsFromDetections();
    await loadPreview();
    showToast(`Anonimizado: ${det.original}`, 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderStatsFromDetections() {
  const stats = { TOTAL: detections.length };
  detections.forEach((d) => {
    stats[d.cat] = (stats[d.cat] || 0) + 1;
  });
  renderStats(stats);
}

const docPreviewEl = $('docPreview');
if (docPreviewEl) {
  docPreviewEl.addEventListener('mouseup', () => {
    if (viewMode !== 'orig') return;
    setTimeout(() => {
      const sel = getSelectionInPreview();
      if (sel) showSelectionToolbar(sel);
      else hideSelectionToolbar();
    }, 10);
  });
}
if ($('selAnonOnlyBtn')) {
  $('selAnonOnlyBtn').addEventListener('click', () => runManualDetectionAndMaybeGroup(false));
}
if ($('selAnonGroupBtn')) {
  $('selAnonGroupBtn').addEventListener('click', () => runManualDetectionAndMaybeGroup(true));
}
if ($('selCat')) {
  $('selCat').addEventListener('change', () => {
    if (!pendingSelection) return;
    selectionClusterId = '';
    initSelectionGroupPicker();
  });
}
if ($('selCancelBtn')) {
  $('selCancelBtn').addEventListener('click', clearTextSelection);
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') clearTextSelection();
});

// ——— Buscador tipo Ctrl+F del preview ———
const searchTool = (() => {
  const barEl = () => $('searchBar');
  const inputEl = () => $('searchInput');
  const countEl = () => $('searchCount');
  const catEl = () => $('searchCat');
  const anonBtnEl = () => $('searchAnonBtn');
  const toggleBtnEl = () => $('openSearch');

  let matches = [];
  let currentIdx = -1;
  let debounceHandle = null;
  let isOpen = false;

  const CAT_KEY = 'anon.searchCat';

  function normalizeForSearch(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  // Mapea índices del texto normalizado (NFD sin marcas) a índices del texto original.
  // Devuelve arrays paralelos: normText, mapStart[i] = índice original del char normalizado i,
  // mapEnd[i] = índice original justo después del char normalizado i.
  function buildNormMap(text) {
    let normText = '';
    const mapStart = [];
    const mapEnd = [];
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      const normCh = ch.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
      for (let j = 0; j < normCh.length; j++) {
        mapStart.push(i);
        mapEnd.push(i + 1);
      }
      normText += normCh;
    }
    return { normText, mapStart, mapEnd };
  }

  function computeMatches() {
    const q = (inputEl()?.value || '').trim();
    if (!q || !docText || viewMode !== 'orig') {
      matches = [];
      currentIdx = -1;
      return;
    }
    const { normText, mapStart, mapEnd } = buildNormMap(docText);
    const normQ = normalizeForSearch(q);
    if (!normQ) {
      matches = [];
      currentIdx = -1;
      return;
    }
    const out = [];
    let from = 0;
    while (true) {
      const idx = normText.indexOf(normQ, from);
      if (idx === -1) break;
      const endIdx = idx + normQ.length - 1;
      if (endIdx >= mapStart.length) break;
      const startOrig = mapStart[idx];
      const endOrig = mapEnd[endIdx];
      if (endOrig > startOrig && (out.length === 0 || out[out.length - 1].start !== startOrig)) {
        out.push({ start: startOrig, end: endOrig });
      }
      from = idx + Math.max(1, normQ.length);
    }
    matches = out;
    if (matches.length === 0) {
      currentIdx = -1;
    } else if (currentIdx < 0 || currentIdx >= matches.length) {
      currentIdx = 0;
    }
  }

  function updateCount() {
    const el = countEl();
    if (!el) return;
    if (!matches.length) {
      el.textContent = inputEl()?.value ? '0 / 0' : '0 / 0';
    } else {
      el.textContent = `${currentIdx + 1} / ${matches.length}`;
    }
  }

  function updateAnonBtn() {
    const btn = anonBtnEl();
    if (!btn) return;
    btn.disabled = matches.length === 0 || viewMode !== 'orig';
  }

  function render() {
    if (viewMode !== 'orig') return;
    renderHighlighted(docText, lastPreviewHighlights, matches, currentIdx);
    scrollCurrentIntoView();
  }

  function scrollCurrentIntoView() {
    const el = document.getElementById('searchMatchCurrent');
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }

  function refresh() {
    computeMatches();
    updateCount();
    updateAnonBtn();
    if (isOpen) render();
  }

  function open() {
    if (viewMode !== 'orig') {
      $('viewOrig')?.click();
    }
    isOpen = true;
    const bar = barEl();
    if (bar) bar.hidden = false;
    toggleBtnEl()?.classList.add('active');
    setTimeout(() => {
      const input = inputEl();
      if (input) {
        input.focus();
        input.select();
      }
    }, 20);
    refresh();
  }

  function close() {
    isOpen = false;
    const bar = barEl();
    if (bar) bar.hidden = true;
    toggleBtnEl()?.classList.remove('active');
    matches = [];
    currentIdx = -1;
    updateCount();
    updateAnonBtn();
    if (viewMode === 'orig') {
      renderHighlighted(docText, lastPreviewHighlights, [], -1);
    }
  }

  function toggle() {
    if (isOpen) close();
    else open();
  }

  function next() {
    if (!matches.length) return;
    currentIdx = (currentIdx + 1) % matches.length;
    updateCount();
    render();
  }

  function prev() {
    if (!matches.length) return;
    currentIdx = (currentIdx - 1 + matches.length) % matches.length;
    updateCount();
    render();
  }

  function scheduleRefresh() {
    if (debounceHandle) clearTimeout(debounceHandle);
    debounceHandle = setTimeout(() => {
      currentIdx = 0;
      refresh();
    }, 120);
  }

  async function anonymizeAll() {
    if (!requireSession()) return;
    if (!matches.length) {
      showToast('No hay coincidencias para anonimizar', 'error');
      return;
    }
    const q = (inputEl()?.value || '').trim();
    if (!q || q.length < 2) {
      showToast('Ingresá al menos 2 caracteres', 'error');
      return;
    }
    const cat = catEl()?.value || 'PERSONA';
    try {
      localStorage.setItem(CAT_KEY, cat);
    } catch (_) {}
    const positions = matches.map((m) => ({
      start: m.start,
      end: m.end,
      raw: docText.substring(m.start, m.end),
    }));
    const btn = anonBtnEl();
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(API + '/api/search-and-anonymize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          cat,
          original: q,
          positions,
        }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      const data = await res.json();
      detections = data.detections;
      renderTable();
      renderStatsFromDetections();
      await loadPreview();
      showToast(`Anonimizadas ${positions.length} coincidencias de "${q}"`, 'success');
      const input = inputEl();
      if (input) {
        input.value = '';
        input.focus();
      }
      matches = [];
      currentIdx = -1;
      updateCount();
      updateAnonBtn();
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      updateAnonBtn();
    }
  }

  function init() {
    const input = inputEl();
    if (input) {
      input.addEventListener('input', scheduleRefresh);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          if (e.shiftKey) prev();
          else next();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          close();
        }
      });
    }
    $('searchNext')?.addEventListener('click', next);
    $('searchPrev')?.addEventListener('click', prev);
    $('searchClose')?.addEventListener('click', close);
    $('openSearch')?.addEventListener('click', toggle);
    $('searchAnonBtn')?.addEventListener('click', anonymizeAll);

    const cat = catEl();
    if (cat) {
      try {
        const saved = localStorage.getItem(CAT_KEY);
        if (saved) cat.value = saved;
      } catch (_) {}
      cat.addEventListener('change', () => {
        try {
          localStorage.setItem(CAT_KEY, cat.value);
        } catch (_) {}
      });
    }

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
        const preview = $('docPreview');
        if (preview && (preview.offsetParent !== null) && !$('workspace').hidden) {
          e.preventDefault();
          open();
        }
      }
    });
  }

  return { init, refresh, open, close, isOpen: () => isOpen };
})();

window.searchTool = searchTool;
searchTool.init();

// Cerrar el buscador cuando el usuario cambia a modo Anonimizado (no hay texto original).
$('viewAnon')?.addEventListener('click', () => {
  if (searchTool.isOpen()) searchTool.close();
});

$('resetAll').addEventListener('click', () => {
  if (!confirm('¿Descartar todo?')) return;
  sessionId = null;
  currentDocName = '';
  detections = [];
  clusters = [];
  fileInput.value = '';
  $('fileInfo').classList.remove('show');
  $('statsRow').hidden = true;
  $('workspace').hidden = true;
  $('exportPanel').hidden = true;
  $('editorPanel').hidden = true;
  $('analyzeBtn').disabled = true;
  setActiveStep(1);
  hideSelectionToolbar();
});
