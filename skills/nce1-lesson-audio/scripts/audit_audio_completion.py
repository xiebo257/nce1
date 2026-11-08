#!/usr/bin/env python3
"""Check the final collection and save a compact, durable validation record."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import soundfile as sf

PARTS = [('lesson','1-lesson'),('practice','2-practice'),('grammar','3-gramar')]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--end',type=int,default=144)
    parser.add_argument('--checked-start',type=int,default=26)
    args=parser.parse_args()
    root=Path('audio/work/batch-025-144')
    tracked=set(subprocess.check_output(['git','ls-files','--','audio'],text=True).splitlines())
    states=[json.loads(p.read_text()) for p in sorted(root.glob('queue-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)]
    lessons=[]
    published_paths=[]
    for n in range(1,args.end+1):
        reviewed=[s for s in states if s['start']<=n<=s['end']][:1]
        if n>=args.checked_start:
            assert reviewed and reviewed[0].get('pushed'), f'Lesson {n} has not completed its latest publication'
        files=[]
        published_paths.append(f'audio/scripts/{n:03}')
        for part,suffix in PARTS:
            path=Path(f'audio/{n:03}-{suffix}.wav')
            assert path.is_file() and str(path) in tracked, path
            published_paths.append(str(path))
            info=sf.info(path)
            assert info.samplerate==24000 and info.channels==1 and info.frames>0, path
            item=dict(file=path.name,seconds=round(info.duration,2),bytes=path.stat().st_size)
            digest=hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
            item['sha256']=digest.hexdigest()
            if n>=args.checked_start:
                script=json.loads(Path(f'audio/scripts/{n:03}/{part}.json').read_text())
                report=json.loads((root/f'{n:03}-{suffix}-asr.json').read_text())
                seen=[]
                for group in report['groups']:
                    expected=' '.join(script['segments'][i-1]['text'] for i in group['segments'])
                    assert expected==group['expected'], (n,part,'stale ASR script')
                    seen.extend(group['segments'])
                assert seen==list(range(1,len(script['segments'])+1)),(n,part,'incomplete ASR coverage')
                item['segments']=len(script['segments'])
                item['retained_asr_differences']=[dict(segment=f['segment'],text=f['text'],heard=f['heard']) for f in report['findings']]
            files.append(item)
        notes=[]
        for state in reviewed:
            accept=root/f"accept-{state['start']:03}-{state['end']:03}.json"
            if accept.exists():notes.append(json.loads(accept.read_text()).get('review',''))
        lessons.append(dict(lesson=n,files=files,review_notes=notes))
    subprocess.run(['git','diff','--exit-code','--quiet','HEAD','--',*published_paths],check=True)
    summary=dict(lessons=len(lessons),files=sum(len(x['files']) for x in lessons),
                 seconds=round(sum(f['seconds'] for x in lessons for f in x['files']),2),
                 bytes=sum(f['bytes'] for x in lessons for f in x['files']))
    result=dict(summary=summary,checked_start=args.checked_start,
                method='Local Qwen3-TTS; source review; grouped and individual Whisper checks; bounded regeneration; WAV and script integrity checks.',
                limitation='Retained transcript differences were reviewed separately. ASR does not verify subjective naturalness, accent, linking, reduction, or pitch contours.',
                lessons=lessons)
    Path('audio/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
