/* Portal Notas demo — vanilla JS, no build step. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ── language ───────────────────────────────────────────────────────────── */
let LANG = 'en';
try { LANG = localStorage.getItem('lang') || ''; } catch (_) { /* storage blocked */ }
if (!LANG) LANG = (navigator.language || '').toLowerCase().startsWith('pt') ? 'pt' : 'en';
const t = (k) => (window.I18N[LANG] && window.I18N[LANG][k]) ?? window.I18N.en[k] ?? k;

function applyI18n() {
  document.documentElement.lang = LANG === 'pt' ? 'pt-BR' : 'en';
  $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$('[data-i18n-html]').forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
  $$('.lang-toggle button').forEach((b) => b.classList.toggle('on', b.dataset.lang === LANG));
  $('#runtime-note').textContent = t(Runtime.MODE === 'browser' ? 'runtime_browser' : 'runtime_server');
}
$$('.lang-toggle button').forEach((b) => b.addEventListener('click', () => {
  LANG = b.dataset.lang;
  try { localStorage.setItem('lang', LANG); } catch (_) { /* storage blocked */ }
  applyI18n();
  refresh();
  if (modal.open && openDetailId) openDetail(openDetailId);
}));

const STATUS_CLASS = {
  'Pending': 'b-pending', 'Missing invoice': 'b-missing', 'Awaiting Purchasing': 'b-purch', 'Ready for Fiscal': 'b-purch',
  'Awaiting Fiscal': 'b-fiscal', 'Ready to print': 'b-print', 'Completed': 'b-done', 'Deleted': 'b-deleted',
};
const statusLabel = (s) => (LANG === 'pt' ? window.STATUS_LABELS[s] || s : s);
const BOARD = ['Awaiting Purchasing', 'Ready for Fiscal', 'Awaiting Fiscal', 'Ready to print'];
const BOARD_HINT = { 'Awaiting Purchasing': 'hint_purch', 'Ready for Fiscal': 'hint_ready', 'Awaiting Fiscal': 'hint_fiscal', 'Ready to print': 'hint_print' };

/* ── transport ──────────────────────────────────────────────────────────── */
async function api(method, url, body, isForm = false) {
  const res = await Runtime.request(method, url, isForm ? { form: body, lang: LANG } : { json: body, lang: LANG });
  if (res.file) return res.file;
  if (res.status >= 400) throw new Error((res.json && res.json.message) || `HTTP ${res.status}`);
  return res.json;
}

async function openFile(url) {
  const f = await api('GET', url);
  const href = URL.createObjectURL(f.blob);
  if (f.inline) {
    window.open(href, '_blank', 'noopener');
  } else {
    const a = document.createElement('a');
    a.href = href;
    a.download = f.filename;
    document.body.append(a);
    a.click();
    a.remove();
  }
  setTimeout(() => URL.revokeObjectURL(href), 60000);
}

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = msg;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), 4800);
}

function badge(e) {
  if (e.status === 'Pending' && e.issue) {
    return `<span class="badge b-review">${t(e.needs_review ? 'needs_review' : 'needs_attention')}</span>`;
  }
  return `<span class="badge ${STATUS_CLASS[e.status] || ''}" title="${esc(LANG === 'pt' ? e.status : window.STATUS_LABELS[e.status])}">${esc(statusLabel(e.status))}</span>`;
}

const pad = (n) => String(n).padStart(2, '0');
function fmt(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function ago(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 90) return t('just_now');
  if (s < 3600) return `${Math.round(s / 60)} ${t('min_ago')}`;
  if (s < 86400 * 2) return `${Math.round(s / 3600)} ${t('h_ago')}`;
  return `${Math.round(s / 86400)} ${t('days_ago')}`;
}

async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message, 'err'); } finally { if (btn) btn.disabled = false; }
}

