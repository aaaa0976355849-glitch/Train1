"""Prepare licensed Kanto candidates on an isolated branch, not in the visitor browser."""
import base64, gzip, hashlib, json
from pathlib import Path
from photo_source import candidate, request
ROOT=Path('japan-checklist'); DEST=ROOT/'images/kanto'; DEST.mkdir(parents=True,exist_ok=True)
def main():
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    spots=[s for s in data if s['region']=='關東']
    selections=json.loads(Path('tools/kanto-selections.json').read_text())
    assert len(spots)==116 and set(selections)=={s['id'] for s in spots}
    oldpath=ROOT/'kanto-photos.json';old=json.loads(oldpath.read_text()) if oldpath.exists() else {}
    manifest={};errors={}
    for spot in spots:
        id=spot['id'];sel=selections[id];signature=hashlib.sha256(json.dumps(sel,sort_keys=True).encode()).hexdigest()
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
            if sel.get('caption'):item['caption']=sel['caption']
            manifest[id]=item;print(id,spot['name'],item['filename'],item['license'],flush=True)
        except Exception as e:
            errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
    oldpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    Path('kanto-preparation-report.json').write_text(json.dumps({'total':116,'downloaded':len(manifest),'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print('RESULT',len(manifest),'/116',flush=True)
if __name__=='__main__':main()
