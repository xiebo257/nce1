#!/usr/bin/env python3
"""Resume a local audio queue, check each small batch, and commit/push incrementally."""
import argparse,json,os,re,subprocess,sys,time
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parent
ROOT=Path('audio/work/batch-025-144')
TTS=Path.home()/'.local/share/nce1-qwen3-tts/bin/python'
MODEL=Path.home()/'.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit'
PARTS=[('lesson','1-lesson'),('practice','2-practice'),('grammar','3-gramar')]

def call(args,log):
 with (ROOT/log).open('a') as f:
  subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'HF_HUB_OFFLINE':'1'},check=True)
def benign(f):
 # Orthography only. Never discard missing negatives, changed pronouns, or inflections.
 text=f['text'].lower();heard=f['heard'].lower()
 if text.startswith('write ') and re.fullmatch(r'[\d ,.!]+',heard.removeprefix('write ').strip()):
  digits=dict(zip('zero one two three four five six seven eight nine'.split(),'0123456789'))
  expected=''.join(digits[w] for w in re.findall(r'[a-z]+',text[6:]) if w in digits)
  actual=''.join(re.findall(r'\d',heard))
  return bool(expected) and expected==actual
 def norm(s):
  s=s.lower().replace('’',"'").replace('schoolbag','school bag').replace('alright','all right').replace('okay','ok')
  s=s.replace('mrs.','missus').replace('mr.','mister').replace('miss is','missus')
  s=re.sub(r'(?<=\d),(?=\d)','',s)
  s=re.sub(r"\b(can't|cannot)\b",'can not',s);s=re.sub(r"\bwon't\b",'will not',s);s=re.sub(r"n't\b",' not',s)
  return re.sub(r'[^a-z0-9]','',s)
 if norm(text)==norm(heard):return True
 return False

def findings(start,end):
 result=[]
 for n in range(start,end+1):
  for part,suffix in PARTS:
   report=json.loads((ROOT/f'{n:03}-{suffix}-asr.json').read_text())
   for f in report['findings']:
    if not benign(f):result.append(dict(lesson=n,part=part,**f))
 return result

def score(f):return sum(max(len(d['expected'].split()),len(d['heard'].split())) for d in f['differences'])

def render(start,end,tag):call([TTS,SCRIPTS/'render_qwen3_batch.py','--start',start,'--end',end,'--model',MODEL],f'render-{tag}.log')
def check(start,end,tag):call([sys.executable,SCRIPTS/'check_audio_asr.py','--start',start,'--end',end],f'asr-{tag}.log')

def process(start,end,publish=True,next_range=None):
 tag=f'{start:03}-{end:03}';state=ROOT/f'queue-{tag}.json'
 if state.exists() and json.loads(state.read_text()).get('pushed'):
  print('SKIP pushed',tag,flush=True);return
 print('RENDER',tag,flush=True);render(start,end,tag)
 prefetch=None
 if next_range:
  next_start,next_end=next_range;next_tag=f'{next_start:03}-{next_end:03}'
  next_state=ROOT/f'queue-{next_tag}.json'
  if not next_state.exists() or not json.loads(next_state.read_text()).get('pushed'):
   log=(ROOT/f'render-{next_tag}.log').open('a')
   prefetch=subprocess.Popen([str(TTS),str(SCRIPTS/'render_qwen3_batch.py'),'--start',str(next_start),'--end',str(next_end),'--model',str(MODEL)],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'HF_HUB_OFFLINE':'1'})
   log.close();print('PREFETCH',next_tag,'pid',prefetch.pid,flush=True)
 print('CHECK',tag,flush=True);check(start,end,tag)
 initial=findings(start,end);best={};repairs=[]
 for f in initial:
  key=(f['lesson'],f['part'],f['segment']);p=Path(f'audio/scripts/{key[0]:03}/{key[1]}.json');s=json.loads(p.read_text())['segments'][key[2]-1]
  best[key]=(score(f),s['generation_seed'],s['generation_temperature'])
 for attempt in range(2):
  candidates=findings(start,end)
  if not candidates:break
  print('REPAIR',tag,attempt+1,len(candidates),flush=True)
  byfile={}
  for f in candidates:
   key=(f['lesson'],f['part'],f['segment']);path=Path(f'audio/scripts/{key[0]:03}/{key[1]}.json')
   d=byfile.setdefault(path,json.loads(path.read_text()));s=d['segments'][key[2]-1]
   prior=best.setdefault(key,(score(f),s['generation_seed'],s['generation_temperature']))
   if score(f)<prior[0]:best[key]=(score(f),s['generation_seed'],s['generation_temperature'])
   s['generation_seed']+=700001+attempt*900001;s['generation_temperature']=.45
   repairs.append(dict(lesson=key[0],part=key[1],segment=key[2],before=f['heard'],attempt=attempt+1))
  for p,d in byfile.items():p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
  render(start,end,tag);check(start,end,tag)
 # Keep the best checked rendition rather than blindly retaining the last attempt.
 remaining=findings(start,end);byfile={};restored=False
 for f in remaining:
  key=(f['lesson'],f['part'],f['segment']);prior=best.get(key)
  if prior and score(f)>=prior[0]:
   path=Path(f'audio/scripts/{key[0]:03}/{key[1]}.json');d=byfile.setdefault(path,json.loads(path.read_text()));s=d['segments'][key[2]-1]
   s['generation_seed'],s['generation_temperature']=prior[1:];restored=True
 for p,d in byfile.items():p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 if restored:render(start,end,tag);check(start,end,tag)
 remaining=findings(start,end)
 (ROOT/f'review-{tag}.json').write_text(json.dumps(dict(initial=initial,repairs=repairs,remaining=remaining),ensure_ascii=False,indent=2)+'\n')
 # A local review marker is required for residual differences after automatic repairs.
 if remaining and not (ROOT/f'accept-{tag}.json').exists():
  print('REVIEW REQUIRED',tag,len(remaining),flush=True)
  state.write_text(json.dumps(dict(start=start,end=end,review_required=len(remaining),pushed=False)))
  return False
 print('PUBLISH',tag,flush=True)
 call([sys.executable,SCRIPTS/'publish_audio_batch.py','--start',start,'--end',end,*(['--publish'] if publish else [])],f'publish-{tag}.log')
 state.write_text(json.dumps(dict(start=start,end=end,pushed=publish,remaining_asr_differences=len(remaining))))
 print('DONE',tag,flush=True);return True

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);p.add_argument('--batch-size',type=int,default=2);p.add_argument('--wait-pid',type=int);p.add_argument('--prefetch',action='store_true',help='Opt in only after measuring throughput on the current machine');a=p.parse_args();ROOT.mkdir(parents=True,exist_ok=True)
 if a.wait_pid:
  while True:
   try:os.kill(a.wait_pid,0)
   except ProcessLookupError:break
   time.sleep(5)
 for n in range(a.start,a.end+1,a.batch_size):
  next_start=n+a.batch_size
  process(n,min(n+a.batch_size-1,a.end),next_range=(next_start,min(next_start+a.batch_size-1,a.end)) if a.prefetch and next_start<=a.end else None)
if __name__=='__main__':main()