/* ── navigation ─────────────────────────────────────────────────────────── */
let current = 'dashboard';
const loaders = {};
function show(tab) {
  current = tab;
  $$('#nav a').forEach((a) => a.classList.toggle('active', a.dataset.tab === tab));
  $$('.tab').forEach((s) => s.classList.toggle('active', s.id === `tab-${tab}`));
  try { localStorage.setItem('tab', tab); } catch (_) { /* storage blocked */ }
  refresh();
}
async function refresh() {
  try { await counts(); await loaders[current]?.(); } catch (e) { toast(e.message, 'err'); }
}
$$('#nav a').forEach((a) => a.addEventListener('click', () => show(a.dataset.tab)));

let summaryCache = null;
async function counts() {
  const s = await api('GET', 'api/summary');
  summaryCache = s;
  $('#count-queue').textContent = s.queue || '';
  $('#count-workflow').textContent = s.in_workflow || '';
  $('#monitor-toggle').checked = s.monitor;
  setMonitor(s.monitor, false);
  return s;
}

/* ── dashboard ──────────────────────────────────────────────────────────── */
loaders.dashboard = async () => {
  const s = summaryCache;
  const k = [[s.queue, 'kpi_queue'], [s.in_workflow, 'kpi_workflow'], [s.invoices_month, 'kpi_month'],
    [s.amount_month, 'kpi_amount'], [s.suppliers, 'kpi_suppliers'], [s.incoming, 'kpi_incoming']];
  $('#kpis').innerHTML = k.map(([v, l]) => `<div class="kpi"><div class="v">${esc(v)}</div><div class="l">${t(l)}</div></div>`).join('');
  $('#pipeline').innerHTML = Object.entries(s.by_status).map(([st, n]) => `<div class="stage"><div class="n">${n}</div>
    <div class="s">${esc(statusLabel(st))}</div><div class="pt">${esc(LANG === 'pt' ? st : window.STATUS_LABELS[st])}</div></div>`).join('');
  const max = Math.max(1, ...s.by_supplier.map((x) => x.total_num));
  $('#by-supplier').innerHTML = s.by_supplier.map((x) => `
    <div class="row"><span>${esc(x.fornecedor)} <span class="sub">(${x.count})</span></span>
    <div class="track"><div class="fill" style="width:${(100 * x.total_num / max).toFixed(1)}%"></div></div>
    <span class="amt">${esc(x.total)}</span></div>`).join('') || `<p class="muted">${t('no_invoices')}</p>`;
};

/* ── queue ──────────────────────────────────────────────────────────────── */
const btn = (label, attrs, cls = '') => `<button class="btn sm ${cls}" ${attrs}>${esc(t(label))}</button>`;
function queueActions(e) {
  const a = [];
  if (e.status === 'Pending') {
    a.push(btn('a_process', `data-act="process" data-id="${e.id}"`, 'primary'));
    if (e.attachments.length) a.push(btn('a_review', `data-review="${e.id}"`));
    if (e.unknown_supplier) a.push(btn('a_ai', `data-ai-email="${e.id}"`));
  }
  if (e.status === 'Missing invoice') {
    if (!e.invoice_requested) a.push(btn('a_ask_nf', `data-act="request_invoice" data-id="${e.id}"`, 'primary'));
    else a.push(btn('a_supplier_reply', `data-act="simulate_supplier_reply" data-id="${e.id}"`, 'primary'));
  }
  a.push(btn('a_delete', `data-act="delete" data-id="${e.id}"`, 'danger'));
  return a.join(' ');
}
function attachLabel(e) {
  if (e.attachments.length) return e.attachments.map((x) => esc(x.filename) + (x.scanned ? ` <span class="badge">${t('scanned')}</span>` : '')).join('<br>');
  return `<span class="sub">${t(e.has_link ? 'link_in_body' : 'no_attachment')}</span>`;
}
loaders.queue = async () => {
  const rows = await api('GET', 'api/emails?view=queue');
  $('#queue-table').innerHTML = rows.length ? `
    <tr><th>${t('th_received')}</th><th>${t('th_from')}</th><th>${t('th_attachments')}</th><th>${t('th_status')}</th><th>${t('th_actions')}</th></tr>
    ${rows.map((e) => `<tr class="click" data-open="${e.id}">
      <td>${fmt(e.received_at)}<div class="sub">${ago(e.received_at)}</div></td>
      <td><b>${esc(e.sender)}</b><div class="sub">${esc(e.subject)}</div>${e.issue ? `<div class="issue">⚠ ${esc(e.issue)}</div>` : ''}</td>
      <td class="small">${attachLabel(e)}</td><td>${badge(e)}</td>
      <td><div class="actions">${queueActions(e)}</div></td></tr>`).join('')}`
    : `<tr><td class="empty">${t('queue_empty')}</td></tr>`;
};

