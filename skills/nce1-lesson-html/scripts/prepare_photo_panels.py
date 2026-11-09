#!/usr/bin/env python3
"""Rectify reviewed picture regions from textbook PHOTOS, without PDF access."""
import json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageOps

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=Path.cwd();regions=json.loads((root/'reports/photo-layout-audit/photo-frame-regions.json').read_text())
 for n,spec in regions.items():
  photo=root/spec['source'];original=ImageOps.exif_transpose(Image.open(photo)).convert('RGB')
  if spec['rotate']:original=original.rotate(spec['rotate'],expand=True)
  original=original.resize(tuple(spec['coordinate_space']))
  out=root/f'illustrations/work/photo-audit/panels/{int(n):03}';out.mkdir(parents=True,exist_ok=True)
  tiles=[];metadata=[]
  page_gray=cv2.cvtColor(np.array(original),cv2.COLOR_RGB2GRAY)
  mask=cv2.adaptiveThreshold(page_gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,18)
  mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
  contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
  for i,box in enumerate(spec['boxes']):
   def box_distance(contour):
    x,y,w,h=cv2.boundingRect(contour)
    return sum(abs(a-b) for a,b in zip(box,[x,y,x+w,y+h]))
   contour=min(contours,key=box_distance)
   hull=cv2.convexHull(contour)
   approx=cv2.approxPolyDP(hull,.025*cv2.arcLength(hull,True),True).reshape(-1,2)
   if len(approx)!=4:approx=cv2.approxPolyDP(hull,.045*cv2.arcLength(hull,True),True).reshape(-1,2)
   if len(approx)>4:
    sums=approx.sum(axis=1);diff=approx[:,0]-approx[:,1]
    approx=approx[[np.argmin(sums),np.argmax(diff),np.argmax(sums),np.argmin(diff)]]
   if box_distance(contour)>45 or len(set(map(tuple,approx)))!=4:
    if not spec.get('quads',{}).get(str(i+1)):
     raise ValueError(f'{n} panel {i+1}: explicit reviewed quad required; distance={box_distance(contour)}, vertices={len(approx)}')
    approx=np.array(spec['quads'][str(i+1)])
   if spec.get('quads',{}).get(str(i+1)):approx=np.array(spec['quads'][str(i+1)])
   # Order the frame polygon; bounding boxes include adjacent sloping frames.
   center=approx.mean(axis=0);order=np.argsort(np.arctan2(approx[:,1]-center[1],approx[:,0]-center[0]));approx=approx[order]
   approx=np.roll(approx,-np.argmin(approx.sum(axis=1)),axis=0)
   pts=approx.tolist();gray=page_gray
   q=np.float32(pts);tw=round((np.linalg.norm(q[1]-q[0])+np.linalg.norm(q[2]-q[3]))/2);th=round((np.linalg.norm(q[3]-q[0])+np.linalg.norm(q[2]-q[1]))/2)
   tr=cv2.getPerspectiveTransform(q,np.float32([[0,0],[tw-1,0],[tw-1,th-1],[0,th-1]]));g=cv2.warpPerspective(gray,tr,(tw,th))
   paper=cv2.morphologyEx(g,cv2.MORPH_CLOSE,np.ones((31,31),np.uint8));norm=np.minimum(255,g.astype(float)*255/np.maximum(paper,1));clean=np.where(norm<165,0,255).astype('uint8')
   tile=Image.fromarray(clean).convert('RGB');tile.save(out/f'{i+1:02}.png');tiles.append(tile)
   metadata.append({'label':i+1,'region':box,'quad_on_page':pts,'file':str((out/f'{i+1:02}.png').relative_to(root))})
  cols=min(3,len(tiles));cw,ch=320,192;rows=(len(tiles)+cols-1)//cols
  sheet=Image.new('RGB',(cols*cw,rows*ch),'white')
  for i,tile in enumerate(tiles):
   tile=ImageOps.contain(tile,(cw-16,ch-16));sheet.paste(tile,(i%cols*cw+(cw-tile.width)//2,i//cols*ch+(ch-tile.height)//2))
  sheet.save(out/'source.png');meta={'lesson':int(n),'source':spec['source'],'source_sha256':digest(photo),'rotation':spec['rotate'],'coordinate_space':spec['coordinate_space'],'tiles':metadata,'cols':cols,'cell':[cw,ch],'source_atlas_sha256':digest(out/'source.png')};(out/'source.json').write_text(json.dumps(meta,indent=2)+'\n')
  print(n,len(tiles))
if __name__=='__main__':main()
