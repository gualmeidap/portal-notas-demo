/* Portal Notas demo: descriptions, report, settings, logs, sent e-mails. */

/* ── descriptions ───────────────────────────────────────────────────────── */
S.desc = { tab: 'map', group: 'A', q: '' };
PAGES.descriptions = {
  async load() {
    const s = S.desc;
    const d = await api('GET', `api/descriptions?group=${s.group}`);
    const tabs = `<div class="tabs">${[['map', ['Mapping (Values)', 'Mapeamento (Valores)']], ['norm', ['Normalization (Names)', 'Normalização (Nomes)']], ['pattern', ['Description pattern (Purchasing)', 'Padrão da descrição (Compras)']]]
      .map(([k, lab]) => `<button data-desctab="${k}" class="${s.tab === k ? 'on' : ''}">${L(...lab)}</button>`).join('')}</div>`;
    let body = '';
    if (s.tab === 'map') {
      const q = s.q.toLowerCase();
      const rows = d.mapping.filter((r) => !q || r.key.toLowerCase().includes(q));
      body = `<div class="toolbar"><input type="text" id="desc-q" value="${esc(s.q)}" placeholder="${L('Search key…', 'Pesquisar chave...')}"><button class="btn blue" data-new-map>+ ${L('New mapping', 'Novo Mapeamento')}</button></div>
        <div class="subtabs"><button data-descgroup="A" class="${s.group === 'A' ? 'on' : ''}">${L('Demo University (DU)', 'Universidade Demo (UD)')}</button><button data-descgroup="B" class="${s.group === 'B' ? 'on' : ''}">${L('Partner Group (Others)', 'Grupo Parceiro (Outras)')}</button></div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Supplier key', 'Chave do fornecedor')}</th><th>${L('Default description', 'Descrição padrão (default)')}</th><th class="center">${L('Rules (values)', 'Regras (valores)')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${rows.map((r) => `<tr><td class="t1">${esc(r.key)}</td><td>${esc(r.default)}</td><td class="center">${L(`${r.rules.length} rule(s)`, `${r.rules.length} regras`)} <span style="color:var(--orange)">+ ${L('sub-states', 'sub-estados')}</span></td>
          <td><div class="btn-row" style="justify-content:center"><button class="btn sm plain" data-edit-map="${esc(r.key)}">${ico('edit')}</button><button class="btn sm red plain" data-del-map="${esc(r.key)}">${ico('trash')}</button></div></td></tr>`).join('')}</tbody></table></div>`;
      window.descCache = d;
    } else if (s.tab === 'norm') {
      body = `<div class="toolbar"><span class="muted small">${L('When the text on the left is found in the supplier name, the portal uses the name on the right everywhere (queue, reports, spreadsheet).', 'Quando o texto da esquerda aparece no nome do fornecedor, o portal usa o nome da direita em todo lugar (fila, relatórios, planilha).')}</span></div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Text found', 'Texto encontrado')}</th><th>${L('Normalized name', 'Nome normalizado')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${d.normalization.map((r) => `<tr><td class="mono">${esc(r.pattern)}</td><td class="t1">${esc(r.name)}</td><td class="center"><button class="btn sm red plain" data-del-norm="${esc(r.pattern)}">${ico('trash')}</button></td></tr>`).join('')}
        <tr><td><input type="text" id="norm-pat" placeholder="EMPRESA EXEMPLO LTDA"></td><td><input type="text" id="norm-name" placeholder="Empresa Exemplo"></td><td class="center"><button class="btn sm blue" data-add-norm>+ ${L('Add', 'Adicionar')}</button></td></tr></tbody></table></div>`;
    } else {
      body = `<div class="pad"><p class="muted small" style="margin-top:0">${L('Template of the description sent to Purchasing for every invoice. Placeholders:', 'Modelo da descrição enviada ao Compras para cada nota. Campos:')} <code>{numero}</code> <code>{descricao}</code> <code>{fornecedor}</code> <code>{vencimento}</code> <code>{unidade}</code></p>
        <label class="f">${L('Pattern', 'Padrão')}<input type="text" id="pattern" value="${esc(d.pattern)}"></label>
        <div class="infobox" style="margin-top:12px"><b>${L('Preview', 'Prévia')}:</b> <span class="mono">${esc(d.sample)}</span></div>
        <button class="btn blue" data-save-pattern>${L('Save pattern', 'Salvar padrão')}</button></div>`;
    }
    $('#page').innerHTML = `<div class="card"><div class="pad" style="padding-bottom:6px"><h2 style="font-size:19px">${L('Description management', 'Gestão de Descrições')}</h2><p class="muted small" style="margin:4px 0 0">${L('Configure the description mapping and the name normalization.', 'Configure o mapeamento de descrições e normalização de nomes.')}</p></div>${tabs}${body}</div>`;
  },
};
function mapForm(cur) {
  const rules = (cur && cur.rules) || [];
  openModal(`<div class="modal-head"><h2>${cur ? L('Edit mapping', 'Editar mapeamento') : L('New mapping', 'Novo mapeamento')}</h2><button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div>
    <form id="map-form" class="form-grid"><label class="f">${L('Supplier key', 'Chave do fornecedor')}<input type="text" name="key" value="${esc(cur ? cur.key : '')}" required ${cur ? 'readonly' : ''}></label>
      <label class="f">${L('Default description', 'Descrição padrão')}<input type="text" name="default" value="${esc(cur ? cur.default : '')}" required></label>
      <div class="wide"><b class="small">${L('Rules by amount (optional)', 'Regras por valor (opcional)')}</b><p class="muted tiny" style="margin:2px 0 8px">${L('If the invoice amount falls in the range, this description is used instead of the default.', 'Se o valor da nota cair na faixa, esta descrição vale no lugar da padrão.')}</p></div>
      ${[0, 1, 2].map((i) => `<label class="f">${L('From (R$)', 'De (R$)')}<input type="number" step="0.01" name="min${i}" value="${esc(rules[i] ? rules[i].min : '')}"></label><label class="f">${L('Up to (R$, empty = no limit)', 'Até (R$, vazio = sem limite)')}<input type="number" step="0.01" name="max${i}" value="${esc(rules[i] && rules[i].max != null ? rules[i].max : '')}"></label><label class="f wide">${L('Description', 'Descrição')}<input type="text" name="text${i}" value="${esc(rules[i] ? rules[i].text : '')}"></label>`).join('')}
      <div class="wide btn-row"><button class="btn blue" type="submit">${L('Save', 'Salvar')}</button></div></form>`);
  $('#map-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target).entries());
    const rs = [0, 1, 2].map((i) => ({ min: f[`min${i}`], max: f[`max${i}`], text: f[`text${i}`] })).filter((r) => r.text);
    await busy(ev.submitter, async () => { await api('PUT', `api/descriptions/${S.desc.group}/${encodeURIComponent(f.key)}`, { default: f.default, rules: rs }); toast(L('Saved.', 'Salvo.'), 'ok'); closeModal(); refresh(); });
  });
}

