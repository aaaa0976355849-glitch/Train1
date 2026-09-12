"""Download bounded, licensed alternatives for visual review; never auto-publish these."""
import io,json,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageOps
from photo_source import api,photo_info,request
OUT=Path('photo-alternatives');OUT.mkdir(exist_ok=True)
queries=json.loads(Path('tools/west/queries.json').read_text())
def collect(pair):
    id,terms=pair;results=[];seen=set();errors=[]
    for q in terms:
        if len(results)>=4:break
        try:pages=api('commons.wikimedia.org',generator='search',gsrsearch=q,gsrnamespace=6,gsrlimit=10)
        except Exception as e:errors.append(str(e));continue
        for p in sorted(pages,key=lambda x:x.get('index',0)):
            f=p['title'].removeprefix('File:')
            if f in seen or not re.search(r'\.(jpg|jpeg|png|webp)$',f,re.I):continue
            seen.add(f)
            try:
                info=photo_info(f);blob=request(info['downloadUrl']);im=Image.open(io.BytesIO(blob));im.load()
                im=ImageOps.exif_transpose(im);im.thumbnail((640,480))
                if min(im.size)<120:continue
                path=OUT/f'{id}-{len(results)+1}.jpg';im.convert('RGB').save(path,'JPEG',quality=88)
                info.update({'preview':path.name,'query':q});results.append(info)
                if len(results)>=4:break
            except Exception as e:errors.append(f+': '+str(e))
    print(id,len(results),'alternatives',flush=True)
    return id,{'photos':results,'errors':errors}
with ThreadPoolExecutor(max_workers=2) as pool:data=dict(pool.map(collect,queries.items()))
(OUT/'metadata.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('Alternative sets',len(data),flush=True)
