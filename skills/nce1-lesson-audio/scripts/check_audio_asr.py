from pathlib import Path
import argparse,json,hashlib,re,difflib,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import mlx_whisper
from num2words import num2words
p=argparse.ArgumentParser();p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);a=p.parse_args()
root=Path('audio/work/batch-025-144');cache=root/'asr-cache';cache.mkdir(exist_ok=True)
model=str(next((Path.home()/'.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots').iterdir()))
def norm(t):
 t=t.lower().replace('’',"'").replace('grey','gray').replace('colour','color').replace('hullo','hello')
 t=re.sub(r'\banne\b','ann',t)
 t=re.sub(r'\bstephen\b','steven',t)
 t=re.sub(r'\bmr\.?(?=\s)', 'mister',t)
 t=re.sub(r'\bmrs\.?(?=\s)', 'missus',t)
 t=re.sub(r'(?<=\d),(?=\d)','',t)
 t=t.replace('schoolbag','school bag').replace('alright','all right').replace('aeroplane','airplane')
 t=re.sub(r'\d+',lambda m:num2words(int(m[0])),t)
 t=re.sub(r"\b(can't|cannot)\b",'can not',t)
 t=re.sub(r"\bwon't\b",'will not',t)
 t=re.sub(r"n['’]t\b",' not',t)
 for short,long in [("i've",'i have'),("we've",'we have'),("they've",'they have'),("you've",'you have'),("i'm",'i am'),("you're",'you are'),("we're",'we are'),("they're",'they are'),("it's",'it is'),("that's",'that is'),("he's",'he is'),("she's",'she is'),("there's",'there is')]:t=re.sub(r'\b'+short+r'\b',long,t)
 t=t.replace('airhostess','air hostess').replace('icecream','ice cream').replace('ice-cream','ice cream')
 return re.findall(r"[a-z]+(?:'[a-z]+)?",t)
def diff(e,t):
 x,y=norm(e),norm(t)
 return [{'expected':' '.join(x[i:j]),'heard':' '.join(y[k:l])} for op,i,j,k,l in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if op!='equal']
def transcribe(x):
 x=np.concatenate([np.zeros(2400,dtype=np.float32),x,np.zeros(4800,dtype=np.float32)])
 key=hashlib.sha256(x.tobytes()).hexdigest();f=cache/(key+'.json')
 if f.exists():return json.loads(f.read_text())['text']
 result=mlx_whisper.transcribe(resample_poly(x,2,3).astype(np.float32),path_or_hf_repo=model,language='en',temperature=0,condition_on_previous_text=False)
 text=result['text'].strip();f.write_text(json.dumps({'text':text}));return text
started=time.monotonic()
for n in range(a.start,a.end+1):
 for part,suffix in [('lesson','1-lesson'),('practice','2-practice'),('grammar','3-gramar')]:
  stem=f'{n:03}-{suffix}';data=json.loads(Path(f'audio/scripts/{n:03}/{part}.json').read_text());work=Path('audio/work')/stem
  manifest=json.loads((work/'manifest.json').read_text());groups=[];group=[];seconds=0
  for i,s in enumerate(data['segments'],1):
   x,sr=sf.read(work/'segments'/f'{i:03}.wav',dtype='float32');assert sr==24000
   if group and seconds+len(x)/sr>23:groups.append(group);group=[];seconds=0
   group.append((i,s,x));seconds+=len(x)/sr+.3
  if group:groups.append(group)
  findings=[];group_results=[]
  for group in groups:
   x=np.concatenate([z for _,_,v in group for z in [v,np.zeros(7200,dtype=np.float32)]]);expected=' '.join(s['text'] for _,s,_ in group);heard=transcribe(x);delta=diff(expected,heard)
   group_results.append(dict(segments=[i for i,_,_ in group],expected=expected,heard=heard,differences=delta))
   if delta:
    for i,s,x in group:
     heard=transcribe(x);delta=diff(s['text'],heard)
     if delta:findings.append(dict(segment=i,role=s['role'],text=s['text'],heard=heard,differences=delta))
  result=dict(file=stem,segments=len(data['segments']),groups=group_results,findings=findings,duration_flags=[s for s in manifest['segments'] if s.get('review_duration')])
  (root/(stem+'-asr.json')).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
  print(stem,'segments',len(data['segments']),'flags',len(findings),'elapsed',round(time.monotonic()-started),flush=True)
