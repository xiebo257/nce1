#!/usr/bin/env python3
"""Refresh the index from existing HTML and connect a generated range to its neighbours."""
import argparse
import html
import re
from pathlib import Path
from render_lessons import step

def replace_once(text, pattern, replacement):
    result, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count != 1: raise ValueError(f'Navigation region not found: {pattern}')
    return result

def text_content(fragment):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>', '', fragment)).split())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--from',dest='first',type=int,required=True)
    p.add_argument('--to',dest='last',type=int,required=True)
    args=p.parse_args();root=args.repo.resolve()
    if not 45 <= args.first <= args.last <= 144: p.error('Expected range 45–144')
    pages={int(p.stem.split('-')[1]):p for p in (root/'html').glob('lesson-[0-9][0-9][0-9].html')}
    if not set(range(args.first,args.last+1)) <= set(pages): raise ValueError('Render the range first')
    changes=[]
    for n in range(max(1,args.first-1),min(144,args.last+1)+1):
        if n not in pages:continue
        path=pages[n];s=path.read_text()
        # Only touch the boundary control of older neighbours.
        for direction in ['previous','next']:
            if n==args.first-1 and direction=='previous':continue
            if n==args.last+1 and direction=='next':continue
            s=replace_once(s,rf'<div class="page-step {direction}">.*?</div>',step(root,n,direction,set(pages)))
        changes.append((path,s))
    cards=[];nav=[]
    for n,path in sorted(pages.items()):
        s=path.read_text()
        title=html.escape(text_content(re.search(r'<h1\b[^>]*>(.*?)</h1>',s,re.S)[1]))
        zh=html.escape(text_content(re.search(r'<p class="hero-translation"[^>]*>(.*?)</p>',s,re.S)[1]))
        href=f'html/lesson-{n:03}.html'
        cards.append(f'<a class="lesson-card" href="{href}"><span class="card-number">Lesson {n:03}</span><span class="card-title">{title}</span><span class="card-translation" lang="zh-CN">{zh}</span><span class="card-arrow">→</span></a>')
        nav.append(f'<a href="{href}"><span>{n:02}</span><div>{title}<small lang="zh-CN">{zh}</small></div><span class="nav-dot"></span></a>')
    path=root/'index.html';s=path.read_text();count=len(pages)
    s=replace_once(s,r'<div class="lesson-grid">.*?</div>','<div class="lesson-grid">\n'+'\n'.join(cards)+'\n</div>')
    s=replace_once(s,r'<nav class="index-nav".*?</nav>','<nav class="index-nav" aria-label="All lessons">\n'+'\n'.join(nav)+'\n</nav>')
    s=replace_once(s,r'第一册：英语初阶，共 \d+ 课。',f'第一册：英语初阶，共 144 课，已完成 {count} 课。')
    s=replace_once(s,r'<span>\d+(?: / 144)? LESSONS(?: AVAILABLE)?</span>',f'<span>{count} / 144 LESSONS AVAILABLE</span>')
    s=replace_once(s,r'<div class="rail-progress">.*?</div>',f'<div class="rail-progress"><span class="small-label">COURSE</span><p><strong>{count}</strong><span> / <span>144</span> lessons</span></p><progress max="144" value="{count}" aria-label="Lessons available"></progress><small lang="zh-CN">第一册 · 已完成 {count} 课</small></div>')
    changes.append((path,s))
    for path,s in changes:
        if path.read_text()!=s:path.write_text(s)
    print(f'Navigation refreshed: {count}/144 available; boundary lessons {args.first}–{args.last}')

if __name__=='__main__':main()
