"""Generate attribution for new regions and switch to static photos only."""
from pathlib import Path
import base64,gzip,hashlib,html,json,re,shutil
ROOT=Path('japan-checklist')
REGIONS={'hokkaido':('北海道',45),'tohoku':('東北',78),'kanto':('關東',116),'hokuriku':('北陸信越',65),'tokai':('東海・山梨',68),'kansai':('關西',114),'chugoku':('中國地方',54),'shikoku':('四國',41),'kyushu':('九州',92),'okinawa':('沖繩',27)}
NEW=['kansai','chugoku','shikoku','kyushu','okinawa']
esc=lambda value:html.escape(str(value),quote=True)
def creditfile(slug):return 'photo-credits.html' if slug=='hokkaido' else f'photo-credits-{slug}.html'
def page(title,body):
    return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1050px;margin:0 auto;padding:24px;background:#f6f1ea;color:#30271f}a{color:#8e251d;overflow-wrap:anywhere}article{padding:20px;margin:24px 0;background:#fffdf9;border:1px solid #e6d9ca;border-radius:16px;scroll-margin-top:15px}h1{line-height:1.3}h2{font-size:20px;margin:0 0 12px}p{overflow-wrap:anywhere;margin:8px 0}img{display:block;max-width:100%;width:360px;max-height:260px;object-fit:contain;background:#eee}nav{display:flex;flex-wrap:wrap;gap:12px}</style></head><body><a href="./">← 回到踩點圖鑑</a><h1>'+esc(title)+'</h1>'+body+'</body></html>\n'
def main():
    allphotos={}
    for slug,(name,count) in REGIONS.items():
        path=ROOT/f'{slug}-photos.json';data=json.loads(path.read_text())
        assert len(data)==count,(slug,len(data))
        for id,p in data.items():
            assert re.fullmatch(r'JP\d{2}-\d{2}',id)
            assert p['src'].startswith('images/'+slug+'/')
            assert hashlib.sha256((ROOT/p['src']).read_bytes()).hexdigest()==p['sha256'],id
            assert p['author'] and p['licenseUrl'] and p['source'],id
        if slug in NEW:
            for id in ['JP26-06','JP26-07','JP26-08','JP30-06','JP40-05','JP46-11']:
                if id in data:data[id]['fit']='contain'
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            intro='<p>照片依各自授權使用。請保留作者、作品名稱、來源及授權連結；CC BY-SA 縮圖與裁切顯示版本沿用原圖授權。照片年代與季節各異，不代表現在的開放狀況。</p><p>合併景點以其中一處代表性景色配圖；場地日景、所在公園或遠景會另外標示，不將其當作展覽或設施近照。</p><a href="photo-credits-index.html">所有地區照片來源</a>'
            parts=[]
            for id,p in data.items():
                parts.append(f'<article id="{esc(id)}"><h2>{esc(id)} · {esc(p["name"])}</h2><img src="{esc(p["src"])}" alt="{esc(p.get("caption",p["name"]))}" loading="lazy"><p>作品：{esc(p["filename"])}</p><p>作者：{esc(p["author"])}</p><p>授權：<a href="{esc(p["licenseUrl"])}">{esc(p["license"])}</a> · <a href="{esc(p["source"])}">原始作品與來源資料</a></p><p>{esc(p["changes"])}</p>'+ (f'<p>配圖說明：{esc(p["caption"])}</p>' if p.get('caption') else '')+'</article>')
            (ROOT/creditfile(slug)).write_text(page(name+'照片來源與授權',intro+'\n'+'\n'.join(parts)))
        allphotos.update(data)
    assert len(allphotos)==700
    catalogue=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    assert set(allphotos)=={s['id'] for s in catalogue}
    links=''.join(f'<p><a href="{creditfile(s)}">{esc(name)} · {count} 張照片</a></p>' for s,(name,count) in REGIONS.items())
    (ROOT/'photo-credits-index.html').write_text(page('700 景點照片來源與授權','<p>全站使用預先選定、存放於本站的固定照片。此頁連往每張照片的作者、來源、個別授權與配圖說明。</p>'+links))
    shutil.copyfile('tools/west/photos-static.js',ROOT/'photos.js')
    index=(ROOT/'index.html').read_text()
    index=re.sub(r'photos.js\?v=[^"\s]+','photos.js?v=all-static-1',index)
    index=re.sub(r'<p>(?:北海道 45 個|全站 700 個景點).*?</p>','<p>全站 700 個景點均配置事先選定、儲存於本站的固定照片，不再即時搜尋。點照片署名可查看作者、來源與授權。少數展覽與園區使用實際場地日景或遠景，會在照片上標示；合併景點以其中一處代表性景色配圖。</p>',index,count=1,flags=re.S)
    index=re.sub(r'<footer>.*?</footer>','<footer>700 景點 · 47 都道府縣 · 固定照片收藏版 · <a href="photo-credits-index.html">全部照片來源與授權</a></footer>',index,flags=re.S)
    (ROOT/'index.html').write_text(index)
    print('Integrated all 700 fixed photographs. App, CSS, data and browser storage keys unchanged.')
if __name__=='__main__':main()
