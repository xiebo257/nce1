#!/usr/bin/env python3
"""Redraw blurry odd-lesson photo panels as individual local-model images."""
import argparse, copy, gc, hashlib, json, math, os, subprocess, time
from collections import deque
from pathlib import Path
from PIL import Image, ImageOps

REPORT=Path('reports/odd-illustration-redraw'); WORK=Path('illustrations/work/redraw-odd')
MODEL='mlx-community/FLUX.2-Klein-4B-4bit'; CELL=(512,320)

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(v): return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def lesson_slots(d): return list(dict.fromkeys(b['image'] for b in d['sections']['lesson'] if b.get('image')))
def plan():
 baseline=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(); lessons={}
 for n in range(71,144,2):
  d=read(f'lessons/lesson-{n:03}.json'); items=[]
  for slot in lesson_slots(d):
   im=d['images'][slot]
   if im.get('width',0)>=512: continue
   source='html/'+im['src']; blocks=[b for b in d['sections']['lesson'] if b.get('image')==slot]
   items.append({'slot':slot,'reference':source,'reference_sha256':digest(source),
    'source_photo':f'img/lesson-{n:03}-01-text.jpg','source_photo_sha256':digest(f'img/lesson-{n:03}-01-text.jpg'),
    'previous':copy.deepcopy(im),'cue':im.get('description',''),'text':' '.join(b.get('text','') for b in blocks),
    'edit_instruction':('Redraw this one reference panel as a crisp full-color educational cartoon. '
      'Preserve the exact people, count, identities, actions, objects and spatial relationship shown. '
      'Use clear smooth outlines, natural anatomy, solid warm colors and subtle cel shading. '
      'Keep all complete subjects inside the frame. No captions, speech bubbles, random letters or extra people. '
      'Meaningful signs, numbers and labels may remain only when clearly present in the reference. '
      'Do not copy blur, scan noise, hatching or paper texture. Scene: '+im.get('description',''))})
  if items: lessons[str(n)]={'items':items,'sections_sha256':fp(d['sections'])}
 result={'baseline':baseline,'cell':list(CELL),'model':MODEL,'lessons':lessons}
 write(REPORT/'plan.json',result); print('PLANNED',sum(len(x['items']) for x in lessons.values()),'images in',len(lessons),'lessons')
def groups(lesson): return [[x] for x in lesson['items']]
def spec(n,item,index):
 return {'model':MODEL,'prompt':item['edit_instruction'],'seed':n*10000+index+7000,'steps':4,'guidance':1.0,
  'width':CELL[0],'height':CELL[1],'cell':list(CELL),'mode':'reference-edit-raw',
  'inputs':[{'slot':item['slot'],'path':item['reference'],'sha256':item['reference_sha256']}]}

