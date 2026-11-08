#!/usr/bin/env python3
"""Compile HTML answer fields into speech scripts; report unsupported content, never omit it."""
import argparse,json,re
from num2words import num2words
from pathlib import Path
from lxml import html
import lesson_compiler_base as base
from lesson_content import VOCAB,USAGE,CAST
BASE=base.BASE
FEMALE={'caroline','mrs. smith','mrs. jackson','mrs. jones','amy','jean','sally','jane','penny','pamela','susan','carol','charlotte','mrs. bird','mrs. williams','jill','mrs. johnson','ann','pauline','kate','lady','nurse','jenny','grandmother','sandra','helen','liz','linda','catherine','lucy','miss marsh','mrs. mills','mrs. frith','julie','christine'}
CAST.update({'A':'Aiden','B':'Serena','C':'Ryan','1st Tramp':'Ryan','2nd Tramp':'Aiden','Actress':'Serena','Reporter':'Aiden','Mrs. Smith':'Serena','Mrs. Jackson':'Vivian','Mrs. Jones':'Serena','Amy':'Vivian','Mr. Smith':'Ryan','A friend':'Aiden'})
OVERRIDES={}
PASSAGES={}
RECOVERED={}
CAST.update({'Jill':'Vivian','Mrs. Johnson':'Vivian','Tom':'Aiden','Grandmother':'Sohee','Charlotte':'Vivian','Carol':'Vivian','Attendant':'Dylan'})
DATA=Path(__file__).resolve().parent.parent/'assets'

def normalize(s):
 return base.clean(s).replace('–','—')

def answer(s):
 s=s.replace('’',"'").replace('×','').replace('∅','')
 s=re.sub(r'\((?:Suggested|Personal|Source|Accept|Other|Answers?|参考|答案)[^)]*\)','',s,flags=re.I)
 s=re.sub(r'\([^)]*\)','',s)
 s=re.sub(r'^[a-z]\s*[—–]\s*','',s)
 s=re.sub(r'^[a-z][.)]\s+(?=[A-Z])','',s)
 return s.strip()

def fill(q,k):
 q=base.no_parens(q)
 values=[x.strip() for x in re.split(r'[;\n]| / ',k)] if re.search(r'[;\n]| / ',k) else [x.strip() for x in k.split(',')]
 slots=re.findall(r'[A-Za-z]*_{2,}[A-Za-z]*',q)
 if len(values)==1 and len(slots)>1 and re.search(r'_{2,}\s+_{2,}',q) and len(k.split())==len(slots):values=k.split()
 if len(values)==1 and '  ' in k:values=re.split(r'\s{2,}',k)

 if len(slots)!=len(values):raise ValueError(('fill mismatch',q,k))
 it=iter(values)
 return re.sub(r'[A-Za-z]*_{2,}[A-Za-z]*',lambda m:next(it),q)

