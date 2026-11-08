from pathlib import Path
from lxml import html
import json,re,sys
from lesson_content import CAST
BASE='Speak in natural conversational American English at a normal pace. Use gentle connected speech and light reductions of unstressed words, without rushing or exaggerated acting.'
NORMAL='Use a relaxed natural falling finish for statements.'
def clean(s):return re.sub(r'\s+',' ',s.replace('’',"'").replace('“','"').replace('”','"').replace('…','')).strip()
def no_parens(s):return re.sub(r'\([^)]*\)','',s)
def sentences(s):
 s=clean(s).replace('Mr.','Mr~').replace('Mrs.','Mrs~').replace('Ms.','Ms~')
 return [t.replace('~','.') for t in re.split(r'(?<=[.!?])\s+(?=[A-Z])',s) if t]
def roleid(label):return re.sub(r'[^a-z0-9]+','_',label.lower()).strip('_')
class Lesson:
 def __init__(self,n):
  self.n=n;self.root=html.parse(f'html/lesson-{n:03}.html');self.s=[];self.section='';self.source=None;self.vocab=[];self.missing=[]
  self.roles={k:{'speaker':v,'description':desc,'instructions':BASE} for k,v,desc in [('narrator','Ryan','Section instructions and vocabulary'),('prompt','Aiden','Exercise prompt'),('answer','Serena','Exercise model response'),('male_answer','Ryan','Male model response'),('female_prompt','Vivian','Female questioner'),('female_answer','Vivian','Second female model response')]}
 def role(self,label):
  id=roleid(label)
  if label not in CAST:raise ValueError(('unknown role',label))
  self.roles.setdefault(id,dict(speaker=CAST[label],description=label,instructions=BASE))
  return id
 def add(self,text,role='narrator',pause=.8,source=None,section=None,extra='',**meta):
  text=clean(text).replace('..','.').replace('. ,', ',').replace('−','minus').replace('+','plus').replace('→','then').replace('—',', ')
  if not text:return
  if not text.endswith(('.', '!', '?')):text+='.'
  assert not re.search(r'[_\[\]/\u4e00-\u9fff]|\b(?:Question|Answer|Statement):',text),(self.n,self.source,text)
  if role=='answer' and re.search(r"\bI(?:'m| am| am not|'m not)\b.*\b(?:policeman|postman|milkman|boy|man)\b",text):role='male_answer'
  chunks=sentences(text)
  # Keep one thought together; divide long turns at sentence boundaries.
  if len(text.split())>22 and len(chunks)>1:
   for i,c in enumerate(chunks):self.add(c,role,pause if i==len(chunks)-1 else .35,source,section,extra,**meta)
   return
  direction=NORMAL
  if text.endswith('?'):
   if ' or ' in text:direction='Ask a choice question, rising on the first choice and falling on the final choice.'
   elif re.match(r'^(What|Who|Whose|Where|When|Why|How)\b',text):direction='Ask a neutral information question with a gentle falling finish.'
   else:direction='Ask a genuine question with a gentle natural rise.'
  self.s.append(dict(role=role,text=text,instructions=direction+' '+extra,pause_after=pause,source_item=source or self.source or 'section-introduction',section=section or self.section,**meta))
 def turn(self,text,start='prompt',end='answer',pause=1.2):
  # Newlines and em dashes preserve turns; a question followed by its answer is split.
  parts=[p.strip() for p in re.split(r'\n+|\s+—\s+',text) if p.strip()]
  if len(parts)>1:
   for i,p in enumerate(parts):self.turn(p,start if i%2==0 else end,end if i%2==0 else start,pause)
   return
  if text.endswith('?') and all(c.endswith('?') for c in sentences(text)):
   self.add(text,start,pause=pause);return
  if '?' in text and text.split('?',1)[1].strip():
   q,a=text.split('?',1);self.add(q+'?',start,pause=1.4);self.turn(a.strip(),start,end,pause) if re.match(r"^(?:What|Who|Which|Is |Are |Do |Does |This one|These)",a.strip()) and '?' in a else self.turn(a.strip(),end,start,pause);return
  self.add(text,start,pause=pause)
 def dialogue(self,text):
  labels='|'.join(re.escape(k) for k in sorted(CAST,key=len,reverse=True))
  matches=list(re.finditer(r'('+labels+r'):\s*',text))
  if not matches:raise ValueError(('missing speaker',text))
  for i,m in enumerate(matches):
   t=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip(' —\n')
   self.add(t,self.role(m[1]),pause=.65)
 def intro(self,art):
  title=clean(' '.join(art.xpath('.//h3//text()')));ins=clean(' '.join(art.xpath('.//p[@class="instruction"]//text()')))
  low=(title+' '+ins).lower()
  if 'dialogue' in title.lower() and self.part=='practice':text='Listen to the completed conversation. Then practice the parts.'
  elif 'plural pronunciation' in low:text='Listen to the plural endings. Repeat the words in each sound group.'
  elif 'numbers' in low:
   text='Listen to each number. Write it in figures, then check the digits.' if 'figures' in low else 'Write each number in words. Listen and check.'
   if 'sums' in low:text='Work out each sum. Then check the number.'
  elif 'copy' in low:text='Listen and copy each complete sentence. Pause whenever you need more time.'
  elif 'about you' in low or 'about yourself' in low:text='These are sample answers. Use your own information when you practice.'
  elif self.n==7 and title.startswith('II.'):text='Listen to different people giving sample answers. Then practice with your own information.'
  elif 'situations' in low or 'situation' in low:text='Listen to each situation. What would you say?'
  elif 'translation' in low:text='Read each Chinese sentence on the page. Listen to the situation in English, then say the model expression.'
  elif 'apostrophes' in low:text='Write each sentence with the correct apostrophes. Listen to the completed sentences.'
  elif 'find possessive' in low:text='Listen to each sentence. Find the possessive noun, then check.'
  elif 'plural' in low and ('rewrite' in low or 'make these' in low):text='Change each sentence to the plural. Listen, try it yourself, then check.'
  elif 'plural' in low:text='Say the plural of each word. Listen, then check.'
  elif 'short forms' in low:text='Use the short forms. Listen to the full sentence, then check the contraction.'
  elif 'write the questions' in low or 'write questions for the answers' in low or 'write the correct questions' in low or 'write the questions for' in low:text='Listen to the statement. Make the matching question, then check.'
  elif 'picture' in low:text='Look at the pictures. Listen to the cues and practice the model sentences.'
  elif 'opposites' in low:text='Say the opposite of each word, then check.'
  elif 'fill' in low or 'complete these sentences' in low or 'complete the sentences' in low or 'complete the questions' in low or 'a or an?' in low:text='Complete the items on the page. Pause to try each one, then listen to the completed version.'
  elif 'ask and answer' in low or 'questions and answers' in low or 'conversations' in low or 'complete the dialogues' in low:text='Listen to the cues. Practice the conversation, then check.'
  elif 'correct the sentences' in low:text='Each sentence has a mistake. Correct it, then listen to the corrected sentence.'
  elif 'rewrite' in low or 'make sentences' in low or 'make statements' in low or 'imperative' in low:text='Listen to the words or sentence. Make the new sentence, then check.'
  else:text='Listen to each prompt. Pause to try it yourself, then check the model answer.'
  if self.n==7 and title.startswith('II.'):text='Listen to different people giving sample answers. Then practice with your own information.'
  if self.n==5 and title.startswith('A.'):text='Listen to the completed conversation. Alex is the example name, and Chinese is the example nationality. Use your own details when you practice.'
  if self.n==4 and title=='Picture questions':text='Practice short answers. Either yes or no is possible here. These are model responses.'
  self.add(text,pause=1.2,source='section-introduction');return title,ins
