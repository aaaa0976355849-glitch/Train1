"""Prepare licensed Kanto candidates on an isolated branch, not in the visitor browser."""
import base64, gzip, hashlib, json
from pathlib import Path
from photo_source import candidate, request
ROOT=Path('japan-checklist'); DEST=ROOT/'images/kanto'; DEST.mkdir(parents=True,exist_ok=True)
# Exact file choices after reviewing candidate photographs and source descriptions.
OVERRIDES={
'JP08-02':{'file':'Tokyo_Skytree_2014_Ⅲ.jpg','fit':'contain'},
'JP08-03':{'file':'日本電波塔（東京タワー）.jpg','fit':'contain'},
'JP08-08':{'file':'A view from Tokyo Metropolitan Government Building Observation -2 (7290963066).jpg','caption':'東京都廳展望室所見夜景。'},
'JP08-15':{'file':'Ginza-WAKO 2012.JPG'},
'JP08-16':{'file':'Tsukiji Outer Market -06.jpg'},
'JP08-19':{'file':'Teamlab toyosu.jpg','caption':'teamLab Planets 豐洲館外觀。'},
'JP08-20':{'file':'TeamLab Borderless Azabudai Hills.jpg','caption':'麻布台之丘館內照片，非舊台場館。'},
'JP08-21':{'file':'Tokyo Tower and around Skyscrapers.jpg','caption':'從六本木新城森大樓屋頂所見東京景色。'},
'JP08-32':{'file':'父島 - panoramio.jpg','caption':'小笠原父島小港海岸。'},
'JP08-40':{'file':'YebisuGardenPlace 2.JPG'},
'JP09-13':{'file':'Kamakura High School Front Level Crossing (53149232862).jpg'},
'JP10-01':{'file':'Tokyo_Disneyland_Cinderella_Castle_2023-07-02.jpg','fit':'contain'},
'JP10-02':{'file':'Mediterranean Harbor (DisneySea) at Night - Dec 2019.jpg'},
'JP10-09':{'file':'九十九里浜.jpg'},
'JP10-10':{'file':'Inubozaki Lighthouse.JPG'},
'JP11-01':{'file':'KawagoeTowerCommons.jpg','fit':'contain'},
'JP11-06':{'file':'Chichibu Hitsujiyama Park Phlox Hill 1.JPG'},
'JP11-07':{'file':'鉄道博物館 Railway museum 16.jpg'},
'JP12-01':{'file':'2025 Hitachi Seaside Park.jpg'},
'JP12-04':{'file':'Ushiku daibutsu 20050520 (8675289214).jpg','fit':'contain'},
'JP12-09':{'file':'Ryujin big suspension bridge.jpg'},
'JP14-01':{'file':'Kusatsu Yubatake 04.JPG'},
'JP14-04':{'file':'Gunma hot springs 2017.jpg','caption':'寶川溫泉汪泉閣露天溫泉景色。'},
'JP14-05':{'file':'Minakami Onsen Tone River view from Yosano Akiko Park.jpg'}
}
def main():
    data=json.loads(gzip.decompress(base64.b64decode(''.join((ROOT/f'data.{i}.txt').read_text() for i in range(1,5)))))
    spots=[s for s in data if s['region']=='關東']
    selections=json.loads(Path('tools/kanto-selections.json').read_text());selections.update(OVERRIDES)
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
            if sel.get('fit')=='contain':item['fit']='contain';item['changes']='縮小尺寸；卡片保留完整照片比例，不裁掉主體。照片沿用原圖授權。'
            manifest[id]=item;print(id,spot['name'],item['filename'],item['license'],flush=True)
        except Exception as e:
            errors[id]={'name':spot['name'],'error':str(e)};print('MISSING',id,str(e),flush=True)
    oldpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    Path('kanto-preparation-report.json').write_text(json.dumps({'total':116,'downloaded':len(manifest),'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print('RESULT',len(manifest),'/116',flush=True)
if __name__=='__main__':main()
