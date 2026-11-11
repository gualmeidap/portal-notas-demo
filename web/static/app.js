/* Portal Notas demo: vanilla JS, no build step.
   app.js = core (language, theme, transport, shell, overview, history, month by month, manual upload, suppliers).
   pages.js = descriptions, report, settings, logs, sent e-mails. boot.js = start-up. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ── language ───────────────────────────────────────────────────────────── */
let LANG = 'en';
try { LANG = localStorage.getItem('lang') || ''; } catch (_) { /* storage blocked */ }
if (!LANG) LANG = (navigator.language || '').toLowerCase().startsWith('pt') ? 'pt' : 'en';
const L = (en, pt) => (LANG === 'pt' ? pt : en);
const tb = (k) => (window.I18N[LANG] || window.I18N.en)[k] || k;

/* ── icons (24px stroke set) ────────────────────────────────────────────── */
const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  archive: '<rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>',
  calcheck: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 16 2 2 4-4"/>',
  upload: '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/>',
  truck: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62L18.3 9.38a1 1 0 0 0-.78-.38H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
  book: '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
  chart: '<path d="M18 20V10M12 20V4M6 20v-6"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8M16 13H8M16 17H8"/>',
  out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  left: '<path d="m15 18-6-6 6-6"/>', right: '<path d="m9 18 6-6-6-6"/>', down: '<path d="m6 9 6 6 6-6"/>', up: '<path d="m18 15-6-6-6 6"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  user: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="10" r="3"/><path d="M7 20.66V19a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1.66"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  printer: '<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  check: '<path d="M20 6 9 17l-5-5"/>', checks: '<path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/>',
  bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  cart: '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  news: '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  server: '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/>',
  send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  plus: '<path d="M5 12h14M12 5v14"/>', x: '<path d="M18 6 6 18M6 6l12 12"/>',
  flask: '<path d="M10 2v7.3L4.5 19a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 9.3V2"/><path d="M8.5 2h7M7 16h10"/>',
  edit: '<path d="M12 20h9"/><path d="M16.4 3.6a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
  table: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
  filter: '<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>',
  clip: '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  sparkle: '<path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
};
const ico = (n, cls = '') => `<svg class="ico ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ''}</svg>`;
// Original mark (a shield with a ticked invoice): the demo has its own brand, not the production logo.
const LOGO = (s = 64) => `<svg width="${s}" height="${Math.round(s * 1.12)}" viewBox="0 0 64 72" aria-hidden="true"><path d="M32 3 59 12v22c0 17-11.5 29-27 35C16.5 63 5 51 5 34V12z" fill="#0f2f55" stroke="#d9b24c" stroke-width="3"/><rect x="21" y="19" width="22" height="28" rx="3" fill="#fff"/><path d="M26 28h12M26 34h12M26 40h7" stroke="#0f2f55" stroke-width="2.4" stroke-linecap="round"/><circle cx="42" cy="43" r="8" fill="#d9b24c"/><path d="m38 43 3 3 5-6" stroke="#0f2f55" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

/* ── theme ──────────────────────────────────────────────────────────────── */
function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('theme', next); } catch (_) { /* storage blocked */ }
}

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
    a.href = href; a.download = f.filename;
    document.body.append(a); a.click(); a.remove();
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
async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message, 'err'); } finally { if (btn) btn.disabled = false; }
}
const qs = (o) => Object.entries(o).filter(([, v]) => v !== '' && v != null).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

/* ── formatting ─────────────────────────────────────────────────────────── */
const pad = (n) => String(n).padStart(2, '0');
const fmtDT = (iso) => { if (!iso) return '-'; const d = new Date(iso); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const fmtD = (iso) => { if (!iso) return '-'; const d = new Date(`${String(iso).slice(0, 10)}T12:00:00`); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`; };
const fmtDfull = (iso) => { const d = new Date(`${String(iso).slice(0, 10)}T12:00:00`); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`; };
const fmtT = (iso) => { const d = new Date(iso); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const money = (n) => Number(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const MONTHS_LONG_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MONTHS_LONG_PT = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const mShort = (ym) => `${(LANG === 'pt' ? MONTHS_PT : MONTHS_EN)[+ym.slice(5, 7) - 1].toLowerCase()}/${ym.slice(2, 4)}`;
const mLong = (ym) => `${(LANG === 'pt' ? MONTHS_LONG_PT : MONTHS_LONG_EN)[+ym.slice(5, 7) - 1]} ${ym.slice(0, 4)}`;
function rel(delta) {
  if (delta === 0) return L('due today', 'vence hoje');
  if (delta === 1) return L('due tomorrow', 'vence amanhã');
  if (delta > 1) return L(`due in ${delta} days`, `vence em ${delta} dias`);
  if (delta === -1) return L('was due yesterday', 'venceu ontem');
  return L(`was due ${-delta} days ago`, `venceu há ${-delta} dias`);
}

/* ── status badges ──────────────────────────────────────────────────────── */
const STATUS_UI = {
  'Pending': ['gray', 'clock'], 'Missing invoice': ['red', 'help'], 'Awaiting Purchasing': ['orange', 'cart'],
  'Ready for Fiscal': ['blue', 'send'], 'Awaiting Fiscal': ['blue', 'building'], 'Awaiting Cover': ['orange', 'file'],
  'Ready to print': ['violet', 'printer'], 'Completed': ['green', 'check'], 'Deleted': ['gray', 'trash'],
};
const statusLabel = (s) => (LANG === 'pt' ? window.STATUS_LABELS[s] || s : s);
function badge(e) {
  if (e.status === 'Pending' && e.issue) return `<span class="st orange">${ico('info')} ${L(e.needs_review ? 'Needs review' : 'Needs attention', e.needs_review ? 'Precisa de revisão' : 'Precisa de atenção')}</span>`;
  const [cls, ic] = STATUS_UI[e.status] || ['gray', 'clock'];
  return `<span class="st ${cls}">${ico(ic)} ${esc(statusLabel(e.status))}</span>`;
}
const triageTone = { red: 'red', blue: 'blue', orange: 'orange', green: 'green', gray: 'gray' };
const CAT_ICON = { scam: 'shield', newsletter: 'news', other_group: 'building', billing_reminder: 'bell', handled: 'check', informative: 'info', account_system: 'server', other: 'help' };

/* ── shell ──────────────────────────────────────────────────────────────── */
const PAGES = {};
const MENU = [
  ['overview', 'grid', ['Overview', 'Visão Geral']], ['history', 'archive', ['Processing History', 'Histórico de Processamento']],
  ['months', 'calcheck', ['Month by Month', 'Mês a Mês']], ['manual', 'upload', ['Manual Upload', 'Envio Manual']],
  ['#', 'SYSTEM', ['SYSTEM', 'SISTEMA']],
  ['suppliers', 'truck', ['Suppliers', 'Fornecedores']], ['descriptions', 'book', ['Descriptions', 'Descrições']],
  ['report', 'chart', ['Report', 'Relatório']], ['settings', 'gear', ['Settings', 'Configurações']],
  ['#', 'LOGS', ['LOGS', 'LOGS']],
  ['logs', 'file', ['System', 'Sistema']], ['outbox', 'mail', ['Sent e-mails', 'E-mails enviados'], 'demo'],
];
let current = 'overview';
let notif = { count: 0, items: [] };
function renderShell() {
  document.documentElement.lang = LANG === 'pt' ? 'pt-BR' : 'en';
  $('#banner-text').innerHTML = L('<strong>Public demo</strong> · fictional suppliers and amounts · Microsoft 365 mocked · your own sandbox (only you see your changes)',
    '<strong>Demo pública</strong> · fornecedores e valores fictícios · Microsoft 365 simulado · seu próprio sandbox (só você vê as suas mudanças)');
  $('#btn-reset').textContent = L('Reset demo', 'Reiniciar demo');
  $('#src-link').textContent = L('Source code', 'Código-fonte');
  $$('.lang-toggle button').forEach((b) => b.classList.toggle('on', b.dataset.lang === LANG));
  $('#sidebar').innerHTML = `
    <div class="sb-top"><button class="sb-toggle" id="sb-toggle" title="Menu">${ico('left')}</button>
      <div class="logo-mark">${LOGO(60)}</div><div class="brand-name">Portal Notas</div></div>
    <nav class="sb-nav">${MENU.map(([id, ic, label, tag]) => (id === '#'
    ? `<div class="sb-group">${L(...label)}</div>`
    : `<a class="sb-link ${id === current ? 'active' : ''}" href="#/${id}" title="${esc(L(...label))}">${ico(ic, 'lg')}<span class="sb-label">${L(...label)}${tag ? `<span class="tag">${tag}</span>` : ''}</span></a>`)).join('')}</nav>
    <div class="sb-foot"><a class="sb-link out" href="#" id="btn-logout">${ico('out', 'lg')}<span class="sb-label">${L('Exit', 'Sair')}</span></a></div>`;
  const page = MENU.find((m) => m[0] === current);
  $('#topbar').innerHTML = `
    <div class="crumbs">Dashboard / <b>${L(...(page ? page[2] : ['', '']))}</b></div>
    <div class="searchbox rel">${ico('search')}<input id="gsearch" type="text" autocomplete="off" placeholder="${L('Search…', 'Pesquisar...')}"><div class="drop-menu" id="search-menu" hidden></div></div>
    <span class="pill mono">${ico('mail')} ${esc(mailbox)}</span>
    <div class="rel"><button class="icon-btn ${notif.count ? 'alert' : ''}" id="btn-bell" title="${L('Due dates', 'Vencimentos')}">${ico('bell')}${notif.count ? `<span class="dot">${notif.count}</span>` : ''}</button><div class="drop-menu" id="bell-menu" hidden></div></div>
    <button class="icon-btn" id="btn-theme" title="${L('Toggle theme', 'Alternar tema')}">${ico('sun')}</button>
    <span class="pill">${ico('user')} <b>admin.demo</b></span>`;
  $('#boot-note').textContent = tb('boot_note');
  $('#boot-logo').innerHTML = LOGO(56);
}
let mailbox = 'invoices.desk@university.example';

document.addEventListener('click', (ev) => {
  const t = ev.target;
  if (t.closest('#sb-toggle')) $('#shell').classList.toggle('collapsed');
  else if (t.closest('#btn-theme')) toggleTheme();
  else if (t.closest('#btn-logout')) { ev.preventDefault(); toast(L('Demo: there is no login here. Use "Reset demo" to start over.', 'Demo: aqui não há login. Use "Reiniciar demo" para recomeçar.')); }
  else if (t.closest('#btn-bell')) { toggleBell(); }
  else if (!t.closest('#bell-menu')) $('#bell-menu') && ($('#bell-menu').hidden = true);
  if (!t.closest('.searchbox') && $('#search-menu')) $('#search-menu').hidden = true;
});
function toggleBell() {
  const m = $('#bell-menu');
  m.hidden = !m.hidden;
  if (m.hidden) return;
  m.innerHTML = notif.items.length ? notif.items.map((x) => `<div class="it" data-goto="suppliers:due"><b>${esc(x.name)}</b> <span class="faint">${L('day', 'dia')} ${x.day}</span><div class="small ${x.state === 'late' ? 'tone-red' : ''}" style="color:var(--${x.state === 'late' ? 'red' : 'orange'})">${rel(x.delta)} · ${L('invoice not here yet', 'a nota ainda não chegou')}</div></div>`).join('')
    : `<div class="it muted">${L('Nothing due.', 'Nada vencendo.')}</div>`;
}
let searchTimer = null;
document.addEventListener('input', (ev) => {
  if (ev.target.id !== 'gsearch') return;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const v = ev.target.value.trim();
    const m = $('#search-menu');
    if (v.length < 2) { m.hidden = true; return; }
    const rows = await api('GET', `api/search?${qs({ q: v })}`).catch(() => []);
    m.innerHTML = rows.length ? rows.map((e) => `<div class="it" data-open="${e.id}"><b>${esc(e.sender)}</b> ${badge(e)}<div class="small muted">${esc(e.subject)}</div></div>`).join('')
      : `<div class="it muted">${L('No results.', 'Nenhum resultado.')}</div>`;
    m.hidden = false;
  }, 250);
});
document.addEventListener('click', (ev) => {
  const g = ev.target.closest('[data-goto]');
  if (!g) return;
  const [page, sub] = g.dataset.goto.split(':');
  if (sub) S.sup.tab = sub;
  location.hash = `#/${page}`;
  if (current === page) refresh();
});
$$('.lang-toggle button').forEach((b) => b.addEventListener('click', () => {
  LANG = b.dataset.lang;
  try { localStorage.setItem('lang', LANG); } catch (_) { /* storage blocked */ }
  renderShell();
  refresh();
  if (modal.open && openDetailId) openDetail(openDetailId);
}));

