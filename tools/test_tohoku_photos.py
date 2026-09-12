"""Real local HTTP images and browser storage, isolated from user travel records."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse
from collections import Counter
import json,hashlib,shutil
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path('japan-checklist');OUT=Path('tohoku-tests');OUT.mkdir(exist_ok=True)
results=[]
def check(name,condition,detail=None):
    results.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition:raise AssertionError(name+': '+str(detail))
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start();URL=f'http://127.0.0.1:{server.server_address[1]}/'
manifest=json.loads((ROOT/'tohoku-photos.json').read_text());hokkaido=json.loads((ROOT/'hokkaido-photos.json').read_text())
allphotos={**hokkaido,**manifest}
check('78 Tohoku photo entries',len(manifest)==78)
check('78 distinct Tohoku files',len({x['sha256'] for x in manifest.values()})==78)
check('45 Hokkaido photo entries retained',len(hokkaido)==45)
check('6 prefectures',len({x['prefecture'] for x in manifest.values()})==6)
for id,photo in allphotos.items():
    data=(ROOT/photo['src']).read_bytes()
    with Image.open(ROOT/photo['src']) as img:w,height=img.size;img.verify()
    check(id+' local image hash, dimensions, attribution',hashlib.sha256(data).hexdigest()==photo['sha256'] and w>=320 and height>=240 and bool(photo['author']) and bool(photo['licenseUrl']))
folded={r:True for r in ['北海道','東北','關東','北陸信越','東海・山梨','關西','中國地方','四國','九州','沖繩']};folded['東北']=False
seed={'JP02-03':{'visited':True,'status':'已去','note':'舊紀錄保留','date':'2025-01-01'},'JP01-01':{'checked':True}}
bootstrap=f"if(!localStorage.getItem('__test_seeded')){{localStorage.setItem('japan700-simple-collapsed-v1',{json.dumps(json.dumps(folded,ensure_ascii=False))});localStorage.setItem('japan700-tracker-v1',{json.dumps(json.dumps(seed,ensure_ascii=False))});localStorage.setItem('__test_seeded','yes');}}"
try:
  with sync_playwright() as p:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox'])
    for label,viewport in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':390,'height':844})]:
      context=browser.new_context(viewport=viewport);context.add_init_script(bootstrap)
      outside=[];errors=[]
      def route(req):
        if urlparse(req.request.url).hostname not in ('127.0.0.1','localhost'):outside.append(req.request.url);req.abort()
        else:req.continue_()
      context.route('**/*',route)
      page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
      page.goto(URL);page.wait_for_function('typeof ready!=="undefined" && ready')
      check(label+' 700 catalogue items',page.locator('.spot').count()==700)
      check(label+' no extra card controls',page.locator('#summary, .spot select, .spot textarea, .spot input[type=date]').count()==0)
      check(label+' preserved legacy tick',page.locator('[data-id="JP02-03"] .check').is_checked())
      page.select_option('#region',label='東北');page.wait_for_function('document.querySelectorAll(".spot").length===78')
      for id in manifest:
        card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
        page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return i && !i.hidden && i.complete && i.naturalWidth>0}',arg=id,timeout=12000)
        check(label+' '+id+' fixed photograph loaded',card.locator('img').evaluate('(img)=>img.dataset.photoKind==="fixed"&&new URL(img.src).origin===location.origin'))
      check(label+' 78 correct credit anchors',page.locator('.photo-credit[href^="photo-credits-tohoku.html#"]').count()==78)
      check(label+' no external requests for Tohoku',not outside,outside)
      page.locator('[data-id="JP04-07"] .check').check()
      check(label+' checked card sorted before unchecked',page.locator('.spot').nth(1).get_attribute('data-id')=='JP04-07')
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='東北')
      check(label+' checked after refresh',page.locator('[data-id="JP04-07"] .check').is_checked())
      check(label+' retained old note and date',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP02-03'].note==='舊紀錄保留' && JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP02-03'].date==='2025-01-01'"))
      page.locator('[data-id="JP04-07"] .check').uncheck();page.reload();page.wait_for_function('ready');page.select_option('#region',label='東北')
      check(label+' unchecked after refresh',not page.locator('[data-id="JP04-07"] .check').is_checked())
      check(label+' cancel restores original ordering',page.locator('.spot').nth(1).get_attribute('data-id')=='JP02-01')
      page.locator('.region-head').click();check(label+' collapse hides cards',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='東北')
      check(label+' collapse persists',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.locator('.region-head').click()
      for pref,count in Counter(x['prefecture'] for x in manifest.values()).items():
        page.select_option('#pref',label=pref);check(label+' filter '+pref,page.locator('.spot').count()==count)
      page.select_option('#pref',value='');page.fill('#search','奧入瀨');check(label+' search',page.locator('.spot').count()==1)
      page.fill('#search','');page.click('#onlyVisited');check(label+' visited-only',page.locator('.spot').count()==1)
      page.click('#onlyVisited');page.select_option('#region',label='北海道');page.locator('.region-head').click()
      for id in hokkaido:
        card=page.locator(f'[data-id="{id}"]');card.scroll_into_view_if_needed()
        page.wait_for_function('(id)=>{const i=document.querySelector(`[data-id="${id}"] .thumb`);return !i.hidden && i.complete && i.naturalWidth>0}',arg=id,timeout=10000)
      check(label+' all 45 Hokkaido photos still load',page.locator('.thumb[data-photo-kind="fixed"]:visible').count()==45)
      check(label+' Hokkaido old tick retained',page.locator('[data-id="JP01-01"] .check').is_checked())
      check(label+' no external requests in completed regions',not outside,outside)
      page.select_option('#region',label='東北');page.select_option('#pref',label='青森')
      page.locator('.region-head').scroll_into_view_if_needed();page.wait_for_timeout(600);page.screenshot(path=str(OUT/f'{label}.png'))
      check(label+' no horizontal page overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
      page.goto(URL+'photo-credits-tohoku.html');check(label+' 78 attribution sections',page.locator('article[id]').count()==78)
      check(label+' licenses and sources included',page.locator('article a[href*="creativecommons.org"]').count()==78 and page.locator('article a[href*="commons.wikimedia.org"]').count()==78)
      check(label+' no JS exceptions',not errors,errors);context.close()
    context=browser.new_context();context.add_init_script(bootstrap);outside=[]
    def missing_route(req):
      u=req.request.url
      if 'tohoku-photos.json' in u:req.fulfill(status=404,body='missing')
      elif urlparse(u).hostname not in ('127.0.0.1','localhost'):outside.append(u);req.abort()
      else:req.continue_()
    context.route('**/*',missing_route);page=context.new_page();page.goto(URL);page.wait_for_function('ready');page.select_option('#region',label='東北');page.locator('[data-id="JP02-01"]').scroll_into_view_if_needed();page.wait_for_timeout(400)
    check('Missing fixed manifest does not trigger external search',not outside,outside)
    check('Missing fixed manifest shows honest placeholder',page.locator('[data-id="JP02-01"] .thumb-fallback').is_visible())
    context.close();browser.close()
finally:
  server.shutdown();(OUT/'results.json').write_text(json.dumps({'passed':sum(x['passed'] for x in results),'total':len(results),'checks':results},ensure_ascii=False,indent=2))
print(f'PASS {len(results)}/{len(results)} checks')
