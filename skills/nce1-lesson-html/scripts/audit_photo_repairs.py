#!/usr/bin/env python3
"""Check photo-repair coverage, assets, preserved sections and audio impact.

This structural audit supplements (and does not replace) the visual photo review.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from PIL import Image
from render_lessons import render

ROOT=Path.cwd()
REPORT=ROOT/'reports/photo-layout-audit'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical_digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def english_stream(blocks):
    text=[]
    for b in blocks:
        if b['type']=='text':text.append(b['text'])
        elif b['type']=='dialogue':text.extend(x['text'] for x in b['lines'])
        elif b['type']=='table':text.extend(str(x) for row in b['rows'] for x in row)
        elif b['type']=='vocabulary':text.extend(x['word'] for x in b['items'])
        elif b['type']=='exercise':
            for q in b['questions']:text.extend([q['prompt'],q['answer']])
    return re.findall(r"[a-z]+(?:'[a-z]+)?|\d+",' '.join(text).lower().replace('’',"'"))

def main():
    mapping=json.loads((REPORT/'repair-map.json').read_text())
    findings=json.loads((REPORT/'visual-findings.json').read_text())
    results=json.loads((REPORT/'repair-results.json').read_text())
    repaired=[];retained=[];assets=[];audio={};coverage=[]
    available=set(range(1,145))
    for n in range(48,145):
        path=ROOT/f'lessons/lesson-{n:03}.json';data=json.loads(path.read_text())
        baseline=json.loads(subprocess.check_output(['git','show',f'{mapping["baseline"]}:lessons/lesson-{n:03}.json'],text=True))
        assert data['sections']['practice']==baseline['sections']['practice'],(n,'Practice changed')
        assert data['sections']['grammar']==baseline['sections']['grammar'],(n,'Grammar changed')
        rendered,_=render(ROOT,data,available)
        assert rendered==(ROOT/f'html/lesson-{n:03}.html').read_text(),(n,'HTML stale')
        for source in findings[str(n)]['sources']:
            assert digest(ROOT/source['path'])==source['sha256'],(n,'source photo changed')
        count=sum(bool(b.get('image')) for b in data['sections']['lesson'])
        source_count=findings[str(n)]['visible_picture_units']
        note=''
        if n==66:
            assert count==16 and any(b['id']=='lesson-calendar' and b['type']=='table' for b in data['sections']['lesson'])
            note='16 pictures plus the July calendar as a real table'
        elif n==67:
            assert count==5;note='one original illustration; retain five pre-existing semantic scenes'
        else:assert count==source_count,(n,count,source_count)
        coverage.append({'lesson':n,'source_units':source_count,'html_images':count,'note':note})
        for im in data['images'].values():
            if not im.get('photo_verification'):continue
            pv=im['photo_verification'];asset=ROOT/'html'/im['src']
            assert digest(asset)==pv['asset_sha256'],(n,'asset hash')
            assert digest(ROOT/pv['photo'])==pv['sha256'],(n,'photo hash')
            with Image.open(asset) as image:assert image.size==(im['width'],im['height'])
            assets.append({'lesson':n,'path':str(asset.relative_to(ROOT)),'sha256':digest(asset)})
        if str(n) not in mapping['lessons']:
            assert data==baseline,(n,'unexpected modification');retained.append(n);continue
        repaired.append(n)
        before=english_stream(baseline['sections']['lesson']);after=english_stream(data['sections']['lesson'])
        audio_path=ROOT/f'audio/scripts/{n:03}/lesson.json'
        critical=n in [73,136,137,138,140]
        audio[str(n)]={'status':'confirmed-script-mismatch' if critical else 'review-content-changes' if before!=after else 'layout-only',
                       'script':str(audio_path.relative_to(ROOT)),
                       'script_sha256':digest(audio_path) if audio_path.exists() else None,
                       'audio_regenerated':False,
                       'note':'Existing narration script still uses replaced or incomplete text.' if critical else
                              'Compare the restored cues/tables with the narration before deciding what to regenerate.' if before!=after else
                              'English sequence unchanged after whitespace/punctuation normalization; no synthesis needed solely for splitting pictures.'}
        results[str(n)].update(json_sha256=digest(path),canonical_sha256=canonical_digest(data),audio_status=audio[str(n)]['status'])
    summary={'range':[48,144],'photos_checked':194,'lessons_repaired':repaired,'lessons_retained':retained,
             'published_panel_assets':len(assets),'coverage':coverage,'assets':assets,
             'verification':['97 JSON/HTML render checks','97 Practice/Grammar comparisons against baseline','194 source photo hashes','published image dimensions and hashes'],
             'limitations':['Source cropping: lessons 56,70,88,96,110,114,118,134. Missing photographed material is not filled from PDF.',
                            'This is a Lesson layout/content repair, not a new full Practice/Grammar proofread.',
                            'Audio has not been resynthesized; see audio-impact.json.']}
    for name,obj in [('repair-results.json',results),('final-verification.json',summary),('audio-impact.json',audio)]:
        (REPORT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checked':97,'repaired':len(repaired),'retained':len(retained),'assets':len(assets),'audio_confirmed_mismatch':[n for n,a in audio.items() if a['status']=='confirmed-script-mismatch']},ensure_ascii=False))

if __name__=='__main__':main()