/* ── workflow board ─────────────────────────────────────────────────────── */
function boardActions(e) {
  switch (e.status) {
    case 'Awaiting Purchasing': return btn('a_purch_reply', `data-act="simulate_purchasing_reply" data-id="${e.id}"`, 'primary');
    case 'Ready for Fiscal': return btn('a_send_fiscal', `data-act="send_fiscal" data-id="${e.id}"`, 'primary');
    case 'Awaiting Fiscal': return btn('a_fiscal_reply', `data-act="simulate_fiscal_reply" data-id="${e.id}"`, 'primary');
    case 'Ready to print': return btn('a_print', `data-file="api/emails/${e.id}/package.pdf"`)
      + ' ' + btn('a_finalize', `data-act="finalize" data-id="${e.id}"`, 'primary');
    default: return '';
  }
}
loaders.workflow = async () => {
  const rows = await api('GET', 'api/emails?view=workflow');
  $('#board').innerHTML = BOARD.map((st) => {
    const items = rows.filter((e) => e.status === st);
    return `<div class="col"><h3><span>${esc(statusLabel(st))} · ${items.length}</span></h3>
      <p class="sub" style="margin:-6px 4px 10px">${t(BOARD_HINT[st])}</p>
      ${items.map((e) => `<div class="card">
        <div class="t"><a href="#" data-open="${e.id}">${esc(e.supplier || e.sender)}</a></div>
        <div class="m">${esc(e.total)} · ${e.process_type === 'Manual' ? t('manual_upload') : esc(e.sender)}</div>
        ${e.po_number ? `<div class="m">${t('po')} ${esc(e.po_number)}</div>` : ''}
        <div class="m">${t('updated')} ${ago(e.updated_at)}</div>
        <div class="a">${boardActions(e)}</div></div>`).join('') || `<p class="sub" style="margin:4px">${t('nothing_here')}</p>`}
    </div>`;
  }).join('');
};

/* ── invoices ───────────────────────────────────────────────────────────── */
loaders.invoices = async () => {
  const rows = await api('GET', 'api/invoices');
  $('#invoice-table').innerHTML = rows.length ? `
    <tr><th>${t('th_extracted')}</th><th>${t('th_campus')}</th><th>${t('th_supplier')}</th><th>${t('th_nf')}</th><th>${t('th_issued')}</th>
      <th>${t('th_due')}</th><th class="num">${t('th_amount')}</th><th>${t('th_source')}</th><th>${t('th_status')}</th></tr>
    ${rows.map((r) => `<tr class="click" data-open="${r.email_id}">
      <td>${fmt(r.extracted_at)}</td><td>${esc(r.unidade)}</td>
      <td><b>${esc(r.fornecedor)}</b><div class="sub">${esc(r.cnpj)}</div><div class="sub">${esc(r.descricao)}</div></td>
      <td>${esc(r.numero)}</td><td>${esc(r.emissao)}</td><td>${esc(r.vencimento)}</td>
      <td class="num">R$ ${esc(r.valor)}</td><td><span class="badge">${esc(r.source)}</span></td><td>${badge(r)}</td></tr>`).join('')}`
    : `<tr><td class="empty">${t('no_invoices')}</td></tr>`;
};

