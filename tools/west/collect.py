"""One-time build/review collection. Nothing here runs in visitors' browsers."""
import base64,gzip,hashlib,json,io
from pathlib import Path
from PIL import Image,ImageOps
from photo_source import candidate,request
ROOT=Path('japan-checklist')
REGIONS={'關西':'kansai','中國地方':'chugoku','四國':'shikoku','九州':'kyushu','沖繩':'okinawa'}
def selections():
    out={};pref=0;n=0
    for line in Path('tools/west/selections.txt').read_text().splitlines():
        if not line.strip():continue
        if line.startswith('['):pref=int(line[1:-1]);n=0;continue
        n+=1;out[f'JP{pref:02}-{n:02}']={k:v for k,v in zip(['ja','en'],line.split('|')) if v}
    for name in ('overrides.json','final-overrides.json'):
        p=Path('tools/west')/name
        if p.exists():out.update(json.loads(p.read_text()))
    return out

def main():
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    spots=[s for s in data if s['region'] in REGIONS];sels=selections()
    assert len(spots)==328 and set(sels)=={s['id'] for s in spots}
    manifests={};errors={}
    for slug in REGIONS.values():
        p=ROOT/f'{slug}-photos.json';manifests[slug]=json.loads(p.read_text()) if p.exists() else {}
        (ROOT/'images'/slug).mkdir(parents=True,exist_ok=True)
    for spot in spots:
        id=spot['id'];slug=REGIONS[spot['region']];sel=sels[id]
        sig=hashlib.sha256(json.dumps(sel,sort_keys=True).encode()).hexdigest()
        try:
            old=manifests[slug].get(id)
            if old and old.get('selectionHash')==sig and (ROOT/old['src']).is_file():
                print(id,'cached',flush=True);continue
            item=candidate(sel);blob=request(item['downloadUrl'])
            im=Image.open(io.BytesIO(blob));im.load()
            if im.format not in ('JPEG','PNG','WEBP'):raise ValueError('Not a photograph format')
            im=ImageOps.exif_transpose(im);im.thumbnail((960,960),Image.Resampling.LANCZOS)
            if min(im.size)<240:raise ValueError('Photo dimensions too small')
            dest=ROOT/'images'/slug/(id+'.jpg');im.convert('RGB').save(dest,'JPEG',quality=87,optimize=True)
            actual=dest.read_bytes()
            item.update({'src':dest.relative_to(ROOT).as_posix(),'name':spot['name'],'prefecture':spot['prefecture'],'sha256':hashlib.sha256(actual).hexdigest(),'bytes':len(actual),'selectionHash':sig,'changes':'縮小尺寸並轉存 JPEG；網頁預設以 4:3 裁切顯示，顯示版本沿用原圖授權。'})
            for k in ['fit','caption','note']:
                if sel.get(k):item[k]=sel[k]
            manifests[slug][id]=item;print(id,spot['name'],item['filename'],item['license'],flush=True)
        except Exception as e:errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
    for slug,manifest in manifests.items():(ROOT/f'{slug}-photos.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report={'total':328,'downloaded':sum(len(m) for m in manifests.values()),'errors':errors,'regions':{k:len(v) for k,v in manifests.items()}}
    Path('west-preparation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
