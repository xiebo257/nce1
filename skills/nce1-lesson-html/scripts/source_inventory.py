#!/usr/bin/env python3
"""Locate existing scans and actual grammar PDF page ranges without OCR or image generation."""
import argparse
import json
import re
from pathlib import Path
from pypdf import PdfReader

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo',type=Path,default=Path.cwd())
p.add_argument('--from',dest='first',type=int,default=45)
p.add_argument('--to',dest='last',type=int,default=144)
a=p.parse_args()
if not 45<=a.first<=a.last<=144:p.error('Expected range 45–144')
root=a.repo.resolve();pdf=root/'pdf/新概念英语语法练习1_按课程索引.pdf';r=PdfReader(pdf)
entries=[]
def walk(items):
    for item in items:
        if isinstance(item,list):walk(item)
        else:entries.append((item.title,r.get_destination_page_number(item)+1))
walk(r.outline)
starts={int(m[1]):(title,page) for title,page in entries if (m:=re.match(r'Lesson\s+(\d+)\b',title))}
key_start=next(page for title,page in entries if title=='Answer Key')
result=[]
for n in range(a.first,a.last+1):
    title,start=starts[n];end=starts[n+1][1]-1 if n+1 in starts else key_start-1
    scans=sorted(root.glob(f'img/lesson-{n:03}-*.jpg'))
    missing=[name for name in [f'lesson-{n:03}-01-text.jpg',f'lesson-{n:03}-02-text.jpg',f'lesson-{n:03}-practice.jpg'] if not (root/'img'/name).exists()]
    keys=[]
    for path in sorted((root/'img').glob('key-*.jpg')):
        nums=[int(x) for x in re.findall(r'\d+',path.stem)]
        if len(nums)==2 and nums[0]<=n<=nums[1]:keys.append(str(path.relative_to(root)))
    result.append(dict(number=n,title=title,scans=[str(s.relative_to(root)) for s in scans],missing=missing,workbook_key_candidates=keys,grammar_pdf=str(pdf.relative_to(root)),grammar_pages=list(range(start,end+1)),grammar_answer_search_start=key_start,html_exists=(root/f'html/lesson-{n:03}.html').exists(),data_exists=(root/f'lessons/lesson-{n:03}.json').exists()))
print(json.dumps(result,ensure_ascii=False,indent=2))