/* ── navigation ─────────────────────────────────────────────────────────── */
async function refresh() {
  try {
    notif = await api('GET', 'api/notifications');
    renderShell();
    await PAGES[current].load();
  } catch (e) { toast(e.message, 'err'); }
}
function route() {
  const id = (location.hash.replace('#/', '') || 'overview').split('?')[0];
  current = PAGES[id] ? id : 'overview';
  try { localStorage.setItem('page', current); } catch (_) { /* storage blocked */ }
  $('#page').scrollTop = 0;
  refresh();
}
window.addEventListener('hashchange', route);

const S = { hist: { filter: 'all', page: 1, category: '', q: '' }, sup: { tab: 'keys', q: '', month: '' }, inv: { month: '' }, guide: true, months: {} };

/* ── page chrome helpers ────────────────────────────────────────────────── */
const head = (title, sub, actions = '') => `<div class="page-head"><div><h1>${title}</h1>${sub ? `<p>${sub}</p>` : ''}</div><div class="btn-row">${actions}</div></div>`;
const pager = (page, pages, total, key) => `<div class="pager"><span>${L(`Page ${page} of ${pages} (Total: ${total})`, `Página ${page} de ${pages} (Total: ${total})`)}</span>
  <button class="btn sm plain" data-pg="${key}:${page - 1}" ${page <= 1 ? 'disabled' : ''}>${L('Previous', 'Anterior')}</button>
  <button class="btn sm plain" data-pg="${key}:${page + 1}" ${page >= pages ? 'disabled' : ''}>${L('Next', 'Próxima')}</button></div>`;

