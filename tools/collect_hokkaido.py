"""Prepare licensed photo candidates on a review branch, never in a visitor's browser."""
import base64, gzip, hashlib, json, re, time
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
ROOT = Path('japan-checklist')
DEST = ROOT / 'images' / 'hokkaido'
DEST.mkdir(parents=True, exist_ok=True)
HEADERS = {'User-Agent':'Japan700PhotoPreparation/1.0 (https://github.com/aaaa0976355849-glitch/Train1; personal travel catalogue)'}
IMAGE_HOSTS = {'upload.wikimedia.org','thumb.wikimedia.org','commons.wikimedia.org'}
HOSTS = IMAGE_HOSTS | {'ja.wikipedia.org','en.wikipedia.org'}
OVERRIDES = {
 'JP01-09':'Otaru-Tenguyama 20220625.jpg',
 'JP01-15':'Noboribetsu hot spring jigokudani.JPG',
 'JP01-19':'Hakodate Hachiman-zaka 2024.jpg',
 'JP01-29':'ニングルの秋（Fall of Ninguru） - panoramio.jpg',
 'JP01-32':'雲海テラス TOMAMU - panoramio (1).jpg',
 'JP01-39':'Hokkaido-Abashiri Drift Icebreaker Ship Aurora-xl.jpg',
 'JP01-42':'Rebun Island (7805402080).jpg',
 'JP01-44':'Jozankei Onsen 01.jpg'
}
class Plain(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, data): self.parts.append(data)
def text(value):
    p=Plain(); p.feed(str(value or '')); return ' '.join(''.join(p.parts).split())
def request(url):
    if url.startswith('//'): url='https:'+url
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in HOSTS:
        raise ValueError('Untrusted source: '+url)
    error=None
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=25) as r:
                if urlparse(r.url).scheme != 'https' or urlparse(r.url).hostname not in HOSTS:
                    raise ValueError('Unexpected redirect host')
                data=r.read(16000001)
                if len(data)>16000000: raise ValueError('Image too large')
                return data
        except Exception as e:
            error=e
            if attempt<2: time.sleep(2+attempt*3)
    raise error

def api(host, **params):
    time.sleep(0.25)
    data=json.loads(request('https://'+host+'/w/api.php?'+urlencode({'action':'query','format':'json','formatversion':2,**params})))
    if data.get('error'): raise ValueError(str(data['error']))
    return data.get('query',{}).get('pages',[])

def filename_for(lang, title):
    pages=api(lang+'.wikipedia.org',titles=title,redirects=1,prop='pageimages|pageprops',piprop='name',pilicense='free')
    for p in pages:
        filename=p.get('pageimage','')
        if re.search(r'(relief|_map|locator|\.svg$)',filename,re.I): continue
        if not p.get('missing') and 'disambiguation' not in p.get('pageprops',{}) and filename:
            return filename,p['title']
    return None,None

def photo_info(filename):
    pages=api('commons.wikimedia.org',titles='File:'+filename,prop='imageinfo',iiprop='url|extmetadata|sha1|mime',iiurlwidth=960)
    info=next((p['imageinfo'][0] for p in pages if p.get('imageinfo')),None)
    if not info: raise ValueError('Commons image metadata missing: '+filename)
    m=info.get('extmetadata',{})
    field=lambda k:text(m.get(k,{}).get('value',''))
    license=field('LicenseShortName')
    if not re.fullmatch(r'(CC BY(?:-SA)? [0-9.]+(?: [A-Za-z]+)?|CC0|Public domain|PDM(?: [0-9.]+)?)',license,re.I):
        raise ValueError('Unsupported license '+license+' '+filename)
    author=field('Attribution') or field('Artist')
    if not author: raise ValueError('Author unavailable: '+filename)
    lu=field('LicenseUrl')
    if lu.startswith('//'): lu='https:'+lu
    if lu.startswith('http:'): lu='https:'+lu[5:]
    if not lu:
        if license=='CC0': lu='https://creativecommons.org/publicdomain/zero/1.0/'
        elif license.lower()=='public domain': lu='https://creativecommons.org/publicdomain/mark/1.0/'
        else: raise ValueError('License URL missing')
    src=info.get('thumburl') or info['url']
    if src.startswith('//'): src='https:'+src
    if urlparse(src).hostname not in IMAGE_HOSTS: raise ValueError('Unexpected image host: '+src)
    source=info['descriptionurl']
    if urlparse(source).hostname!='commons.wikimedia.org': raise ValueError('Unexpected description host: '+source)
    return {'filename':filename,'downloadUrl':src,'originalUrl':info['url'],'source':source,'author':author,'license':license,'licenseUrl':lu,'description':field('ImageDescription'),'sourceSha1':info.get('sha1',''),'changes':'縮小尺寸；網頁以 4:3 裁切顯示。裁切顯示版本沿用原圖授權。'}

def candidate(selection):
    if selection.get('file'): return photo_info(selection['file'])
    errors=[]
    for lang in ('ja','en'):
        if not selection.get(lang): continue
        try:
            filename,title=filename_for(lang,selection[lang])
            if filename:
                item=photo_info(filename);item['matchedArticle']=lang+':'+title;return item
        except Exception as e: errors.append(str(e))
    raise ValueError('; '.join(errors) or 'No exact article photo')

catalogue=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
spots=[s for s in catalogue if s['region']=='北海道']
selections=json.loads(Path('tools/hokkaido-selections.json').read_text())
for id, filename in OVERRIDES.items(): selections[id]={'file':filename}
assert len(spots)==45 and set(selections)=={s['id'] for s in spots}
manifest={}; errors={}
old_path=ROOT/'hokkaido-photos.json'
old=json.loads(old_path.read_text()) if old_path.exists() else {}
for spot in spots:
    id=spot['id']; selection=selections[id]
    try:
        item=old.get(id)
        if item and (not selection.get('file') or selection['file']==item['filename']) and (ROOT/item['src']).exists():
            manifest[id]=item; print(id,'cached',flush=True);continue
        item=candidate(selection)
        data=request(item['downloadUrl'])
        if data.startswith(b'\xff\xd8\xff'): ext='jpg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'): ext='png'
        elif data.startswith(b'RIFF') and data[8:12]==b'WEBP': ext='webp'
        else: raise ValueError('Not JPEG/PNG/WebP: '+item['downloadUrl']+' '+repr(data[:80]))
        p=DEST/(id+'.'+ext);p.write_bytes(data)
        item.update({'src':p.relative_to(ROOT).as_posix(),'name':spot['name'],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
        manifest[id]=item
        print(id,spot['name'],item['filename'],item['license'],len(data),flush=True)
    except Exception as e:
        errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
(ROOT/'hokkaido-photos.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
Path('hokkaido-preparation-report.json').write_text(json.dumps({'total':45,'downloaded':len(manifest),'errors':errors},ensure_ascii=False,indent=2)+'\n')
print('RESULT',len(manifest),'/45')