/* ── report ─────────────────────────────────────────────────────────────── */
S.rep = { group: 'A', who: 'suppliers', kind: '', q: '', open: '' };
const KIND_ICON = { both: ['green', ['NF + boleto', 'NF + boleto']], nf: ['blue', ['NF only', 'só NF']], boleto: ['orange', ['boleto only', 'só boleto']], none: ['gray', ['no PDF', 'sem PDF']] };
PAGES.report = {
  async load() {
    const r = S.rep;
    const [dl, sn, ty] = await Promise.all([api('GET', 'api/report/deadlines'), api('GET', `api/report/senders?group=${r.group}`), api('GET', `api/report/types?${qs({ kind: r.kind, q: r.q })}`)]);
    const dayOf = (iso) => +iso.slice(8, 10);
    const dueTxt = (m) => `${mShort(m.ym)} · ${L('due', 'vence')} ${fmtD(m.due)} (${m.delta < 0 ? `<span style="color:var(--red)">${L(`overdue ${-m.delta} days`, `venceu há ${-m.delta} dias`)}</span>` : m.delta === 0 ? L('today', 'hoje') : L(`in ${m.delta} days`, `em ${m.delta} dias`)})`;
    const rowsDl = dl.rows.map((x) => {
      const exp = dayOf(x.months[0].nf.expected);
      return `<tr><td><div class="t1">${esc(x.name)}</div><div class="faint small">${L('due day', 'vence dia')} ${x.day}</div></td>
        <td class="small"><b>NF:</b> ${x.team_informed ? `${L('around day', 'por volta do dia')} ${exp} <span class="faint">(${L('provided by the team', 'informado pela equipe')})</span>` : `~${x.nf_offset} ${L('days before the due date', 'dias antes do vencimento')} <span class="faint">(${L('from', 'de')} -${x.nf_offset + 2} ${L('to', 'a')} ${x.nf_offset + 2})</span>, ${L('around day', 'por volta do dia')} ${exp}`}<br><b>${L('Boleto', 'Boleto')}:</b> ${L('together with the NF', 'junto com a NF')}</td>
        <td>${x.months.map((m) => `<div class="rep-month">${dueTxt(m)}</div><div class="rep-chips">${m.nf.arrived
          ? `<span class="chip green">✓ ${L('NF posted', 'NF lançada')} · ${L('no.', 'nº')} ${esc(m.nf.number)} · R$ ${money(m.nf.amount)} · ${L('issued', 'emitida')} ${fmtD(m.nf.issued)}</span><span class="chip blue">${L('boleto arrived', 'boleto chegou')} ${fmtD(m.boleto.at)} · R$ ${money(m.boleto.amount)} · ${L('due', 'vence')} ${fmtD(m.boleto.due)} (${rel(m.boleto.delta)})</span>`
          : `<span class="chip ${m.nf.late ? 'red' : 'gray'}">${L('NF not arrived', 'NF não chegou')} · ${L('expected', 'prevista')} ${fmtD(m.nf.expected)} (${L('until', 'até')} ${fmtD(m.nf.until)})</span><span class="chip gray">${L('boleto not arrived', 'boleto não chegou')}</span>`}</div>`).join('')}</td>
        <td class="small">${x.last ? `NF ${esc(x.last.number)} · ${rel(x.last.delta)} <span class="chip ${x.last.tag === 'done' ? 'green' : x.last.tag === 'in_queue' ? 'orange' : 'blue'} tiny">${{ done: L('done', 'já foi'), in_queue: L('in queue', 'na fila'), in_workflow: L('in Purchasing/Fiscal', 'no Compras/Fiscal') }[x.last.tag]}</span>` : '-'}${x.outside ? `<div><span class="chip dashed tiny">${L('1 outside the portal', '1 fora do portal')}</span></div>` : ''}</td></tr>`;
    }).join('');
    const list = sn[r.who];
    const rowsSn = list.map((x) => { const [tone, lab] = KIND_ICON[x.kind]; const open = r.open === x.sender;
      return `<tr class="click" data-expand="${esc(x.sender)}"><td>${ico(open ? 'down' : 'right')}</td><td class="t1">${esc(x.sender)}</td><td class="center">${x.emails}</td><td class="center">${x.nf}</td><td class="center">${x.boleto}</td><td><span class="chip ${tone}">${L(...lab)}</span> <span class="muted small">${{ attachment: L('PDF attachment', 'PDF anexo'), link: L('link in the body', 'link no corpo'), none: L('no document', 'sem documento') }[x.how]}</span></td></tr>${open ? `<tr><td></td><td colspan="5" id="sender-detail" class="small muted">…</td></tr>` : ''}`; }).join('');
    const typeChips = Object.entries(ty.counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<span class="chip click ${r.kind === k ? 'blue' : ''}" data-kind="${k}">${k === 'invoice' ? L('Real invoice', 'Nota de verdade') : esc(ty.labels[k] || k)} ${n}</span>`).join(' ');
    $('#page').innerHTML = `<div class="card"><header style="display:block"><h2 style="font-size:19px">${L('Deadlines by supplier', 'Prazos por fornecedor')}</h2><p class="muted small" style="margin:4px 0 0">${L('When each supplier usually sends the invoice and the boleto (read from the PDFs in the e-mails), whether this month’s invoice has arrived (and was posted in the portal) or is expected, and the status of the latest invoices.', 'Quando cada fornecedor costuma mandar a nota e o boleto (lido dos PDFs dos e-mails), se a nota deste mês já chegou no e-mail (e se foi lançada no portal) ou quando está prevista, e a situação das últimas notas.')}</p><p class="faint tiny" style="margin:3px 0 0">${L(`Pattern read from ${dl.read_emails} e-mails`, `Padrão lido de ${dl.read_emails} e-mails`)}</p></header>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Sending pattern', 'Padrão de envio')}</th><th>${L('This month and next', 'Este mês e o próximo')}</th><th>${L('Latest invoices', 'Últimas notas')}</th></tr></thead><tbody>${rowsDl}</tbody></table></div></div>
    <div class="card"><header style="display:block"><h2 style="font-size:19px">${L('Supplier report', 'Relatório de Fornecedores')}</h2><p class="muted small" style="margin:4px 0 0">${L('What each supplier sends by e-mail: invoice, boleto, both or nothing attached. Click a row to see the e-mails one by one.', 'O que cada fornecedor manda por e-mail: nota fiscal, boleto, os dois juntos ou nada anexado. Clique numa linha para ver os e-mails um a um.')}</p></header>
      <div class="tabs"><button data-repgroup="A" class="${r.group === 'A' ? 'on' : ''}">${L('Demo University (DU)', 'Universidade Demo (UD)')}</button><button data-repgroup="B" class="${r.group === 'B' ? 'on' : ''}">${L('Partner Group (Others)', 'Grupo Parceiro (Outras)')}</button></div>
      <div class="btn-row" style="justify-content:space-between;padding:12px 20px"><span class="seg"><button data-repwho="suppliers" class="${r.who === 'suppliers' ? 'on' : ''}">${L('Suppliers', 'Fornecedores')} <small>${sn.suppliers.length}</small></button><button data-repwho="others" class="${r.who === 'others' ? 'on' : ''}">${L('Other senders', 'Outros remetentes')} <small>${sn.others.length}</small></button></span>
        <span class="legend-row" style="padding:0"><span><i class="chip green" style="padding:0 6px">&nbsp;</i> NF + ${L('boleto', 'boleto')}</span><span><i class="chip blue" style="padding:0 6px">&nbsp;</i> ${L('NF only', 'só NF')}</span><span><i class="chip orange" style="padding:0 6px">&nbsp;</i> ${L('boleto only', 'só boleto')}</span><span><i class="chip gray" style="padding:0 6px">&nbsp;</i> ${L('no PDF', 'sem PDF')}</span></span></div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th></th><th>${L('Supplier / sender', 'Fornecedor / Remetente')}</th><th class="center">E-mails</th><th class="center">${L('Invoice (NF)', 'Nota Fiscal')}</th><th class="center">Boleto</th><th>${L('How it arrives', 'Como chega')}</th></tr></thead><tbody>${rowsSn || `<tr><td colspan="6" class="empty">${L('No senders.', 'Nenhum remetente.')}</td></tr>`}</tbody></table></div></div>
    <div class="card"><header style="display:block"><h2 style="font-size:19px">${L('E-mail types', 'Tipos de e-mail')}</h2><p class="muted small" style="margin:4px 0 0">${L('Everything that came into the portal, separated by what it is: real invoice, boleto only, payment confirmation, reminder, newsletter, ticket… Each row says which rule decided. Click a type to filter.', 'Tudo que entrou no portal, separado pelo que é: nota de verdade, só boleto, confirmação de pagamento, cobrança, newsletter, chamado etc. Cada linha diz a regra que decidiu. Clique num tipo para filtrar.')}</p><p class="faint tiny" style="margin:3px 0 0">${L('AI reading: mock classifier (a local model in production).', 'Leitura por IA: classificador simulado (modelo local em produção).')}</p></header>
      <div class="toolbar"><div>${typeChips}${r.kind ? ` <span class="chip click" data-kind="">✕ ${L('clear', 'limpar')}</span>` : ''}</div><input type="text" id="type-q" value="${esc(r.q)}" placeholder="${L('Search sender or subject…', 'Buscar remetente ou assunto...')}"></div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Arrived', 'Chegou')}</th><th>${L('Sender / subject', 'Remetente / assunto')}</th><th>${L('Type (rule · AI)', 'Tipo (regra · IA)')}</th><th>${L('Why', 'Por quê')}</th><th>Status</th></tr></thead><tbody>
      ${ty.rows.map((x) => `<tr class="click" data-open="${x.id}"><td class="when">${fmtDT(x.received_at)}</td><td><div class="t1">${esc(x.sender)}</div><div class="sub">${esc(x.subject)}</div></td><td><span class="chip ${x.type === 'invoice' ? 'green' : 'gray'}">${esc(x.type_label)}</span> <span class="tag ${x.source === 'ai' ? 'violet' : 'gray'}">${x.source === 'ai' ? 'IA' : L('rule', 'regra')}</span></td><td class="muted small">${esc(x.why)}</td><td>${badge({ status: x.status })}</td></tr>`).join('')}</tbody></table></div>
      <div class="pager"><span>${L(`Showing ${ty.rows.length} of ${ty.total}`, `Mostrando ${ty.rows.length} de ${ty.total}`)}</span></div></div>`;
    if (r.open) {
      const el = $('#sender-detail');
      const items = await api('GET', `api/report/sender?${qs({ name: r.open })}`);
      if (el) el.innerHTML = items.map((e) => `<div style="padding:3px 0"><a href="#" data-open="${e.id}">${esc(e.subject)}</a> <span class="faint">· ${fmtDT(e.received_at)}</span> ${badge({ status: e.status })}</div>`).join('') || '-';
    }
  },
};

/* ── settings ───────────────────────────────────────────────────────────── */
let cfg = null;
const tagsBox = (id, list, ph) => `<div class="tags-in" data-tags="${id}">${list.map((x) => `<span class="chip">${esc(x)}<button data-tag-rm="${id}|${esc(x)}">×</button></span>`).join('')}<input type="text" data-tag-in="${id}" placeholder="${ph}"></div>`;
PAGES.settings = {
  async load() {
    cfg = await api('GET', 'api/settings');
    const po = cfg.settings, rm = cfg.removal, g = cfg.tickets, tm = cfg.teams;
    const supOpts = (sel) => `<option value="">${L('Choose…', 'Escolha...')}</option>${cfg.suppliers.map((s) => `<option ${s === sel ? 'selected' : ''}>${esc(s)}</option>`).join('')}`;
    const sect = (icon, tone, title, sub, inner, extra = '') => `<div class="card"><header><div class="btn-row" style="gap:12px"><span class="sect-icon ${tone}">${ico(icon, 'lg')}</span><div><h2>${title}</h2><div class="muted small">${sub}</div></div></div>${extra}</header>${inner}</div>`;
    $('#page').innerHTML = `<div style="max-width:1080px;margin:0 auto">
      <div class="pill" style="width:100%;border-radius:10px;justify-content:flex-start;margin-bottom:16px">${ico('info')} ${L('You are in', 'Você está em')} <b class="mono">${esc(po.mailbox)}</b> · <span class="muted">${L('Technical', 'Técnico')}</span><span class="faint small" style="margin-left:auto">${L('Filters and screens only show this mailbox.', 'Filtros e telas mostram só esta caixa.')}</span></div>
      ${sect('send', 'orange', L('Purchasing and Fiscal sectors', 'Setores Compras e Fiscal'), L('Who each mailbox sends the invoices to, and whose replies are recognized', 'Para quem cada caixa envia as notas, e de quem as respostas são reconhecidas'),
      `<div class="pad"><div class="grid-2">${[['purchasing', L('Purchasing', 'Compras'), L('Step 1: checks the invoice and returns it with the PO number.', '1ª etapa: confere a nota e devolve com o nº do pedido.'), ''], ['fiscal', 'Fiscal', L('Step 2: receives Purchasing’s reply and posts the invoice.', '2ª etapa: recebe a resposta do Compras e lança a nota.'), 'fiscal']].map(([k, lab, sub, cls]) => `<div class="sector ${cls}"><b>${lab}</b><div class="muted small" style="margin-bottom:10px">${sub}</div>
        <label class="f">${L('Receives the invoices', 'Recebe as notas')}<input type="text" id="sec-${k}" value="${esc(po[k].receives)}"></label><label class="f" style="margin-top:10px">${L(`Also recognized as a reply from ${lab}`, `Também reconhecidos como resposta do ${lab}`)}${tagsBox(`sec-${k}`, po[k].also, L('add…', 'adicionar...'))}</label></div>`).join('')}</div>
        <p class="faint small">${L('The address under “Receives the invoices” already counts as the sector’s reply. Use the recognized list for other addresses that also reply (e.g. a colleague answering from a personal mailbox).', 'O endereço em “Recebe as notas” já conta como resposta do setor. Use a lista de reconhecidos para outros endereços que também respondem (ex.: um colega respondendo da caixa pessoal).')}</p>
        <div class="btn-row"><button class="btn plain" data-cfg-undo>${L('Undo', 'Desfazer')}</button><button class="btn blue" data-save-sectors>${ico('check')} ${L('Save changes', 'Salvar alterações')}</button></div></div>`, `<span class="tag green" style="font-size:11px">${L('Production', 'Produção')}</span>`)}
      ${sect('send', 'red', L('Direct send by supplier', 'Envio Direto por Fornecedor'), L('Suppliers whose invoice skips Purchasing and Fiscal and goes straight to one person (e.g. whoever pays)', 'Fornecedores cuja nota pula Compras e Fiscal e vai direto para uma pessoa (ex.: quem paga)'),
      `<div class="rule-box"><p><b>${L('How it leaves', 'Como sai')}:</b> ${L('<i>Process and send</i> reads the invoice and sends the table; <i>Forward the e-mail</i> sends the original untouched, without reading the PDF (for protected PDFs). In the queue those e-mails get a Forward button instead of Process.', '<i>Processar e enviar</i> lê a nota e manda a tabela; <i>Encaminhar o e-mail</i> manda o original como está, sem ler o PDF (para PDFs protegidos). Na fila, esses e-mails ganham o botão Encaminhar no lugar de Processar.')}</p>
        <p><b>${L('After sending', 'Depois de enviar')}:</b> ${L('<i>Close as Completed</i> ends the record at once; <i>Wait for the cover</i> keeps the package in Awaiting Cover until the person who pays replies with the cover, then it goes to Ready to print.', '<i>Fecha como Concluído</i> encerra o registro na hora; <i>Espera a capa de volta</i> deixa o pacote em Aguardando Capa até quem paga responder com a capa, aí vai para Pronto para Impressão.')}</p></div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Recipient (e-mail)', 'Destinatário (e-mail)')}</th><th>${L('How it leaves', 'Como sai')}</th><th>${L('After sending', 'Depois de enviar')}</th><th>${L('Note', 'Observação')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${cfg.direct_rules.map((r) => `<tr><td class="t1">${esc(r.supplier)}</td><td class="mono small">${esc(r.dest)}</td><td>${r.how === 'forward' ? L('Forward the e-mail', 'Encaminhar o e-mail') : L('Process and send', 'Processar e enviar')}</td><td>${r.after === 'wait_cover' ? L('Wait for the cover', 'Espera a capa de volta') : L('Close as Completed', 'Fecha como Concluído')}</td><td class="muted small">${esc(r.note)}</td><td class="center"><button class="btn sm red plain" data-del-direct="${r.id}">${ico('trash')}</button></td></tr>`).join('')}
        <tr><td><select id="dr-sup">${supOpts('')}</select></td><td><input type="text" id="dr-dest" placeholder="person@university.example"></td><td><select id="dr-how"><option value="process">${L('Process and send', 'Processar e enviar')}</option><option value="forward">${L('Forward the e-mail', 'Encaminhar o e-mail')}</option></select></td><td><select id="dr-after"><option value="close">${L('Close as Completed', 'Fecha como Concluído')}</option><option value="wait_cover">${L('Wait for the cover', 'Espera a capa de volta')}</option></select></td><td><input type="text" id="dr-note"></td><td class="center"><button class="btn sm blue" data-save-direct>${L('Save rule', 'Salvar regra')}</button></td></tr></tbody></table></div>`)}
      ${sect('truck', 'orange', L('Purchasing by supplier', 'Compras por Fornecedor'), L('Suppliers whose invoice goes to another Purchasing desk and then follows the normal flow to Fiscal', 'Fornecedores cuja nota vai a outro Compras e depois segue o fluxo normal até o Fiscal'),
      `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Purchasing (e-mail)', 'Compras (e-mail)')}</th><th>${L('Note', 'Observação')}</th><th class="center">${L('Actions', 'Ações')}</th></tr></thead><tbody>
        ${cfg.purchasing_rules.map((r) => `<tr><td class="t1">${esc(r.supplier)}</td><td class="mono small">${esc(r.to)}</td><td class="muted small">${esc(r.note)}</td><td class="center"><button class="btn sm red plain" data-del-buy="${r.id}">${ico('trash')}</button></td></tr>`).join('')}
        <tr><td><select id="pr-sup">${supOpts('')}</select></td><td><input type="text" id="pr-to" placeholder="purchasing.other@university.example"></td><td><input type="text" id="pr-note"></td><td class="center"><button class="btn sm blue" data-save-buy>${L('Save rule', 'Salvar regra')}</button></td></tr></tbody></table></div>`)}
      ${sect('shield', 'blue', L('E-mails outside the system', 'E-mails fora do sistema'), L('Newsletters, tickets and notices that leave the queue by themselves on arrival', 'Newsletters, chamados e avisos que saem da fila sozinhos ao chegar'),
      `<div class="rule-box"><p>${L('Rules are born in the queue review (“remove the next ones automatically”) or here. A sender can be the address (news@shop.example) or the domain (shop.example, also covers subdomains). Whoever leaves goes to the portal trash and to Deleted Items in Outlook: it can be restored.', 'As regras nascem na revisão da fila (“remover sozinhos os próximos”) ou aqui. Remetente pode ser o endereço (news@loja.example) ou o domínio (loja.example, vale para os subdomínios). Quem sai vai para a lixeira do portal e para Itens Excluídos no Outlook: dá para restaurar.')}</p></div>
        <div class="pad"><div class="grid-2" style="grid-template-columns:repeat(3,1fr)">${[['senders', L('Removed senders', 'Remetentes removidos'), 'marketing@eventos-tech.example'], ['subjects', L('Removed subjects', 'Assuntos removidos'), 'webinar'], ['never_point', L('Never point at', 'Nunca apontar'), 'sender.example']].map(([k, lab, ph]) => `<label class="f">${lab}${tagsBox(`rm-${k}`, rm[k], ph)}</label>`).join('')}</div></div>`)}
      ${sect('send', 'blue', L('Daily summary on Teams', 'Resumo diário no Teams'), L('One card per business day in the channel: the month, what is missing, the paid invoices, the queue and what came back from Purchasing', 'Um card por dia útil no canal: o mês, o que falta, as notas pagas, a fila e o que voltou do Compras'),
      `<div class="pad"><dl class="kv" style="grid-template-columns:140px 1fr"><dt>${L('SEND', 'ENVIO')}</dt><dd>${tm.enabled ? L(`On · ${tm.channel} (mock)`, `Ligado · ${tm.channel} (simulado)`) : L('Off', 'Desligado')}</dd><dt>${L('LAST SEND', 'ÚLTIMO ENVIO')}</dt><dd>${tm.last_sent ? fmtDT(tm.last_sent) : '—'}</dd><dt>${L('CARD BUTTONS', 'BOTÕES DO CARD')}</dt><dd>${tm.buttons.map((b) => `<span class="chip">${esc(b)}</span>`).join(' ')}</dd></dl>
        <div class="btn-row" style="justify-content:flex-start"><button class="btn plain" data-teams-preview>${L('See preview', 'Ver prévia')}</button><button class="btn plain" data-teams-send>${L('Post now (mock)', 'Publicar agora (simulado)')}</button></div></div>`)}
      ${sect('help', 'green', L('Tickets in the service desk', 'Chamados no service desk'), L('Chases the invoice that has not arrived: one ticket per supplier and month, with follow-ups', 'Cobra a nota que não chegou: um chamado por fornecedor e mês, com acompanhamentos'),
      `<div class="pad"><dl class="kv" style="grid-template-columns:140px 1fr"><dt>${L('USER', 'USUÁRIO')}</dt><dd>${esc(g.user)}</dd><dt>${L('CATEGORY', 'CATEGORIA')}</dt><dd>${esc(g.category)}</dd><dt>${L('RECIPIENTS', 'QUEM RECEBE')}</dt><dd>${esc(g.recipients)}</dd></dl>
        <div class="btn-row" style="justify-content:flex-start;margin-bottom:12px"><b class="small">${L('Mode', 'Modo')}</b><span class="seg">${[['off', L('Off', 'Desligado')], ['simulation', L('Simulation', 'Simulação')], ['on', L('On (mock)', 'Ligado (simulado)')]].map(([k, lab]) => `<button data-tickets-mode="${k}" class="${g.mode === k ? 'on' : ''}">${lab}</button>`).join('')}</span></div>
        <div class="form-grid" style="grid-template-columns:repeat(4,1fr)"><label class="f">${L('Open days before', 'Abrir dias antes')}<input type="number" id="g-open" value="${g.open_days_before}"></label><label class="f">${L('Last notice days after', 'Último aviso dias depois')}<input type="number" id="g-follow" value="${g.followup_days_after}"></label><label class="f">${L('Ignore overdue by more than (days)', 'Ignorar vencidos há mais de (dias)')}<input type="number" id="g-ignore" value="${g.ignore_older_than}"></label><label class="f">${L('Check at', 'Verificar às')}<input type="time" id="g-at" value="${g.check_at}"></label></div>
        <div class="btn-row" style="justify-content:flex-start;margin-top:12px"><button class="btn blue" data-save-tickets>${L('Save terms', 'Salvar prazos')}</button><button class="btn plain" data-tickets-preview>${L('Today’s preview', 'Prévia de hoje')}</button><button class="btn plain" data-tickets-test>${L('Test connection', 'Testar conexão')}</button></div><div id="tickets-preview" style="margin-top:12px"></div></div>`)}</div>`;
  },
};
document.addEventListener('keydown', async (ev) => {
  const inp = ev.target.closest && ev.target.closest('[data-tag-in]');
  if (!inp || ev.key !== 'Enter') return;
  ev.preventDefault();
  const id = inp.dataset.tagIn, v = inp.value.trim();
  if (!v) return;
  if (id.startsWith('rm-')) {
    await busy(null, async () => { const r = await api('POST', `api/settings/removal/${id.slice(3)}`, { value: v }); toast(r.message, 'ok'); await refresh(); });
  } else {
    const k = id.slice(4);
    cfg.settings[k].also.push(v);
    inp.value = '';
    const box = inp.closest('.tags-in');
    box.insertAdjacentHTML('afterbegin', `<span class="chip">${esc(v)}<button data-tag-rm="${id}|${esc(v)}">×</button></span>`);
  }
});
async function ticketsPreview() {
  const rows = await api('GET', 'api/settings/tickets/preview');
  $('#tickets-preview').innerHTML = rows.length ? `<div class="tbl-wrap card"><table class="tbl"><thead><tr><th>${L('Supplier', 'Fornecedor')}</th><th>${L('Due', 'Vencimento')}</th><th>${L('Action', 'Ação')}</th></tr></thead><tbody>${rows.map((r) => `<tr><td class="t1">${esc(r.supplier)}</td><td>${fmtD(r.due)} · ${rel(r.delta)}</td><td><span class="chip ${r.action === 'open' ? 'blue' : 'orange'}">${r.action === 'open' ? L('open ticket', 'abrir chamado') : L('follow-up', 'acompanhamento')}</span></td></tr>`).join('')}</tbody></table></div>`
    : `<div class="muted small">${L('Nothing to chase today.', 'Nada a cobrar hoje.')}</div>`;
}
document.addEventListener('click', async (ev) => {
  const el = ev.target.closest('[data-desctab],[data-descgroup],[data-new-map],[data-edit-map],[data-del-map],[data-add-norm],[data-del-norm],[data-save-pattern],[data-expand],[data-repgroup],[data-repwho],[data-kind],[data-tag-rm],[data-cfg-undo],[data-save-sectors],[data-save-direct],[data-del-direct],[data-save-buy],[data-del-buy],[data-teams-preview],[data-teams-send],[data-tickets-mode],[data-save-tickets],[data-tickets-preview],[data-tickets-test]');
  if (!el) return;
  const d = el.dataset;
  if (d.desctab) { S.desc.tab = d.desctab; refresh(); }
  else if (d.descgroup) { S.desc.group = d.descgroup; refresh(); }
  else if (d.newMap !== undefined) mapForm(null);
  else if (d.editMap) mapForm(window.descCache.mapping.find((r) => r.key === d.editMap));
  else if (d.delMap) { await api('DELETE', `api/descriptions/${S.desc.group}/${encodeURIComponent(d.delMap)}`); refresh(); }
  else if (d.addNorm !== undefined) await busy(el, async () => { await api('POST', 'api/normalization', { pattern: $('#norm-pat').value, name: $('#norm-name').value }); refresh(); });
  else if (d.delNorm) { await api('DELETE', `api/normalization?${qs({ pattern: d.delNorm })}`); refresh(); }
  else if (d.savePattern !== undefined) await busy(el, async () => { await api('PUT', 'api/pattern', { pattern: $('#pattern').value }); toast(L('Pattern saved. New invoices use it.', 'Padrão salvo. As próximas notas usam ele.'), 'ok'); refresh(); });
  else if (d.expand) { S.rep.open = S.rep.open === d.expand ? '' : d.expand; refresh(); }
  else if (d.repgroup) { S.rep.group = d.repgroup; S.rep.open = ''; refresh(); }
  else if (d.repwho) { S.rep.who = d.repwho; S.rep.open = ''; refresh(); }
  else if (d.kind !== undefined) { S.rep.kind = S.rep.kind === d.kind ? '' : d.kind; refresh(); }
  else if (d.tagRm) {
    const [id, v] = d.tagRm.split('|');
    if (id.startsWith('rm-')) await busy(el, async () => { await api('DELETE', `api/settings/removal/${id.slice(3)}?${qs({ value: v })}`); refresh(); });
    else { const k = id.slice(4); cfg.settings[k].also = cfg.settings[k].also.filter((x) => x !== v); el.closest('.chip').remove(); }
  } else if (d.cfgUndo !== undefined) refresh();
  else if (d.saveSectors !== undefined) await busy(el, async () => {
    await api('PUT', 'api/settings/sectors', { purchasing: { receives: $('#sec-purchasing').value, also: cfg.settings.purchasing.also }, fiscal: { receives: $('#sec-fiscal').value, also: cfg.settings.fiscal.also } });
    toast(L('Saved. New forwards use these addresses.', 'Salvo. Os próximos encaminhamentos usam estes endereços.'), 'ok'); refresh();
  });
  else if (d.saveDirect !== undefined) await busy(el, async () => { await api('PUT', 'api/settings/direct', { supplier: $('#dr-sup').value, dest: $('#dr-dest').value, how: $('#dr-how').value, after: $('#dr-after').value, note: $('#dr-note').value }); toast(L('Rule saved.', 'Regra salva.'), 'ok'); refresh(); });
  else if (d.delDirect) { await api('DELETE', `api/settings/direct/${d.delDirect}`); refresh(); }
  else if (d.saveBuy !== undefined) await busy(el, async () => { await api('PUT', 'api/settings/purchasing-rule', { supplier: $('#pr-sup').value, to: $('#pr-to').value, note: $('#pr-note').value }); toast(L('Rule saved.', 'Regra salva.'), 'ok'); refresh(); });
  else if (d.delBuy) { await api('DELETE', `api/settings/purchasing-rule/${d.delBuy}`); refresh(); }
  else if (d.teamsPreview !== undefined) {
    const t = await api('GET', 'api/settings/teams/preview');
    openModal(`<div class="modal-head"><h2>${L('Teams card preview', 'Prévia do card no Teams')}</h2><button class="btn sm plain" data-close>${L('Close', 'Fechar')}</button></div>
      <div class="record"><b>${L('Invoices', 'Notas')} · ${mLong(t.month)}</b><p class="small">${L('Still missing', 'Ainda faltam')} (${t.missing_total}): ${t.missing.map(esc).join(', ') || '—'}</p><p class="small">${L(`Paid/completed: ${t.paid} · In the queue: ${t.queue} · Came back from Purchasing: ${t.returned}`, `Pagas/concluídas: ${t.paid} · Na fila: ${t.queue} · Voltaram do Compras: ${t.returned}`)}</p><div class="btn-row" style="justify-content:flex-start"><span class="chip blue">${L('Open portal', 'Abrir portal')}</span><span class="chip blue">${L('Month by month', 'Mês a mês')}</span></div></div>`);
  } else if (d.teamsSend !== undefined) await busy(el, async () => { const r = await api('POST', 'api/settings/teams/send'); toast(r.message, 'ok'); refresh(); });
  else if (d.ticketsMode) await busy(el, async () => { await api('PUT', 'api/settings/tickets', { mode: d.ticketsMode }); refresh(); });
  else if (d.saveTickets !== undefined) await busy(el, async () => { await api('PUT', 'api/settings/tickets', { open_days_before: $('#g-open').value, followup_days_after: $('#g-follow').value, ignore_older_than: $('#g-ignore').value, check_at: $('#g-at').value }); toast(L('Terms saved.', 'Prazos salvos.'), 'ok'); await ticketsPreview(); });
  else if (d.ticketsPreview !== undefined) await busy(el, ticketsPreview);
  else if (d.ticketsTest !== undefined) await busy(el, async () => { const r = await api('POST', 'api/settings/tickets/test'); toast(r.message, 'ok'); });
});
document.addEventListener('input', (ev) => {
  if (ev.target.id === 'desc-q') { S.desc.q = ev.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(refresh, 250); }
  if (ev.target.id === 'type-q') { S.rep.q = ev.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(refresh, 300); }
});

/* ── logs ───────────────────────────────────────────────────────────────── */
S.logs = { level: 'all', days: 7, area: 'all', q: '', live: false };
let logTimer = null;
PAGES.logs = {
  async load() {
    const f = S.logs;
    const [cnt, rows] = await Promise.all([api('GET', 'api/logs/counts'), api('GET', `api/logs?${qs({ level: f.level, days: f.days, area: f.area, q: f.q })}`)]);
    const lv = { INFO: ['blue', L('Info', 'Info')], WARNING: ['orange', L('Warning', 'Aviso')], ERROR: ['red', L('Error', 'Erro')], SUCCESS: ['blue', L('Info', 'Info')] };
    const chip = (k, lab, n, ic = '') => `<button class="chip click ${f.level === k ? 'blue' : ''}" data-loglevel="${k}" style="font-size:12px;padding:3px 12px">${ic}${lab} <b>${n}</b></button>`;
    const today = new Date().toDateString();
    $('#page').innerHTML = `${head(L('System Logs', 'Logs do Sistema'), L('What the portal and the robot did: who triggered it, in which area, and the detail of each error', 'O que o portal e o robô fizeram: quem disparou, em que área, e o detalhe de cada erro'),
      `<label class="small muted" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="log-live" ${f.live ? 'checked' : ''}> ${L('Live', 'Ao vivo')}</label><button class="btn plain" data-refresh>${ico('refresh')} ${L('Refresh', 'Atualizar')}</button>`)}
    <div class="card"><div class="toolbar" style="background:none">${chip('all', L('All', 'Todos'), cnt.all)}${chip('ERROR', L('Errors', 'Erros'), cnt.ERROR)}${chip('WARNING', L('Warnings', 'Avisos'), cnt.WARNING)}${chip('INFO', L('Information', 'Informações'), cnt.INFO)}
      <span class="btn-row"><select id="log-days" style="width:auto"><option value="1" ${f.days == 1 ? 'selected' : ''}>${L('Last 24 hours', 'Últimas 24 horas')}</option><option value="7" ${f.days == 7 ? 'selected' : ''}>${L('Last 7 days', 'Últimos 7 dias')}</option><option value="30" ${f.days == 30 ? 'selected' : ''}>${L('Last 30 days', 'Últimos 30 dias')}</option></select>
      <select id="log-area" style="width:auto"><option value="all">${L('All areas', 'Todas as áreas')}</option>${cnt.areas.map((a) => `<option ${a === f.area ? 'selected' : ''}>${esc(a)}</option>`).join('')}</select><input type="text" id="log-q" value="${esc(f.q)}" placeholder="${L('Search message, user, e-mail, ID', 'Buscar mensagem, usuário, e-mail, ID')}" style="width:230px"></span></div>
      <div class="tbl-wrap" style="max-height:62vh;overflow:auto"><table class="tbl"><thead><tr><th>${L('When', 'Quando')}</th><th>${L('Level', 'Nível')}</th><th>${L('Area · who', 'Área · quem')}</th><th>${L('Message', 'Mensagem')}</th></tr></thead><tbody>
      ${rows.map((r) => { const [tone, lab] = lv[r.level] || ['gray', r.level]; const d = new Date(r.ts); return `<tr><td class="when">${fmtT(r.ts)}<div class="faint tiny">${d.toDateString() === today ? L('today', 'hoje') : fmtD(r.ts)}</div></td><td><span class="tag ${tone}" style="margin:0">${lab}</span></td><td><b class="small">${esc(r.area)}</b><div class="faint tiny">${ico('user')} ${esc(r.who)}</div></td><td class="small">${esc(r.message)}</td></tr>`; }).join('') || `<tr><td colspan="4" class="empty">${L('No entries.', 'Nenhum registro.')}</td></tr>`}</tbody></table></div>
      <div class="pager"><span>${L(`Showing the ${rows.length} most recent of ${cnt.all}. Refine the filters to see the rest.`, `Mostrando os ${rows.length} mais recentes de ${cnt.all}. Refine os filtros para ver os demais.`)}</span></div></div>`;
    clearInterval(logTimer);
    if (f.live) logTimer = setInterval(() => { if (current === 'logs') PAGES.logs.load(); }, 5000);
  },
};
document.addEventListener('click', (ev) => { const b = ev.target.closest('[data-loglevel]'); if (b) { S.logs.level = b.dataset.loglevel; refresh(); } });
document.addEventListener('change', (ev) => {
  const id = ev.target.id;
  if (id === 'log-days') { S.logs.days = +ev.target.value; refresh(); }
  else if (id === 'log-area') { S.logs.area = ev.target.value; refresh(); }
  else if (id === 'log-live') { S.logs.live = ev.target.checked; if (!ev.target.checked) clearInterval(logTimer); else refresh(); }
});
document.addEventListener('input', (ev) => { if (ev.target.id === 'log-q') { S.logs.q = ev.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(refresh, 300); } });

/* ── sent e-mails (demo-only screen: what would leave through Graph sendMail) ── */
PAGES.outbox = {
  async load() {
    const msgs = await api('GET', 'api/outbox');
    $('#page').innerHTML = `${head(L('Sent e-mails', 'E-mails enviados'), L('Everything the system would send (Graph sendMail in production): forwards to Purchasing and Fiscal, requests to suppliers, the Finance spreadsheet. This screen only exists in the demo.', 'Tudo que o sistema enviaria (Graph sendMail em produção): encaminhamentos ao Compras e Fiscal, pedidos a fornecedores, a planilha do Financeiro. Esta tela só existe na demo.'))}
    <div class="stack">${msgs.map((m) => `<div class="mail"><div class="h"><span><b>${L('To', 'Para')}:</b> ${esc(m.to)} <span class="tag gray">${esc(m.kind)}</span></span><span class="muted small">${fmtDT(m.ts)}</span></div><div><b>${esc(m.subject)}</b></div>${m.attachments.length ? `<div class="muted small">${ico('clip')} ${m.attachments.map(esc).join(', ')}</div>` : ''}${m.body ? `<pre>${esc(m.body)}</pre>` : ''}</div>`).join('') || `<p class="muted">${L('Nothing sent yet.', 'Nada enviado ainda.')}</p>`}</div>`;
  },
};