/* ── history ────────────────────────────────────────────────────────────── */
loaders.history = async () => {
  const rows = await api('GET', 'api/emails?view=history');
  $('#history-table').innerHTML = rows.length ? `
    <tr><th>${t('th_closed')}</th><th>${t('th_from')}</th><th>${t('th_supplier')}</th><th class="num">${t('th_amount')}</th><th>${t('th_status')}</th><th></th></tr>
    ${rows.map((e) => `<tr class="click" data-open="${e.id}">
      <td>${fmt(e.updated_at)}</td><td><b>${esc(e.sender)}</b><div class="sub">${esc(e.subject)}</div></td>
      <td>${esc(e.supplier)}${e.po_number ? `<div class="sub">${t('po')} ${esc(e.po_number)}</div>` : ''}</td>
      <td class="num">${esc(e.total)}</td><td>${badge(e)}</td>
      <td>${e.status === 'Deleted' ? btn('a_restore', `data-act="restore" data-id="${e.id}"`)
        : e.has_package ? btn('a_package', `data-file="api/emails/${e.id}/package.pdf"`) : ''}</td></tr>`).join('')}`
    : `<tr><td class="empty">${t('history_empty')}</td></tr>`;
};

/* ── suppliers ──────────────────────────────────────────────────────────── */
let vendorsCache = [];
loaders.vendors = async () => {
  vendorsCache = await api('GET', 'api/vendors');
  $('#vendor-table').innerHTML = `
    <tr><th>${t('th_key')}</th><th>${t('th_supplier')}</th><th>${t('th_campus')}</th><th>CNPJ</th><th>${t('th_route')}</th>
      <th class="num">${t('th_invoices')}</th><th class="num">${t('th_total')}</th><th></th></tr>
    ${vendorsCache.map((v) => `<tr>
      <td><code>${esc(v.key)}</code></td><td><b>${esc(v.fornecedor)}</b><div class="sub">${esc(v.sender_domain)}</div></td>
      <td>${esc(v.unidade)}</td><td>${esc(v.cnpj)}</td>
      <td>${v.direct_to_fiscal ? `<span class="badge b-fiscal">${t('direct_fiscal')}</span>` : `<span class="badge b-purch">${t('purchasing_first')}</span>`}</td>
      <td class="num">${v.invoices}</td><td class="num">${esc(v.total)}</td>
      <td><div class="actions">${btn('edit', `data-edit-vendor="${esc(v.key)}"`)} ${btn('remove', `data-del-vendor="${esc(v.key)}"`, 'danger')}</div></td></tr>`).join('')}`;
};

function vendorForm(v = {}, note = '') {
  const units = [...new Set(vendorsCache.map((x) => x.unidade))];
  openModal(`
    <div class="modal-head"><h2>${t(v.key && !note ? 'edit_vendor' : 'new_vendor_title')}</h2><button class="btn sm" data-close>${t('close')}</button></div>
    ${note}
    <form id="vendor-form" class="form-grid">
      <label>${t('f_key')}<input type="text" name="key" value="${esc(v.key)}" required></label>
      <label>${t('f_name')}<input type="text" name="fornecedor" value="${esc(v.fornecedor)}" required></label>
      <label>${t('f_campus')}<input type="text" name="unidade" value="${esc(v.unidade)}" list="units" required>
        <datalist id="units">${units.map((u) => `<option value="${esc(u)}">`).join('')}</datalist></label>
      <label>${t('f_cnpj')}<input type="text" name="cnpj" value="${esc(v.cnpj)}"></label>
      <label>${t('f_domain')}<input type="text" name="sender_domain" value="${esc(v.sender_domain)}"></label>
      <label style="flex-direction:row;align-items:center;gap:6px;margin-top:18px"><input type="checkbox" name="direct_to_fiscal" ${v.direct_to_fiscal ? 'checked' : ''}> ${t('f_direct')}</label>
      <div class="wide actions"><button class="btn primary" type="submit">${t('save_rule')}</button></div>
    </form>`);
  $('#vendor-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const body = Object.fromEntries(f.entries());
    body.direct_to_fiscal = f.has('direct_to_fiscal');
    await busy(ev.submitter, async () => {
      await api('PUT', `api/vendors/${encodeURIComponent(body.key)}`, body);
      toast(t('vendor_saved'), 'ok');
      closeModal();
      refresh();
    });
  });
}

