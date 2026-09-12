"""Integrate reviewed fixed assets; do not modify catalogue or travel-state code."""
from pathlib import Path
from html import escape as h
from urllib.parse import urlparse
import json,hashlib
from PIL import Image
ROOT=Path('japan-checklist')
s=(ROOT/'photos.js').read_text()
if 'const fixedRegion =' not in s:
    start=s.index('  // Fixed, locally hosted photographs:');end=s.index('  const aliases =',start)
    block=r'''  // Fixed photographs are served locally. Never search for these IDs at runtime.
  const fixedRegion = id => /^JP01-\d{2}$/.test(id) ? 'hokkaido' :
    /^JP0[2-7]-\d{2}$/.test(id) ? 'tohoku' : '';
  const localPhoto = (id, src) => typeof src === 'string' && !!fixedRegion(id) &&
    new RegExp('^images/' + fixedRegion(id) + '/' + id + '\\.(jpg|png|webp)$').test(src);
  function loadFixed(region) {
    return fetch(`${region}-photos.json?v=tohoku-static-1`, {credentials:'same-origin'})
      .then(r => { if (!r.ok) throw new Error('Fixed catalogue unavailable'); return r.json(); })
      .then(data => {
        if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
        const valid = {};
        for (const [id, photo] of Object.entries(data)) {
          if (fixedRegion(id) === region && photo && localPhoto(id, photo.src) &&
              safeURL(photo.source, 'commons.wikimedia.org') && photo.author && photo.license) {
            valid[id] = {...photo, fixedId:id};
          }
        }
        return valid;
      }).catch(() => ({}));
  }
  const fixedPhotos = {hokkaido: loadFixed('hokkaido'), tohoku: loadFixed('tohoku')};
'''
    s=s[:start]+block+s[end:]
    s=s.replace('if (isHokkaido(spot.id)) return fixedPhotos.then(photos => photos[spot.id] || null);','if (fixedRegion(spot.id)) return fixedPhotos[fixedRegion(spot.id)].then(photos => photos[spot.id] || null);')
    s=s.replace('credit.href = fixed ? `photo-credits.html#${photo.fixedId}` : source;',"credit.href = fixed ? `${fixedRegion(photo.fixedId) === 'tohoku' ? 'photo-credits-tohoku.html' : 'photo-credits.html'}#${photo.fixedId}` : source;")
    (ROOT/'photos.js').write_text(s)
s=(ROOT/'index.html').read_text().replace('photos.js?v=hokkaido-static-1','photos.js?v=tohoku-static-1')
s=s.replace('北海道 45 個項目使用預先挑選並儲存在本網站的固定照片，瀏覽時不搜尋圖片。','北海道 45 個、東北 78 個景點使用預先挑選並儲存在本網站的固定照片，瀏覽這兩區時不搜尋圖片。')
s=s.replace('<a href="photo-credits.html">北海道圖片來源與授權</a>','<a href="photo-credits.html">北海道圖片授權</a> · <a href="photo-credits-tohoku.html">東北圖片授權</a>')
(ROOT/'index.html').write_text(s)
manifest=json.loads((ROOT/'tohoku-photos.json').read_text());assert len(manifest)==78
entries=[]
for prefecture in ['青森','宮城','岩手','秋田','山形','福島']:
    photos=[(id,p) for id,p in manifest.items() if prefecture in p['prefecture']]
    entries.append(f'<section><h2>{h(prefecture)} · {len(photos)} 張</h2>')
    for id,p in sorted(photos):
        f=ROOT/p['src'];assert f.exists() and hashlib.sha256(f.read_bytes()).hexdigest()==p['sha256']
        with Image.open(f) as image:image.verify()
        assert urlparse(p['source']).hostname=='commons.wikimedia.org' and urlparse(p['licenseUrl']).hostname=='creativecommons.org'
        assert p['author'] and p['license']
        entries.append(f'<article id="{h(id)}"><img src="{h(p["src"])}" alt="{h(p["name"])}" loading="lazy" width="240" height="180"><div><h3>{h(p["name"])} <small>{h(id)}</small></h3><p>作者：{h(p["author"])}</p><p>授權：<a href="{h(p["licenseUrl"])}" rel="noopener noreferrer" target="_blank">{h(p["license"])}</a> · <a href="{h(p["source"])}" rel="noopener noreferrer" target="_blank">原圖與來源頁</a></p><p class="filename">作品：{h(p["filename"])}</p><p>{h(p["changes"])}</p></div></article>')
    entries.append('</section>')
head='''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>東北照片來源與授權 · 日本景點踩點圖鑑</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f6f1ea;color:#2f261f;font:16px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Noto Sans CJK TC",sans-serif}main{max-width:1080px;margin:auto;padding:28px 20px}a{color:#9e251d}h1{font-size:28px;line-height:1.35}h2{margin-top:34px;font-size:23px}h3{margin:0;font-size:18px}small{font-size:12px;color:#75685c}p{margin:6px 0}article{display:flex;gap:20px;padding:20px;background:#fffdf9;border:1px solid #e6d9ca;border-radius:15px;margin:14px 0;scroll-margin-top:20px}article img{width:240px;height:180px;object-fit:cover;border-radius:9px}article>div{min-width:0}.filename{font-size:13px;overflow-wrap:anywhere}article p{overflow-wrap:anywhere}article:target{outline:3px solid #b42318}@media(max-width:640px){article{flex-direction:column;padding:14px}article img{width:100%;height:auto;aspect-ratio:4/3}main{padding:20px 14px}}</style></head><body><main><p><a href="index.html">← 返回踩點圖鑑</a> · <a href="photo-credits.html">北海道照片授權</a></p><h1>東北 78 張固定照片：來源與授權</h1><p>照片已預先選定並存放於本網站。各作品分別依下列授權重用，不因本網站的其他內容而改變其原授權；CC BY-SA 作品的裁切顯示版本同樣採原授權。</p><p>照片拍攝時間、季節不同，不代表今日實景。名稱合併多處景點的項目，配圖呈現其中一處代表景色；「乳頭溫泉鄉」以鶴之湯、「八幡平」以八幡沼步道景色呈現。</p>'''
(ROOT/'photo-credits-tohoku.html').write_text(head+'\n'+'\n'.join(entries)+'\n</main></body></html>\n')
print('Integrated 78 static Tohoku photographs and attribution entries')
