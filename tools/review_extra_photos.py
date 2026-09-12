"""Download bounded alternative candidates to artifacts only, for visual selection."""
import json,re
from pathlib import Path
from photo_source import api,photo_info,request
DEST=Path('review-extra');DEST.mkdir(exist_ok=True)
QUERIES={
'JP15-06':'Gala Yuzawa ski',
'JP18-03':'Fukui Dinosaur Museum exterior',
'JP19-16':'Kurobe Lake',
'JP21-12':'Kawazu cherry river',
'JP24-09':'Nabana illumination garden',
'JP24-12':'Magose stone path'
}
CATS={'JP18-10':'Mizu Island (Fukui)'}
EXACT={
'JP19-11':['白馬岩岳マウンテンリゾート20211030-IMG '+n+'.jpg' for n in ['7126','7135','7149','7155','7190','7206','7275','7282','7288','7329','7359','7365']]+['白馬岩岳マウンテンリゾート20231103-IMG '+n+'.jpg' for n in ['8071','8077','8104','8113','8139','8152']],
'JP21-02':['231006 Nihondaira Shizuoka Japan'+n+'s3.jpg' for n in ['01','02','03','04','05','06','07','08','09','10','11','12','15','16','17']]
}
out={}
for id in dict.fromkeys([*QUERIES,*CATS,*EXACT]):
    filenames=[]
    try:
        if id in QUERIES:
            pages=api('commons.wikimedia.org',generator='search',gsrnamespace=6,gsrsearch=QUERIES[id],gsrlimit=6,prop='imageinfo',iiprop='url')
            filenames=[p['title'].removeprefix('File:') for p in pages]
        elif id in CATS:
            pages=api('commons.wikimedia.org',generator='categorymembers',gcmtitle='Category:'+CATS[id],gcmnamespace=6,gcmlimit=30,prop='imageinfo',iiprop='url')
            filenames=[p['title'].removeprefix('File:') for p in pages]
        else:filenames=EXACT[id]
        items=[]
        for n,name in enumerate(filenames):
            if not re.search(r'\.(jpg|jpeg|png|webp)$',name,re.I):continue
            try:
                p=photo_info(name);blob=request(p['downloadUrl'])
                if not blob.startswith(b'\xff\xd8\xff'):continue
                path=DEST/(id+'-'+str(n)+'.jpg');path.write_bytes(blob)
                p['preview']=path.as_posix();items.append(p)
            except Exception as e:print('EXTRA SKIP',id,name,str(e),flush=True)
        out[id]=items;print('EXTRA',id,len(items),flush=True)
    except Exception as e:out[id]=[];print('EXTRA ERROR',id,str(e),flush=True)
(DEST/'manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
