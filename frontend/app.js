/* Live UI: every number below comes from /api/state or /api/whatif (backend engine). */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const inr = n => '₹' + Math.round(n).toLocaleString('en-IN');
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const role = () => document.body.dataset.role || 'hq';
  const ROUTE = {transfer:'Transfer', markdown:'Sell', donate:'Donate', compost:'Compost / biogas'};
  const LADDER = {markdown:0, transfer:1, donate:2, compost:4};
  const api = async (path, body) => {
    const r = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { toast(j.error || 'Something went wrong'); throw new Error(j.error); }
    return j;
  };
  function toast(msg) {
    let t = $('#toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); t.style.cssText = 'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#16202B;color:#fff;padding:10px 16px;border-radius:6px;z-index:60;font-size:14px;max-width:90vw'; document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => t.hidden = true, 3500);
  }
  let S = null, editing = {};

  /* ---------- Prevent: drafts ---------- */
  const BADGE = {pending:['wait','Awaiting approval'], approved:['ok','Approved'], rejected:['high','Rejected']};
  function renderDrafts() {
    $('#drafts').innerHTML = S.drafts.map(d => {
      const [bc, bt] = d.needs_hq && d.status === 'pending' ? ['hq','Needs HQ approval'] : BADGE[d.status];
      const done = d.status !== 'pending';
      const rows = d.lines.map(l => `<tr><td class="item">${esc(l.name)}</td><td class="num">${l.usual} ${l.unit}</td>
        <td class="num"><span class="qty" data-sku="${l.sku}" data-cost="${l.cost}" ${editing[d.outlet] && !done ? 'contenteditable="true" style="outline:1px dashed #2340A8"' : ''}>${l.order}</span> ${l.unit}
        ${l.transfer_in ? `<span class="chg">= ${l.need} needed − ${l.transfer_in} transfer</span>` : `<span class="chg ${l.need >= l.usual ? 'up' : 'down'}">${l.need >= l.usual ? '▲' : '▼'} ${Math.abs(Math.round((l.need - l.usual) / l.usual * 100))}%</span>`}</td>
        <td class="why">${esc(l.why)}</td><td class="conf ${l.conf === 'Medium' ? 'med' : ''}">${l.conf} ± ${l.pm}</td></tr>`).join('');
      return `<div class="sheet" data-outlet="${d.outlet}" data-draft="${d.outlet}">
        <div class="sheet-head"><div><h3>Outlet ${d.outlet} · order draft for Monday</h3><p><span class="val">${inr(d.value)}</span> order value · saves ≈ ${inr(d.saving)} vs usual (est.)</p></div><span class="badge ${bc}">${bt}${d.reason ? ': ' + esc(d.reason) : ''}</span></div>
        <div class="scroll-x"><table class="order-table"><caption class="vh">Outlet ${d.outlet} order draft</caption><thead><tr><th>Item</th><th class="num">Usual</th><th class="num">Draft</th><th>Why</th><th title="Range from an 8-week backtest">Confidence</th></tr></thead><tbody>${rows}</tbody></table></div>
        <div class="actions"><span class="note">${d.needs_hq ? `Above the ${inr(S.limit)} outlet limit, so HQ approves` : `Within the ${inr(S.limit)} outlet limit`}</span>
        <button class="btn small" data-act="reject" ${done ? 'disabled' : ''}>Reject with reason</button>
        <button class="btn small" data-act="edit" ${done ? 'disabled' : ''}>${editing[d.outlet] ? 'Done editing' : 'Edit lines'}</button>
        <button class="btn primary small ${d.status === 'approved' ? 'done' : ''}" data-act="approve" ${done ? 'disabled' : ''}>${d.status === 'approved' ? 'Approved · sent to supplier' : d.needs_hq ? 'Approve as HQ' : 'Approve draft'}</button></div>
        <div class="reasons" hidden><span>What did the model miss?</span>${['Supplier issue','Local event not in calendar','Price change','Other'].map(r => `<button class="btn small" data-act="reason">${r}</button>`).join('')}</div></div>`;
    }).join('');
  }

  /* ---------- Prevent: what-if (server-side newsvendor) ---------- */
  function renderWhatIfShell() {
    const w = S.whatif;
    $('#whatif').innerHTML = `<div class="ctl"><h3>What if we change the ${w.name.toLowerCase()} order?</h3>
      <p>Outlet ${w.outlet}, Monday. Forecast demand ${w.mu} ${w.unit} ± ${w.sd} (est.). Cost ₹${w.cost}/${w.unit}, price ₹${w.price}/${w.unit}, unsold stock marked down to ₹${w.salvage}/${w.unit}.</p>
      <div class="range"><label for="qty">Order quantity <output id="qtyOut" for="qty"></output></label>
      <input id="qty" type="range" min="50" max="90" step="1" value="${w.best}"><div class="marks"><span style="left:${(w.best - 50) / 40 * 100}%">Best ${w.best}</span><span style="left:${(w.usual - 50) / 40 * 100}%">Usual ${w.usual}</span></div></div></div>
      <dl class="results" aria-live="polite">${[['Procurement cost','wCost'],['Expected waste','wWaste'],['Stock-out risk','wOut'],['Expected margin','wMargin']].map(([t, i]) => `<div><dt>${t}</dt><dd id="${i}"></dd><p class="vs" id="${i}Vs"></p></div>`).join('')}</dl>
      <p class="whatif-foot">Newsvendor estimate with normal demand and markdown salvage, computed by the backend. Estimates, not guaranteed savings.</p>`;
    $('#qty').addEventListener('input', whatIf); whatIf();
  }
  let wTok = 0;
  async function whatIf() {
    const q = +$('#qty').value, tok = ++wTok;
    const r = await fetch(`/api/whatif?outlet=${S.whatif.outlet}&sku=${S.whatif.sku}&qty=${q}`).then(x => x.json());
    if (tok !== wTok) return;
    const vs = (id, d, fmt, lowGood) => { const e = $('#' + id + 'Vs'); const flat = Math.abs(d) < 0.05; e.className = 'vs ' + (flat ? 'flat' : (lowGood ? d < 0 : d > 0) ? 'good' : 'bad'); e.textContent = flat ? `Same as usual ${S.whatif.usual}` : `${d > 0 ? '+' : '−'}${fmt(Math.abs(d))} vs usual`; };
    $('#qtyOut').textContent = q + ' ' + S.whatif.unit + (q === r.best ? ' · best margin' : '');
    $('#wCost').textContent = inr(r.cost); vs('wCost', r.d_cost, inr, true);
    $('#wWaste').textContent = r.waste.toFixed(1) + ' ' + S.whatif.unit; vs('wWaste', r.d_waste, d => d.toFixed(1), true);
    $('#wOut').textContent = Math.round(r.stockout * 100) + '%'; vs('wOut', r.d_stockout * 100, d => Math.round(d) + ' pts', true);
    $('#wMargin').textContent = inr(r.margin); vs('wMargin', r.d_margin, inr, false);
  }

  /* ---------- Detect ---------- */
  const LOGBADGE = {logged:['ok','Logged'], needs_confirmation:['wait','Needs confirmation'], needs_review:['high','Could not read, re-enter']};
  function renderLogs() {
    $('#logs').innerHTML = `<div class="sheet-head"><div><h3>Staff logs</h3><p>Type, paste a WhatsApp message or a voice transcript (English, ಕನ್ನಡ, हिंदी). Confirmed logs remove stock and update risk.</p></div></div>
      <form id="logForm" class="logform" style="display:grid;gap:8px;padding:12px 16px;border-bottom:1px solid var(--rule)">
        <div style="display:flex;gap:8px;flex-wrap:wrap"><select name="outlet" aria-label="Outlet" class="btn small"><option value="14">Outlet 14</option><option value="27">Outlet 27</option></select>
        <select name="source" aria-label="Source" class="btn small"><option value="text">Typed / WhatsApp</option><option value="voice">Voice transcript</option></select></div>
        <div style="display:flex;gap:8px"><input name="text" required maxlength="200" aria-label="Waste entry" placeholder="e.g. 3 kg banana overripe  ·  ಐದು ಕೆಜಿ ಟೊಮೆಟೊ ಹಾಳಾಗಿದೆ" style="flex:1;height:36px;border:1px solid var(--rule-strong);border-radius:6px;padding:0 10px;font:inherit"><button class="btn primary small" type="submit">Log waste</button></div></form>
      <ul class="feed">${S.logs.map(l => { const [c, t] = LOGBADGE[l.status]; return `<li class="log" data-outlet="${l.outlet}"><div><p class="log-top"><strong>${l.status === 'needs_review' ? 'Unrecognised entry' : esc(l.sku) + ' · ' + l.qty + ' ' + esc(l.unit) + ' · ' + esc(l.reason)}</strong><span class="badge ${c}">${t}</span></p>
        <p class="log-meta">${esc(l.source)} · Outlet ${l.outlet} · ${esc(l.time)} · extraction confidence ${l.confidence} (${esc(l.engine)})</p><p class="quote">“${esc(l.text)}”</p>
        ${l.status === 'needs_confirmation' ? `<div class="row-actions"><button class="btn small primary" data-act="confirmlog" data-id="${l.id}">Confirm entry</button></div>` : ''}</div></li>`; }).join('')}</ul>`;
    $('#logForm').addEventListener('submit', async e => {
      e.preventDefault(); const f = new FormData(e.target);
      const r = await api('/api/logs', {outlet: f.get('outlet'), text: f.get('text'), source: f.get('source')});
      toast(r.status === 'logged' ? 'Logged. Stock and risk updated.' : r.status === 'needs_confirmation' ? 'Saved. Please confirm the entry.' : 'Could not read that entry. Try "5 kg tomatoes spoiled".');
      await load();
    });
  }
  function renderRisks() {
    const act = (id) => (S.plans[id] || []).filter(a => a.qty > 0).map(a => a.route === 'transfer' ? `${a.qty} → transfer to Outlet ${a.target}` : a.route === 'markdown' ? `${a.qty} → 25% markdown` : a.route === 'donate' ? `${a.qty} → donate` : `${a.qty} → ${a.route}`).join(' · ');
    $('#risks').innerHTML = `<div class="sheet-head"><div><h3>Spoilage risk · next 48 hours</h3><p>Stock × forecast demand × shelf life × humidity</p></div></div><div>${S.lots.map(l => {
      const rec = (S.plans[l.id] || []).reduce((t, a) => t + (a.route === 'donate' ? 0 : a.est), 0);
      return `<div class="risk causal" data-outlet="${l.outlet}"><div class="cz"><p class="item"><strong>${esc(l.name)} · ${l.stock} ${l.unit} · Outlet ${l.outlet}</strong><span class="badge ${l.level === 'high' ? 'high' : l.level === 'medium' ? 'med' : 'ok'}">${l.level[0].toUpperCase() + l.level.slice(1)}</span></p>
      <dl class="cz-grid"><div><dt>Forecast demand</dt><dd>${l.forecast}</dd></div><div><dt>Stock</dt><dd>${l.stock}</dd></div><div><dt>Shelf life left</dt><dd>${l.life} d</dd></div><div><dt>Expected unsold</dt><dd class="bad">${l.unsold}</dd></div><div><dt>Recovery window</dt><dd>${l.window} h</dd></div></dl>
      <p class="cz-act"><b>Recommended:</b> ${esc(act(l.id) || 'nothing to do')}</p>
      <p class="cz-val">${l.kind === 'sell' ? `<span class="ok">${inr(rec)} expected recovery</span><span class="bad">${inr(l.value_at_risk)} at risk if ignored</span>` : `<span class="ok">≈ ${(S.plans[l.id] || []).reduce((t, a) => t + (a.meals || 0), 0)} meals if donated</span>`}</p></div><a class="btn small" href="#rescue">Plan rescue</a></div>`;
    }).join('')}</div>`;
  }

  /* ---------- Rescue ---------- */
  function renderRescue() {
    const rows = S.lots.flatMap(l => (S.plans[l.id] || []).map(a => {
      const ladder = [0,1,2,3,4,5].map(i => `<i class="${i < LADDER[a.route] ? 'past' : i === LADDER[a.route] ? 'on' : ''}"></i>`).join('');
      const why = a.route === 'transfer' ? `To Outlet ${a.target}, which would otherwise buy this fresh; its order draft drops by ${a.qty}. Truck cost is shared by lots on the same route.`
        : a.route === 'markdown' ? 'Mark down 25% and move to the front of the shelf.' : a.route === 'donate' ? `City Food Bank (demo partner), pickup 8 pm, ≈ ${a.meals} meals.${a.blocked ? '<span class="safety">Pickup is blocked until staff confirm the food-safety check</span>' : ''}` : 'Compost / biogas partner (demo).';
      const st = a.status === 'measured' ? `<span class="badge ok">Measured</span>` : a.status === 'applied' ? `<span class="badge ok">${a.route === 'transfer' ? 'Pickup scheduled' : 'Live'}</span>`
        : a.blocked ? `<button class="btn small primary" data-act="safety" data-lot="${l.id}">Confirm safety check</button>`
        : `<button class="btn small primary" data-act="apply" data-id="${esc(a.id)}">${a.route === 'transfer' ? 'Schedule transfer' : a.route === 'markdown' ? 'Apply markdown' : 'Schedule pickup'}</button>`;
      return `<tr data-outlet="${l.outlet}"><td class="item">${esc(l.name)} · ${a.qty} ${l.unit}<small>Outlet ${l.outlet}</small></td><td><span class="route">${ROUTE[a.route]}</span><span class="ladder" aria-hidden="true">${ladder}</span></td><td class="why">${why}</td>
        <td class="num">${a.route === 'donate' ? a.meals + ' meals' : inr(a.est) + (a.route === 'transfer' ? ' net' : '')}</td><td>${st}</td></tr>`;
    })).join('');
    $('#rescueBody').innerHTML = `<table class="rescue-table"><caption class="vh">Surplus lots and their routes</caption><thead><tr><th>Lot</th><th>Route</th><th>Plan</th><th class="num">Recovers</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  /* ---------- Prove ---------- */
  function renderProve() {
    const c = S.carry;
    $('#carry').innerHTML = `<div><dt class="head">Week to date <span>28 Sep – 4 Oct</span></dt><dd class="vh">Totals so far this week</dd></div><div><dt>Realized saving</dt><dd class="pos">${inr(c.real)}</dd></div><div><dt>Waste avoided</dt><dd>${c.kg} kg</dd></div><div><dt>CO₂e avoided</dt><dd>≈ ${c.co2e_t} t <small>est.</small></dd></div><div><dt>Meals rescued</dt><dd>${c.meals}</dd></div><div><dt>Awaiting approval</dt><dd>${c.pending} <small>order drafts</small></dd></div>`;
    $('#strip').innerHTML = `<div><small>At risk, next 48 h</small><b class="bad">${inr(S.strip.at_risk)}</b><span>sellable lots</span></div><span class="arrow" aria-hidden="true">→</span><div><small>Rescue plan recovers</small><b class="ok">${inr(S.strip.recover)}</b><span>${S.strip.at_risk ? Math.round(S.strip.recover / S.strip.at_risk * 100) : 0}% · bread to food bank (≈ ${S.strip.meals} meals)</span></div>`;
    $('#navPrevent').textContent = c.pending; $('#navPrevent').classList.toggle('hot', c.pending > 0);
    $('#pendingCount2').textContent = c.pending;
    const NAME = {ba27:'Bananas', sp14:'Spinach', pa27:'Papaya', br14:'Bread'};
    $('#prove').innerHTML = `<div class="sheet" data-hq><div class="sheet-head"><div><h3>Impact ledger · all outlets</h3><p>Realized = measured after the action was taken</p></div></div><div class="scroll-x"><table class="ledger"><caption class="vh">Weekly impact ledger</caption><thead><tr><th>Week</th><th class="num">Recommendations</th><th class="num">Accepted</th><th class="num">Estimated saving</th><th class="num">Realized saving</th><th class="num">Realized vs est.</th></tr></thead><tbody>
      ${S.ledger.map(r => `<tr><td>${esc(r.week)}</td><td class="num">${r.recs}</td><td class="num">${r.acc}</td><td class="num">${inr(r.est)}</td><td class="num real">${inr(r.real)}</td><td class="num">${r.pct ?? '–'}%</td></tr>`).join('')}</tbody></table></div></div>
      <div class="sheet" data-hq><div class="sheet-head"><div><h3>Closed loop · today's rescues, lot by lot</h3><p>Recommended → acted on → measured</p></div><button class="btn small primary" data-act="close" ${S.applied ? '' : 'disabled'}>Close the day${S.applied ? ' (' + S.applied + ' actions)' : ''}</button></div>
      ${S.lotrows.length ? `<div class="scroll-x"><table><thead><tr><th>Lot</th><th>Action</th><th class="num">Estimated</th><th class="num">Realized</th></tr></thead><tbody>${S.lotrows.map(r => `<tr><td class="item">${NAME[r.lot] || r.lot} · ${r.qty}</td><td>${ROUTE[r.route]}</td><td class="num">${inr(r.est)}</td><td class="num real">${inr(r.real)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="note" style="padding:14px 16px">Apply a rescue action, then close the day. This demo simulates end-of-day outcomes (80–105% of estimate); in production, realized values come from POS data.</p>'}</div>`;
  }

  /* ---------- Local context from Google Places (or labelled synthetic) ---------- */
  const CAT = [['stay','Hostels & lodging'],['edu','Education'],['food','Food & groceries'],['office','Offices'],['transit','Transit'],['home','Residential']];
  async function renderContext() {
    for (const o of ['14', '27']) {
      const c = await fetch('/api/context?outlet=' + o).then(r => r.json()).catch(() => null);
      const art = document.querySelector(`article[data-outlet="${o}"]`); if (!c || !art) continue;
      art.querySelector('.bars').innerHTML = CAT.map(([k, l]) => `<li class="bar" style="--c:var(--c-${k});--v:${Math.min(c.vector[k] || 0, 4) / 4}"><span class="lab"><i class="sw"></i>${l}</span><span class="track"><i></i></span><b>${(c.vector[k] || 0).toFixed(1)}×</b></li>`).join('');
      art.querySelector('.bars-note').textContent = `${c.note} Black tick = city median (1.0×).` + (c.twin_similarity != null ? ` Similarity to the other outlet: ${c.twin_similarity}.` : '');
    }
  }
  async function load() { S = await api('/api/state'); renderDrafts(); renderWhatIfShell(); renderLogs(); renderRisks(); renderRescue(); renderProve(); }

  document.addEventListener('input', e => {
    const q = e.target.closest('.qty'); if (!q) return;
    const sheet = q.closest('[data-draft]');
    sheet.querySelector('.val').textContent = inr([...sheet.querySelectorAll('.qty')].reduce((t, x) => t + (parseInt(x.textContent) || 0) * +x.dataset.cost, 0));
  });
  document.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t || t.disabled) return;
    if (t.matches('[data-role-btn]')) { document.body.dataset.role = t.dataset.roleBtn; $$('[data-role-btn]').forEach(b => b.setAttribute('aria-pressed', String(b === t))); return; }
    const act = t.dataset.act; if (!act) return;
    const sheet = t.closest('[data-draft]'), o = sheet && sheet.dataset.draft;
    try {
      if (act === 'approve') {
        const overrides = {}; sheet.querySelectorAll('.qty').forEach(x => overrides[x.dataset.sku] = parseInt(x.textContent) || 0);
        await api(`/api/drafts/${o}/approve`, {role: role(), overrides}); editing[o] = false;
      } else if (act === 'edit') { editing[o] = !editing[o]; renderDrafts(); return; }
      else if (act === 'reject') { const r = sheet.querySelector('.reasons'); r.hidden = !r.hidden; return; }
      else if (act === 'reason') await api(`/api/drafts/${o}/reject`, {reason: t.textContent});
      else if (act === 'confirmlog') await api(`/api/logs/${t.dataset.id}/confirm`, {});
      else if (act === 'safety') await api(`/api/lots/${t.dataset.lot}/safety`, {});
      else if (act === 'apply') await api('/api/actions/apply', {id: t.dataset.id});
      else if (act === 'close') await api('/api/close-day', {});
      await load();
    } catch (err) { /* toast already shown */ }
  });
  load(); renderContext();
})();
