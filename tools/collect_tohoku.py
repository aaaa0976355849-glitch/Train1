"""Build-time photo preparation only. Exact article/file choices are reviewed before publication."""
import base64, gzip, hashlib, json, re, time
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT=Path('japan-checklist'); DEST=ROOT/'images/tohoku'; DEST.mkdir(parents=True,exist_ok=True)
HOSTS={'upload.wikimedia.org','thumb.wikimedia.org','commons.wikimedia.org','ja.wikipedia.org','en.wikipedia.org'}
HEADERS={'User-Agent':'Japan700PhotoPreparation/2.0 (https://github.com/aaaa0976355849-glitch/Train1; travel catalogue)'}
class Plain(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,data): self.parts.append(data)
def text(value):
    p=Plain(); p.feed(str(value or '')); return ' '.join(''.join(p.parts).split())
def request(url):
    if url.startswith('//'): url='https:'+url
    if urlparse(url).scheme!='https' or urlparse(url).hostname not in HOSTS: raise ValueError('Untrusted source')
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers=HEADERS),timeout=25) as r:
                if urlparse(r.url).scheme!='https' or urlparse(r.url).hostname not in HOSTS: raise ValueError('Untrusted redirect')
                data=r.read(16000001)
                if len(data)>16000000: raise ValueError('Image too large')
                return data
        except Exception:
            if attempt==2: raise
            time.sleep(2+attempt*3)
def api(host,**params):
    time.sleep(.25)
    data=json.loads(request('https://'+host+'/w/api.php?'+urlencode({'action':'query','format':'json','formatversion':2,**params})))
    if data.get('error'): raise ValueError(str(data['error']))
    return data.get('query',{}).get('pages',[])
def filename_for(lang,title):
    pages=api(lang+'.wikipedia.org',titles=title,redirects=1,prop='pageimages|pageprops',piprop='name',pilicense='free')
    for p in pages:
        f=p.get('pageimage','')
        if re.search(r'(relief|_map|locator|logo|\.svg$|\.gif$)',f,re.I): continue
        if not p.get('missing') and 'disambiguation' not in p.get('pageprops',{}) and f: return f,p['title']
    return None,None
def photo_info(filename):
    pages=api('commons.wikimedia.org',titles='File:'+filename,prop='imageinfo',iiprop='url|extmetadata|sha1|mime',iiurlwidth=960)
    info=next((p['imageinfo'][0] for p in pages if p.get('imageinfo')),None)
    if not info: raise ValueError('No Commons metadata: '+filename)
    m=info.get('extmetadata',{}); field=lambda k:text(m.get(k,{}).get('value',''))
    license=field('LicenseShortName'); author=field('Attribution') or field('Artist')
    if not re.fullmatch(r'(CC BY(?:-SA)? [0-9.]+(?: [A-Za-z]+)?|CC0|Public domain|PDM(?: [0-9.]+)?)',license,re.I): raise ValueError('Unsupported license '+license)
    if not author: raise ValueError('Author missing')
    lu=field('LicenseUrl')
    if lu.startswith('//'): lu='https:'+lu
    if lu.startswith('http:'): lu='https:'+lu[5:]
    if not lu:
        if license=='CC0': lu='https://creativecommons.org/publicdomain/zero/1.0/'
        elif license.lower() in {'public domain','pdm'}: lu='https://creativecommons.org/publicdomain/mark/1.0/'
        else: raise ValueError('License URL missing')
    if urlparse(lu).hostname!='creativecommons.org': raise ValueError('Unsupported license URL')
    src=info.get('thumburl') or info['url']
    if src.startswith('//'): src='https:'+src
    if urlparse(src).hostname not in HOSTS: raise ValueError('Unexpected photo host')
    source=info['descriptionurl']
    if urlparse(source).hostname!='commons.wikimedia.org': raise ValueError('Unexpected credit host')
    return {'filename':filename,'downloadUrl':src,'originalUrl':info['url'],'source':source,'author':author,'license':license,'licenseUrl':lu,'description':field('ImageDescription'),'sourceSha1':info.get('sha1',''),'changes':'縮小尺寸；網頁以 4:3 裁切顯示。裁切顯示版本沿用原圖授權。'}
def candidate(sel):
    if sel.get('file'): return photo_info(sel['file'])
    errors=[]
    for lang in ('ja','en'):
        for title in ([sel[lang]] if isinstance(sel.get(lang),str) else sel.get(lang,[])):
            try:
                f,matched=filename_for(lang,title)
                if f:
                    p=photo_info(f);p['matchedArticle']=lang+':'+matched;return p
            except Exception as e: errors.append(str(e))
    raise ValueError('; '.join(errors) or 'No exact article photograph')
def main():
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    spots=[s for s in data if s['region']=='東北']; order=['青森','宮城','岩手','秋田','山形','福島']
    spots.sort(key=lambda s:(next(i for i,p in enumerate(order) if p in s['prefecture']),s['id']))
    selections=json.loads(Path('tools/tohoku-selections.json').read_text())
    assert len(spots)==78 and set(selections)=={s['id'] for s in spots}
    oldpath=ROOT/'tohoku-photos.json';old=json.loads(oldpath.read_text()) if oldpath.exists() else {}
    manifest={};errors={}
    for spot in spots:
        id=spot['id'];sel=selections[id]; signature=hashlib.sha256(json.dumps(sel,sort_keys=True).encode()).hexdigest()
        try:
            item=old.get(id)
            if item and item.get('selectionHash')==signature and (ROOT/item['src']).is_file():
                manifest[id]=item;print(id,'cached',flush=True);continue
            item=candidate(sel);blob=request(item['downloadUrl'])
            if blob.startswith(b'\xff\xd8\xff'):ext='jpg'
            elif blob.startswith(b'\x89PNG\r\n\x1a\n'):ext='png'
            elif blob.startswith(b'RIFF') and blob[8:12]==b'WEBP':ext='webp'
            else:raise ValueError('Not a JPEG/PNG/WebP photograph')
            path=DEST/(id+'.'+ext);path.write_bytes(blob)
            item.update({'src':path.relative_to(ROOT).as_posix(),'name':spot['name'],'prefecture':spot['prefecture'],'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'selectionHash':signature})
            manifest[id]=item;print(id,spot['name'],item['filename'],item['license'],flush=True)
        except Exception as e:
            errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
    oldpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    Path('tohoku-preparation-report.json').write_text(json.dumps({'total':78,'downloaded':len(manifest),'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print('RESULT',len(manifest),'/78',flush=True)
if __name__=='__main__':main()
