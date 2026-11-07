#!/usr/bin/env python3
"""Validate a small completed range, update its index, then commit and push explicit paths."""
import argparse,json,re,subprocess,fcntl
from pathlib import Path
import soundfile as sf
import numpy as np
from lxml import html
PARTS=[('lesson','1-lesson'),('practice','2-practice'),('grammar','3-gramar')]
def validate(n):
 folder=Path(f'audio/scripts/{n:03}');tree=html.parse(f'html/lesson-{n:03}.html');roles=json.loads((folder/'roles.json').read_text());stats=[]
 for part,suffix in PARTS:
  path=Path(f'audio/{n:03}-{suffix}.wav');data=json.loads((folder/f'{part}.json').read_text());manifest=json.loads((Path('audio/work')/path.stem/'manifest.json').read_text())
  x,sr=sf.read(path,dtype='float32');info=sf.info(path)
  assert sr==24000 and x.ndim==1 and len(x) and np.isfinite(x).all() and np.max(np.abs(x))>0,path
  assert info.subtype=='PCM_16' and path.stat().st_size<100*1024**2,path
  assert len(data['segments'])==len(manifest['segments']),path
  expected={e.get('id') for e in tree.xpath('//section[@id=$part]//*[@data-key]',part=part)}
  covered={s['source_item'] for s in data['segments']}|{i for s in data['segments'] for i in s.get('source_items',[])}
  assert not expected-covered,(path,expected-covered)
  frames=0
  for i,(s,m) in enumerate(zip(data['segments'],manifest['segments']),1):
   assert s['role'] in roles and s['generation_seed']==m['seed'],(path,i)
   assert not re.search(r'[_\[\]/\u4e00-\u9fff]|\b(?:Question|Answer|Statement):',s['text']),s
   frames+=sf.info(Path('audio/work')/path.stem/'segments'/f'{i:03}.wav').frames+round(s.get('pause_after',.8)*sr)
  assert frames==len(x),(path,frames,len(x))
  stats.append(dict(file=str(path),seconds=info.duration,segments=len(data['segments']),source_items=len(expected),bytes=path.stat().st_size))
 words=json.loads((folder/'lesson.json').read_text()).get('vocabulary_words',[])
 sourcewords=[' '.join(e.xpath('./text()')).strip() for e in tree.xpath('//section[@id="lesson"]//dl[@class="vocabulary"]//dt')]
 recovered=json.loads((folder/'lesson.json').read_text()).get('recovered_vocabulary',{}).get('words',[])
 assert words==sourcewords+[w for w in recovered if w not in sourcewords],(n,'vocabulary order mismatch')
 text=f'# 第 {n} 课录音\n\n依据 [lesson-{n:03}.html](../../../html/lesson-{n:03}.html) 中的课文、提示及答案字段生成，包含示例和完整答案。词汇按 HTML 顺序并入 lesson；日常例句和现代用法说明属于补充内容。个人信息题使用示范答案。\n\n'
 text+='| 文件 | 时长（秒） | 片段 | 答题条目 |\n| --- | ---: | ---: | ---: |\n'+'\n'.join(f'| [{x["file"].split("/")[-1]}](../../{x["file"].split("/")[-1]}) | {x["seconds"]:.1f} | {x["segments"]} | {x["source_items"]} |' for x in stats)+'\n\n'
 text+='词汇：'+(', '.join(words) if words else '本课没有独立的生词表。')+'\n\n'
 text+='角色见 [roles.json](roles.json)。音频使用本地 Qwen3-TTS；已检查脚本覆盖、WAV 解码、片段与文件一致性。语音识别用于辅助内容检查，不证明口音、连读和语调自然；实际听感请试听。\n'
 (folder/'README.md').write_text(text)
 return stats

def index(start,end):
 rows=[]
 tracked=set(subprocess.check_output(['git','ls-files','--','audio'],text=True).splitlines())
 for n in range(1,145):
  files=[Path(f'audio/{n:03}-{s}.wav') for _,s in PARTS]
  if not all(p.exists() for p in files):continue
  if not start<=n<=end and not all(str(p) in tracked for p in files):continue
  title=' '.join(html.parse(f'html/lesson-{n:03}.html').xpath('//h1/text()')).strip()
  cells=[]
  for p in files:
   sec=round(sf.info(p).duration);cells.append(f'[{sec//60}:{sec%60:02}]({p.name})')
  rows.append(f'| {n:03} | {title} | '+ ' | '.join(cells)+f' | [脚本](scripts/{n:03}/README.md) |')
 Path('audio/README.md').write_text('# New Concept English 1 · 美式英语录音\n\n词汇合并在 lesson 中，顺序跟随 HTML。practice 含完整练习答案；gramar 含提示与答案，保留原文件命名。使用已选定的本地 Qwen3-TTS 多角色声音，正常语速。\n\n| 课 | 标题 | Lesson（含词汇） | Practice | Grammar | 内容依据 |\n| --- | --- | --- | --- | --- | --- |\n'+'\n'.join(rows)+'\n\n[多角色试听](examples/voices.md) · [生成 skill](../skills/nce1-lesson-audio/SKILL.md)\n\n中间片段、缓存与检查报告位于忽略提交的 `work/`。语音识别检查文字内容，无法验证实际口音与语调自然程度。\n')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);p.add_argument('--publish',action='store_true');a=p.parse_args()
 assert 1<=a.start<=a.end<=144
 Path('audio/work').mkdir(exist_ok=True)
 lock=open('audio/work/publish.lock','w');fcntl.flock(lock,fcntl.LOCK_EX)
 stats=[];paths=['audio/README.md']
 for n in range(a.start,a.end+1):
  stats.extend(validate(n));paths.append(f'audio/scripts/{n:03}');paths.extend(f'audio/{n:03}-{s}.wav' for _,s in PARTS)
 index(a.start,a.end);root=Path('audio/work/batch-025-144');root.mkdir(parents=True,exist_ok=True);(root/f'integrity-{a.start:03}-{a.end:03}.json').write_text(json.dumps(stats,indent=2)+'\n')
 print('PASS',len(stats),'files',round(sum(x['seconds'] for x in stats)/60,1),'minutes',flush=True)
 if a.publish:
  subprocess.run(['git','add','--',*paths],check=True)
  subprocess.run(['git','diff','--cached','--stat','--',*paths],check=True)
  changed=subprocess.run(['git','diff','--quiet','HEAD','--',*paths]).returncode
  if changed:
   subprocess.run(['git','commit','--only','-m',f'feat(audio): add lessons {a.start:03} through {a.end:03}','--',*paths],check=True)
  subprocess.run(['git','push','origin','main'],check=True)
if __name__=='__main__':main()