async function aiRegister(form) {
  const r = await api('POST', 'api/vendors/ai-extract', form, true);
  const s = r.suggestion;
  if (!vendorsCache.length) vendorsCache = await api('GET', 'api/vendors');
  vendorForm({ key: s.chave_normalizada, fornecedor: s.nome_fantasia || s.razao_social, unidade: '', cnpj: '' },
    `<div class="infobox">${t('llm_suggested')} ${t(r.mode === 'ollama' ? 'llm_real' : 'llm_mock')}:
     <code>${esc(JSON.stringify(s))}</code>. ${t('llm_city')} <b>${esc(s.unidade || '-')}</b>. ${t('llm_pick')}</div>`);
}
$('#ai-file').addEventListener('change', async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  await busy(null, () => aiRegister(fd));
  ev.target.value = '';
});
$('#btn-new-vendor').addEventListener('click', () => vendorForm());

/* ── record editor (review + manual upload) ─────────────────────────────── */
const FIELDS = ['fornecedor', 'unidade', 'cnpj', 'numero', 'emissao', 'vencimento', 'competencia', 'valor', 'descricao'];
const REQUIRED = ['fornecedor', 'unidade', 'numero', 'valor'];

function recordEditor(records, docs, withRoute) {
  const docList = `<ul class="docs">${docs.map((d) => `<li><b>${esc(d.filename)}</b>: ${esc(d.doc_type)} (${esc(d.source)})
    ${d.warnings.length ? ` <span class="issue">⚠ ${esc(d.warnings.join(' '))}</span>` : ''}</li>`).join('')}</ul>`;
  if (!records.length) return `${docList}<div class="warnbox">${t('no_nf_found')}</div>`;
  return docList + records.map((r, i) => `
    <div class="record" data-rec="${i}">
      ${r.warnings.length ? `<div class="warnbox">${esc(r.warnings.join(' '))}</div>` : ''}
      <div class="form-grid">
        ${FIELDS.map((k) => `<label class="${k === 'descricao' ? 'wide' : ''}">${t(`fl_${k}`)}
          <input type="text" name="${k}" value="${esc(r[k])}" class="${!r[k] && REQUIRED.includes(k) ? 'warn' : ''}"></label>`).join('')}
        ${withRoute ? `<label style="flex-direction:row;align-items:center;gap:6px"><input type="checkbox" name="direct_to_fiscal" ${r.direct_to_fiscal ? 'checked' : ''}> ${t('direct_fiscal')}</label>` : ''}
      </div>
      <input type="hidden" name="vendor_key" value="${esc(r.vendor_key)}">
      <input type="hidden" name="source" value="${esc(r.source)}">
      <input type="hidden" name="files" value="${esc(JSON.stringify(r.files))}">
    </div>`).join('');
}
function collectRecords(root) {
  return $$('.record', root).map((el) => {
    const r = {};
    $$('input', el).forEach((inp) => {
      if (inp.type === 'checkbox') r[inp.name] = inp.checked;
      else if (inp.name === 'files') r.files = JSON.parse(inp.value || '[]');
      else r[inp.name] = inp.value;
    });
    return r;
  });
}

