#!/usr/bin/env python3
"""Colorize a lesson's source panels together, then split them into reviewed candidates.

A shared model pass keeps repeated cartoon characters consistent and avoids loading
and encoding the model for every tiny picture. Does not publish or approve images.
"""
import argparse
import gc
import json
import math
import os
from pathlib import Path
import time
from illustrate_lessons import MODEL_ID, MODEL_PATH, candidate_paths, digest, lesson_jobs, specification, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--from',dest='start',type=int,default=52)
    p.add_argument('--to',dest='end',type=int,default=144)
    a=p.parse_args();repo=a.repo.resolve()
    if not 45<=a.start<=a.end<=144:p.error('Range must be within 45–144')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import mlx.core as mx
    from PIL import Image,ImageOps
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2KleinEdit
    mx.set_cache_limit(256*1024**2);model=None
    for n in range(a.start,a.end+1):
        if n%2:continue
        jobs=[j for j in lesson_jobs(repo,n,768,512) if j.get('source_reference') and not j.get('exact_diagram')]
        if not jobs:continue
        specs=[specification(repo,j) for j in jobs]
        cached=True
        for j,s in zip(jobs,specs):
            img,meta=candidate_paths(repo,j)
            if not img.exists() or not meta.exists():cached=False;break
            old=json.loads(meta.read_text())
            if old.get('fingerprint')!=s['fingerprint'] or old.get('sha256')!=digest(img):cached=False;break
        if cached:print('CACHED_LESSON',n,flush=True);continue
        cols=min(4,math.ceil(math.sqrt(len(jobs))))
        cw,ch=((256,192) if len(jobs)>15 else (320,224)) if len(jobs)>1 else (jobs[0]['width'],jobs[0]['height'])
        if len(jobs)>1:
            aspects=[]
            for j in jobs:
                with Image.open(repo/j['source_reference']) as original:
                    aspects.append(original.width/original.height)
            if min(aspects)>3:
                cols,cw,ch=1,1024,288
        rows=math.ceil(len(jobs)/cols)
        width,height=cols*cw,rows*ch
        source=Image.new('RGB',(width,height),'white')
        for i,j in enumerate(jobs):
            with Image.open(repo/j['source_reference']) as original:
                tile=ImageOps.contain(original.convert('RGB'),(cw-8,ch-8)) if len(jobs)>1 else original.convert('RGB').resize((cw,ch))
                source.paste(tile,(i%cols*cw+(cw-tile.width)//2,i//cols*ch+(ch-tile.height)//2))
        directory=repo/f'illustrations/work/atlases/{n:03}';directory.mkdir(parents=True,exist_ok=True)
        source_path=directory/'source.png';source.save(source_path)
        prompt=(f'Colorize this exact textbook cartoon sheet in place. There are {len(jobs)} input tiles in {cols} columns and {rows} rows. '
                'Keep the grid positions, panel borders, every face, hairstyle, pose, object, count and spatial relation EXACTLY unchanged. '
                'Repeated characters must have the same hair color, skin tone and clothing colors in every panel. '
                'Use natural skin tones, cheerful full-color clothing, realistic object colors, and pure white background. '
                'Remove gray paper texture and faint reverse-page bleed-through. Preserve all visible letters, numerals and clock hands. '
                'Do not draw extra objects, people, labels or captions. Do not move, resize, combine, omit or rearrange any tile. '
                'Color only the existing drawing, preserving the original black outlines.')
        if len(jobs)==1:prompt=jobs[0]['prompt']
        if model is None:
            model=Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(),model_path=str(MODEL_PATH),quantize=4)
        print('COLORIZING_LESSON',n,len(jobs),width,height,flush=True)
        start=time.monotonic();mx.reset_peak_memory()
        result=model.generate_image(seed=n*1000+901,prompt=prompt,num_inference_steps=4,width=width,height=height,guidance=1.0,image_paths=[source_path])
        output=directory/'colored.png';result.save(str(output));elapsed=round(time.monotonic()-start,2)
        atlas_meta={'model':MODEL_ID,'seed':n*1000+901,'prompt':prompt,'width':width,'height':height,'steps':4,
                    'seconds':elapsed,'peak_mlx_gb':round(mx.get_peak_memory()/1e9,3),'input_sha256':digest(source_path),
                    'output_sha256':digest(output),'slots':[j['slot'] for j in jobs],
                    'inputs':[{'path':j['source_reference'],'sha256':s['source_reference_sha256']} for j,s in zip(jobs,specs)]}
        write_json(directory/'generation.json',atlas_meta)
        with Image.open(output) as atlas:
            for i,(j,s) in enumerate(zip(jobs,specs)):
                img,meta=candidate_paths(repo,j);img.parent.mkdir(parents=True,exist_ok=True)
                box=(i%cols*cw,i//cols*ch,(i%cols+1)*cw,(i//cols+1)*ch)
                atlas.crop(box).save(img)
                s.update(sha256=digest(img),status='candidate',seconds=elapsed/len(jobs),atlas_generation=atlas_meta,
                         postprocess={'method':'split-shared-colorized-atlas','crop_box':list(box),'output_size':[cw,ch]})
                write_json(meta,s)
        del result;mx.clear_cache();gc.collect()
        print('LESSON_CANDIDATES_REQUIRE_REVIEW',n,elapsed,'seconds',flush=True)


if __name__=='__main__':main()
