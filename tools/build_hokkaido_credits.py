"""Build a static, script-free attribution page from the reviewed manifest."""
from pathlib import Path
from html import escape
import json,hashlib,re,sys
from urllib.parse import urlparse
root=Path(sys.argv[1])
data=json.loads((root/'hokkaido-photos.json').read_text())
assert len(data)==45
h=lambda x:escape(str(x),quote=True)
parts=['''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>北海道照片來源與授權｜日本景點踩點圖鑑</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f1ea;color:#2f261f;font:16px/1.65 system-ui,-apple-system,"Noto Sans TC",sans-serif}main{max-width:1040px;margin:auto;padding:28px 20px}h1{font-size:28px}a{color:#9f221b;overflow-wrap:anywhere}section{background:#fffdf9;border:1px solid #e6d9ca;border-radius:16px;padding:18px;display:grid;grid-template-columns:200px 1fr;gap:20px;margin:18px 0;scroll-margin-top:20px}section:target{outline:3px solid #b42318}img{width:100%;height:auto;border-radius:8px}h2{font-size:19px;margin:0 0 8px}p{margin:6px 0;overflow-wrap:anywhere}.filename{color:#6d5948;font-size:13px}.notice{border-left:4px solid #b42318;padding:8px 18px;background:#fffdf9}@media(max-width:580px){section{grid-template-columns:1fr}img{max-height:220px;object-fit:contain;background:#f2eee8}h1{font-size:23px}}
</style></head><body><main><a href="./">← 回到踩點圖鑑</a><h1>北海道照片來源與授權</h1><p>45 個景點，各自對應固定照片。照片檔案已儲存在本網站；瀏覽北海道時不呼叫圖片搜尋服務。</p><div class="notice"><p>照片著作權屬各原作者。本網站依下方逐張列出的授權使用；未表示作者為本網站背書。公有領域照片亦保留來源。</p><p>處理方式：使用縮圖；圖鑑卡片以 4:3 比例裁切顯示，未以生成方式增刪景物。照片及其裁切顯示版本沿用下列各自授權，包含 CC BY-SA 的相同方式分享條件。點「原始檔案與授權說明」可查看原圖、拍攝資訊與完整授權。本頁縮圖保留原比例。</p><p>照片拍攝時間各異，僅用於辨識景點，不代表今日現況；多個景點合併為一項時，以其中具代表性的一處配圖。</p></div>''']
for id,v in sorted(data.items()):
    assert re.fullmatch('JP01-[0-9]{2}',id)
    assert re.fullmatch(r'images/hokkaido/JP01-[0-9]{2}\.(jpg|png|webp)',v['src'])
    assert hashlib.sha256((root/v['src']).read_bytes()).hexdigest()==v['sha256']
    assert urlparse(v['source']).hostname=='commons.wikimedia.org'
    assert urlparse(v['licenseUrl']).scheme=='https'
    parts.append(f'''<section id="{id}"><img src="{h(v['src'])}" width="200" alt="{h(v['name'])}" loading="lazy"><div><h2>{id} · {h(v['name'])}</h2><p>作者／署名：{h(v['author'])}</p><p>授權：<a href="{h(v['licenseUrl'])}" target="_blank" rel="noopener noreferrer">{h(v['license'])}</a></p><p><a href="{h(v['source'])}" target="_blank" rel="noopener noreferrer">原始檔案與授權說明（Wikimedia Commons）</a></p><p class="filename">作品名稱：{h(v['filename'])}</p><p class="filename">{h(v['changes'])}</p></div></section>''')
parts.append('<p><a href="./">← 回到踩點圖鑑</a></p></main></body></html>')
(root/'photo-credits.html').write_text('\n'.join(parts)+'\n')
print('credits:',len(data),'bytes',(root/'photo-credits.html').stat().st_size)
