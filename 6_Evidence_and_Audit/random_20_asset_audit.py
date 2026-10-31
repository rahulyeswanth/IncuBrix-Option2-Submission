#!/usr/bin/env python3
"""Reproduce the fixed 20-asset sample and machine-verifiable checks."""
import argparse, csv, json, random, re, subprocess
from pathlib import Path
from PIL import Image

SEED = 20261030

def inspect(root, aid):
    d=root/aid; spec=json.loads((d/'spec.json').read_text(encoding='utf-8'))
    fmt=spec['format']; expected=tuple(spec['size']); duration=''; dimensions=''; final=''
    if fmt=='Short video':
        final=d/'final.mp4'; data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(final)],text=True))
        dimensions=(data['streams'][0]['width'],data['streams'][0]['height']); duration=round(float(data['format']['duration']),3)
    elif fmt=='Carousel':
        final=d/'carousel.pdf'; slides=sorted(d.glob('slide_*.png'))
        with Image.open(slides[0]) as im: dimensions=im.size
    elif fmt=='Graphic':
        final=d/'final.png';
        with Image.open(final) as im: dimensions=im.size
    else:
        final=d/'final.txt'; dimensions='n/a'
    return {'asset_id':aid,'platform':spec['platform'],'format':fmt,'hook':spec['hook'],
      'hook_words':len(spec['hook'].split()),'dimensions':dimensions,'expected_dimensions':expected,
      'duration_seconds':duration,'media_exists':final.exists() and final.stat().st_size>0,
      'utm_valid':all(k+'=' in spec['utm_link'] for k in ['utm_source','utm_medium','utm_campaign','utm_content','utm_term']) and f"utm_content={aid}" in spec['utm_link'],
      'editable_source':(d/'spec.json').exists(),'has_cta':bool(spec.get('cta')),
      'hashtag_count':len(re.findall(r'#\w+',spec['caption']))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--assets',type=Path,default=Path('../2_Final_Content/assets')); ap.add_argument('--out',type=Path,default=Path('random_20_machine_checks.csv')); a=ap.parse_args()
    ids=sorted(p.name for p in a.assets.iterdir() if p.is_dir()); sample=random.Random(SEED).sample(ids,20)
    rows=[inspect(a.assets,x) for x in sample]
    with a.out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    print(f'seed={SEED} population={len(ids)} sample={len(rows)} output={a.out}')
if __name__=='__main__': main()