/* ── overview ───────────────────────────────────────────────────────────── */
const TONE = { orange: 'var(--orange)', green: 'var(--green)', gray: 'var(--gray)', violet: 'var(--violet)', blue: 'var(--blue)', red: 'var(--red)' };
function sparkline(daily) {
  const w = 380, h = 78, pl = 22, pb = 14, max = Math.max(4, ...daily.map((d) => d.n));
  const x = (i) => pl + (daily.length === 1 ? 0 : (i * (w - pl - 6)) / (daily.length - 1));
  const y = (n) => h - pb - (n / max) * (h - pb - 8);
  const pts = daily.map((d, i) => `${x(i).toFixed(1)},${y(d.n).toFixed(1)}`);
  const ticks = daily.filter((d) => d.day === 1 || d.day % 2 === 1 || d.day === daily.length).map((d) => `<text x="${x(d.day - 1)}" y="${h - 2}" font-size="8" fill="var(--faint)" text-anchor="middle">${pad(d.day)}</text>`).join('');
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" role="img" aria-label="${L('Invoices processed per day', 'Notas processadas por dia')}">
    ${[0, 5, 10].map((v) => `<line x1="${pl}" x2="${w - 6}" y1="${y(Math.min(v, max))}" y2="${y(Math.min(v, max))}" stroke="var(--border)" stroke-dasharray="2 3"/>`).join('')}
    <polygon points="${pl},${h - pb} ${pts.join(' ')} ${x(daily.length - 1)},${h - pb}" fill="color-mix(in srgb, var(--blue) 18%, transparent)"/>
    <polyline points="${pts.join(' ')}" fill="none" stroke="var(--blue)" stroke-width="1.6"/>
    ${daily.filter((d) => d.n > 0).map((d) => `<circle cx="${x(d.day - 1)}" cy="${y(d.n)}" r="2.6" fill="var(--blue)"/>`).join('')}${ticks}</svg>`;
}
function donut(groups) {
  const order = [['awaiting_purchasing', 'orange', ['Awaiting Purchasing', 'Aguardando Compras']], ['completed', 'green', ['Completed', 'Concluído']],
    ['pending', 'gray', ['Pending', 'Pendente']], ['ready_to_print', 'violet', ['Ready to print', 'Pronto para Impressão']], ['awaiting_fiscal', 'blue', ['Awaiting Fiscal', 'Aguardando Fiscal']]];
  const total = order.reduce((a, [k]) => a + (groups[k] || 0), 0) || 1, C = 2 * Math.PI * 52;
  let off = 0;
  const arcs = order.filter(([k]) => groups[k]).map(([k, tone]) => {
    const len = (groups[k] / total) * C;
    const seg = `<circle cx="70" cy="70" r="52" fill="none" stroke="${TONE[tone]}" stroke-width="17" stroke-dasharray="${len.toFixed(1)} ${(C - len).toFixed(1)}" stroke-dashoffset="${(-off).toFixed(1)}" transform="rotate(-90 70 70)"/>`;
    off += len;
    return seg;
  }).join('');
  const legend = order.filter(([k]) => groups[k]).map(([, tone, lab]) => `<div><i style="background:${TONE[tone]}"></i>${L(...lab)}</div>`).join('');
  return `<div style="display:flex;align-items:center;justify-content:center;gap:26px"><svg viewBox="0 0 140 140" width="150" height="150" role="img" aria-label="${L('Share by status', 'Divisão por status')}">${arcs}</svg><div class="legend">${legend}</div></div>`;
}
function tagsOf(e) {
  return (e.manual ? `<span class="tag green">${L('MANUAL', 'MANUAL')}</span>` : '') + (e.bulk ? `<span class="tag orange">${L('BULK', 'MASSA')}</span>` : `<span class="tag violet">${L('SINGLE', 'ÚNICO')}</span>`);
}
function rowActions(e) {
  const b = [];
  const demo = (act, label, extra = '') => `<button class="btn sm demo" data-act="${act}" data-id="${e.id}" title="${L('Demo shortcut: in production this arrives by e-mail', 'Atalho da demo: em produção isso chega por e-mail')}">${ico('flask')} ${label}</button>${extra}`;
  b.push(`<button class="btn sm red" data-act="delete" data-id="${e.id}" title="${L('Delete', 'Excluir')}">${ico('trash')}</button>`);
  switch (e.status) {
    case 'Pending':
      if (e.can_forward) b.push(`<button class="btn sm purple" data-act="forward" data-id="${e.id}">${ico('send')} ${L('Forward', 'Encaminhar')}</button>`);
      else b.push(`<button class="btn sm dark" data-act="process" data-id="${e.id}">${ico('bolt')} ${L('Process', 'Processar')}</button>`);
      if (e.attach_count && !e.can_forward) b.push(`<button class="btn sm plain" data-review="${e.id}">${L('Review', 'Revisar')}</button>`);
      if (e.unknown_supplier) b.push(`<button class="btn sm plain" data-ai-email="${e.id}">${ico('sparkle')} ${L('Register (AI)', 'Cadastrar (IA)')}</button>`);
      break;
    case 'Missing invoice':
      b.push(e.invoice_requested ? demo('simulate_supplier_reply', L('Supplier replies', 'Fornecedor responde'))
        : `<button class="btn sm dark" data-act="request_invoice" data-id="${e.id}">${ico('mail')} ${L('Ask for invoice', 'Pedir nota')}</button>`);
      break;
    case 'Awaiting Purchasing': b.push(demo('simulate_purchasing_reply', L('Purchasing replies', 'Compras responde'))); break;
    case 'Ready for Fiscal': b.push(demo('send_fiscal', L('Send to Fiscal', 'Enviar ao Fiscal'))); break;
    case 'Awaiting Fiscal': b.push(demo('simulate_fiscal_reply', L('Fiscal replies', 'Fiscal responde'))); break;
    case 'Awaiting Cover': b.push(demo('simulate_cover_reply', L('Cover comes back', 'Capa volta'))); break;
    case 'Ready to print':
      b.push(`<button class="btn sm purple" data-file="api/emails/${e.id}/package.pdf">${ico('printer')} ${L('Print', 'Imprimir')}</button>`);
      b.push(`<button class="btn sm green" data-act="finalize" data-id="${e.id}">${ico('check')} ${L('Finish', 'Finalizar')}</button>`);
      break;
    case 'Deleted': return `<button class="btn sm blue plain" data-act="restore" data-id="${e.id}">${ico('refresh')} ${L('Restore', 'Restaurar')}</button>`;
    default:
  }
  return b.join(' ');
}
PAGES.overview = {
  async load() {
    const [ov, queue, invs] = await Promise.all([api('GET', 'api/overview'), api('GET', 'api/emails?view=open'), api('GET', 'api/invoices')]);
    const cal = ov.calendar, c = cal.counts;
    const months = [...new Set([ov.month, ...invs.map((r) => r.extracted_at.slice(0, 7))])].sort().reverse();
    if (!S.inv.month || !months.includes(S.inv.month)) S.inv.month = ov.month;
    const rows = invs.filter((r) => r.extracted_at.slice(0, 7) === S.inv.month);
    const guide = S.guide ? `<div class="guide"><div class="btn-row" style="justify-content:space-between"><b>${ico('flask')} ${L('Demo guide', 'Roteiro da demo')}</b><button class="link-btn" data-hide-guide>${L('hide', 'ocultar')}</button></div>
      <ol><li>${L('<b>Read now</b> (card below): two new e-mails arrive (a scanned invoice and an unknown supplier).', '<b>Ler agora</b> (card abaixo): chegam dois e-mails novos (uma nota digitalizada e um fornecedor desconhecido).')}</li>
      <li>${L('<b>Process All</b>: boleto without invoice is flagged, low-confidence OCR goes to review, protected PDFs are just forwarded.', '<b>Processar Tudo</b>: boleto sem nota é sinalizado, OCR de baixa confiança vai para revisão, PDFs protegidos são só encaminhados.')}</li>
      <li>${L('Use the dashed <b>demo</b> buttons to play the part of Purchasing and Fiscal (in production they reply by e-mail and the portal reads the thread).', 'Use os botões tracejados de <b>demo</b> para fazer o papel do Compras e do Fiscal (em produção eles respondem por e-mail e o portal lê a conversa).')}</li>
      <li>${L('Watch <b>Month by Month</b>, <b>Suppliers › Due dates</b> and the calendar card update as invoices arrive.', 'Acompanhe <b>Mês a Mês</b>, <b>Fornecedores › Vencimentos</b> e o card do calendário se atualizando conforme as notas chegam.')}</li></ol></div>` : '';
    $('#page').innerHTML = `${head(L('Portal Notas Control Panel', 'Painel de Controle Portal Notas'), L('Monitoring and processing of fiscal documents', 'Monitoramento e processamento de documentos fiscais'))}${guide}
    <div class="grid-3">
      <div class="card pad"><div class="btn-row" style="justify-content:space-between"><span class="muted small">${L('Processed (current month)', 'Processados (Mês Atual)')}</span>${ico('checks', 'lg')}</div>
        <div class="big">${ov.processed}</div>${sparkline(ov.daily)}
        <div class="kv-row"><div>${L('Automatic', 'Automático')}: <b>${ov.auto}</b><br>${L('Bulk', 'Massa')}: <b>${ov.bulk}</b></div><div>${L('Manual', 'Manual')}: <b>${ov.manual}</b><br>${L('Single', 'Único')}: <b>${ov.single}</b></div></div>
        <div class="small" style="color:var(--green);margin-top:10px">${L('Automatic reading', 'Leitura automática')} · ${L('last', 'última')} ${fmtT(ov.last_sync)}
          · <button class="link-btn" data-read-now>${L('Read now', 'Ler agora')}</button> · <label class="small muted"><input type="checkbox" id="monitor-toggle" ${monitorOn ? 'checked' : ''}> ${L('auto every 20 s', 'auto a cada 20 s')}</label></div></div>
      <div class="card pad"><div class="btn-row" style="justify-content:space-between"><span class="nav-month"><b>${mLong(ov.month)}</b></span><span class="muted small">${L(`${ov.completed_month} completed · ${ov.in_queue} in queue`, `${ov.completed_month} concluídos · ${ov.in_queue} na fila`)}</span></div>
        <div style="margin-top:12px">${donut(ov.groups)}</div><div class="muted small" style="margin-top:6px">${L('In queue today (all months)', 'Na fila hoje (todos os meses)')}: <b style="color:var(--text)">${ov.in_queue}</b></div></div>
      <div class="card pad"><div class="btn-row" style="justify-content:space-between"><span class="nav-month"><b>${mLong(ov.month)}</b></span><span class="muted small">${cal.suppliers} ${L('suppliers', 'fornecedores')}</span></div>
        <div class="cal-chips"><span class="chip red">${L(`${c.late} overdue`, `${c.late} atrasadas`)}</span><span class="chip orange">${L(`${c.soon} due soon`, `${c.soon} a vencer`)}</span><span class="chip gray">${L(`${c.on_time} on time`, `${c.on_time} no prazo`)}</span><span class="chip blue">${L(`${c.in_progress} in progress`, `${c.in_progress} em andamento`)}</span><span class="chip green">${L(`${c.completed} completed`, `${c.completed} concluídas`)}</span></div>
        <div class="small muted" style="margin-bottom:4px">${L('No invoice yet', 'Sem nota')} <span class="faint">${cal.missing_total}</span></div>
        <div class="cal-list">${cal.missing.map((x) => `<div class="row"><span class="l"><i style="background:${x.state === 'late' ? 'var(--red)' : x.state === 'soon' ? 'var(--orange)' : 'var(--gray)'}"></i>${esc(x.name)} <span class="faint small">${L('day', 'dia')} ${x.day}</span></span><span>${cal.ticket_mode === 'simulation' ? `<span class="chip dashed tiny">${L('simulated', 'simulado')}</span> ` : ''}<span class="small muted">${rel(x.delta)}</span></span></div>`).join('') || `<div class="muted small">${L('Everything arrived.', 'Tudo chegou.')}</div>`}</div>
        <div class="btn-row" style="justify-content:space-between;margin-top:8px"><button class="link-btn" data-goto="suppliers:due">${L(`See all ${cal.missing_total} notes`, `Ver as ${cal.missing_total} notas`)}</button><button class="link-btn muted" data-goto="suppliers:due">${L('Calendar', 'Calendário')} →</button></div></div>
    </div>
    <div class="card"><header><h2>${L('Processing Queue', 'Fila de Processamento')}</h2><div class="btn-row"><button class="icon-btn" data-refresh title="${L('Refresh', 'Atualizar')}">${ico('refresh')}</button><button class="btn dark" data-process-all>${ico('bolt')} ${L('Process All', 'Processar Tudo')}</button></div></header>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>E-mail</th><th>${L('Date received', 'Data recebimento')}</th><th class="center">Status</th><th class="right">${L('Actions', 'Ações')}</th></tr></thead><tbody>
      ${queue.map((e) => `<tr class="click" data-open="${e.id}"><td><div class="t1">${esc(e.sender)}${tagsOf(e)}</div><div class="sub">${esc(e.subject)}${e.issue ? `<div class="issue">⚠ ${esc(e.issue)}</div>` : ''}</div></td>
        <td class="when">${fmtDT(e.received_at)}</td><td class="center">${badge(e)}</td><td><div class="btn-row">${e.attach_count > 1 ? `<span class="muted tiny">${ico('clip')} ${e.attach_count}</span>` : ''}${rowActions(e)}</div></td></tr>`).join('') || `<tr><td colspan="4" class="empty">${L('The queue is empty.', 'A fila está vazia.')}</td></tr>`}
      </tbody></table></div><div class="pager"><span>${L(`Page 1 of 1 (Total: ${queue.length})`, `Página 1 de 1 (Total: ${queue.length})`)}</span></div></div>
    <div class="card"><header><h2>${L('Extracted NF-e', 'NF-e Extraídas')}</h2><div class="btn-row"><label class="btn plain">${ico('filter')}<select id="inv-month" style="border:0;background:none;padding:0 4px;width:auto">${months.map((m) => `<option value="${m}" ${m === S.inv.month ? 'selected' : ''}>${m.slice(5)}/${m.slice(0, 4)}</option>`).join('')}</select></label>
      <button class="btn plain" data-file="api/invoices/export.xlsx">${ico('table')} ${L('Open in Excel', 'Abrir no Excel')}</button><button class="btn plain" data-finance>${ico('send')} ${L('Send to Finance', 'Enviar ao Financeiro')}</button></div></header>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Registered on', 'Registrada em')}</th><th>${L('Unit', 'Unidade')}</th><th>${L('Supplier', 'Fornecedor')}</th><th>NF</th><th class="num">${L('Amount', 'Valor')}</th><th>${L('Due date', 'Vencimento')}</th><th>${L('Description', 'Descrição')}</th><th>Status</th><th>${L('Attachments', 'Anexos')}</th><th>${L('PO no.', 'Nº Pedido')}</th><th>${L('Purchasing date', 'Data Compras')}</th><th>${L('Fiscal date', 'Data Fiscal')}</th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click" data-open="${r.email_id}"><td class="when">${fmtDT(r.extracted_at)}</td><td>${esc(r.unidade)}</td><td class="t1">${esc(r.fornecedor)}</td><td class="mono">${esc(r.numero)}</td>
        <td class="num val">${esc(r.valor)}</td><td class="when">${esc(r.vencimento) || '-'}</td><td class="muted small" title="${esc(r.description)}" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.description)}</td><td>${badge(r)}</td>
        <td>${r.sharepoint_url ? `<span class="small" style="color:var(--blue)">${ico('folder')} SharePoint</span>` : `<span class="chip gray tiny">${L('In progress', 'Em andamento')}</span>`}</td>
        <td class="val">${esc(r.po_number) || '-'}</td><td class="when">${r.purchasing_at ? fmtDT(r.purchasing_at) : '-'}</td><td class="when">${r.fiscal_at ? fmtDT(r.fiscal_at) : '-'}</td></tr>`).join('') || `<tr><td colspan="12" class="empty">${L('No invoices in this month.', 'Nenhuma nota neste mês.')}</td></tr>`}
      </tbody></table></div></div>`;
  },
};

