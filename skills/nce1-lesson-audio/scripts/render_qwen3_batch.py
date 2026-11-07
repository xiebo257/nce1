#!/usr/bin/env python3
"""Render reviewed lesson JSON files locally, reusing exact speech and resuming safely."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model
from render_qwen3_audio import resolve_segments

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def write_json(path, value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)

def render(model, script, model_path, cache, output):
    data=json.loads(script.read_text());segments=resolve_segments(data,script)
    supported={s.lower() for s in model.supported_speakers}
    if any(s['speaker'].lower() not in supported for s in segments):
        raise ValueError(f'Unsupported speaker in {script}')
    work=output.parent/'work'/output.stem;parts=work/'segments';parts.mkdir(parents=True,exist_ok=True)
    times=[];frames=[];started=time.monotonic();sr=24000
    for i,s in enumerate(segments,1):
        # A content-derived seed makes repeated teaching phrases reproducible.
        identity=dict(model=str(model_path.resolve()),text=s['text'],speaker=s['speaker'],instructions=s['instructions'])
        seed=s.get('generation_seed',int(digest(identity)[:8],16)%(2**31))
        temperature=s.get('generation_temperature',.65)
        identity.update(seed=seed,temperature=temperature,renderer_version=1)
        key=digest(identity);wav=cache/(key+'.wav');meta=cache/(key+'.json')
        reused=False
        if wav.exists() and meta.exists():
            audio,rate=sf.read(wav,dtype='float32');details=json.loads(meta.read_text())
            if rate!=sr or not len(audio) or not np.isfinite(audio).all():raise ValueError(f'Invalid cached audio: {wav}')
            reused=True
        else:
            words=len(s['text'].split());limit=max(3.8,2+words*.65)
            attempts=[]
            for attempt in range(3):
                trial_seed=seed+attempt*100003;mx.random.seed(trial_seed);chunks=[]
                for result in model.generate_custom_voice(text=s['text'],speaker=s['speaker'],language='English',instruct=s['instructions'],temperature=temperature,max_tokens=min(260,max(60,words*10+35))):
                    if result.sample_rate!=sr:raise ValueError('Unexpected sample rate')
                    chunks.append(np.asarray(result.audio,dtype=np.float32).reshape(-1))
                if not chunks:raise RuntimeError(f'Empty result for {script}:{i}')
                audio=np.concatenate(chunks)
                if not len(audio) or not np.isfinite(audio).all():raise ValueError('Invalid generated audio')
                seconds=len(audio)/sr;attempts.append(dict(seed=trial_seed,seconds=seconds))
                mx.clear_cache()
                if seconds<=limit:break
            details=dict(seed=trial_seed,temperature=temperature,seconds=seconds,attempts=attempts,review_duration=seconds>limit)
            sf.write(wav,audio,sr,subtype='PCM_16');write_json(meta,details)
            if trial_seed != seed:
                repaired_identity=dict(identity,seed=trial_seed)
                repaired_key=digest(repaired_identity)
                sf.write(cache/(repaired_key+'.wav'),audio,sr,subtype='PCM_16')
                write_json(cache/(repaired_key+'.json'),details)
        sf.write(parts/f'{i:03}.wav',audio,sr,subtype='PCM_16')
        frames.extend([audio,np.zeros(round(s.get('pause_after',.8)*sr),dtype=np.float32)])
        times.append(dict(segment=i,role=s.get('role'),speaker=s['speaker'],source_item=s.get('source_item'),seconds=len(audio)/sr,cache_key=key,reused=reused,**{k:v for k,v in details.items() if k!='seconds'}))
        # Persist effective generation parameters so the script can be reproduced without cache.
        data['segments'][i-1]['generation_seed']=details['seed']
        data['segments'][i-1]['generation_temperature']=details['temperature']
        if i%20==0 or i==len(segments):
            print(f'{output.stem} {i}/{len(segments)} elapsed={time.monotonic()-started:.1f}s',flush=True)
            write_json(work/'progress.json',dict(completed=i,total=len(segments),segments=times))
    tmp=output.with_name(output.stem+'.tmp.wav');sf.write(tmp,np.concatenate(frames),sr,subtype='PCM_16');tmp.replace(output)
    write_json(script,data)
    write_json(work/'manifest.json',dict(model=str(model_path),script=str(script),sample_rate=sr,elapsed_seconds=time.monotonic()-started,segments=times))
    print(f'DONE {output} seconds={sum(t["seconds"]+s.get("pause_after",.8) for s,t in zip(segments,times)):.2f}',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--audio-dir',type=Path,default=Path('audio'))
    a=p.parse_args()
    if not 1<=a.start<=a.end<=144:p.error('Expected 1 <= start <= end <= 144')
    scripts=[(a.audio_dir/'scripts'/f'{n:03}'/(part+'.json'),a.audio_dir/f'{n:03}-{suffix}.wav') for n in range(a.start,a.end+1) for part,suffix in [('lesson','1-lesson'),('practice','2-practice'),('grammar','3-gramar')]]
    for script,_ in scripts:
        if not script.is_file():raise FileNotFoundError(script)
        resolve_segments(json.loads(script.read_text()),script)
    cache=a.audio_dir/'work'/'speech-cache';cache.mkdir(parents=True,exist_ok=True)
    model=load_model(str(a.model.expanduser().resolve()))
    for script,output in scripts:render(model,script,a.model,cache,output)
if __name__=='__main__':main()
