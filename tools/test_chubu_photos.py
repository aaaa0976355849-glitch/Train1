"""Verify real local image files, browser loading and persisted travel records."""
import json,hashlib,base64,gzip,re,shutil
from pathlib import Path
from collections import Counter
from functools import partial
from threading import Thread
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path('japan-checklist');OUT=Path('chubu-tests');OUT.mkdir(exist_ok=True)
results=[];complete=False

def check(name,condition,detail=None):
    results.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition:raise AssertionError(name+': '+str(detail))

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_address[1]}/'
GROUPS={'hokkaido':('北海道',45),'tohoku':('東北',78),'kanto':('關東',116),'hokuriku':('北陸信越',65),'tokai':('東海・山梨',68)}
photos={slug:json.loads((ROOT/f'{slug}-photos.json').read_text()) for slug in GROUPS}
new={**photos['hokuriku'],**photos['tokai']};allphotos={k:p for v in photos.values() for k,p in v.items()}
data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
folded={r:True for r in dict.fromkeys(s['region'] for s in data)};folded['北陸信越']=False
seed={'JP15-01':{'visited':True,'status':'已去','note':'保留舊備註','date':'2024-05-06'},'JP20-01':{'visited':True,'status':'想再去'},'JP01-01':{'checked':True}}
bootstrap='if(!localStorage.getItem("__test_seeded")){localStorage.setItem("japan700-simple-collapsed-v1",'+json.dumps(json.dumps(folded,ensure_ascii=False))+');localStorage.setItem("japan700-tracker-v1",'+json.dumps(json.dumps(seed,ensure_ascii=False))+');localStorage.setItem("__test_seeded","1");}'
try:
    check('Original 700 records retained',len(data)==700 and len({x['id'] for x in data})==700)
    check('47 prefectures retained',len({x['prefecture'] for x in data})==47)
    check('New region counts 65 + 68',len(photos['hokuriku'])==65 and len(photos['tokai'])==68)
    check('133 distinct new photographs',len(new)==133 and len({p['sha256'] for p in new.values()})==133)
    check('239 previous photographs retained',sum(len(photos[k]) for k in ['hokkaido','tohoku','kanto'])==239)
    for slug,(region,count) in GROUPS.items():
        check(slug+' catalogue IDs',set(photos[slug])=={s['id'] for s in data if s['region']==region})
        for id,p in photos[slug].items():
            path=ROOT/p['src'];blob=path.read_bytes()
            with Image.open(path) as image:w,h=image.size;image.verify()
            check(id+' physical image and attribution',hashlib.sha256(blob).hexdigest()==p['sha256'] and w>=320 and h>=240 and bool(p['author']) and bool(p['licenseUrl']) and urlparse(p['source']).hostname=='commons.wikimedia.org')
    with sync_playwright() as api:
        chrome=shutil.which('google-chrome') or shutil.which('chromium')
        browser=api.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox'])
        for label,viewport in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':390,'height':844})]:
            context=browser.new_context(viewport=viewport);context.add_init_script(bootstrap)
            outside=[];errors=[]
            def route(req):
                if urlparse(req.request.url).hostname not in ('127.0.0.1','localhost'):outside.append(req.request.url);req.abort()
                else:req.continue_()
            context.route('**/*',route);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(URL);page.wait_for_function('typeof ready!=="undefined"&&ready')
            check(label+' original UI simplified',page.locator('.spot').count()==700 and page.locator('#summary,.spot select,.spot textarea,.spot input[type=date]').count()==0)
            check(label+' progress before filters',page.evaluate('document.querySelector(".region-progress").getBoundingClientRect().top<document.querySelector(".toolbar").getBoundingClientRect().top'))
            for slug in ['hokuriku','tokai']:
                region,count=GROUPS[slug];manifest=photos[slug];ids=list(manifest)
                page.select_option('#region',label=region);page.click('#expandAll')
                check(label+' '+region+' card count',page.locator('.spot').count()==count)
                for id in ids:
                    card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
                    page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return i&&!i.hidden&&i.complete&&i.naturalWidth>0}',arg=id,timeout=12000)
                    check(label+' '+id+' loaded from fixed local path',card.locator('img').evaluate('(i)=>i.dataset.photoKind==="fixed"&&new URL(i.src).origin===location.origin') and card.locator('img').get_attribute('src').endswith(manifest[id]['src']))
                check(label+' '+slug+' credit anchors',page.locator(f'.photo-credit[href^="photo-credits-{slug}.html#"]').count()==count)
                target=ids[-1];box=page.locator(f'[data-id="{target}"] .check');box.check()
                order=page.locator('.spot').evaluate_all('(els)=>els.map(e=>({id:e.dataset.id,checked:e.querySelector(".check").checked}))')
                check(label+' '+slug+' checked-first ordering',next(i for i,x in enumerate(order) if x['id']==target)<next(i for i,x in enumerate(order) if not x['checked']))
                page.reload();page.wait_for_function('ready');page.select_option('#region',label=region)
                check(label+' '+slug+' checked persists',page.locator(f'[data-id="{target}"] .check').is_checked())
                page.locator(f'[data-id="{target}"] .check').uncheck();page.reload();page.wait_for_function('ready');page.select_option('#region',label=region)
                check(label+' '+slug+' unchecked persists',not page.locator(f'[data-id="{target}"] .check').is_checked())
                page.locator('.region-head').click();page.reload();page.wait_for_function('ready');page.select_option('#region',label=region)
                check(label+' '+slug+' collapse persists',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
                page.locator('.region-head').click()
                for pref,n in Counter(p['prefecture'] for p in manifest.values()).items():
                    page.select_option('#pref',label=pref);check(label+' '+pref+' filter',page.locator('.spot').count()==n)
                page.select_option('#pref',value='')
                first=next(s for s in data if s['id']==ids[0]);page.fill('#search',first['name'])
                check(label+' '+slug+' search matches',page.locator(f'[data-id="{ids[0]}"]').count()==1)
                page.fill('#search','');page.click('#onlyVisited')
                check(label+' '+slug+' visited-only',page.locator('.spot').count()==1)
                page.click('#onlyVisited');page.locator('.region-head').scroll_into_view_if_needed();page.wait_for_timeout(500)
                page.screenshot(path=str(OUT/f'{label}-{slug}.png'))
                check(label+' '+slug+' no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                check(label+' '+slug+' no external search',not outside,outside)
            check(label+' old note and date retained',page.evaluate('(()=>{const s=JSON.parse(localStorage.getItem("japan700-tracker-v1"))["JP15-01"];return s.note==="保留舊備註"&&s.date==="2024-05-06";})()'))
            for slug in ['hokkaido','tohoku','kanto']:
                region,count=GROUPS[slug];page.select_option('#region',label=region);page.click('#expandAll')
                for id in photos[slug]:
                    card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
                    page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return i&&!i.hidden&&i.complete&&i.naturalWidth>0}',arg=id,timeout=12000)
                check(label+' regression '+slug+' all photos load',page.locator('.thumb[data-photo-kind="fixed"]:visible').count()==count)
            check(label+' completed regions made no external requests',not outside,outside)
            page.select_option('#region',label='北海道');check(label+' Hokkaido checked state preserved',page.locator('[data-id="JP01-01"] .check').is_checked())
            for slug in ['hokuriku','tokai']:
                page.goto(URL+f'photo-credits-{slug}.html')
                check(label+' '+slug+' complete attribution page',page.locator('article[id]').count()==GROUPS[slug][1] and page.locator('article a[rel=license]').count()==GROUPS[slug][1])
            check(label+' no JS exceptions',not errors,errors);context.close()
        for slug,id in [('hokuriku','JP15-01'),('tokai','JP20-01')]:
            context=browser.new_context();context.add_init_script(bootstrap);outside=[]
            def missing_route(req):
                u=req.request.url
                if f'{slug}-photos.json' in u:req.fulfill(status=404,body='missing')
                elif urlparse(u).hostname not in ('127.0.0.1','localhost'):outside.append(u);req.abort()
                else:req.continue_()
            context.route('**/*',missing_route);page=context.new_page();page.goto(URL);page.wait_for_function('ready');page.select_option('#region',label=GROUPS[slug][0]);page.click('#expandAll');page.locator(f'[data-id="{id}"]').scroll_into_view_if_needed();page.wait_for_timeout(500)
            check(slug+' missing manifest never searches externally',not outside,outside)
            check(slug+' missing manifest has honest fallback',page.locator(f'[data-id="{id}"] .thumb-fallback').is_visible())
            context.close()
        browser.close()
    complete=True
finally:
    server.shutdown();(OUT/'results.json').write_text(json.dumps({'complete':complete,'passed':sum(x['passed'] for x in results),'total':len(results),'checks':results},ensure_ascii=False,indent=2))
print('PASS',len(results),'/',len(results),'checks; complete=',complete)
