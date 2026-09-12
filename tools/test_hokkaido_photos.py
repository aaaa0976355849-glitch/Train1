"""Integration checks with real local HTTP images and browser storage, external requests blocked."""
from pathlib import Path
import json,threading,functools,http.server,hashlib,gzip,base64,sys,shutil
from PIL import Image
from playwright.sync_api import sync_playwright
root=Path(sys.argv[1]); out=Path('hokkaido-tests');out.mkdir(exist_ok=True)
results=[]
def check(name,condition):
    results.append({'test':name,'pass':bool(condition)})
    (out/'results.json').write_text(json.dumps({'passed':sum(r['pass'] for r in results),'checks':results},ensure_ascii=False,indent=2))
    if not condition: raise AssertionError(name)
data=json.loads(gzip.decompress(base64.b64decode(''.join((root/f'data.{i}.txt').read_text() for i in range(1,5)))))
m=json.loads((root/'hokkaido-photos.json').read_text())
check('catalogue 700 unique attractions',len(data)==700 and len({s['id'] for s in data})==700)
check('47 prefectures',len({s['prefecture'] for s in data})==47)
check('all 45 Hokkaido IDs have fixed photos',set(m)=={s['id'] for s in data if s['region']=='北海道'})
check('45 distinct photo hashes',len({v['sha256'] for v in m.values()})==45)
for id,v in m.items():
    p=root/v['src'];Image.open(p).verify()
    check(id+' verified local photo',p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'])
check('45 author and license records',all(v['author'] and v['licenseUrl'] and v['source'] for v in m.values()))
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',8118),functools.partial(Handler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    executable=shutil.which('google-chrome') or shutil.which('chromium') or p.chromium.executable_path
    browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
    for device,w,h in [('desktop',1440,1000),('mobile',390,844)]:
        context=browser.new_context(viewport={'width':w,'height':h})
        external=[];errors=[]
        def route(r):
            if r.request.url.startswith('http://127.0.0.1:8118/'):
                r.continue_()
            else:
                external.append(r.request.url);r.abort()
        context.route('**/*',route)
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8118/',wait_until='networkidle')
        page.wait_for_function("document.querySelectorAll('.spot').length === 700")
        check(device+' no overall summary',page.locator('#summary').count()==0)
        check(device+' progress above filters',page.locator('.region-progress').bounding_box()['y']<page.locator('.toolbar').bounding_box()['y'])
        check(device+' all 10 regions retained',page.locator('.region-section').count()==10)
        page.select_option('#region',label='北海道')
        check(device+' filtered 45 cards',page.locator('.spot').count()==45)
        for id in sorted(m):
            card=page.locator(f'.spot[data-id="{id}"]');card.scroll_into_view_if_needed()
            page.wait_for_function("id=>{const i=document.querySelector('[data-id=\"'+id+'\"] img.thumb');return i&&!i.hidden&&i.complete&&i.naturalWidth>0&&i.dataset.photoKind==='fixed'}",arg=id,timeout=8000)
        check(device+' 45 photos loaded from same origin',page.locator('img[data-photo-kind="fixed"]').count()==45)
        check(device+' no external image search requests',len(external)==0)
        page.locator('.region-head').click()
        check(device+' collapse hides grid',not page.locator('.region-cards').is_visible())
        page.reload(wait_until='networkidle')
        page.select_option('#region',label='北海道')
        check(device+' collapse state persists on reload',not page.locator('.region-cards').is_visible())
        page.locator('.region-head').click()
        page.locator('[data-id="JP01-45"] .check').check()
        check(device+' checked sorts first',page.locator('.spot').first.get_attribute('data-id')=='JP01-45')
        check(device+' checkbox stored',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP01-45'].checked") is True)
        page.reload(wait_until='networkidle');page.select_option('#region',label='北海道')
        check(device+' checked state survives reload',page.locator('[data-id="JP01-45"] .check').is_checked())
        page.locator('[data-id="JP01-45"] .check').uncheck()
        check(device+' uncheck restores original order',page.locator('.spot').first.get_attribute('data-id')=='JP01-01')
        page.evaluate("localStorage.setItem('japan700-tracker-v1',JSON.stringify({'JP01-02':{status:'已去',note:'舊備註保留',date:'2020-01-01'},'JP01-06':{status:'想再去'},'JP01-07':{checked:false,visited:true,status:'已去'}}))")
        page.reload(wait_until='networkidle');page.select_option('#region',label='北海道')
        check(device+' legacy completed state respected',page.locator('[data-id="JP01-02"] .check').is_checked())
        check(device+' legacy revisit state respected',page.locator('[data-id="JP01-06"] .check').is_checked())
        check(device+' explicit unchecked has priority',not page.locator('[data-id="JP01-07"] .check').is_checked())
        page.locator('[data-id="JP01-02"] .check').uncheck()
        check(device+' legacy note survives',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP01-02'].note")=='舊備註保留')
        check(device+' legacy date survives',page.evaluate("JSON.parse(localStorage.getItem('japan700-tracker-v1'))['JP01-02'].date")=='2020-01-01')
        page.locator('#onlyVisited').click()
        check(device+' only visited filter',page.locator('.spot').count()==1)
        page.locator('#onlyVisited').click();page.fill('#search','青池')
        check(device+' search works',page.locator('.spot').count()==1 and page.locator('.spot-name').inner_text()=='美瑛青池')
        page.fill('#search','');page.locator('#collapseAll').click()
        check(device+' collapse all works',not page.locator('.region-cards').is_visible())
        page.locator('#expandAll').click()
        check(device+' expand all works',page.locator('.region-cards').is_visible())
        check(device+' no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        page.evaluate("localStorage.removeItem('japan700-tracker-v1');localStorage.removeItem('japan700-simple-collapsed-v1')")
        page.reload(wait_until='networkidle');page.select_option('#region',label='北海道')
        for i in range(0,10):page.locator('.spot').nth(i).scroll_into_view_if_needed()
        page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(200)
        page.screenshot(path=str(out/f'{device}.png'),full_page=False)
        page.goto('http://127.0.0.1:8118/photo-credits.html#JP01-32',wait_until='networkidle')
        check(device+' all attribution anchors exist',page.locator('section[id^="JP01-"]').count()==45)
        check(device+' attribution has no script dependency',page.locator('script').count()==0)
        check(device+' no JS runtime errors',not errors)
        context.close()
    browser.close()
server.shutdown()
print('PASS',len(results),'checks')