def clean_reference(source, target):
 im=Image.open(source).convert('RGB'); w,h=im.size
 pix=im.load(); white={(x,y) for y in range(h) for x in range(w)
              if min(pix[x,y])>235 and max(pix[x,y])-min(pix[x,y])<18}
 seen=set(); fills=[]
 for start in white:
  if start in seen: continue
  q=[start];seen.add(start); comp=[]; edge=False
  while q:
   x,y=q.pop();comp.append((x,y));edge |= x in (0,w-1) or y in (0,h-1)
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if 0<=nx<w and 0<=ny<h and (nx,ny) in white and (nx,ny) not in seen:
     seen.add((nx,ny));q.append((nx,ny))
  if not edge and len(comp)>700:
   xs=[p[0] for p in comp];ys=[p[1] for p in comp]
   if max(xs)-min(xs)>40 and max(ys)-min(ys)>15: fills.append((min(xs),min(ys),max(xs),max(ys)))
 from PIL import ImageDraw
 mask=set()
 for x0,y0,x1,y1 in fills:
  for y in range(max(0,y0-5),min(h,y1+6)):
   for x in range(max(0,x0-5),min(w,x1+6)): mask.add((x,y))
 # Small iterative inpaint restores a nearby sky, wall or plain background and
 # avoids leaving a white rectangle where a speech bubble was erased.
 base=im.load(); known=set((x,y) for y in range(h) for x in range(w) if (x,y) not in mask)
 for _ in range(400):
  updates=[]
  for x,y in list(mask):
   vals=[]
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if (nx,ny) in known: vals.append(base[nx,ny])
   if vals: updates.append((x,y,tuple(sum(v[k] for v in vals)//len(vals) for k in range(3))))
  if not updates: break
  for x,y,c in updates: base[x,y]=c;known.add((x,y));mask.discard((x,y))
 im.save(target)
def generate(numbers=None):
 os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
 import mlx.core as mx
 from mflux.models.common.config import ModelConfig
 from mflux.models.flux2.variants import Flux2KleinEdit
 mx.set_cache_limit(256*1024**2); model=None
 plan=read(REPORT/'plan.json')['lessons']; numbers=numbers or [int(x) for x in plan]
 for n in numbers:
  lesson=plan[str(n)]
  for i,item in enumerate(lesson['items'],1):
   folder=WORK/f'{n:03}'/f'group-{i:02}';folder.mkdir(parents=True,exist_ok=True)
   s=spec(n,item,i); key=fp(s); out=folder/'redrawn.png'; rec=folder/'generation.json'
   if rec.exists() and out.exists() and read(rec).get('fingerprint')==key and read(rec).get('sha256')==digest(out):
    print('CACHED',n,item['slot'],flush=True);continue
   ref=folder/'reference.png';Image.open(item['reference']).convert('RGB').save(ref)
   if model is None:model=Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(),model_path=str(Path.home()/'.cache/nce1-models/FLUX.2-Klein-4B-4bit'),quantize=4)
   print('START',n,item['slot'],flush=True);start=time.monotonic()
   result=model.generate_image(seed=s['seed'],prompt=s['prompt'],num_inference_steps=4,width=512,height=320,guidance=1.0,image_paths=[ref])
   result.save(str(out),overwrite=True)
   with Image.open(out) as im: assert im.size==(512,320)
   write(rec,dict(s,fingerprint=key,sha256=digest(out),seconds=round(time.monotonic()-start,2),status='candidate-needs-visual-review'))
   print('CANDIDATE',n,item['slot'],flush=True);del result;mx.clear_cache();gc.collect()
def contact(numbers):
 from PIL import ImageDraw
 plan=read(REPORT/'plan.json')['lessons']
 for n in numbers:
  ims=[]
  for i,item in enumerate(plan[str(n)]['items'],1):
   p=WORK/f'{n:03}'/f'group-{i:02}'/f'{item["slot"]}.png'
   if not p.exists(): p=WORK/f'{n:03}'/f'group-{i:02}'/'redrawn.png'
   if p.exists():
    im=Image.open(p).convert('RGB').resize((256,160));ims.append((item['slot'],im))
  sheet=Image.new('RGB',(768,((len(ims)+2)//3)*190),'white');d=ImageDraw.Draw(sheet)
  for j,(label,im) in enumerate(ims):x=j%3*256;y=j//3*190;sheet.paste(im,(x,y));d.text((x+4,y+163),label,fill='black')
  path=WORK/f'{n:03}'/'contact-01.jpg';path.parent.mkdir(parents=True,exist_ok=True);sheet.save(path,quality=90);print(path)
def review(numbers,notes):
 plan=read(REPORT/'plan.json')['lessons']
 for n in numbers:
  records={}
  for i,item in enumerate(plan[str(n)]['items'],1):
   folder=WORK/f'{n:03}'/f'group-{i:02}';rec=read(folder/'generation.json');out=folder/'redrawn.png'
   assert rec['fingerprint']==fp(spec(n,item,i));assert rec['sha256']==digest(out)
   records[str(i)]={'slot':item['slot'],'sha256':digest(out)}
  write(REPORT/f'reviews/{n:03}.json',{'lesson':n,'notes':notes,'groups':records})
def publish(numbers):
 from PIL import Image
 plan=read(REPORT/'plan.json')['lessons']
 for n in numbers:
  approval=read(REPORT/f'reviews/{n:03}.json');path=Path(f'lessons/lesson-{n:03}.json');data=read(path);assert fp(data['sections'])==plan[str(n)]['sections_sha256']
  results=[]
  for i,item in enumerate(plan[str(n)]['items'],1):
   folder=WORK/f'{n:03}'/f'group-{i:02}';out=folder/'redrawn.png';assert digest(out)==approval['groups'][str(i)]['sha256']
   archive=Path(f'illustrations/redraw-odd/{n:03}/group-{i:02}');archive.mkdir(parents=True,exist_ok=True)
   (archive/'reference.png').write_bytes(Path(item['reference']).read_bytes());(archive/'generation.json').write_bytes((folder/'generation.json').read_bytes())
   target=Path(f'html/assets/lesson-{n:03}/{item["slot"]}-redrawn.webp');target.parent.mkdir(parents=True,exist_ok=True)
   with Image.open(out) as im:im.save(target,'WEBP',quality=95,method=6);w,h=im.size
   meta=data['images'][item['slot']];meta.update(src=str(target.relative_to('html')),width=w,height=h,display_width=256,origin='local-model-redraw',description=item['cue'],alt=item['cue'],generation={'model':MODEL,'manifest':str(archive/'generation.json')})
   if meta.get('photo_verification'):meta['photo_verification']['asset_sha256']=digest(target)
   results.append({'slot':item['slot'],'asset':str(target),'sha256':digest(target),'dimensions':[w,h]})
  path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');write(REPORT/f'published/{n:03}.json',{'lesson':n,'images':results,'sections_sha256':plan[str(n)]['sections_sha256']})
  subprocess.run(['python3','skills/nce1-lesson-html/scripts/render_lessons.py','--repo','.','--from',str(n),'--to',str(n)],check=True);print('PUBLISHED',n,len(results))
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','generate','contact','review','publish']);p.add_argument('--lessons',nargs='+',type=int);p.add_argument('--notes');a=p.parse_args()
 if a.command=='plan':plan();return
 if a.command=='generate':generate(a.lessons);return
 if a.command=='contact':contact(a.lessons);return
 if a.command=='review':review(a.lessons,a.notes or 'Visually inspected every individual redraw.');return
 publish(a.lessons)
if __name__=='__main__':main()