async function openReview(id) {
  const p = await api('GET', `api/emails/${id}/preview`);
  openModal(`
    <div class="modal-head"><div><h2>${t('review_title')}</h2><p class="muted small">${t('review_sub')}</p></div>
    <button class="btn sm" data-close>${t('close')}</button></div>
    <div id="review-body">${recordEditor(p.records, p.documents, true)}</div>
    ${p.records.length ? `<div class="actions"><button class="btn primary" id="btn-confirm">${t('confirm_forward')}</button></div>` : ''}`);
  $('#btn-confirm')?.addEventListener('click', (ev) => busy(ev.target, async () => {
    const r = await api('POST', `api/emails/${id}/confirm`, { records: collectRecords($('#review-body')) });
    toast(r.message, 'ok');
    closeModal();
    refresh();
  }));
}

/* ── manual upload ──────────────────────────────────────────────────────── */
loaders.manual = async () => {
  const names = await api('GET', 'api/samples');
  $('#sample-links').innerHTML = names.map((n) => `<a class="chip" href="#" data-file="api/samples/${n}">${esc(n)}</a>`).join('');
};
async function manualUpload(files) {
  if (!files.length) return;
  const fd = new FormData();
  [...files].forEach((f) => fd.append('files', f));
  $('#manual-preview').innerHTML = `<p class="muted">${t('reading_pdfs')}</p>`;
  try {
    const p = await api('POST', 'api/manual/preview', fd, true);
    $('#manual-preview').innerHTML = recordEditor(p.records, p.documents, false) + (p.records.length ? `
      <div class="actions"><label class="small">${t('send_to')}
        <select id="manual-dest"><option value="purchasing">${t('dest_purchasing')}</option><option value="fiscal">${t('dest_fiscal')}</option></select></label>
      <button class="btn primary" id="btn-manual-confirm">${t('confirm')}</button></div>` : '');
    $('#btn-manual-confirm')?.addEventListener('click', (ev) => busy(ev.target, async () => {
      const r = await api('POST', 'api/manual/confirm', { token: p.token, destination: $('#manual-dest').value, records: collectRecords($('#manual-preview')) });
      toast(r.message, 'ok');
      $('#manual-preview').innerHTML = `<div class="infobox">${esc(r.message)} <a href="#" data-open="${r.email_id}">${t('open')}</a></div>`;
      counts();
    }));
  } catch (e) {
    $('#manual-preview').innerHTML = `<div class="warnbox">${esc(e.message)}</div>`;
  }
}
const dz = $('#dropzone');
$('#manual-files').addEventListener('change', (ev) => { manualUpload(ev.target.files); ev.target.value = ''; });
['dragover', 'dragenter'].forEach((n) => dz.addEventListener(n, (ev) => { ev.preventDefault(); dz.classList.add('over'); }));
['dragleave', 'drop'].forEach((n) => dz.addEventListener(n, () => dz.classList.remove('over')));
dz.addEventListener('drop', (ev) => { ev.preventDefault(); manualUpload(ev.dataTransfer.files); });

/* ── outbox / logs ──────────────────────────────────────────────────────── */
loaders.outbox = async () => {
  const msgs = await api('GET', 'api/outbox');
  $('#outbox-list').innerHTML = msgs.map((m) => `<div class="mail">
    <div class="h"><span><b>${t('to')}:</b> ${esc(m.to)} <span class="badge">${esc(m.kind)}</span></span><span class="sub">${fmt(m.ts)}</span></div>
    <div><b>${esc(m.subject)}</b></div>
    ${m.attachments.length ? `<div class="sub">📎 ${m.attachments.map(esc).join(', ')}</div>` : ''}
    ${m.body ? `<pre>${esc(m.body)}</pre>` : ''}</div>`).join('') || `<p class="muted">${t('nothing_sent')}</p>`;
};
loaders.logs = async () => {
  const rows = await api('GET', 'api/logs');
  $('#log-table').innerHTML = `<tr><th>${t('th_time')}</th><th>${t('th_level')}</th><th>${t('th_message')}</th></tr>` + rows.map((l) =>
    `<tr><td>${fmt(l.ts)}</td><td><span class="badge b-${esc(l.level)}">${esc(l.level)}</span></td><td>${esc(l.message)}</td></tr>`).join('');
};

