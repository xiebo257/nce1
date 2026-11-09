#!/usr/bin/env python3
"""Apply a stable lesson palette and reviewed region fills to model colors.

Only enclosed source-paper regions are filled; source ink and geometry are fixed.
This is postprocessing of local-model output, not a text-to-image substitute.
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageColor
from preserve_panel_lineart import transfer

PALETTE={'skin':'#f3c9a8','cloth':'#9dc8ce','hair':'#ead38b','paper':'#ffffff'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lessons',type=int,nargs='+',required=True);args=p.parse_args()
 config_path=Path('reports/photo-layout-audit/color-refinements.json');config=json.loads(config_path.read_text()) if config_path.exists() else {}
 for n in args.lessons:
  directory=Path(f'illustrations/work/photo-audit/panels/{n:03}');meta=json.loads((directory/'source.json').read_text());src=np.array(Image.open(directory/'source.png').convert('RGB'));guide=np.array(Image.open(directory/'colored.png').convert('RGB'));result=np.full_like(src,255);cw,ch=meta['cell'];cols=meta['cols']
  for i in range(len(meta['tiles'])):
   x,y=i%cols*cw,i//cols*ch;a=src[y:y+ch,x:x+cw];b=guide[y:y+ch,x:x+cw];tile=transfer(a,b,[])
   rgb=tile.astype(int);colored=(rgb.max(2)-rgb.min(2)>15)&(rgb.max(2)>80)
   warm=colored&(rgb[:,:,0]>rgb[:,:,2]+10)&(rgb[:,:,0]>=rgb[:,:,1])
   tile[warm]=ImageColor.getrgb(PALETTE['skin']);tile[colored&~warm]=ImageColor.getrgb(PALETTE['cloth'])
   gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);ink=(gray<150).astype('uint8');closed=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8));count,labels,stats,_=cv2.connectedComponentsWithStats(1-closed,connectivity=4)
   for px,py,name in config.get(str(n),{}).get(str(i+1),[]):
    label=labels[py,px]
    if label==0:
     choices=[]
     for dy in range(-5,6):
      for dx in range(-5,6):
       yy,xx=py+dy,px+dx
       if 0<=yy<ch and 0<=xx<cw and labels[yy,xx]>0:choices.append((dx*dx+dy*dy,int(labels[yy,xx])))
     if not choices:raise ValueError((n,i+1,px,py,'no fill region'))
     label=min(choices)[1]
    rx,ry,rw,rh,area=stats[label]
    if area>cw*ch*.4 and name!='paper':raise ValueError((n,i+1,px,py,'background region'))
    tile[(labels==label)&(gray>=150)]=ImageColor.getrgb(PALETTE.get(name,name))
   tile[gray<90]=0
   Image.fromarray(tile).save(directory/f'candidate-{i+1:02}.png');result[y:y+ch,x:x+cw]=tile
  Image.fromarray(result).save(directory/'preserved.png')
  record=json.loads((directory/'generation.json').read_text());record['color_refinement']={'palette':PALETTE,'regions':config.get(str(n),{})};record['preserved_sha256']=hashlib.sha256((directory/'preserved.png').read_bytes()).hexdigest();(directory/'generation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print('REFINED',n)
if __name__=='__main__':main()