class Lesson(base.Lesson):
 def __init__(self,n):
  super().__init__(n);self.roles['answer']['speaker']='Ryan';self.roles['prompt']['speaker']='Aiden'
  self.labels={normalize(e.text_content()) for e in self.root.xpath('//p[@class="small-label"]') if e.getparent().xpath('./p[@class="spoken"]')}
  for e in self.root.xpath('//*[@data-prompt]'):
   self.labels.update(re.findall(r'(?:^|\n| — )([A-Za-z][A-Za-z .\'-]{0,25}):',e.get('data-prompt')))
  for e in self.root.xpath('//section[@id="lesson"]//div[@class="reading-prompt"]/p[not(@lang)]'):
   self.labels.update(re.findall(r'(?:^|\n)([A-Z][A-Z .\'-]+):',e.text_content()))
  self.labels.update(s['character'] for s in PASSAGES.get(str(n),[]) if 'character' in s)
  explicit={normalize(e.text_content()) for e in self.root.xpath('//p[@class="small-label"]') if e.getparent().xpath('./p[@class="spoken"]')}
  self.labels={label for label in self.labels if label and (label in explicit or label in CAST or label.isupper() or all(w[0].isupper() or w in ['the','and','of'] for w in label.split()))};self.skip=set()
  saved=Path(f'audio/scripts/{n:03}/roles.json')
  saved_roles=json.loads(saved.read_text()) if saved.exists() else {}
  used=set()
  for label in sorted(self.labels):
   old=saved_roles.get(base.roleid(label),{}).get('speaker') or next((v for k,v in CAST.items() if k.lower()==label.lower()),None)
   pool=['Serena','Vivian','Sohee','Ono_Anna'] if label.lower() in FEMALE or label.lower().startswith(('mrs.','miss ')) else ['Ryan','Aiden','Uncle_Fu','Dylan','Eric']
   speaker=old or next((x for x in pool if x not in used),pool[0])
   if n==141 and label.lower()=='lady':speaker='Ono_Anna'
   if n==113:speaker={'conductor':'Ryan','man':'Aiden','1st passenger':'Uncle_Fu','2nd passenger':'Dylan','3rd passenger':'Serena','4th passenger':'Vivian','1st tramp':'Eric','2nd tramp':'Uncle_Fu','two tramps':'Eric'}.get(label.lower(),speaker)
   used.add(speaker)
   CAST[label]=speaker
 def add(self,text,role='narrator',pause=.8,source=None,section=None,extra='',**meta):
  text=re.sub(r'^(?:\d+[.]?[a-z][.]?|[a-z][.])\s+(?=[A-Z])','',text)
  if self.n==119:text=re.sub(r'^[a-j] (?=(?:After|Before)\b)','',text)
  text=text.replace('×','times').replace('÷','divided by').replace('=','equals')
  # Leading-zero identifiers are digit sequences, never cardinal numbers.
  text=re.sub(r'\b0\d{3,}\b',lambda m:', '.join(num2words(int(d)) for d in m[0]),text)
  clock=re.fullmatch(r'(\d{1,2}):(\d{2})\.?',text.strip())
  if clock:
   hour,minute=map(int,clock.groups());suffix=' p.m.' if hour>=12 else ''
   text=num2words(hour%12 or 12)+(' '+num2words(minute) if minute>=10 else ' oh '+num2words(minute) if minute else " o'clock")+suffix+'.'
  if 'character' in meta:role=self.role(meta.pop('character'))
  text=re.sub(r'\.{2,}|…','',text).strip()
  if text.lower().strip('.')=='putting':text='Putting my keys in my bag. The verb form is putting.';meta['supplemental']=True
  labels='|'.join(re.escape(k) for k in sorted(set(CAST)|self.labels,key=len,reverse=True))
  if re.match(r'^(?:'+labels+r'):\s*',text,re.I):
   self.dialogue(text);return
  super().add(text,role,pause,source,section,extra,**meta)
 def role(self,label):
  if not label or label.upper()=='NARRATOR' or re.fullmatch(r'\d+(?:st|nd|rd|th)',label):return 'narrator'
  if label not in CAST:CAST[label]=next((v for k,v in CAST.items() if k.lower()==label.lower()),'Serena' if label.lower() in FEMALE else 'Aiden')
  return super().role(label)
 def is_dialogue(self,text):
  labels='|'.join(re.escape(k) for k in sorted(set(CAST)|self.labels,key=len,reverse=True))
  return bool(re.match(r'^(?:'+labels+r'):',text,re.I))
 def dialogue(self,text):
  labels='|'.join(re.escape(k) for k in sorted(set(CAST)|self.labels,key=len,reverse=True))
  matches=list(re.finditer(r'(?<!\w)('+labels+r'):\s*',text,flags=re.I))
  if not matches:raise ValueError(('missing speaker',text))
  for i,m in enumerate(matches):
   t=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip(' —–\n')
   label=next((k for k in CAST if k.lower()==m[1].lower()),m[1]);self.add(t,self.role(label),pause=.65)
 def turn(self,text,start='prompt',end='answer',pause=1.2):
  text=re.sub(r'(?:QUESTION|NEGATIVE|POSITIVE|AFFIRMATIVE):\s*','',text,flags=re.I)
  text=re.sub(r'(?:^|\n)(at|on|in):',r'\1.',text,flags=re.I)
  if self.is_dialogue(text):return self.dialogue(text)
  # A newline is often a sentence boundary within one answer, not a new actor.
  text=re.sub(r'\s+/\s+', ' — ',text).replace('\n',' ')
  text=re.sub(r'^(?:at|on|in):',lambda m:m[0][:-1]+'.',text,flags=re.I)
  return super().turn(text,start,end,pause)
 def exercise(self,item,title,ins):
  if item['id'] in self.skip:return
  self.source=item['id'];q=item['data-prompt'];k=answer(item['data-key']);low=(title+' '+ins).lower()
  rawk=k
  if '_' in q and '\n' in q and '/' in q.split('\n')[0] and '_' not in q.split('\n')[0]:q=q.split('\n',1)[1]
  if '_' in q and re.search(r'\bwill … say',k):k=k.replace('will … say','will, say')
  if self.n==113 and 'practice'==self.part:q=q.replace('...','_____')
  q=re.sub(r'^Picture \d+\s*:\s*|^\d+(?:st|nd|rd|th):\s*','',q)
  if 'dialogue' in low:q=re.sub(r'^A few minutes later\.\s*','',q)

  override=OVERRIDES.get(f'{self.n:03}/{self.source}')
  if override:
   for s in override:self.add(**s)
   return
  if 'match' in low and re.fullmatch(r'[a-z](?:[,; ]+[a-z])*',k):raise ValueError(('matching letters need source phrase resolution',item['id'],k))
  k=re.sub(r"\b([A-Za-z]+(?:'[A-Za-z]+)?)/[A-Za-z]+(?:'[A-Za-z]+)?",r'\1',k)
  if ' / ' in k and '_' not in q:
   choices=k.split(' / ')
   if all(re.search(r'[.!?]$',x.strip()) for x in choices):k=choices[0]
   elif re.search(r'[.!?]$',choices[-1].strip()) and not re.search(r'[.!?]',choices[0]):k=choices[-1]
   else:k=k.replace(' / ','. ')
  k=k.replace('/No', ' / No')
  if ' / ' in k and '_' not in q:k=k.split(' / ')[0]
  if '_' in q:
   k=re.sub(r'([A-Za-z]+) / ([A-Za-z]+)(?=,|$)',r'\1',k)
  else:k=k.replace('/',', ')
  k=re.sub(r'\.{3,}', '',k).strip()

  q=re.sub(r'^(?:\d+[.]?[a-z]|\d+|[a-z])[.)]\s+(?=[A-Z])','',q)
  q=q.replace('[your name]','Alex')
  q=re.sub(r'\[[^]]*\]','',q)
  if 'Complete the contrast' in q:
   q=''
  if re.search(r'[\u4e00-\u9fff]',k):raise ValueError(('unresolved key annotation',k))
  if not '_' in q:k=k.replace('/',', ')
  if 'translation' in low or re.search(r'[\u4e00-\u9fff]',q):
   self.add(k,'answer',pause=2);return
  if self.n==118 and item['id'].startswith('l118-gii'):
   completed=q.replace('___',k.rstrip('.'))
   self.add(completed,'answer',pause=1.5);return
  if '_' in q:
   if re.match(r"^[A-Z][A-Z ']+:",q) and len(re.findall(r'_{2,}',q))==1:
    self.add(q.split(':')[0].title()+'. '+k,'answer',pause=1.5);return
   if re.search(r'[.!?]$',k) and len(k.split())>=max(4,len(base.no_parens(q).split())-2):completed=k
   else:
    try:completed=fill(q,k)
    except ValueError:
     if re.search(r'[.!?]',k):completed=k
     else:
      # Merge progressive/same-prompt blanks, retaining every source ID in metadata.
      current=base.no_parens(q);node=self.root.xpath('//*[@id=$id]',id=item['id'])[0]
      siblings=node.xpath('ancestor::article[1]//*[@data-key]');pos=siblings.index(node);consumed=[]
      def bare(t):
       t=re.sub(r'^\d+\.\s*','',base.no_parens(t))
       t=re.sub(r'^[A-Za-z][A-Za-z .\'-]{0,25}:\s*','',t)
       return re.sub(r'\s+([,.;!?])',r'\1',base.clean(t)).replace('’',"'")
      original=bare(q)
      for following in siblings[pos:]:
       candidate=bare(following.get('data-prompt'));value=answer(following.get('data-key'))
       if consumed and candidate!=bare(current) and candidate!=original:
        # A later source field may already reveal a subsequent answer.
        pattern='^'+re.escape(bare(current)).replace('___',r'.+?')+'$'
        if re.fullmatch(pattern,candidate):current=base.no_parens(following.get('data-prompt'))
        elif bare(current).endswith(candidate):current=current[:len(current)-len(bare(current))]+candidate
        else:break
       if not re.search(r'_{2,}',current):break
       consumed.append(following.get('id'));current=re.sub(r'_{2,}',lambda m:value,current,count=1)
       if not re.search(r'_{2,}',current):break
      if re.search(r'_{2,}',current):raise ValueError(('incomplete source blanks',q,k))
      completed=current
      self.skip.update(consumed[1:])
      self.pending_sources=consumed
   begin=len(self.s)
   if self.is_dialogue(completed):self.dialogue(completed)
   else:self.turn(completed,'prompt' if '?' in completed else 'answer','answer',pause=1.3)
   for segment in self.s[begin:]:segment['source_items']=getattr(self,'pending_sources',[])
   self.pending_sources=[]
   return
  if 'numbers' in low:
   if 'figures' in low:
    self.add(q,'prompt',pause=1.5);self.add('Write '+', '.join('zero one two three four five six seven eight nine'.split()[int(d)] for d in k if d.isdigit())+'.','answer',written_answer=k);return
   if 'sum' in low:self.add(q.replace('=','equals what?'),'prompt',pause=1.6);self.add('That makes '+k+'.','answer');return
   self.add('The number is '+k+'.','answer',pause=1.5);return
  labels='|'.join(re.escape(k) for k in sorted(set(CAST)|self.labels,key=len,reverse=True))
  if re.match(r'^(?:'+labels+r'):',q,re.I):
   if not base.no_parens(q).split(':',1)[1].strip():self.turn(k,'answer','prompt');return
   if ':' in k:self.dialogue(k);return
   if '/' in q:self.turn(k,'prompt' if '?' in k else 'answer','answer');return
   if re.search(r':\s*(?:\.\.\.)?$',q):self.dialogue(re.sub(r'\.\.\.$','',q)+k);return
   if '...' in q:self.dialogue(q.replace('...',k));return
   self.dialogue(base.no_parens(q));return
  cue=normalize(base.no_parens(q)).replace('/' ,', ').replace('→',', then ').replace('…','').strip()
  cue=re.sub(r'\.{2,}', '',cue)
  if '/' in q and '?' in k:cue=''
  if cue and normalize(cue)!=normalize(k):self.add(cue,'prompt',pause=1.7)
  self.turn(k,'prompt' if '?' in k else 'answer','answer',pause=1.2)
 def recovered_vocabulary(self):
  record=RECOVERED.get(str(self.n),{})
  words=[w for w in record.get('words',[]) if w not in self.vocab]
  if not words:return
  self.add('More words from the textbook. Listen and repeat.',source='recovered-vocabulary-introduction',section='vocabulary')
  for word in words:
   self.vocab.append(word)
   self.add(word+'. '+VOCAB[word],source='vocabulary-'+word,section='vocabulary',pause=1.5,supplemental=True,vocabulary_word=word,recovered_from=record['source'])
 def article(self,art):
  cls=art.get('class','');title=normalize(' '.join(art.xpath('.//h3//text()')))
  if 'vocabulary-block' in cls:
   self.section='vocabulary';self.source=None;self.add('Now, the words and expressions. Listen and repeat.',pause=1.2)
   for dt in art.xpath('.//dl[@class="vocabulary"]//dt'):
    word=normalize(' '.join(dt.xpath('./text()')));self.vocab.append(word);self.source='vocabulary-'+word
    if word not in VOCAB:raise ValueError(('missing vocabulary example',word))
    spoken={'in':'The word in','Mr.':'Mister','Mrs.':'Missus','tooth (plural: teeth)':'Tooth. The plural is teeth'}.get(word,word)
    self.add(spoken+'. '+VOCAB[word],'narrator',pause=1.5,supplemental=True,vocabulary_word=word)
    for note in USAGE.get(word,[]):self.add(note,pause=1.1,supplemental=True,vocabulary_word=word)
   self.recovered_vocabulary()
   return
  if 'lesson-notes' in cls:
   self.section='notes'
   for i,e in enumerate(art.xpath('.//span[@class="small-label"]'),1):
    t=re.sub(r'^\d+\s*[·.]?\s*','',normalize(e.text_content()))
    if t and not re.search(r'[/\u4e00-\u9fff_]|\.{2,}|…',t):self.add(t,source=f'lesson-note-{i}',pause=1)
   return
  self.section=title;self.source=None;title,ins=self.intro(art)
  for e in art.xpath('.//*[@data-key] | .//p[@class="section-intro"]'):
   if e.get('data-key') is not None:self.exercise(dict(e.attrib),title,ins)
   elif ':' in e.text_content():self.source='printed-dialogue-'+str(len(self.s));self.dialogue(normalize(e.text_content()))
 def compile(self):
  folder=Path(f'audio/scripts/{self.n:03}');folder.mkdir(parents=True,exist_ok=True)
  for part in ['lesson','practice','grammar']:
   self.part=part;self.s=[];self.section=part;self.source=None
   sec=self.root.xpath(f'//section[@id="{part}"]')[0]
   self.add(f'Lesson {self.n}.'+('' if part=='lesson' else ' Practice.' if part=='practice' else ' Grammar practice.'))
   reading=sec.xpath('.//*[@data-key and (contains(@id,"reading") or @id="lesson-question")]')
   dialogue=sec.xpath('.//p[@class="spoken"]')
   if part=='lesson' and not dialogue and self.n%2==1:
    replacement=PASSAGES.get(str(self.n))
    if replacement:
     for segment in replacement:self.add(**segment)
    else:
     for i,e in enumerate(sec.xpath('.//div[@class="reading-prompt"]/p[not(@lang)]'),1):
      t=e.text_content().strip()
      if t.startswith(('Listen','Question:')) or not re.search(r'[A-Za-z]',t):continue
      t=answer(t)
      chunks=re.split(r'[\u4e00-\u9fff][^A-Za-z]*',t)
      t=' '.join(c for c in chunks if len(c.split())>3)
      if not t:continue
      if re.match(r'[A-Z][A-Z .]+:',t):self.source=f'lesson-passage-{i}';self.dialogue(t)
      else:
       for j,line in enumerate(base.sentences(t),1):self.add(line,source=f'lesson-passage-{i}-{j}',section='passage',pause=.6)
   if dialogue:
    if reading:self.add(re.split(r'[\u4e00-\u9fff]',reading[0].get('data-prompt'))[0].strip(),pause=1.5,source=reading[0].get('id'))
    for idx,e in enumerate(dialogue,1):
     label=normalize(' '.join(e.getparent().xpath('./p[@class="small-label"]/text()')))
     self.add(e.text_content(),self.role(label),pause=.6,source=f'lesson-dialogue-{idx}',section='dialogue')
    if reading:self.add(answer(reading[0].get('data-key')),pause=1.2,source=reading[0].get('id'),section='reading-answer')
   for art in sec.xpath('.//article'):
    if dialogue and reading and reading[0] in art.iterdescendants():continue
    self.article(art)
   if part=='lesson':self.recovered_vocabulary()
   expected={e.get('id') for e in sec.xpath('.//*[@data-key]')};covered={s['source_item'] for s in self.s}|{i for s in self.s for i in s.get('source_items',[])}
   if expected-covered:raise ValueError(('uncovered items',expected-covered))
   data=dict(seed=42,roles_file='roles.json',source=f'html/lesson-{self.n:03}.html',source_items=len(expected),notes='Completed HTML answer keys. Supplemental vocabulary examples use modern everyday contexts. Open answers are models, not personal facts.',segments=self.s)
   if part=='lesson':data['vocabulary_words']=self.vocab;data['recovered_vocabulary']=RECOVERED.get(str(self.n),{})
   path=folder/f'{part}.json'
   if path.exists():
    repairs={(s['source_item'],s['role'],s['text']):s for s in json.loads(path.read_text())['segments']}
    for s in self.s:
     old=repairs.get((s['source_item'],s['role'],s['text']),{})
     for key in ['generation_seed','generation_temperature']:
      if key in old:s[key]=old[key]
   path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  (folder/'roles.json').write_text(json.dumps(self.roles,ensure_ascii=False,indent=2)+'\n')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);a=p.parse_args()
 for name,target in [('vocabulary-examples.json',VOCAB),('vocabulary-usage.json',USAGE),('speech-overrides.json',OVERRIDES),('passage-overrides.json',PASSAGES),('recovered-vocabulary.json',RECOVERED)]:
  path=DATA/name
  if path.exists():target.update(json.loads(path.read_text()))
 failures=[]
 for n in range(a.start,a.end+1):
  try:Lesson(n).compile()
  except (ValueError,AssertionError,IndexError) as e:failures.append(dict(lesson=n,error=str(e)))
 report=Path('audio/work/batch-025-144/compile-errors.json');report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(compiled=a.end-a.start+1-len(failures),failures=failures),ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
