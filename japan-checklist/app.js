'use strict';
// Keep the deployed storage key: upgrading the UI must not reset travel records.
const STORAGE = 'japan700-tracker-v1';
const COLLAPSE_STORAGE = 'japan700-simple-collapsed-v1';
const REGION_ORDER = ['北海道','東北','關東','北陸信越','東海・山梨','關西','中國地方','四國','九州','沖繩'];
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain = o => !!o && typeof o === 'object' && !Array.isArray(o);
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
let spots = [], state = {}, collapsed = {}, regions = [], onlyVisited = false;
let byId = new Map(), byRegion = new Map(), ready = false, storageWarning = false;

function notify(text, error = false) {
  $('#saveStatus').textContent = text;
  $('#saveStatus').classList.toggle('warning', error);
}
function readObject(key) {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return null;
    const obj = JSON.parse(raw);
    if (!plain(obj)) throw new Error('Invalid stored data');
    return obj;
  } catch { storageWarning = true; return null; }
}
function checkedValue(value) {
  if (typeof value === 'boolean') return value;
  if (!plain(value)) return false;
  if (typeof value.checked === 'boolean') return value.checked;
  if (typeof value.visited === 'boolean') return value.visited;
  return value.status === '已去' || value.status === '想再去';
}
function validRecords(raw, strict = false) {
  if (!plain(raw)) throw new Error('備份格式不正確');
  const out = {};
  for (const [id, value] of Object.entries(raw)) {
    if (!byId.has(id)) continue;
    const valid = typeof value === 'boolean' || (plain(value) &&
      (typeof value.checked === 'boolean' || typeof value.visited === 'boolean' ||
       ['待確認','想去','已去','想再去','暫不安排'].includes(value.status) ||
       typeof value.note === 'string' || typeof value.date === 'string'));
    if (!valid) { if (strict) throw new Error('景點紀錄格式不正確'); else continue; }
    // Keep dates and notes in backups even though they are no longer displayed.
    out[id] = {...(plain(value) ? value : {}), checked: checkedValue(value)};
  }
  if (strict && Object.keys(raw).length && !Object.keys(out).length) throw new Error('找不到相符的景點紀錄');
  return out;
}
function loadState() {
  const current = readObject(STORAGE);
  if (current !== null) state = validRecords(current);
  else state = {...validRecords(readObject('japan700-simple-v1') || {}),
                ...validRecords(readObject('japan700-simple-v2') || {})};
  collapsed = readObject(COLLAPSE_STORAGE) || {};
  if (storageWarning) notify('部分本機紀錄無法讀取或瀏覽器限制儲存；請保留原備份，並使用匯出備份。', true);
}
function saveState(message = '已儲存到此瀏覽器。') {
  try {
    localStorage.setItem(STORAGE, JSON.stringify(state));
    storageWarning = false;
    notify(message);
    return true;
  } catch {
    storageWarning = true;
    notify('瀏覽器無法儲存：目前變更只在這個分頁，請先匯出備份，避免遺失。', true);
    return false;
  }
}
function saveCollapsed() {
  try { localStorage.setItem(COLLAPSE_STORAGE, JSON.stringify(collapsed)); }
  catch { notify('收合設定無法儲存；本次仍可操作，請匯出備份保留勾選。', true); }
}
function isDone(spot) { return checkedValue(state[spot.id]); }
function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }
function ordered(list) {
  return [...list].sort((a, b) => Number(isDone(b)) - Number(isDone(a)) || a.order - b.order);
}
function filtered() {
  const q = $('#search').value.trim().toLocaleLowerCase();
  const region = $('#region').value, pref = $('#pref').value;
  return spots.filter(s => (!q || `${s.name} ${s.prefecture} ${s.region}`.toLocaleLowerCase().includes(q)) &&
    (!region || s.region === region) && (!pref || s.prefecture === pref) && (!onlyVisited || isDone(s)));
}
function regionLabel(region) {
  const all = byRegion.get(region), done = all.filter(isDone).length;
  return `${done}/${all.length} 已完成 · ${pct(done, all.length)}%`;
}
function renderProgress() {
  $('#regionProgress').innerHTML = regions.map(r => {
    const all = byRegion.get(r), done = all.filter(isDone).length;
    return `<div class="prog"><div class="prog-top"><b>${esc(r)}</b><span>${done}/${all.length} · ${pct(done, all.length)}%</span></div><div class="bar" aria-hidden="true"><i style="width:${pct(done, all.length)}%"></i></div></div>`;
  }).join('');
}
function card(spot) {
  const done = isDone(spot);
  return `<article class="spot ${done ? 'visited' : ''}" data-id="${esc(spot.id)}" title="${esc(spot.prefecture)}">
    <div class="thumb-wrap"><div class="thumb-fallback" role="img" aria-label="${esc(spot.name)}：照片待載入"><span>照片待載入</span></div><img class="thumb" alt="${esc(spot.name)}" width="640" height="480" loading="lazy" decoding="async" hidden><a class="photo-credit" target="_blank" rel="noopener noreferrer" hidden></a></div>
    <label class="spot-body"><span class="spot-name">${esc(spot.name)}</span><input class="check" type="checkbox" aria-label="${esc(spot.name)}，已去" ${done ? 'checked' : ''}></label>
  </article>`;
}
function renderCards() {
  window.JapanPhotos?.disconnect();
  const list = filtered();
  $('#visibleCount').textContent = `目前顯示 ${list.length} 個景點`;
  $('#empty').hidden = list.length !== 0;
  $('#cards').innerHTML = regions.map((r, n) => {
    const items = list.filter(s => s.region === r);
    if (!items.length) return '';
    const closed = collapsed[r] === true;
    return `<section class="region-section card" data-region="${esc(r)}">
      <h2 class="region-heading"><button class="region-head" type="button" aria-expanded="${!closed}" aria-controls="region-cards-${n}"><span><span class="region-name">${esc(r)}</span><span class="region-count">${regionLabel(r)}</span></span><span class="region-toggle">${closed ? '展開 ＋' : '收合 −'}</span></button></h2>
      <div class="region-cards" id="region-cards-${n}" ${closed ? 'hidden' : ''}>${ordered(items).map(card).join('')}</div>
    </section>`;
  }).join('');
  window.JapanPhotos?.observe(document.querySelectorAll('.spot'), byId);
}
function render() { renderProgress(); renderCards(); }
function updateSectionFold(section, closed) {
  const region = section.dataset.region;
  collapsed[region] = closed;
  section.querySelector('.region-cards').hidden = closed;
  section.querySelector('.region-head').setAttribute('aria-expanded', String(!closed));
  section.querySelector('.region-toggle').textContent = closed ? '展開 ＋' : '收合 −';
}
function updateChecked(input) {
  const el = input.closest('.spot'), id = el.dataset.id, spot = byId.get(id);
  const done = input.checked;
  // Explicit false always overrides an earlier "想再去" or "已去" state.
  state[id] = {...state[id], checked: done, visited: done, status: done ? '已去' : '待確認'};
  saveState();
  renderProgress();
  if (onlyVisited && !done) { renderCards(); return; }
  const section = el.closest('.region-section'), grid = section.querySelector('.region-cards');
  el.classList.toggle('visited', done);
  section.querySelector('.region-count').textContent = regionLabel(spot.region);
  // Move existing nodes rather than recreating images or losing keyboard focus.
  [...grid.children].sort((a, b) => {
    const x = byId.get(a.dataset.id), y = byId.get(b.dataset.id);
    return Number(isDone(y)) - Number(isDone(x)) || x.order - y.order;
  }).forEach(node => grid.appendChild(node));
  input.focus({preventScroll: true});
}
function updatePrefs() {
  const selected = $('#pref').value, region = $('#region').value;
  const prefs = [...new Set(spots.filter(s => !region || s.region === region).map(s => s.prefecture))];
  $('#pref').innerHTML = '<option value="">全部都道府縣</option>' + prefs.map(p => `<option>${esc(p)}</option>`).join('');
  if (prefs.includes(selected)) $('#pref').value = selected;
}
function exportBackup() {
  if (!ready) return;
  const payload = {version: 3, exportedAt: new Date().toISOString(), state};
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}));
  const a = document.createElement('a'); a.href = url;
  a.download = `japan700-backup-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function importBackup(file) {
  if (!ready || !file) return;
  if (file.size > 5 * 1024 * 1024) throw new Error('備份檔案過大');
  const obj = JSON.parse(await file.text());
  if (!plain(obj)) throw new Error('備份格式不正確');
  if (own(obj, 'version') && ![1, 2, 3].includes(obj.version)) throw new Error('不支援此備份版本');
  const incoming = validRecords(own(obj, 'state') ? obj.state : obj, true);
  if (!confirm('將合併備份；相同景點以匯入檔案為準。是否繼續？')) return;
  state = {...state, ...incoming};
  saveState('備份已合併並儲存在此瀏覽器。'); render();
}
function bindUI() {
  $('#region').insertAdjacentHTML('beforeend', regions.map(r => `<option>${esc(r)}</option>`).join(''));
  updatePrefs();
  $('#search').addEventListener('input', renderCards);
  $('#region').addEventListener('change', () => { updatePrefs(); renderCards(); });
  $('#pref').addEventListener('change', renderCards);
  $('#onlyVisited').addEventListener('click', () => {
    onlyVisited = !onlyVisited;
    $('#onlyVisited').setAttribute('aria-pressed', String(onlyVisited));
    $('#onlyVisited').textContent = onlyVisited ? '顯示全部' : '只看已踩'; renderCards();
  });
  $('#cards').addEventListener('change', e => { if (e.target.matches('.check')) updateChecked(e.target); });
  $('#cards').addEventListener('click', e => {
    const head = e.target.closest('.region-head'); if (!head) return;
    const section = head.closest('.region-section');
    updateSectionFold(section, head.getAttribute('aria-expanded') === 'true'); saveCollapsed();
  });
  for (const [id, closed] of [['expandAll', false], ['collapseAll', true]]) {
    $('#' + id).addEventListener('click', () => {
      document.querySelectorAll('.region-section').forEach(s => updateSectionFold(s, closed)); saveCollapsed();
    });
  }
  $('#exportBtn').addEventListener('click', exportBackup);
  $('#importFile').addEventListener('change', async e => {
    try { await importBackup(e.target.files[0]); } catch (err) { notify(`無法匯入：${err.message}。原紀錄未變更。`, true); }
    e.target.value = '';
  });
  window.addEventListener('storage', e => {
    if (e.key === STORAGE) { loadState(); render(); }
    if (e.key === COLLAPSE_STORAGE) { collapsed = readObject(COLLAPSE_STORAGE) || {}; renderCards(); }
  });
}
async function init() {
  try {
    const parts = await Promise.all([1,2,3,4].map(async i => {
      const r = await fetch(`data.${i}.txt`); if (!r.ok) throw new Error('data'); return r.text();
    }));
    const bytes = Uint8Array.from(atob(parts.join('').replace(/\s/g, '')), c => c.charCodeAt(0));
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    const data = JSON.parse(await new Response(stream).text());
    if (!Array.isArray(data) || data.length !== 700 || new Set(data.map(s => s.id)).size !== 700) throw new Error('Invalid catalogue');
    spots = data.map((s, order) => ({...s, order}));
    byId = new Map(spots.map(s => [s.id, s]));
    const existing = [...new Set(spots.map(s => s.region))];
    regions = [...REGION_ORDER.filter(r => existing.includes(r)), ...existing.filter(r => !REGION_ORDER.includes(r))];
    byRegion = new Map(regions.map(r => [r, spots.filter(s => s.region === r)]));
    loadState(); ready = true; bindUI(); render();
  } catch {
    $('#empty').hidden = false;
    $('#empty').textContent = '景點載入失敗，請重新整理或更新瀏覽器。本機勾選紀錄未被清除。';
    $('#visibleCount').textContent = '無法載入景點';
  }
}
init();
