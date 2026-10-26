"""Test actual HTTP site/photographs with isolated storage, mouse, touch and keyboard."""
import os,json,threading,functools,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=Path.cwd();SITE=ROOT/'japan-checklist';ENGINE=os.environ.get('ENGINE','chromium');OUT=ROOT/'scroll-tests'/ENGINE;OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(SITE)))
threading.Thread(target=server.serve_forever,daemon=True).start();URL=f'http://127.0.0.1:{server.server_port}/'
results=[];complete=False
def check(name,condition,detail=None):
    results.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition:raise AssertionError(f'{name}: {detail}')
def position(page,id):
    return page.evaluate('''id=>{const c=document.querySelector(`[data-id="${id}"]`),r=c.getBoundingClientRect();return {scroll:scrollY,top:r.top,width:r.width,height:r.height,checked:c.querySelector('.check').checked,order:[...c.parentElement.children].map(x=>x.dataset.id)};}''',id)
def tap(page,locator,touch):
    b=locator.bounding_box();assert b
    x,y=b['x']+b['width']/2,b['y']+b['height']/2
    if touch:page.touchscreen.tap(x,y)
    else:page.mouse.click(x,y)
def start_trace(page,id):
    page.evaluate('''id=>{const c=document.querySelector(`[data-id="${id}"]`);window.testCard=c;window.testImg=c.querySelector('img');window.testScrolls=[scrollY];window.testTrace=true;const f=()=>{testScrolls.push(scrollY);if(testTrace)requestAnimationFrame(f);};requestAnimationFrame(f);}''',id)
