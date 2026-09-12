"""Prepare fixed photo candidates for two regions on an isolated review branch."""
import base64,gzip,hashlib,json
from pathlib import Path
from photo_source import candidate,request
ROOT=Path('japan-checklist')
REGIONS={'北陸信越':('hokuriku',65),'東海・山梨':('tokai',68)}
def main():
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    selections=json.loads(Path('tools/chubu-selections.json').read_text())
    targets=[s for s in data if s['region'] in REGIONS]
    assert len(targets)==133 and set(selections)=={s['id'] for s in targets}
    report={}
    for region,(slug,total) in REGIONS.items():
        dest=ROOT/'images'/slug;dest.mkdir(parents=True,exist_ok=True)
        manifest_path=ROOT/f'{slug}-photos.json'
        old=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        manifest={};errors={}
        for spot in [s for s in targets if s['region']==region]:
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
                path=dest/(id+'.'+ext);path.write_bytes(blob)
                item.update({'src':path.relative_to(ROOT).as_posix(),'name':spot['name'],'prefecture':spot['prefecture'],'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'selectionHash':signature})
                for key in ('caption','fit'):
                    if key in sel:item[key]=sel[key]
                manifest[id]=item;print(id,spot['name'],item['filename'],item['license'],flush=True)
            except Exception as e:
                errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        report[slug]={'total':total,'downloaded':len(manifest),'errors':errors}
        print('RESULT',slug,len(manifest),'/',total,flush=True)
    Path('chubu-preparation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
