"""Integrate fixed Kanto photographs without changing travel records or catalogue."""
import base64,gzip,hashlib,html,json,re
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path('japan-checklist')
photos=json.loads((ROOT/'kanto-photos.json').read_text())
data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
kanto=[s for s in data if s['region']=='關東']
assert len(photos)==116 and set(photos)=={s['id'] for s in kanto}
assert len({v['sha256'] for v in photos.values()})==116
for s in kanto:
    v=photos[s['id']]
    assert v['name']==s['name'] and v['prefecture']==s['prefecture']
    assert re.fullmatch('images/kanto/'+re.escape(s['id'])+r'\.(jpg|png|webp)',v['src'])
    assert hashlib.sha256((ROOT/v['src']).read_bytes()).hexdigest()==v['sha256']
    assert v['author'] and urlparse(v['licenseUrl']).hostname=='creativecommons.org'
    assert urlparse(v['source']).hostname=='commons.wikimedia.org'
expected={'app.js':'4eae57bec4b3095f1bc2db15634a2bcd572110db','style.css':'556efff28f30850a6f117638f902e4fd2de64dc9','data.1.txt':'d54f6d69608518517a5dd598f23d14a25dd26f08','data.2.txt':'254c08deff6bc7147095d87f13701b535cb7a9b7','data.3.txt':'60fe0fccfaa95b83bb6cc85bd4caa75d58d19ba5','data.4.txt':'89db6f9b21af714097d1793c66ab21938fee2195'}
for name,sha in expected.items():
    blob=(ROOT/name).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==sha,name
p=ROOT/'photos.js';js=p.read_text()
old="/^JP0[2-7]-\\d{2}$/.test(id) ? 'tohoku' : '';"
new="/^JP0[2-7]-\\d{2}$/.test(id) ? 'tohoku' :\n    /^JP(?:0[89]|1[0-4])-\\d{2}$/.test(id) ? 'kanto' : '';"
if old in js:js=js.replace(old,new,1)
else:assert new in js
js=js.replace("tohoku: loadFixed('tohoku')}","tohoku: loadFixed('tohoku'), kanto: loadFixed('kanto')}")
old="fixedRegion(photo.fixedId) === 'tohoku' ? 'photo-credits-tohoku.html' : 'photo-credits.html'"
new="fixedRegion(photo.fixedId) === 'hokkaido' ? 'photo-credits.html' : 'photo-credits-' + fixedRegion(photo.fixedId) + '.html'"
if old in js:js=js.replace(old,new)
else:assert new in js
js=js.replace('tohoku-static-1','kanto-static-1')
needle="img.loading = 'eager'; img.referrerPolicy"
replacement="img.style.objectFit = fixed && photo.fit === 'contain' ? 'contain' : 'cover';\n    img.loading = 'eager'; img.referrerPolicy"
if "img.style.objectFit = fixed" not in js:
    assert needle in js;js=js.replace(needle,replacement)
p.write_text(js)
p=ROOT/'index.html';page=p.read_text().replace('photos.js?v=tohoku-static-1','photos.js?v=kanto-static-1')
page=page.replace('北海道 45 個、東北 78 個景點','北海道 45 個、東北 78 個、關東 116 個景點').replace('瀏覽這兩區時','瀏覽這三區時')
link=' · <a href="photo-credits-kanto.html">關東圖片授權</a>'
if link not in page:page=page.replace('</footer>',link+'</footer>')
p.write_text(page)
e=lambda x:html.escape(str(x),quote=True)
style=re.search(r'<style>(.*?)</style>',(ROOT/'photo-credits-tohoku.html').read_text(),re.S).group(1)
out=['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>關東照片來源與授權 · 日本景點踩點圖鑑</title><style>'+style+'</style></head><body><main>',
'<p><a href="index.html">← 返回踩點圖鑑</a> · <a href="photo-credits.html">北海道</a> · <a href="photo-credits-tohoku.html">東北</a></p><h1>關東 116 張固定照片：來源與授權</h1>',
'<p>照片預先選定並存放於本網站，不於瀏覽時搜尋。各作品按下列授權重用，縮圖與裁切顯示沿用原圖授權。照片季節與拍攝時間不一，不代表今日現況；合併多處景點時以其中一處代表性景色配圖。</p>']
pref=None
for s in kanto:
    if s['prefecture']!=pref:
        pref=s['prefecture'];out.append('<h2>'+e(pref)+'</h2>')
    v=photos[s['id']];id=s['id'];fit='contain' if v.get('fit')=='contain' else 'cover'
    out.append(f'<article id="{e(id)}"><img src="{e(v["src"])}" alt="{e(s["name"])}" loading="lazy" width="240" height="180" style="object-fit:{fit}"><div><h3>{e(s["name"])} <small>{e(id)}</small></h3><p>作者：{e(v["author"])}</p><p>授權：<a href="{e(v["licenseUrl"])}" target="_blank" rel="noopener noreferrer">{e(v["license"])}</a> · <a href="{e(v["source"])}" target="_blank" rel="noopener noreferrer">原圖與來源頁</a></p><p class="filename">作品：{e(v["filename"])}</p><p>{e(v["changes"])}</p><p>{e(v.get("caption",""))}</p></div></article>')
out.append('</main></body></html>');(ROOT/'photo-credits-kanto.html').write_text('\n'.join(out)+'\n')
print('Integrated 116 fixed photos; original catalogue, style and app code unchanged.')
