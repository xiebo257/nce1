#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the reviewed photo-layout map, preserving independent Practice/Grammar.

Source text is declarative in repair-map.json. No OCR reading-order heuristics and
no PDF access. A baseline Git commit makes repeated runs deterministic. Color
candidates require a hash-bound visual approval before they can be published.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(path, value, indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=indent)+'\n')


def clock_picture(time, path):
    """Exact diagram, drawn from visually checked times rather than a generative model."""
    hour, minute = map(int, time.split(':'))
    scale = 3; size = 240*scale; c=size/2; radius=100*scale
    im=Image.new('RGB',(size,size),'white');d=ImageDraw.Draw(im)
    d.ellipse((c-radius,c-radius,c+radius,c+radius),fill='#fff9e7',outline='#27647a',width=6*scale)
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',17*scale)
    for tick in range(60):
        angle=tick*math.pi/30-math.pi/2
        a=radius-8*scale;b=a-(8 if tick%5==0 else 3)*scale
        d.line((c+math.cos(angle)*a,c+math.sin(angle)*a,c+math.cos(angle)*b,c+math.sin(angle)*b),fill='#435c64',width=2*scale)
    for value in range(1,13):
        angle=value*math.pi/6-math.pi/2;r=radius-28*scale
        d.text((c+math.cos(angle)*r,c+math.sin(angle)*r),str(value),font=font,fill='#203d4b',anchor='mm')
    for angle,length,width in [((hour%12+minute/60)*math.pi/6,49,6),(minute*math.pi/30,73,4)]:
        angle-=math.pi/2
        d.line((c,c,c+math.cos(angle)*length*scale,c+math.sin(angle)*length*scale),fill='#174d62',width=width*scale)
    d.ellipse((c-5*scale,c-5*scale,c+5*scale,c+5*scale),fill='#174d62')
    im.resize((240,240),Image.Resampling.LANCZOS).save(path,quality=92)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lessons',type=int,nargs='+',required=True)
    args=parser.parse_args();root=Path.cwd()
    mapping=json.loads((root/'reports/photo-layout-audit/repair-map.json').read_text())
    reviews_path=root/'reports/photo-layout-audit/color-reviews.json'
    reviews=json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    logpath=root/'reports/photo-layout-audit/repair-results.json'
    results=json.loads(logpath.read_text()) if logpath.exists() else {}
    for n in args.lessons:
        recipe=mapping['lessons'][str(n)];photo=root/recipe['source'];source='../'+recipe['source']
        path=root/f'lessons/lesson-{n:03}.json'
        raw=subprocess.check_output(['git','show',f'{mapping["baseline"]}:lessons/lesson-{n:03}.json'],text=True)
        old=json.loads(raw);data=copy.deepcopy(old);blocks=data['sections']['lesson']
        image_blocks=[b for b in blocks if b.get('image')]
        target_ids={b['id'] for b in image_blocks} if recipe['panels'] else set()
        old_slots={b['image'] for b in image_blocks} if recipe['panels'] else set()
        folder=root/f'html/assets/lesson-{n:03}';folder.mkdir(exist_ok=True)
        if recipe['image_mode']=='photo-color':
            work=root/f'illustrations/work/photo-audit/panels/{n:03}'
            if reviews.get(str(n),{}).get('sha256')!=digest(work/'preserved.png'):
                raise ValueError(f'Lesson {n}: final color atlas has not been visually approved')
            for character in data.get('characters',{}).values():
                character.pop('illustration_appearance',None)
                character['illustration_note']='Appearance follows the photographed source drawings; use the same source character in every scene.'
                character['photo_reference']=source
            data['illustration_palette']='Source black ink, warm peach skin and pale teal accents; reviewed source regions override model color drift.'
            archive=root/f'illustrations/photo-repairs/{n:03}';archive.mkdir(parents=True,exist_ok=True)
            for filename in ['source.png','source.json','generation.json']:
                shutil.copy2(work/filename,archive/filename)
            shutil.copy2(work/'colored.png',archive/'color-guide.png')
            write_json(archive/'review.json',reviews[str(n)])
        new_blocks=[]
        for i,panel in enumerate(recipe['panels']):
            slot=f'photo-panel-{i+1:02}';dest=folder/f'{slot}.webp';extra={}
            if recipe['image_mode']=='photo-color':
                img=Image.open(work/f'candidate-{i+1:02}.png').convert('RGB')
                extra={'generation_record':f'illustrations/photo-repairs/{n:03}/generation.json',
                       'review_record':f'illustrations/photo-repairs/{n:03}/review.json'}
            else:
                oldslot=panel.get('old_slot',recipe.get('old_slot'))
                oldimage=root/'html'/old['images'][oldslot]['src'];img=Image.open(oldimage).convert('RGB')
                if 'crop' in panel:box=panel['crop']
                else:
                    cols=panel.get('cols',recipe.get('cols'));rows=panel.get('rows',math.ceil(len(recipe['panels'])/cols));index=panel.get('cell_index',i)
                    box=[round(index%cols*img.width/cols),round(index//cols*img.height/rows),round((index%cols+1)*img.width/cols),round((index//cols+1)*img.height/rows)]
                img=img.crop(box)
                extra={'reused_asset':str(oldimage.relative_to(root)),'reused_sha256':digest(oldimage),'crop':box}
            img.save(dest,quality=94)
            text=panel.get('text') or ' '.join(line['text'] for line in panel.get('lines',[]))
            metadata={'kind':'scene' if n%2 else 'item','status':'ready','description':text,
                      'source':source,'src':str(dest.relative_to(root/'html')),'width':img.width,'height':img.height,
                      'display_width':320 if n%2 else 256,'origin':'photo-verified-color-panel','caption':f'Picture {panel["label"]}',
                      'photo_verification':{'photo':recipe['source'],'sha256':digest(photo),'label':panel['label'],'asset_sha256':digest(dest),**extra}}
            if panel.get('source_group'):metadata['caption']+=f' · Group {panel["source_group"]}'
            data['images'][slot]=metadata
            block={'id':image_blocks[0]['id'] if i==0 else f'lesson-photo-panel-{i+1:02}',
                   'type':'dialogue' if 'lines' in panel else 'text','source':source,'image':slot,'source_label':panel['label']}
            block.update({k:v for k,v in panel.items() if k in ['lines','text','translation','source_group','cue_heading']})
            if panel.get('source_status'):
                block['source_status']='原照片下缘裁切：此处为图片说明或保留文字，未将缺失原句视为已核验。'
                metadata['photo_verification']['limitation']=panel['source_status']
            new_blocks.append(block)
        replaced=[];inserted=False
        for block in blocks:
            if block['id'] in recipe.get('remove_blocks',[]):continue
            if block['id'] in target_ids:
                if not inserted:
                    for b in recipe.get('before_panels',[]):replaced.append(dict(b,source=source))
                    replaced.extend(new_blocks)
                    for b in recipe.get('after_panels',[]):replaced.append(dict(b,source=source))
                    inserted=True
            else:replaced.append(block)
        blocks=replaced;data['sections']['lesson']=blocks
        for slot in old_slots:del data['images'][slot]
        if recipe.get('merge_dialogue'):
            for b in blocks:
                if b['type'] != 'dialogue': continue
                merged=[]
                for line in b['lines']:
                    if merged and merged[-1]['speaker']==line['speaker']:
                        for key in ['text','translation']:merged[-1][key]+=' '+line[key]
                    else:merged.append(copy.deepcopy(line))
                for i,line in enumerate(merged):line['number']=i+1
                b['lines']=merged;b['source']=source
        if recipe.get('dialogue_lines'):
            b=next(b for b in blocks if b['type']=='dialogue')
            b['lines']=recipe['dialogue_lines'];b['source']=source
        if recipe.get('question_text'):
            b=next(b for b in blocks if b['type']=='text' and 'question' in b['id'])
            b.update(text=recipe['question_text'],translation=recipe['question_translation'],source=source)
            blocks.remove(b);blocks.insert(1,b)
        if recipe.get('contrast_pairs'):
            action_blocks=[b for b in blocks if b.get('image','').startswith('action-')]
            for i,b in enumerate(action_blocks):
                b['source_group']=i//2+1
                data['images'][b['image']]['caption']+=f' · Pair {i//2+1}'
        if recipe.get('source_limitation'):
            blocks.append({'id':'lesson-photo-source-note','type':'text','source':source,
                           'text':recipe['source_limitation']})
        if recipe.get('intro_text'):
            intro=next(b for b in blocks if 'intro' in b['id']);intro['text']=recipe['intro_text'];intro.pop('translation',None)
            if recipe.get('intro_translation'):intro['translation']=recipe['intro_translation']
        if recipe.get('fix_cue_speakers'):
            for b in blocks:
                if b['type']=='dialogue' and b.get('image'):
                    lines=b.pop('lines');b['type']='text';b['text']='\n'.join(x['text'] for x in lines);b['translation']='\n'.join(x['translation'] for x in lines);b['source']=source
        if recipe.get('clocks'):
            clockblocks=[]
            for i,time in enumerate(recipe['clocks']):
                slot=f'photo-clock-{i+1:02}';dest=folder/f'{slot}.webp';clock_picture(time,dest)
                data['images'][slot]={'kind':'item','status':'ready','description':f'Clock {i+1}: {time}',
                   'source':source,'src':str(dest.relative_to(root/'html')),'width':240,'height':240,
                   'display_width':240,'caption':f'{i+1} · {time}','origin':'exact-clock-diagram',
                   'photo_verification':{'photo':recipe['source'],'sha256':digest(photo),'time':time,'asset_sha256':digest(dest)}}
                clockblocks.append({'id':'lesson-clocks' if i==0 else f'lesson-clock-{i+1:02}','type':'text','source':source,'text':time,'image':slot})
            index=next(i for i,b in enumerate(blocks) if b['id']=='lesson-clocks');blocks[index:index+1]=clockblocks
        for entry in recipe.get('tables',[]):
            table=entry['block'];replace=entry.get('replace')
            if replace:
                index=next(i for i,b in enumerate(blocks) if b['id']==replace);blocks[index]=table
            elif n==66:
                index=next(i for i,b in enumerate(blocks) if b['id'].startswith('lesson-enjoy'));blocks.insert(index,table)
            else:
                index=next(i for i,b in enumerate(blocks) if b.get('image'));blocks.insert(index,table)
        if n==96:
            table=next(b for b in blocks if b['type']=='table');blocks.remove(table)
            index=next(i for i,b in enumerate(blocks) if b['id']=='lesson-photo-panel-13');blocks.insert(index,table)
        if n==73:
            data['description']='Mrs. Mills loses her way in London and asks a German tourist for directions. 米尔斯夫人在伦敦迷路，向一位德国游客问路。'
            for b in blocks:
                if b['id']=='lesson-intro':
                    b['text']='Listen then answer this question.\nWhy did the man need a phrasebook?';b['translation']='听录音，然后回答问题。为什么这位男士需要一本常用语手册？';b['source']=source
                elif b['id']=='lesson-listening-answer':
                    b.update(source=source,instruction='Listen then answer this question.',translation='根据课文回答问题。',context='Mrs. Mills asks a German tourist for directions.')
                    b['questions'][0].update(prompt='Why did the man need a phrasebook?',answer='Because he did not speak English.')
                elif b['id']=='lesson-notes':
                    b['source']='../img/lesson-073-02-text.jpg'
                    b['items']=[{'title':'…, and she lost her way.','text':'句中的 and 意为“所以”，表示结果。'},
                                {'title':'she said to herself','text':'她心中暗想。'}]
                elif b['id']=='lesson-reference-translation':
                    b.update(source=source,text='参考译文\n'+'\n'.join(p['translation'] for p in recipe['panels']))
        if recipe.get('replace_listening'):
            exercise=next(b for b in blocks if b['type']=='exercise' and 'listen' in b['id'])
            exercise['context']='Supplementary practice based on the photographed captions. 依据照片正文补充的练习。'
            exercise['source']=source;exercise['answer_kind']='suggested'
            qs=[]
            for i,panel in enumerate(recipe['panels']):
                qs.append({'id':f'l{n}-photo-listen-{i+1}','number':i+1,'prompt':f'Picture {panel["label"]}: Say the sentence(s).','answer':panel['text']})
            exercise['questions']=qs;exercise['expected_items']=len(qs)
            data['description']=f'{len(qs)} source pictures with individually matched captions. 根据教材照片恢复逐图正文。'
            data['answer_note']='Lesson picture captions are transcribed from the textbook photograph. Listening practice answers are supplementary. Independent Practice and Grammar answer provenance is recorded in their exercise groups.'
        if n==114:
            for b in blocks:
                if b['type']=='exercise' and 'listen' in b['id']:
                    for q in b['questions']:
                        for k in ['prompt','answer']:q[k]=q[k].replace('cookies','biscuits')
        if n==80:
            blocks.insert(0,{'id':'lesson-photo-introduction','type':'text','source':source,'text':'Listen and answer the questions.'})
        data['expected_answers']=sum(not q.get('example',False) for sec in data['sections'].values() for b in sec if b['type']=='exercise' for q in b['questions'])
        assert data['sections']['practice']==old['sections']['practice']
        assert data['sections']['grammar']==old['sections']['grammar']
        data['photo_layout_review']={'report':'reports/photo-layout-audit/visual-findings.json',
                                    'source':recipe['source'],'sha256':digest(photo),'scope':'Lesson picture/text layout'}
        indent=len(re.match(r'\{\n( +)',raw).group(1))
        write_json(path,data,indent)
        results[str(n)]={'panels':len(recipe['panels']),'clocks':len(recipe.get('clocks',[])),
                         'practice_unchanged':True,'grammar_unchanged':True,'audio_status':'needs-text-comparison',
                         'json_sha256':digest(path)}
        write_json(logpath,results)
        print('REPAIRED',n,len(recipe['panels']),flush=True)


if __name__=='__main__':main()
