"""Real-browser checks use isolated localStorage and local HTTP; no user records."""
import base64,gzip,hashlib,json,re,shutil
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse
from collections import Counter
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path('japan-checklist');OUT=Path('west-tests');OUT.mkdir(exist_ok=True)
GROUPS={'hokkaido':('北海道',45),'tohoku':('東北',78),'kanto':('關東',116),'hokuriku':('北陸信越',65),'tokai':('東海・山梨',68),'kansai':('關西',114),'chugoku':('中國地方',54),'shikoku':('四國',41),'kyushu':('九州',92),'okinawa':('沖繩',27)}
results=[];complete=False;reports={}
def check(name,value,detail=None):
    results.append({'name':name,'passed':bool(value),'detail':detail})
    if not value:raise AssertionError(name+': '+str(detail))
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start();URL=f'http://127.0.0.1:{server.server_address[1]}/'
try:
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    check('Catalogue has 700 distinct IDs and 47 prefectures',len(data)==700 and len({s['id'] for s in data})==700 and len({s['prefecture'] for s in data})==47)
    manifests={slug:json.loads((ROOT/f'{slug}-photos.json').read_text()) for slug in GROUPS}
    allphotos={id:v for m in manifests.values() for id,v in m.items()}
    check('Every catalogue ID has one fixed photograph',set(allphotos)=={s['id'] for s in data})
    for slug,(name,total) in GROUPS.items():
        m=manifests[slug];check(name+' complete manifest',len(m)==total)
        for id,v in m.items():
            path=ROOT/v['src'];blob=path.read_bytes()
            with Image.open(path) as img:w,h=img.size;img.verify()
            check(id+' file integrity and licensing',hashlib.sha256(blob).hexdigest()==v['sha256'] and min(w,h)>=240 and v['author'] and v['licenseUrl'] and v['source'].startswith('https://commons.wikimedia.org/wiki/File:'))
    photosjs=(ROOT/'photos.js').read_text()
    check('Runtime search code removed',not re.search(r'w/api.php|wikipedia.org|async function lookup|pageimages|sessionStorage',photosjs))
    folded={name:True for name,_ in GROUPS.values()}
    seed={'JP25-01':{'visited':True,'status':'想再去','note':'retain note','date':'2024-01-01'},'JP01-01':{'checked':True}}
    bootstrap="if(!localStorage.getItem('__seeded')){localStorage.setItem('japan700-tracker-v1',"+json.dumps(json.dumps(seed))+");localStorage.setItem('japan700-simple-collapsed-v1',"+json.dumps(json.dumps(folded))+");localStorage.setItem('__seeded','yes');}"
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
        for label,viewport in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':390,'height':844})]:
            context=browser.new_context(viewport=viewport);context.add_init_script(bootstrap)
            outside=[];errors=[]
            def route(r):
                if urlparse(r.request.url).hostname!='127.0.0.1':outside.append(r.request.url);r.abort()
                else:r.continue_()
            context.route('**/*',route);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(URL);page.wait_for_function('typeof ready!=="undefined" && ready')
            check(label+' all 700 cards',page.locator('.spot').count()==700)
            check(label+' no unwanted controls',page.locator('#summary,.spot select,.spot textarea,.spot input[type=date]').count()==0)
            check(label+' legacy tick retained',page.locator('[data-id="JP25-01"] .check').is_checked())
            for slug,(name,total) in GROUPS.items():
                page.select_option('#region',label=name)
                head=page.locator('.region-head')
                if head.get_attribute('aria-expanded')!='true':head.click()
                check(label+' '+name+' count',page.locator('.spot').count()==total)
                for id in manifests[slug]:
                    card=page.locator(f'[data-id="{id}"]');card.evaluate('(e)=>e.scrollIntoView({block:"center"})')
                    page.wait_for_function('(id)=>{let i=document.querySelector(`[data-id="${id}"] img.thumb`);return i&&!i.hidden&&i.complete&&i.naturalWidth>0}',arg=id,timeout=15000)
                    check(label+' '+id+' real local photo',card.locator('img').evaluate('(i)=>i.dataset.photoKind==="fixed"&&new URL(i.src).origin===location.origin'))
                check(label+' '+name+' credit links',page.locator('.photo-credit[href*="#JP"]').count()==total)
                if slug in ['kansai','chugoku','shikoku','kyushu','okinawa']:
                    for pref,count in Counter(x['prefecture'] for x in manifests[slug].values()).items():
                        page.select_option('#pref',label=pref);check(label+' prefecture filter '+pref,page.locator('.spot').count()==count)
                    page.select_option('#pref',value='')
                    page.locator('.region-head').evaluate('(e)=>e.scrollIntoView()');page.wait_for_timeout(200)
                    page.screenshot(path=str(OUT/f'{label}-{slug}.png'))
                check(label+' '+name+' no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            check(label+' no outside requests for all 700',not outside,outside)
            page.select_option('#region',label='關西')
            page.locator('[data-id="JP25-05"] .check').check()
            check(label+' checked-first sorting',page.locator('.spot').nth(1).get_attribute('data-id')=='JP25-05')
            page.reload();page.wait_for_function('ready');page.select_option('#region',label='關西')
            check(label+' check persists after reload',page.locator('[data-id="JP25-05"] .check').is_checked())
            check(label+' old notes and dates retained',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP25-01'].note==='retain note'&&JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP25-01'].date==='2024-01-01'"))
            page.locator('[data-id="JP25-05"] .check').uncheck();page.reload();page.wait_for_function('ready');page.select_option('#region',label='關西')
            check(label+' untick persists after reload',not page.locator('[data-id="JP25-05"] .check').is_checked())
            check(label+' untick restores original order',page.locator('.spot').nth(1).get_attribute('data-id')=='JP25-02')
            page.locator('[data-id="JP25-01"] .check').uncheck();page.reload();page.wait_for_function('ready');page.select_option('#region',label='關西')
            check(label+' old revisit tick can be cleared',not page.locator('[data-id="JP25-01"] .check').is_checked())
            page.locator('.region-head').click();page.reload();page.wait_for_function('ready');page.select_option('#region',label='關西')
            check(label+' collapse persists',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
            page.click('#expandAll');check(label+' expand all works',page.locator('.region-cards').evaluate('(e)=>!e.hidden'))
            page.fill('#search','清水寺');check(label+' search',page.locator('.spot').count()==1)
            page.fill('#search','');page.click('#onlyVisited');check(label+' visited filter empty after untick',page.locator('.spot').count()==0)
            page.click('#onlyVisited');page.select_option('#region',label='北海道')
            check(label+' previous region tick retained',page.locator('[data-id="JP01-01"] .check').is_checked())
            page.select_option('#region',label='關西');page.fill('#search','teamLab Botanical Garden')
            page.locator('.spot').evaluate('(e)=>e.scrollIntoView()');page.wait_for_selector('.photo-note')
            check(label+' venue image clearly labelled','場地日景' in page.locator('.photo-note').inner_text())
            page.goto(URL+'photo-credits-index.html');check(label+' all ten credit pages indexed',page.locator('a[href^="photo-credits"]').count()==10)
            for slug in ['kansai','chugoku','shikoku','kyushu','okinawa']:
                page.goto(URL+f'photo-credits-{slug}.html');check(label+' '+slug+' attribution entries',page.locator('article[id]').count()==GROUPS[slug][1])
                check(label+' '+slug+' licenses linked',page.locator('article a[href*="creativecommons.org"]').count()==GROUPS[slug][1])
            check(label+' no JavaScript exceptions',not errors,errors)
            reports[label]={'externalRequests':outside,'pageErrors':errors,'photosLoaded':700};context.close()
        for mode in ['manifest','image']:
            context=browser.new_context();outside=[]
            def broken(r):
                u=r.request.url
                if (mode=='manifest' and 'kansai-photos.json' in u) or (mode=='image' and '/images/kansai/JP25-01.' in u):r.fulfill(status=404,body='not found')
                elif urlparse(u).hostname!='127.0.0.1':outside.append(u);r.abort()
                else:r.continue_()
            context.route('**/*',broken);page=context.new_page();page.goto(URL);page.wait_for_function('ready');page.select_option('#region',label='關西');card=page.locator('[data-id="JP25-01"]');card.evaluate('(e)=>e.scrollIntoView()')
            page.wait_for_function('document.querySelector("[data-id=JP25-01] .thumb-fallback").textContent.includes("失敗")')
            check(mode+' failure has honest fallback and no search',card.locator('.thumb-fallback').is_visible() and not outside,outside);context.close()
        browser.close()
    complete=True
finally:
    server.shutdown()
    report={'complete':complete,'passed':sum(x['passed'] for x in results),'total':len(results),'browsers':reports,'checks':results}
    (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PASS',len(results),'checks')