/* ── detail modal ───────────────────────────────────────────────────────── */
const modal = $('#modal');
let openDetailId = null;
function openModal(html) { $('#modal-body').innerHTML = html; if (!modal.open) modal.showModal(); }
function closeModal() { openDetailId = null; modal.close(); }
modal.addEventListener('click', (ev) => { if (ev.target === modal || ev.target.closest('[data-close]')) closeModal(); });
modal.addEventListener('close', () => { openDetailId = null; });

async function openDetail(id) {
  const e = await api('GET', `api/emails/${id}`);
  openDetailId = id;
  const actions = ['Pending', 'Missing invoice'].includes(e.status) ? queueActions(e)
    : e.status === 'Deleted' ? btn('a_restore', `data-act="restore" data-id="${e.id}"`) : boardActions(e);
  openModal(`
    <div class="modal-head"><div><h2>${esc(e.subject)}</h2><div class="sub">${esc(e.sender)} · ${fmt(e.received_at)}</div></div>
      <div class="actions">${badge(e)}<button class="btn sm" data-close>${t('close')}</button></div></div>
    ${e.issue ? `<div class="warnbox">${esc(e.issue)}</div>` : ''}
    <dl class="kv">
      <dt>${t('d_folder')}</dt><dd><code>${esc(e.folder)}</code> · ${t(e.read ? 'd_read' : 'd_unread')}</dd>
      <dt>${t('d_origin')}</dt><dd>${t(`origin_${e.process_type}`)}</dd>
      ${e.po_number ? `<dt>${t('d_po')}</dt><dd>${esc(e.po_number)}</dd>` : ''}
      ${e.sharepoint_url ? `<dt>SharePoint</dt><dd><code>${esc(decodeURIComponent(e.sharepoint_url))}</code></dd>` : ''}
      <dt>${t('d_attachments')}</dt><dd>${e.attachments.map((a) => `<a href="#" data-file="api/emails/${e.id}/attachments/${encodeURIComponent(a.filename)}">${esc(a.filename)}</a>${a.scanned ? ` <span class="badge">${t('ocr_badge')}</span>` : ''}`).join('<br>') || '-'}
        ${e.has_package ? `<br><a href="#" data-file="api/emails/${e.id}/package.pdf">${t('d_package')}</a>` : ''}</dd>
      ${e.body ? `<dt>${t('d_body')}</dt><dd class="small">${esc(e.body)}</dd>` : ''}
    </dl>
    ${e.invoices.length ? `<h2>${t('d_invoices')}</h2><div class="panel flush"><table class="table">
      <tr><th>${t('th_supplier')}</th><th>${t('th_campus')}</th><th>${t('th_nf')}</th><th>${t('th_due')}</th><th class="num">${t('th_amount')}</th></tr>
      ${e.invoices.map((r) => `<tr><td>${esc(r.fornecedor)}</td><td>${esc(r.unidade)}</td><td>${esc(r.numero)}</td><td>${esc(r.vencimento)}</td><td class="num">R$ ${esc(r.valor)}</td></tr>`).join('')}
    </table></div>` : ''}
    <h2>${t('d_timeline')}</h2>
    <ul class="timeline">${e.timeline.map((x) => `<li><b>${esc(statusLabel(x.status))}</b> · <span class="sub">${fmt(x.ts)} · ${esc(x.folder)}</span><div>${esc(x.note)}</div></li>`).join('')}</ul>
    <div class="actions" style="margin-top:12px">${actions}</div>`);
}

