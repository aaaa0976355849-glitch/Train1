"""Integrate only reviewed fixed images; preserve the catalogue and storage code."""
from pathlib import Path
from html import escape as E
from urllib.parse import urlparse
import json,gzip,base64,hashlib,re
ROOT=Path('japan-checklist')
GROUPS={'hokuriku':('北陸信越',65),'tokai':('東海・山梨',68)}
data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
for slug,(label,count) in GROUPS.items():
    photos=json.loads((ROOT/f'{slug}-photos.json').read_text())
    wanted=[s for s in data if s['region']==label]
    assert len(wanted)==count and set(photos)=={s['id'] for s in wanted}
    assert len({p['sha256'] for p in photos.values()})==count
    blocks=[]
    for spot in wanted:
        id=spot['id'];p=photos[id]
        assert re.fullmatch('images/'+slug+'/'+id+r'\.(jpg|png|webp)',p['src'])
        assert hashlib.sha256((ROOT/p['src']).read_bytes()).hexdigest()==p['sha256']
        assert urlparse(p['source']).hostname=='commons.wikimedia.org'
        assert urlparse(p['licenseUrl']).hostname=='creativecommons.org'
        assert p['author'] and p['license']
        caption=p.get('caption','本圖展示此景點；複合景點以其中一處具代表性的景色配圖。')
        if id=='JP21-14':caption='堂之島海蝕洞入口與海岸景觀；本圖不是洞內天窗角度。'
        blocks.append(f'<article id="{id}"><img src="{E(p["src"],quote=True)}" alt="{E(spot["name"],quote=True)}" loading="lazy"><div><h2>{E(spot["name"])}</h2><p>{E(caption)}</p><p>作者：{E(p["author"])}</p><p>作品：{E(p["filename"])}</p><p><a href="{E(p["source"],quote=True)}">原圖與來源</a> · <a rel="license" href="{E(p["licenseUrl"],quote=True)}">{E(p["license"])}</a></p><p>{E(p["changes"])}</p></div></article>')
    page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LABEL圖片授權</title><style>body{font:16px/1.7 system-ui,sans-serif;margin:0;background:#f6f1ea;color:#302820}main{max-width:1000px;margin:auto;padding:24px}article{display:flex;gap:20px;padding:20px;margin:18px 0;border:1px solid #e6d9ca;border-radius:16px;background:#fffdf9;scroll-margin-top:18px}article img{width:220px;height:165px;object-fit:contain}article div{min-width:0}p{overflow-wrap:anywhere;margin:.5em 0}h2{font-size:20px;margin:0}a{color:#9c261e}@media(max-width:600px){article{display:block}article img{width:100%;height:200px}}</style><main><a href="index.html">← 回到景點圖鑑</a><h1>LABEL・固定照片出處</h1><p>COUNT 個景點的圖片已儲存在本網站，不進行即時搜尋。各圖片依原授權使用；CC BY-SA 圖片的裁切顯示版本沿用原圖授權。季節與拍攝日期各異，不代表即時現況。</p>'''.replace('LABEL',label).replace('COUNT',str(count))+'\n'+'\n'.join(blocks)+'\n</main></html>\n'
    (ROOT/f'photo-credits-{slug}.html').write_text(page)
f=ROOT/'photos.js';s=f.read_text()
old="/^JP(?:0[89]|1[0-4])-\\d{2}$/.test(id) ? 'kanto' : '';"
new="/^JP(?:0[89]|1[0-4])-\\d{2}$/.test(id) ? 'kanto' :\n    /^JP1[5-9]-\\d{2}$/.test(id) ? 'hokuriku' :\n    /^JP2[0-4]-\\d{2}$/.test(id) ? 'tokai' : '';"
if old in s:s=s.replace(old,new,1)
else:assert new in s
old="kanto: loadFixed('kanto')};";new="kanto: loadFixed('kanto'), hokuriku: loadFixed('hokuriku'), tokai: loadFixed('tokai')};"
if old in s:s=s.replace(old,new,1)
else:assert new in s
s=s.replace('kanto-static-1','chubu-static-1');f.write_text(s)
f=ROOT/'index.html';s=f.read_text().replace('photos.js?v=kanto-static-1','photos.js?v=chubu-static-1')
text='北海道 45 個、東北 78 個、關東 116 個、北陸信越 65 個、東海・山梨 68 個景點使用預先挑選並儲存在本站的固定照片，瀏覽這五區時不搜尋圖片。點照片署名可查看作者、來源與授權；圖片依各自授權使用，部分採完整比例、其餘裁切顯示。其他地區尚未完成固定配圖。'
s=re.sub(r'<p>北海道 45 個.*?</p>',lambda m:'<p>'+text+'</p>',s,flags=re.S)
if 'photo-credits-hokuriku.html' not in s:s=s.replace('</footer>',' · <a href="photo-credits-hokuriku.html">北陸信越圖片授權</a> · <a href="photo-credits-tokai.html">東海・山梨圖片授權</a></footer>')
f.write_text(s)
print('Integrated 65 + 68 fixed photos; catalogue, app.js and style.css are untouched.')