def stop_trace(page):return page.evaluate('()=>{testTrace=false;return testScrolls;}')
try:
  with sync_playwright() as p:
    engine=getattr(p,ENGINE)
    args={'headless':True}
    if ENGINE=='chromium':args.update(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox','--disable-dev-shm-usage'])
    browser=engine.launch(**args)
    for mode,touch,width,height in [('desktop',False,1440,1000),('mobile-touch',True,390,844)]:
      context=browser.new_context(viewport={'width':width,'height':height},has_touch=touch,is_mobile=touch)
      page=context.new_page();errors=[];outside=[]
      page.on('pageerror',lambda e:errors.append(str(e)))
      def route(r):
        if urlparse(r.request.url).hostname not in ('127.0.0.1','localhost'):outside.append(r.request.url);r.abort()
        else:r.continue_()
      context.route('**/*',route)
      page.goto(URL);page.wait_for_function('typeof ready!=="undefined" && ready')
      check(mode+' 700 cards',page.locator('.spot').count()==700)
      choices=page.evaluate('regions.map(r=>byRegion.get(r)[Math.floor(byRegion.get(r).length*.6)].id)')
      for id in choices:
        card=page.locator(f'[data-id="{id}"]');button=card.locator('.check')
        card.evaluate('(e)=>e.scrollIntoView({block:"center",behavior:"instant"})')
        page.wait_for_function('id=>{const i=document.querySelector(`[data-id="${id}"] img`);return !i.hidden&&i.complete&&i.naturalWidth>0;}',arg=id)
        page.wait_for_timeout(80);before=position(page,id);start_trace(page,id)
        tap(page,button,touch);page.wait_for_timeout(200);after=position(page,id);trace=stop_trace(page)
        check(mode+' '+id+' check same scroll',max(abs(s-before['scroll']) for s in trace)<=1,{'before':before['scroll'],'after':after['scroll'],'range':[min(trace),max(trace)]})
        check(mode+' '+id+' card same position',abs(after['top']-before['top'])<=1 and after['order']==before['order'],{'before':before['top'],'after':after['top']})
        check(mode+' '+id+' stable card dimensions',abs(after['height']-before['height'])<=.1 and abs(after['width']-before['width'])<=.1)
        check(mode+' '+id+' same DOM and photo',page.evaluate('id=>testCard===document.querySelector(`[data-id="${id}"]`)&&testImg===testCard.querySelector("img")',id))
        check(mode+' '+id+' saved true',page.evaluate('id=>JSON.parse(localStorage.getItem("japan700-tracker-v1"))[id].checked',id) is True)
        start_trace(page,id);tap(page,button,touch);page.wait_for_timeout(180);trace=stop_trace(page);after2=position(page,id)
        check(mode+' '+id+' uncheck same scroll',max(abs(s-before['scroll']) for s in trace)<=1,{'before':before['scroll'],'after':after2['scroll']})
        check(mode+' '+id+' uncheck keeps order and saves false',after2['order']==before['order'] and not page.evaluate('id=>JSON.parse(localStorage.getItem("japan700-tracker-v1"))[id].checked',id))
        start_trace(page,id);tap(page,card.locator('.spot-name'),touch);page.wait_for_timeout(150);trace=stop_trace(page)
        check(mode+' '+id+' label tap stays and ticks',button.is_checked() and max(abs(s-before['scroll']) for s in trace)<=1)
      last=choices[-1];button=page.locator(f'[data-id="{last}"] .check');button.evaluate('(e)=>e.focus({preventScroll:true})')
      before=position(page,last);start_trace(page,last);page.keyboard.press('Space');page.wait_for_timeout(180);trace=stop_trace(page)
      check(mode+' keyboard Space no jump',max(abs(s-before['scroll']) for s in trace)<=1 and not button.is_checked())
      check(mode+' keyboard focus retained',button.evaluate('(e)=>e===document.activeElement'))
      tap(page,button,touch)
      for _ in range(4):tap(page,button,touch)
      check(mode+' rapid toggles stable',abs(page.evaluate('scrollY')-before['scroll'])<=1 and button.is_checked())
      page.select_option('#region',label='沖繩')
      check(mode+' checked-first on filter',page.locator('.spot').first.get_attribute('data-id')==last)
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='沖繩')
      check(mode+' saved and sorted on reload',page.locator('.spot').first.get_attribute('data-id')==last and page.locator(f'[data-id="{last}"] .check').is_checked())
      page.evaluate('''()=>{state={};for(const s of byRegion.get('關西'))state[s.id]={checked:true,visited:true,status:'已去',note:'保留備註',date:'2025-01-01'};saveState();}''')
      page.select_option('#region',label='關西');page.click('#onlyVisited');id='JP25-20';card=page.locator(f'[data-id="{id}"]')
      card.evaluate('(e)=>e.scrollIntoView({block:"center",behavior:"instant"})');page.wait_for_timeout(100)
      count=page.locator('.spot').count();y=page.evaluate('scrollY');neighbor=card.evaluate('(e)=>e.nextElementSibling.dataset.id')
      page.evaluate('id=>window.neighborNode=document.querySelector(`[data-id="${id}"]`)',neighbor)
      tap(page,card.locator('.check'),touch);page.wait_for_timeout(200)
      check(mode+' visited-only removes one',page.locator('.spot').count()==count-1 and page.locator(f'[data-id="{id}"]').count()==0)
      check(mode+' visited-only same scroll',abs(page.evaluate('scrollY')-y)<=1,{'before':y,'after':page.evaluate('scrollY')})
      check(mode+' visited-only retains other nodes',page.evaluate('id=>neighborNode===document.querySelector(`[data-id="${id}"]`)',neighbor))
      check(mode+' visited-only count',str(count-1) in page.locator('#visibleCount').inner_text())
      check(mode+' legacy note and date retained',page.evaluate('id=>{const x=JSON.parse(localStorage.getItem("japan700-tracker-v1"))[id];return x.checked===false&&x.note==="保留備註"&&x.date==="2025-01-01"}',id))
      page.evaluate('''()=>{state={'JP47-01':{checked:true}};saveState();}''');page.select_option('#region',label='沖繩');card=page.locator('[data-id="JP47-01"]')
      card.scroll_into_view_if_needed();tap(page,card.locator('.check'),touch)
      check(mode+' last visited empty result',page.locator('.spot').count()==0 and page.locator('#empty').is_visible())
      page.click('#onlyVisited');page.select_option('#region',label='九州');page.select_option('#pref',label='佐賀縣')
      check(mode+' prefecture filter',page.locator('.spot').count()>0 and page.locator('.region-section').count()==1)
      page.click('.region-head');check(mode+' collapse',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.reload();page.wait_for_function('ready');page.select_option('#region',label='九州');page.select_option('#pref',label='佐賀縣')
      check(mode+' collapse persists',page.locator('.region-cards').evaluate('(e)=>e.hidden'))
      page.click('.region-head');page.locator('.region-head').scroll_into_view_if_needed();page.wait_for_timeout(200)
      page.screenshot(path=str(OUT/(mode+'.png')))
      check(mode+' no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
      check(mode+' no JS errors',not errors,errors);check(mode+' no external requests',not outside,outside)
      context.close()
    browser.close();complete=True
finally:
  server.shutdown();(OUT/'results.json').write_text(json.dumps({'engine':ENGINE,'passed':sum(x['passed'] for x in results),'total':len(results),'complete':complete,'checks':results},ensure_ascii=False,indent=2))
print('PASS',ENGINE,len(results),'checks',flush=True)
