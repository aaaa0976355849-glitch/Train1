"""Real images and browser storage, isolated from the user's own data."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse
from collections import Counter
import hashlib,json,shutil
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path('japan-checklist');OUT=Path('kanto-tests');OUT.mkdir(exist_ok=True)
results=[];complete=False
def check(name,ok,detail=None):
    results.append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:raise AssertionError(name+': '+str(detail))
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start();URL=f'http://127.0.0.1:{server.server_address[1]}/'
manifest=json.loads((ROOT/'kanto-photos.json').read_text())
previous={**json.loads((ROOT/'hokkaido-photos.json').read_text()),**json.loads((ROOT/'tohoku-photos.json').read_text())}
allphotos={**previous,**manifest}
check('116 Kanto entries',len(manifest)==116)
check('123 previous fixed photos retained',len(previous)==123)
check('116 distinct photos',len({v['sha256'] for v in manifest.values()})==116)
check('7 prefectures',len({v['prefecture'] for v in manifest.values()})==7)
for id,v in allphotos.items():
    b=(ROOT/v['src']).read_bytes()
    with Image.open(ROOT/v['src']) as img:w,h=img.size;img.verify()
    check(id+' hash, image, credits',hashlib.sha256(b).hexdigest()==v['sha256'] and w>=320 and h>=240 and bool(v['author']) and bool(v['licenseUrl']))
folded={r:True for r in ['北海道','東北','關東','北陸信越','東海・山梨','關西','中國地方','四國','九州','沖繩']};folded['關東']=False
seed={'JP08-02':{'visited':True,'status':'已去','note':'舊紀錄保留','date':'2025-01-01'},'JP01-01':{'checked':True},'JP02-01':{'checked':True}}
bootstrap=f"if(!localStorage.getItem('__test_seeded')){{localStorage.setItem('japan700-simple-collapsed-v1',{json.dumps(json.dumps(folded,ensure_ascii=False))});localStorage.setItem('japan700-tracker-v1',{json.dumps(json.dumps(seed,ensure_ascii=False))});localStorage.setItem('__test_seeded','yes');}}"
try:
  with sync_playwright() as p:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox'])
    for label,size in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':390,'height':844})]:
      ctx=browser.new_context(viewport=size);ctx.add_init_script(bootstrap);outside=[];errors=[]
      def route(req):
        if urlparse(req.request.url).hostname not in ('127.0.0.1','localhost'):outside.append(req.request.url);req.abort()
        else:req.continue_()
      ctx.route('**/*',route);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
      page.goto(URL);page.wait_for_function('typeof ready!=="undefined" && ready')
      check(label+' 700 cards retained',page.locator('.spot').count()==700)
      check(label+' no extra card controls',page.locator('#summary,.spot select,.spot textarea,.spot input[type=date]').count()==0)
      check(label+' progress above filters',page.locator('.region-progress').bounding_box()['y']<page.locator('.toolbar').bounding_box()['y'])
      check(label+' legacy tick preserved',page.locator('[data-id="JP08-02"] .check').is_checked())
      page.select_option('#region',label='關東');check(label+' 116 Kanto cards',page.locator('.spot').count()==116)
      for id in manifest:
        card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
        page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return i&&!i.hidden&&i.complete&&i.naturalWidth>0}',arg=id,timeout=12000)
        check(label+' '+id+' local photo',card.locator('img').evaluate('(i)=>i.dataset.photoKind==="fixed"&&new URL(i.src).origin===location.origin'))
      check(label+' portrait tower kept whole',page.locator('[data-id="JP08-02"] img').evaluate('(i)=>getComputedStyle(i).objectFit==="contain"'))
      check(label+' 116 attribution anchors',page.locator('.photo-credit[href^="photo-credits-kanto.html#"]').count()==116)
      check(label+' no external image search',not outside,outside)
      page.locator('[data-id="JP10-01"] .check').check()
      check(label+' checked-first sorting',page.locator('.spot').nth(1).get_attribute('data-id')=='JP10-01')
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='關東')
      check(label+' tick after reload',page.locator('[data-id="JP10-01"] .check').is_checked())
      check(label+' old notes and dates preserved',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP08-02'].note==='舊紀錄保留' && JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP08-02'].date==='2025-01-01'"))
      page.locator('[data-id="JP10-01"] .check').uncheck();page.reload();page.wait_for_function('ready');page.select_option('#region',label='關東')
      check(label+' untick after reload',not page.locator('[data-id="JP10-01"] .check').is_checked())
      check(label+' original order restored',page.locator('.spot').nth(1).get_attribute('data-id')=='JP08-01')
      page.locator('.region-head').click();check(label+' collapse works',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='關東')
      check(label+' collapse persists',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.locator('.region-head').click()
      for pref,count in Counter(v['prefecture'] for v in manifest.values()).items():
        page.select_option('#pref',label=pref);check(label+' filter '+pref,page.locator('.spot').count()==count)
      page.select_option('#pref',value='');page.fill('#search','淺草寺');check(label+' search',page.locator('.spot').count()==1)
      page.fill('#search','');page.click('#onlyVisited');check(label+' visited-only',page.locator('.spot').count()==1);page.click('#onlyVisited')
      for region in ['北海道','東北']:
        page.select_option('#region',label=region);page.locator('.region-head').click()
        relevant={id:v for id,v in previous.items() if (id.startswith('JP01-'))==(region=='北海道')}
        for id in relevant:
          card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
          page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return !i.hidden&&i.complete&&i.naturalWidth>0}',arg=id,timeout=12000)
        check(label+' '+region+' regression images',page.locator('.thumb[data-photo-kind="fixed"]:visible').count()==len(relevant))
        first='JP01-01' if region=='北海道' else 'JP02-01'
        check(label+' '+region+' stored tick',page.locator(f'[data-id="{first}"] .check').is_checked())
        page.locator('.region-head').click()
      check(label+' previous regions no external search',not outside,outside)
      page.select_option('#region',label='關東');page.select_option('#pref',label='東京都')
      page.locator('.region-head').scroll_into_view_if_needed();page.wait_for_timeout(700);page.screenshot(path=str(OUT/f'{label}.png'))
      check(label+' no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
      page.goto(URL+'photo-credits-kanto.html');check(label+' 116 credit sections',page.locator('article[id]').count()==116)
      check(label+' 116 licenses',page.locator('article a[href*="creativecommons.org"]').count()==116)
      check(label+' 116 sources',page.locator('article a[href*="commons.wikimedia.org"]').count()==116)
      check(label+' no JS exceptions',not errors,errors);ctx.close()
    ctx=browser.new_context();ctx.add_init_script(bootstrap);outside=[]
    def missing(req):
      u=req.request.url
      if 'kanto-photos.json' in u:req.fulfill(status=404,body='missing')
      elif urlparse(u).hostname not in ('127.0.0.1','localhost'):outside.append(u);req.abort()
      else:req.continue_()
    ctx.route('**/*',missing);page=ctx.new_page();page.goto(URL);page.wait_for_function('ready');page.select_option('#region',label='關東');page.locator('[data-id="JP08-01"]').scroll_into_view_if_needed();page.wait_for_timeout(500)
    check('Missing manifest does not trigger search',not outside,outside)
    check('Missing manifest shows placeholder',page.locator('[data-id="JP08-01"] .thumb-fallback').is_visible())
    ctx.close();browser.close();complete=True
finally:
    server.shutdown();(OUT/'results.json').write_text(json.dumps({'complete':complete,'passed':sum(v['passed'] for v in results),'total':len(results),'checks':results},ensure_ascii=False,indent=2))
print('PASS',len(results),'/',len(results))
