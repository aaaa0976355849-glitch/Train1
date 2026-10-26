"""Keep checklist interactions in place; retain deployed storage and photo assets."""
from pathlib import Path
import hashlib
root=Path('japan-checklist')
p=root/'app.js';app=p.read_text()
new='''function updateChecked(input) {
  const el = input.closest('.spot'), id = el.dataset.id, spot = byId.get(id);
  const done = input.checked;
  // Keep the clicked card and native focus in place. Reparenting a focused
  // checkbox during its change event can make mobile browsers follow it.
  // Checked-first sorting still runs on the next deliberate filter or reload.
  state[id] = {...state[id], checked: done, visited: done, status: done ? '已去' : '待確認'};
  saveState();
  el.classList.toggle('visited', done);
  const section = el.closest('.region-section'), grid = section.querySelector('.region-cards');
  section.querySelector('.region-count').textContent = regionLabel(spot.region);
  renderProgress();
  if (onlyVisited && !done) {
    // Remove only this filtered-out card, not every section and loaded photo.
    const left = window.scrollX, top = window.scrollY;
    const hadFocus = document.activeElement === input;
    const next = el.nextElementSibling?.querySelector('.check') ||
      el.previousElementSibling?.querySelector('.check');
    el.remove();
    if (!grid.children.length) section.remove();
    const count = $('#cards').querySelectorAll('.spot').length;
    $('#visibleCount').textContent = `目前顯示 ${count} 個景點`;
    $('#empty').hidden = count !== 0;
    if (hadFocus) {
      const target = next?.isConnected ? next :
        $('#cards').querySelector('.region-head') || $('#onlyVisited');
      target.focus({preventScroll: true});
    }
    // Keep the viewport unless the remaining page is naturally shorter.
    window.scrollTo({left, top, behavior: 'instant'});
  }
}
'''
a=app.index('function updateChecked(input) {');b=app.index('function updatePrefs() {',a)
old=app[a:b]
assert 'grid.appendChild(node)' in old or old==new, 'Unexpected concurrent checkbox changes'
p.write_text(app[:a]+new+app[b:])
p=root/'style.css';css=p.read_text();old='.spot.visited{border:2px solid var(--accent)}';new='.spot.visited{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}'
assert old in css or new in css
p.write_text(css.replace(old,new))
p=root/'index.html';html=p.read_text();html=html.replace('style.css?v=20260912-3','style.css?v=20261026-scroll-1').replace('app.js?v=20260912-3','app.js?v=20261026-scroll-1')
note='    <p>勾選與取消時卡片保持原位，不會跳回頂端；重新整理或切換篩選時，已勾選的景點會排在前面。</p>\n'
if note not in html:html=html.replace('    <p>紀錄保存在這台裝置',note+'    <p>紀錄保存在這台裝置')
p.write_text(html)
p=root/'README.md';readme=p.read_text()
heading='## 勾選位置修正（2026-10-26）'
if heading not in readme:
    first,rest=readme.split('\n',1)
    readme=first+'\n\n'+heading+'\n\n勾選與取消只更新原卡片、儲存紀錄與完成度，不會立刻將正在操作的卡片移到地區最前面，也不會重新聚焦搬移後的勾選框。已勾選置前仍在重新載入頁面或重新篩選時套用。勾選邊框不再改變卡片尺寸；「只看已踩」取消時僅移除該卡片並保留捲動位置，若剩餘頁面比視窗更短，瀏覽器仍會自然縮減可捲動範圍。\n\n沿用原有 localStorage 儲存位置，700 景點、圖片檔、照片清單與授權頁未變更。\n'+rest
p.write_text(readme)
for name in ['app.js','style.css','index.html']:
    b=(root/name).read_bytes();print(name,hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest())