/* ── history ────────────────────────────────────────────────────────────── */
PAGES.history = {
  async load() {
    const h = S.hist;
    const [tr, hist] = await Promise.all([api('GET', 'api/triage'), api('GET', `api/history?${qs({ filter: h.filter, page: h.page, category: h.category })}`)]);
    const seg = (k, lab, n) => `<button data-hfilter="${k}" class="${h.filter === k ? 'on' : ''}">${lab} <small>${n}</small></button>`;
    $('#page').innerHTML = `${head(L('Processing History', 'Histórico de Processamento'), L('E-mails and invoices processed and completed successfully', 'E-mails e faturas processados e finalizados com sucesso'))}
    <p class="faint small" style="margin:-10px 0 16px">${ico('info')} ${L('Note: deleted documents are kept for up to 7 days so they can be restored before the attachments are permanently cleaned.', 'Nota: documentos excluídos são mantidos por até 7 dias para eventual restauração antes da limpeza permanente dos anexos.')}</p>
    <div class="card"><header><h2>${L('Trash triage', 'Triagem da lixeira')}</h2><span class="faint small">${L('Click a category to see its e-mails', 'Clique numa categoria para ver os e-mails dela')}</span></header>
      <div class="metrics"><div class="metric"><small>${L('In the trash', 'Na lixeira')}</small><b>${tr.total}</b></div><div class="metric warn"><small>${L('No reason noted', 'Sem motivo anotado')}</small><b>${tr.unnoted_pct}%</b></div>
        <div class="metric"><small>${L('Need a decision', 'Pedem decisão')}</small><b>${tr.decision}</b></div><div class="metric"><small>${L('To review', 'Para revisar')}</small><b>${tr.review}</b></div></div>
      <div style="margin-top:12px">${tr.categories.map((c) => `<div class="cat-row ${h.category === c.key ? 'on' : ''}" data-cat="${c.key}"><span style="color:var(--${triageTone[c.tone] === 'gray' ? 'muted' : triageTone[c.tone]})">${ico(CAT_ICON[c.key], 'lg')}</span>
        <div style="min-width:0"><div class="t1" style="font-weight:600">${esc(c.label)}</div><div class="top">${c.top.map((t) => `${esc(t.sender)} ${t.n}`).join(', ')}</div></div><div class="n">${c.count}</div><div class="act"><span class="tag ${c.tone}" style="font-size:11px;text-transform:none;padding:3px 10px;margin:0">${esc(c.action)}</span></div></div>`).join('')}</div></div>
    <div class="card"><header><h2>${L('Processing History', 'Histórico de Processamento')}${h.category ? ` <span class="chip blue click" data-cat="">${esc(tr.categories.find((c) => c.key === h.category).label)} ✕</span>` : ''}</h2>
      <div class="seg">${seg('all', L('All', 'Todos'), hist.counts.all)}${seg('done', L('Completed', 'Concluídos'), hist.counts.done)}${seg('deleted', L('Deleted', 'Excluídos'), hist.counts.deleted)}</div></header>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Sender', 'Remetente')}</th><th>${L('Supplier', 'Fornecedor')}</th><th>${L('E-mail subject', 'Assunto do e-mail')}</th><th>Status</th><th>${L('Note', 'Observação')}</th><th>${L('Closed on', 'Concluído em')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
      ${hist.rows.map((r) => `<tr class="click" data-open="${r.id}"><td style="max-width:170px">${esc(r.sender)}</td><td class="t1">${esc(r.supplier) || '<span class="faint">—</span>'}</td>
        <td>${esc(r.subject)}${r.manual ? '<span class="tag green">MANUAL</span>' : ''}</td><td>${r.status === 'Deleted' ? `<span class="st gray">${L('Deleted', 'Excluído')}</span>` : `<span class="st green">${L('Success', 'Sucesso')}</span>`}</td>
        <td>${r.category ? `<span class="tag ${r.tone}" style="margin:0">${esc(r.category_label.split(':')[0])}</span> <span class="muted tiny">${esc(r.reason)}</span>` : '<span class="faint">-</span>'}</td><td class="when">${fmtDT(r.closed_at)}</td>
        <td class="center">${r.status === 'Deleted' ? `<button class="btn sm blue plain" data-act="restore" data-id="${r.id}" title="${L('Restore', 'Restaurar')}">${ico('refresh')}</button>` : '<span class="faint">-</span>'}</td></tr>`).join('')}</tbody></table></div>${pager(hist.page, hist.pages, hist.total, 'hist')}</div>`;
  },
};