/* ── global click handling ──────────────────────────────────────────────── */
document.addEventListener('click', async (ev) => {
  const el = ev.target.closest('[data-act],[data-review],[data-open],[data-ai-email],[data-edit-vendor],[data-del-vendor],[data-file]');
  if (!el) return;
  if (el.dataset.file) {
    ev.preventDefault();
    ev.stopPropagation();
    await busy(el.tagName === 'BUTTON' ? el : null, () => openFile(el.dataset.file));
  } else if (el.dataset.act) {
    ev.stopPropagation();
    await busy(el, async () => {
      const r = await api('POST', `api/emails/${el.dataset.id}/actions/${el.dataset.act}`);
      toast(r.message, ['Pending', 'Missing invoice'].includes(r.status) ? '' : 'ok');
      if (modal.open) await openDetail(el.dataset.id);
      await refresh();
    });
  } else if (el.dataset.review) {
    ev.stopPropagation();
    await busy(el, () => openReview(el.dataset.review));
  } else if (el.dataset.aiEmail) {
    ev.stopPropagation();
    const fd = new FormData();
    fd.append('email_id', el.dataset.aiEmail);
    await busy(el, () => aiRegister(fd));
  } else if (el.dataset.editVendor) {
    vendorForm(vendorsCache.find((v) => v.key === el.dataset.editVendor));
  } else if (el.dataset.delVendor) {
    if (!window.confirm(`${t('confirm_remove')} ${el.dataset.delVendor}?`)) return;
    await busy(el, async () => { await api('DELETE', `api/vendors/${encodeURIComponent(el.dataset.delVendor)}`); refresh(); });
  } else if (el.dataset.open) {
    if (ev.target.closest('button')) return;
    ev.preventDefault();
    await busy(null, () => openDetail(el.dataset.open));
  }
});

async function fetchInbox(b) {
  return busy(b, async () => { const r = await api('POST', 'api/inbox/fetch'); toast(r.message); await refresh(); });
}
async function processAll(b) {
  return busy(b, async () => { const r = await api('POST', 'api/queue/process'); toast(r.message, 'ok'); await refresh(); });
}
$('#btn-fetch').addEventListener('click', (ev) => fetchInbox(ev.target));
$('#btn-process-all').addEventListener('click', (ev) => processAll(ev.target));
$$('[data-run]').forEach((b) => b.addEventListener('click', () => (b.dataset.run === 'fetch' ? fetchInbox(b) : processAll(b))));
$('#btn-finance').addEventListener('click', (ev) => busy(ev.target, async () => {
  const r = await api('POST', 'api/finance/send');
  toast(r.message, 'ok');
}));
$('#btn-reset').addEventListener('click', async () => {
  if (!window.confirm(t('reset_confirm'))) return;
  await api('POST', 'api/reset');
  toast(t('reset_done'), 'ok');
  refresh();
});

/* ── auto-monitor: production polls the mailbox on a schedule ───────────── */
let timer = null;
function setMonitor(on, persist = true) {
  if (persist) api('POST', `api/monitor/${on ? 'start' : 'stop'}`).catch(() => {});
  if (on && !timer) {
    timer = setInterval(async () => {
      try { await api('POST', 'api/inbox/fetch'); await api('POST', 'api/queue/process'); refresh(); } catch (_) { /* next tick */ }
    }, 20000);
  } else if (!on && timer) { clearInterval(timer); timer = null; }
}
$('#monitor-toggle').addEventListener('change', (ev) => { setMonitor(ev.target.checked); toast(t(ev.target.checked ? 'monitor_on' : 'monitor_off')); });

/* ── start ──────────────────────────────────────────────────────────────── */
(async () => {
  applyI18n();
  if (Runtime.MODE === 'browser') {
    const boot = $('#boot');
    boot.hidden = false;
    try {
      await Runtime.boot((key, pct) => {
        if (key) $('#boot-step').textContent = t(key);
        $('#boot-fill').style.width = `${pct}%`;
      });
    } catch (e) {
      $('#boot-step').textContent = t('boot_failed') + e.message;
      return;
    }
    boot.hidden = true;
  }
  let start = 'dashboard';
  try { start = localStorage.getItem('tab') || 'dashboard'; } catch (_) { /* storage blocked */ }
  show($(`#nav a[data-tab="${start}"]`) ? start : 'dashboard');
})();