/* ── month by month ─────────────────────────────────────────────────────── */
PAGES.months = {
  async load() {
    const m = await api('GET', 'api/months');
    const cell = (name, ym, s) => {
      const ic = { arrived: ico('check'), outside: ico('checks'), missed: ico('x'), soon: ico('info'), pending: '·', dash: '–' }[s];
      const click = ['missed', 'soon', 'pending', 'outside'].includes(s) ? `class="cell ${s} click" data-mark="${esc(name)}|${ym}" title="${L('Click to mark (or undo) “done outside”', 'Clique para marcar (ou desfazer) “feito por fora”')}"` : `class="cell ${s}"`;
      return `<span ${click}>${ic}</span>`;
    };
    $('#page').innerHTML = `<div class="card"><div class="pad"><h2 style="font-size:19px">${L('Month by month', 'Mês a mês')}</h2>
      <p class="muted small" style="margin:4px 0 0">${L('For each tracked supplier, whether each month’s invoice has reached the portal, by the due day set in Suppliers › Due dates. It is the same count as the calendar and the ticket service. Counted from', 'Para cada fornecedor acompanhado, se a nota de cada mês chegou ao portal, pelo dia de vencimento cadastrado em Fornecedores › Vencimentos. É a mesma conta do calendário e do service desk. Conta a partir de')} ${mShort(m.months[0])}.</p></div>
      <div class="mcards">${m.months.map((c) => { const k = m.cards[c]; const miss = k.total - k.arrived;
        const st = c < m.current ? (miss ? [`${L('missing', 'faltam')} ${miss}`, 'var(--red)'] : [L('all arrived', 'todos chegaram'), 'var(--green)']) : c === m.current ? (miss ? [`${L('missing', 'faltam')} ${miss}`, 'var(--red)'] : [L('all arrived', 'todos chegaram'), 'var(--green)']) : [`${miss} ${L('on the way', 'a caminho')}`, 'var(--muted)'];
        return `<div class="mcard ${c === m.current ? 'cur' : ''}"><small>${mShort(c)}${c === m.current ? ` · ${L('this month', 'este mês')}` : ''}</small><b>${k.arrived} ${L('of', 'de')} ${k.total}${k.outside ? ` <span class="faint small" style="font-weight:400">(${k.outside} ${L('outside', 'por fora')})</span>` : ''}</b><span class="small" style="color:${st[1]}">${st[0]}</span></div>`; }).join('')}</div>
      <div class="tbl-wrap"><table class="tbl grid-m"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th>${m.months.map((c) => `<th class="c">${mShort(c).toUpperCase()}</th>`).join('')}</tr></thead><tbody>
      ${m.rows.map((r) => `<tr><td><b>${esc(r.name)}</b> <span class="faint small">${L('day', 'dia')} ${r.day}</span></td>${m.months.map((c) => `<td class="c">${cell(r.name, c, r.cells[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <div class="legend-row"><span><span class="cell arrived">${ico('check')}</span> ${L('arrived', 'chegou')}</span><span><span class="cell missed">${ico('x')}</span> ${L('overdue, no invoice', 'venceu sem nota')}</span><span><span class="cell soon">${ico('info')}</span> ${L('due within 7 days', 'vence em até 7 dias')}</span><span><span class="cell pending">·</span> ${L('still on time', 'ainda no prazo')}</span><span><span class="cell outside">${ico('checks')}</span> ${L('done outside', 'feito por fora')}</span><span><span class="cell dash">–</span> ${L('on demand, no use', 'sob demanda, sem uso')}</span><span style="margin-left:auto">${L('Click a cell to mark (or undo) “done outside”.', 'Clique numa célula para marcar (ou desfazer) “feito por fora”.')}</span></div></div>`;
  },
};

/* ── manual upload ──────────────────────────────────────────────────────── */
let manualFiles = [];
const FIELDS = ['fornecedor', 'unidade', 'cnpj', 'numero', 'emissao', 'vencimento', 'competencia', 'valor', 'descricao'];
const REQUIRED = ['fornecedor', 'unidade', 'numero', 'valor'];
const FIELD_L = { fornecedor: ['Supplier', 'Fornecedor'], unidade: ['Unit', 'Unidade'], cnpj: ['Tax ID (CNPJ)', 'CNPJ'], numero: ['Invoice no.', 'Nº da NF'], emissao: ['Issue date', 'Emissão'], vencimento: ['Due date', 'Vencimento'], competencia: ['Reference', 'Competência'], valor: ['Amount (R$)', 'Valor (R$)'], descricao: ['Description', 'Descrição'] };
function recordEditor(records, docs, withRoute) {
  const docList = `<ul class="docs">${docs.map((d) => `<li><b>${esc(d.filename)}</b>: ${esc(d.doc_type)} (${esc(d.source)})${d.warnings.length ? ` <span class="issue">⚠ ${esc(d.warnings.join(' '))}</span>` : ''}</li>`).join('')}</ul>`;
  if (!records.length) return `${docList}<div class="warnbox">${L('No invoice (NF) recognized in these files.', 'Nenhuma nota fiscal (NF) reconhecida nestes arquivos.')}</div>`;
  return docList + records.map((r, i) => `<div class="record" data-rec="${i}">${r.warnings.length ? `<div class="warnbox">${esc(r.warnings.join(' '))}</div>` : ''}
    <div class="form-grid">${FIELDS.map((k) => `<label class="f ${k === 'descricao' ? 'wide' : ''}">${L(...FIELD_L[k])}<input type="text" name="${k}" value="${esc(r[k])}" class="${!r[k] && REQUIRED.includes(k) ? 'warn' : ''}"></label>`).join('')}
    ${withRoute ? `<label class="f" style="flex-direction:row;align-items:center;gap:8px"><input type="checkbox" name="direct_to_fiscal" style="width:auto" ${r.direct_to_fiscal ? 'checked' : ''}> ${L('Direct to Fiscal', 'Direto para o Fiscal')}</label>` : ''}</div>
    <input type="hidden" name="vendor_key" value="${esc(r.vendor_key)}"><input type="hidden" name="source" value="${esc(r.source)}"><input type="hidden" name="files" value="${esc(JSON.stringify(r.files))}"></div>`).join('');
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
function manualList() {
  $('#file-list').innerHTML = manualFiles.map((f, i) => `<div class="filebar"><span>${ico('file')} ${esc(f.name)} <span class="faint">(${Math.round(f.size / 1024)} KB)</span></span><button class="link-btn" data-rm-file="${i}">${ico('x')}</button></div>`).join('')
    || `<div class="filebar muted" style="justify-content:center;border-style:dashed">${L('No files in the queue', 'Nenhum arquivo na fila')}</div>`;
  $('#file-count').textContent = L(`${manualFiles.length} file(s)`, `${manualFiles.length} arquivo(s)`);
  $('#btn-extract').disabled = !manualFiles.length;
}
PAGES.manual = {
  async load() {
    const names = await api('GET', 'api/samples');
    $('#page').innerHTML = `${head(L('Manual Document Upload', 'Envio Manual de Documentos'), L('Upload invoices and boletos: the system separates them and sends one e-mail per supplier', 'Faça o upload de Notas Fiscais e Boletos: o sistema separa e envia um e-mail por fornecedor'))}
    <div class="card"><header><h2 class="muted" style="font-weight:600">${ico('upload')} ${L('Upload area', 'Área de Upload')}</h2><span class="faint small">● ${L('Waiting for files', 'Aguardando arquivos')}</span></header><div class="pad">
      <label class="dropzone" id="dropzone"><input type="file" id="manual-files" accept="application/pdf" multiple hidden><span class="plus">+</span><span>${L('Drag and drop here or click to select (PDF)', 'Arraste e solte aqui ou clique para selecionar (PDF)')}</span><span style="color:var(--blue)">+ ${L('Add several files', 'Adicionar vários arquivos')}</span></label>
      <p class="muted small">${L('No PDF at hand? Download a fictional sample, then drop it above:', 'Sem PDF à mão? Baixe um exemplo fictício e solte acima:')} ${names.map((n) => `<a class="chip click" href="#" data-file="api/samples/${n}">${esc(n)}</a>`).join(' ')}</p>
      <div class="btn-row" style="justify-content:space-between;margin-top:14px"><b>${L('Files in queue', 'Arquivos na Fila')}</b><span class="faint small" id="file-count"></span></div><div id="file-list"></div>
      <button class="btn blue" id="btn-extract" style="width:100%;justify-content:center;margin-top:12px;padding:11px">${ico('search')} ${L('Extract data and preview by supplier', 'Extrair Dados e Visualizar por Fornecedor')}</button>
      <div id="manual-preview" style="margin-top:16px"></div></div></div>`;
    manualFiles = [];
    manualList();
    const dz = $('#dropzone');
    const add = (list) => { manualFiles = manualFiles.concat([...list].filter((f) => f.name.toLowerCase().endsWith('.pdf'))).slice(0, 6); manualList(); };
    $('#manual-files').addEventListener('change', (ev) => { add(ev.target.files); ev.target.value = ''; });
    ['dragover', 'dragenter'].forEach((n) => dz.addEventListener(n, (ev) => { ev.preventDefault(); dz.classList.add('over'); }));
    ['dragleave', 'drop'].forEach((n) => dz.addEventListener(n, () => dz.classList.remove('over')));
    dz.addEventListener('drop', (ev) => { ev.preventDefault(); add(ev.dataTransfer.files); });
  },
};
async function manualExtract(btn) {
  const fd = new FormData();
  manualFiles.forEach((f) => fd.append('files', f));
  $('#manual-preview').innerHTML = `<p class="muted">${L('Reading PDFs…', 'Lendo PDFs…')}</p>`;
  try {
    const p = await api('POST', 'api/manual/preview', fd, true);
    $('#manual-preview').innerHTML = recordEditor(p.records, p.documents, false) + (p.records.length ? `
      <div class="btn-row" style="justify-content:flex-start;margin-top:10px"><label class="f" style="flex-direction:row;align-items:center;gap:8px">${L('Send to', 'Enviar para')}
        <select id="manual-dest" style="width:auto"><option value="purchasing">${L('Purchasing (needs a PO)', 'Compras (precisa de pedido)')}</option><option value="fiscal">${L('Fiscal directly', 'Direto ao Fiscal')}</option></select></label>
      <button class="btn blue" id="btn-manual-confirm">${ico('check')} ${L('Confirm and send', 'Confirmar e enviar')}</button></div>` : '');
    $('#btn-manual-confirm')?.addEventListener('click', (ev) => busy(ev.currentTarget, async () => {
      const r = await api('POST', 'api/manual/confirm', { token: p.token, destination: $('#manual-dest').value, records: collectRecords($('#manual-preview')) });
      toast(r.message, 'ok');
      manualFiles = []; manualList();
      $('#manual-preview').innerHTML = `<div class="infobox">${esc(r.message)} <a href="#" data-open="${r.email_id}">${L('Open', 'Abrir')}</a></div>`;
      notif = await api('GET', 'api/notifications');
    }));
  } catch (e) { $('#manual-preview').innerHTML = `<div class="warnbox">${esc(e.message)}</div>`; }
}

/* ── suppliers (key map + due dates) ────────────────────────────────────── */
let vendorsCache = [];
const SIT = {
  late: ['red', ['Overdue', 'Atrasada']], soon: ['orange', ['Due soon', 'A vencer']], received: ['green', ['Received', 'Recebida']], in_progress: ['blue', ['In progress', 'Em andamento']],
  on_time: ['gray', ['On time', 'No prazo']], on_demand: ['gray', ['On demand', 'Sob demanda']], outside_portal: ['gray', ['Outside the portal', 'Fora do portal']], paid: ['green', ['Paid', 'Paga']], done_outside: ['green', ['Done outside', 'Feito por fora']],
};
PAGES.suppliers = {
  async load() {
    const s = S.sup;
    const tabs = `<div class="tabs"><button data-suptab="keys" class="${s.tab === 'keys' ? 'on' : ''}">${L('Demo University (DU)', 'Universidade Demo (UD)')}</button><button data-suptab="due" class="${s.tab === 'due' ? 'on' : ''}">${ico('calendar')} ${L('Due dates', 'Vencimentos')}</button></div>`;
    let body = '';
    if (s.tab === 'keys') {
      vendorsCache = await api('GET', 'api/vendors');
      const q = s.q.toLowerCase();
      const rows = vendorsCache.filter((v) => !q || `${v.fornecedor} ${v.unidade} ${v.key}`.toLowerCase().includes(q));
      body = `<div class="toolbar"><input type="text" id="sup-q" value="${esc(s.q)}" placeholder="${L('Search by supplier or unit…', 'Pesquisar por fornecedor ou unidade...')}"><div class="btn-row"><label class="btn plain" for="ai-file">${ico('sparkle')} ${L('Register from PDF (local LLM)', 'Cadastrar a partir do PDF (LLM local)')}</label><input type="file" id="ai-file" accept="application/pdf" hidden><button class="btn blue" data-new-vendor>+ ${L('Add supplier', 'Adicionar Fornecedor')}</button></div></div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Key (map)', 'Chave (Mapa)')}</th><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Unit', 'Unidade')}</th><th>${L('Route', 'Rota')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${rows.map((v) => `<tr><td class="mono">${esc(v.key)}</td><td class="t1">${esc(v.fornecedor)}<div class="sub">${esc(v.cnpj)} · ${v.invoices} ${L('invoice(s)', 'nota(s)')}</div></td><td>${esc(v.unidade)}</td>
          <td>${v.direct_to_fiscal ? `<span class="tag blue" style="margin:0">${L('Direct Fiscal', 'Direto Fiscal')}</span>` : `<span class="tag orange" style="margin:0">${L('Purchasing first', 'Compras primeiro')}</span>`}</td>
          <td><div class="btn-row" style="justify-content:center"><button class="btn sm plain" data-edit-vendor="${esc(v.key)}">${L('Edit', 'Editar')}</button><button class="btn sm red plain" data-del-vendor="${esc(v.key)}">${L('Delete', 'Excluir')}</button></div></td></tr>`).join('')}</tbody></table></div>`;
    } else {
      const ym = s.month || (await api('GET', 'api/months')).current;
      s.month = ym;
      const d = await api('GET', `api/due?month=${ym}`);
      const q = s.q.toLowerCase();
      const rows = d.rows.filter((r) => !q || `${r.name} ${r.unit}`.toLowerCase().includes(q));
      const c = d.counts;
      const shift = (n) => { const y = +ym.slice(0, 4) * 12 + (+ym.slice(5) - 1) + n; return `${Math.floor(y / 12)}-${pad((y % 12) + 1)}`; };
      body = `<div class="toolbar"><input type="text" id="sup-q" value="${esc(s.q)}" placeholder="${L('Search by supplier or unit…', 'Pesquisar por fornecedor ou unidade...')}"><button class="btn blue" data-new-due>+ ${L('Add due date', 'Adicionar Vencimento')}</button></div>
        <div class="btn-row" style="justify-content:space-between;padding:14px 20px"><span class="nav-month"><button data-dmonth="${shift(-1)}">${ico('left')}</button><b>${mLong(ym)}</b><button data-dmonth="${shift(1)}">${ico('right')}</button></span>
          <span class="muted small" style="max-width:420px">${L('Day of the month on which each supplier’s invoice usually falls due. The portal crosses it with the invoices already received: the bell in the header warns if the invoice has not arrived. Mark paid or unpaid for the cycle.', 'Dia do mês em que a nota de cada fornecedor costuma vencer. O portal cruza isso com as notas já recebidas: o sino do cabeçalho avisa se a nota não chegou. Marque Paga ou Não paga no ciclo.')}</span>
          <span class="cal-chips"><span class="chip red">${L(`${c.late} overdue`, `${c.late} atrasadas`)}</span><span class="chip orange">${L(`${c.soon} due soon (≤ 7 days)`, `${c.soon} a vencer (≤ 7 dias)`)}</span><span class="chip green">${L(`${c.received} received`, `${c.received} recebidas`)}</span><span class="chip gray">${L(`${c.on_time} on time`, `${c.on_time} no prazo`)}</span><span class="chip gray">${L(`${c.on_demand} on demand`, `${c.on_demand} sob demanda`)}</span><span class="chip gray">${L(`${c.outside_portal} outside the portal`, `${c.outside_portal} fora do portal`)}</span></span></div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Day', 'Dia')}</th><th>${L('Unit', 'Unidade')}</th><th>${L('Destination', 'Destino')}</th><th>${L('Situation', 'Situação')}</th><th>${L('Note', 'Observação')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${rows.map((r) => { const [tone, lab] = SIT[r.state]; const late = ['late', 'soon'].includes(r.state);
          return `<tr><td class="t1">${esc(r.name)}</td><td class="mono t1">${r.day}</td><td>${esc(r.unit)}</td><td class="muted small">${esc(r.dest)}</td>
          <td><span class="tag ${tone}" style="margin:0">${L(...lab)}</span>${late ? `<div class="small muted" style="margin-top:3px;max-width:160px">${rel(r.delta)} (${fmtD(r.due)}) ${L('and the invoice has not arrived', 'e a nota ainda não chegou')}</div>` : ''}
            <div class="btn-row" style="justify-content:flex-start;margin-top:4px"><button class="chip click" data-paid="${esc(r.name)}|1">${L('Paid', 'Paga')}</button><button class="chip click" data-paid="${esc(r.name)}|0">${L('Unpaid', 'Não paga')}</button></div></td>
          <td class="muted small" style="max-width:260px">${esc(r.note)}</td><td><div class="btn-row" style="justify-content:center"><button class="btn sm plain" data-edit-due="${esc(r.name)}">${L('Edit', 'Editar')}</button><button class="btn sm red plain" data-del-due="${esc(r.name)}">${L('Delete', 'Excluir')}</button></div></td></tr>`; }).join('')}</tbody></table></div>`;
    }
    $('#page').innerHTML = `<div class="card"><div class="pad" style="padding-bottom:6px"><h2 style="font-size:19px">${L('Supplier management', 'Gerenciamento de Fornecedores')}</h2><p class="muted small" style="margin:4px 0 0">${L('Manage the supplier key base, their units and the due-date calendar.', 'Gerencie a base de chaves de fornecedores, suas unidades e o calendário de vencimentos.')}</p></div>${tabs}${body}</div>`;
    $('#ai-file')?.addEventListener('change', async (ev) => {
      const file = ev.target.files[0];
      if (!file) return;
      const fd = new FormData(); fd.append('file', file);
      await busy(null, () => aiRegister(fd));
      ev.target.value = '';
    });
  },
};
function vendorForm(v = {}, note = '') {
  const units = [...new Set(vendorsCache.map((x) => x.unidade))];
  openModal(`<div class="modal-head"><h2>${v.key && !note ? L('Edit supplier', 'Editar fornecedor') : L('New supplier', 'Novo fornecedor')}</h2><button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div>${note}
    <form id="vendor-form" class="form-grid">
      <label class="f">${L('Key (searched in the PDF text)', 'Chave (procurada no texto do PDF)')}<input type="text" name="key" value="${esc(v.key)}" required></label>
      <label class="f">${L('Supplier name', 'Nome do fornecedor')}<input type="text" name="fornecedor" value="${esc(v.fornecedor)}" required></label>
      <label class="f">${L('Unit', 'Unidade')}<input type="text" name="unidade" value="${esc(v.unidade)}" list="units" required><datalist id="units">${units.map((u) => `<option value="${esc(u)}">`).join('')}</datalist></label>
      <label class="f">${L('Tax ID (CNPJ)', 'CNPJ')}<input type="text" name="cnpj" value="${esc(v.cnpj)}"></label>
      <label class="f">${L('Sender domain', 'Domínio do remetente')}<input type="text" name="sender_domain" value="${esc(v.sender_domain)}"></label>
      <label class="f" style="flex-direction:row;align-items:center;gap:8px;margin-top:20px"><input type="checkbox" name="direct_to_fiscal" style="width:auto" ${v.direct_to_fiscal ? 'checked' : ''}> ${L('Goes directly to Fiscal', 'Vai direto para o Fiscal')}</label>
      <div class="wide btn-row"><button class="btn blue" type="submit">${L('Save rule', 'Salvar regra')}</button></div></form>`);
  $('#vendor-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const body = Object.fromEntries(f.entries());
    body.direct_to_fiscal = f.has('direct_to_fiscal');
    await busy(ev.submitter, async () => { await api('PUT', `api/vendors/${encodeURIComponent(body.key)}`, body); toast(L('Supplier rule saved.', 'Regra de fornecedor salva.'), 'ok'); closeModal(); refresh(); });
  });
}
async function aiRegister(form) {
  const r = await api('POST', 'api/vendors/ai-extract', form, true);
  const s = r.suggestion;
  if (!vendorsCache.length) vendorsCache = await api('GET', 'api/vendors');
  vendorForm({ key: s.chave_normalizada, fornecedor: s.nome_fantasia || s.razao_social, unidade: '', cnpj: '' },
    `<div class="infobox">${L('The local LLM suggested', 'O LLM local sugeriu')} (${r.mode === 'ollama' ? L('real model via Ollama', 'modelo real via Ollama') : L('mock, no model running', 'simulado, sem modelo rodando')}): <code>${esc(JSON.stringify(s))}</code>. ${L('City found:', 'Cidade encontrada:')} <b>${esc(s.unidade || '-')}</b>. ${L('Pick the unit and save.', 'Escolha a unidade e salve.')}</div>`);
}
function dueForm(r = {}) {
  openModal(`<div class="modal-head"><h2>${r.name ? L('Edit due date', 'Editar vencimento') : L('Add due date', 'Adicionar vencimento')}</h2><button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div>
    <form id="due-form" class="form-grid"><label class="f">${L('Supplier', 'Fornecedor')}<input type="text" name="name" value="${esc(r.name)}" placeholder="Ex: Locaweb" required ${r.name ? 'readonly' : ''}></label>
      <label class="f">${L('Due day (1-31)', 'Dia do vencimento (1-31)')}<input type="number" min="1" max="31" name="day" value="${esc(r.day)}" required></label>
      <label class="f">${L('Unit', 'Unidade')}<input type="text" name="unit" value="${esc(r.unit)}"></label><label class="f">${L('Destination (e-mail)', 'Destino (e-mail)')}<input type="text" name="dest" value="${esc(r.dest)}"></label>
      <label class="f wide">${L('Note', 'Observação')}<input type="text" name="note" value="${esc(r.note)}"></label>
      <label class="f" style="flex-direction:row;align-items:center;gap:8px"><input type="checkbox" name="track" style="width:auto" ${r.track !== false ? 'checked' : ''}> ${L('Track in the portal', 'Acompanhar no portal')}</label>
      <label class="f" style="flex-direction:row;align-items:center;gap:8px"><input type="checkbox" name="on_demand" style="width:auto" ${r.on_demand ? 'checked' : ''}> ${L('On demand (bills only when used)', 'Sob demanda (só fatura quando há uso)')}</label>
      <div class="wide btn-row"><button class="btn blue" type="submit">${L('Save', 'Salvar')}</button></div></form>`);
  $('#due-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const body = Object.fromEntries(f.entries());
    body.track = f.has('track'); body.on_demand = f.has('on_demand');
    await busy(ev.submitter, async () => { await api('PUT', `api/due/${encodeURIComponent(body.name)}`, body); toast(L('Saved.', 'Salvo.'), 'ok'); closeModal(); refresh(); });
  });
}

/* ── review + detail modal ──────────────────────────────────────────────── */
const modal = $('#modal');
let openDetailId = null;
function openModal(html) { $('#modal-body').innerHTML = html; if (!modal.open) modal.showModal(); }
function closeModal() { openDetailId = null; modal.close(); }
modal.addEventListener('click', (ev) => { if (ev.target === modal || ev.target.closest('[data-close]')) closeModal(); });
modal.addEventListener('close', () => { openDetailId = null; });
async function openReview(id) {
  const p = await api('GET', `api/emails/${id}/preview`);
  openModal(`<div class="modal-head"><div><h2>${L('Review and confirm', 'Revisar e confirmar')}</h2><p class="muted small">${L('Fix any field before anything moves on. Nothing is forwarded until you confirm.', 'Corrija qualquer campo antes de seguir. Nada é encaminhado até você confirmar.')}</p></div><button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div>
    <div id="review-body">${recordEditor(p.records, p.documents, true)}</div>${p.records.length ? `<div class="btn-row"><button class="btn blue" id="btn-confirm">${ico('check')} ${L('Confirm and forward', 'Confirmar e encaminhar')}</button></div>` : ''}`);
  $('#btn-confirm')?.addEventListener('click', (ev) => busy(ev.currentTarget, async () => {
    const r = await api('POST', `api/emails/${id}/confirm`, { records: collectRecords($('#review-body')) });
    toast(r.message, 'ok'); closeModal(); refresh();
  }));
}
async function openDetail(id) {
  const e = await api('GET', `api/emails/${id}`);
  openDetailId = id;
  const open = ['Pending', 'Missing invoice'].includes(e.status);
  openModal(`<div class="modal-head"><div><h2>${esc(e.subject)}</h2><div class="muted small">${esc(e.sender)} · ${fmtDT(e.received_at)}</div></div><div class="btn-row">${badge(e)}<button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div></div>
    ${e.issue ? `<div class="warnbox">${esc(e.issue)}</div>` : ''}
    <dl class="kv"><dt>${L('Mailbox folder', 'Pasta na caixa')}</dt><dd><code>${esc(e.folder)}</code> · ${e.read ? L('read', 'lido') : L('unread', 'não lido')}</dd>
      <dt>${L('Origin', 'Origem')}</dt><dd>${e.process_type === 'Manual' ? L('Manual upload', 'Upload manual') : L('Automatic (mailbox)', 'Automática (caixa de e-mail)')}</dd>
      ${e.po_number ? `<dt>${L('PO number', 'Nº do pedido')}</dt><dd class="val">${esc(e.po_number)}</dd>` : ''}${e.sharepoint_url ? `<dt>SharePoint</dt><dd><code>${esc(decodeURIComponent(e.sharepoint_url))}</code></dd>` : ''}
      <dt>${L('Attachments', 'Anexos')}</dt><dd>${e.attachments.map((a) => `<a href="#" data-file="api/emails/${e.id}/attachments/${encodeURIComponent(a.filename)}">${esc(a.filename)}</a>${a.scanned ? ` <span class="tag gray">OCR</span>` : ''}`).join('<br>') || '-'}${e.has_package ? `<br><a href="#" data-file="api/emails/${e.id}/package.pdf">${L('Print package (cover + invoice + boleto)', 'Pacote para imprimir (capa + nota + boleto)')}</a>` : ''}</dd>
      ${e.body ? `<dt>${L('Body', 'Corpo')}</dt><dd class="small">${esc(e.body)}</dd>` : ''}</dl>
    ${e.invoices.length ? `<h3>${L('Extracted invoices', 'Notas extraídas')}</h3><div class="tbl-wrap card"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Unit', 'Unidade')}</th><th>NF</th><th>${L('Due date', 'Vencimento')}</th><th class="num">${L('Amount', 'Valor')}</th></tr></thead><tbody>${e.invoices.map((r) => `<tr><td>${esc(r.fornecedor)}</td><td>${esc(r.unidade)}</td><td>${esc(r.numero)}</td><td>${esc(r.vencimento)}</td><td class="num val">R$ ${esc(r.valor)}</td></tr>`).join('')}</tbody></table></div>` : ''}
    <h3>${L('Timeline', 'Linha do tempo')}</h3><ul class="timeline">${e.timeline.map((x) => `<li><b>${esc(statusLabel(x.status))}</b> · <span class="muted small">${fmtDT(x.ts)} · ${esc(x.folder)}</span><div>${esc(x.note)}</div></li>`).join('')}</ul>
    <div class="btn-row" style="justify-content:flex-start;margin-top:12px">${open || e.status === 'Deleted' || e.status !== 'Completed' ? rowActions(e) : ''}</div>`);
}

/* ── global click handling ──────────────────────────────────────────────── */
let monitorOn = false, monitorTimer = null;
function setMonitor(on) {
  monitorOn = on;
  api('POST', `api/monitor/${on ? 'start' : 'stop'}`).catch(() => {});
  if (on && !monitorTimer) {
    monitorTimer = setInterval(async () => { try { await api('POST', 'api/inbox/fetch'); await api('POST', 'api/queue/process'); refresh(); } catch (_) { /* next tick */ } }, 20000);
  } else if (!on && monitorTimer) { clearInterval(monitorTimer); monitorTimer = null; }
}
document.addEventListener('change', (ev) => {
  if (ev.target.id === 'monitor-toggle') { setMonitor(ev.target.checked); toast(L(ev.target.checked ? 'Auto-monitor on: the inbox is read every 20 s.' : 'Auto-monitor off.', ev.target.checked ? 'Monitor automático ligado: a caixa é lida a cada 20 s.' : 'Monitor automático desligado.')); }
  else if (ev.target.id === 'inv-month') { S.inv.month = ev.target.value; refresh(); }
});
document.addEventListener('input', (ev) => { if (ev.target.id === 'sup-q') { S.sup.q = ev.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(refresh, 250); } });
document.addEventListener('click', async (ev) => {
  const el = ev.target.closest('[data-act],[data-review],[data-open],[data-ai-email],[data-edit-vendor],[data-del-vendor],[data-file],[data-pg],[data-hfilter],[data-cat],[data-mark],[data-suptab],[data-dmonth],[data-paid],[data-edit-due],[data-del-due],[data-new-due],[data-new-vendor],[data-process-all],[data-read-now],[data-refresh],[data-finance],[data-hide-guide],[data-rm-file],#btn-extract,#btn-reset');
  if (!el) return;
  const d = el.dataset;
  if (d.file) { ev.preventDefault(); ev.stopPropagation(); await busy(el.tagName === 'BUTTON' ? el : null, () => openFile(d.file)); }
  else if (d.act) {
    ev.stopPropagation();
    await busy(el, async () => {
      const r = await api('POST', `api/emails/${d.id}/actions/${d.act}`);
      toast(r.message, ['Pending', 'Missing invoice'].includes(r.status) ? '' : 'ok');
      if (modal.open) await openDetail(d.id);
      await refresh();
    });
  } else if (d.review) { ev.stopPropagation(); await busy(el, () => openReview(d.review)); }
  else if (d.aiEmail) { ev.stopPropagation(); const fd = new FormData(); fd.append('email_id', d.aiEmail); await busy(el, () => aiRegister(fd)); }
  else if (d.editVendor) vendorForm(vendorsCache.find((v) => v.key === d.editVendor));
  else if (d.newVendor !== undefined) vendorForm();
  else if (d.delVendor) { if (window.confirm(`${L('Remove', 'Remover')} ${d.delVendor}?`)) await busy(el, async () => { await api('DELETE', `api/vendors/${encodeURIComponent(d.delVendor)}`); refresh(); }); }
  else if (d.open) { if (ev.target.closest('button') && !ev.target.closest('.drop-menu')) return; ev.preventDefault(); $('#search-menu') && ($('#search-menu').hidden = true); await busy(null, () => openDetail(d.open)); }
  else if (d.pg) { const [k, n] = d.pg.split(':'); if (k === 'hist') { S.hist.page = +n; refresh(); } else if (window.pagerHook) window.pagerHook(k, +n); }
  else if (d.hfilter) { S.hist.filter = d.hfilter; S.hist.page = 1; refresh(); }
  else if (d.cat !== undefined) { S.hist.category = S.hist.category === d.cat ? '' : d.cat; S.hist.filter = S.hist.category ? 'deleted' : S.hist.filter; S.hist.page = 1; refresh(); }
  else if (d.mark) { const [name, month] = d.mark.split('|'); await api('POST', 'api/months/mark', { name, month }); refresh(); }
  else if (d.suptab) { S.sup.tab = d.suptab; S.sup.q = ''; refresh(); }
  else if (d.dmonth) { S.sup.month = d.dmonth; refresh(); }
  else if (d.paid) { const [name, v] = d.paid.split('|'); await api('POST', `api/due/${encodeURIComponent(name)}/paid`, { month: S.sup.month, paid: v === '1' }); refresh(); }
  else if (d.editDue) { const cur = (await api('GET', `api/due?month=${S.sup.month}`)).rows.find((r) => r.name === d.editDue); dueForm(cur); }
  else if (d.newDue !== undefined) dueForm();
  else if (d.delDue) { if (window.confirm(`${L('Remove', 'Remover')} ${d.delDue}?`)) { await api('DELETE', `api/due/${encodeURIComponent(d.delDue)}`); refresh(); } }
  else if (d.processAll !== undefined) await busy(el, async () => { const r = await api('POST', 'api/queue/process'); toast(r.message, 'ok'); await refresh(); });
  else if (d.readNow !== undefined) await busy(el, async () => { const r = await api('POST', 'api/inbox/fetch'); toast(r.message); await refresh(); });
  else if (d.refresh !== undefined) refresh();
  else if (d.finance !== undefined) await busy(el, async () => { const r = await api('POST', 'api/finance/send'); toast(r.message, 'ok'); });
  else if (d.hideGuide !== undefined) { S.guide = false; refresh(); }
  else if (d.rmFile !== undefined) { manualFiles.splice(+d.rmFile, 1); manualList(); }
  else if (el.id === 'btn-extract') await busy(el, () => manualExtract(el));
  else if (el.id === 'btn-reset') { if (!window.confirm(L('Restart the demo with fresh sample data?', 'Reiniciar a demo com dados de exemplo novos?'))) return; await api('POST', 'api/reset'); toast(L('Demo restarted.', 'Demo reiniciada.'), 'ok'); refresh(); }
});
