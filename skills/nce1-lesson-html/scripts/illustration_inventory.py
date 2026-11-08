#!/usr/bin/env python3
"""Audit Lesson artwork by provenance, including both odd and even lessons."""
import argparse
import json
from pathlib import Path


def inventory(repo, start=45, end=144):
    rows = []
    for number in range(start, end + 1):
        data = json.loads((repo / f'lessons/lesson-{number:03}.json').read_text())
        slots = list(dict.fromkeys(b['image'] for b in data['sections']['lesson'] if b.get('image')))
        row = dict(lesson=number, slots=len(slots), published=0, old_crops=0,
                   pending=0, missing_files=[], unprepared=[])
        for key in slots:
            slot = data['images'][key]
            src = slot.get('src')
            exists = bool(src and (repo / 'html' / src).is_file())
            if slot.get('status') == 'ready' and not exists:
                row['missing_files'].append(key)
            if slot.get('origin') in {'local-model', 'local-diagram'} and slot.get('status') == 'ready' and exists:
                row['published'] += 1
            elif slot.get('status') == 'ready' and exists:
                row['old_crops'] += 1
            else:
                row['pending'] += 1
            if not slot.get('illustration_scene'):
                row['unprepared'].append(key)
        row['needs_slots'] = not slots
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--from', dest='start', type=int, default=45)
    parser.add_argument('--to', dest='end', type=int, default=144)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if not 45 <= args.start <= args.end <= 144:
        parser.error('Expected 45 <= from <= to <= 144')
    rows = inventory(args.repo.resolve(), args.start, args.end)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print('Lesson  Slots  Published  Old crops  Pending  Unprepared  Needs slots')
    for r in rows:
        print(f"{r['lesson']:03}     {r['slots']:5}  {r['published']:9}  {r['old_crops']:9}  "
              f"{r['pending']:7}  {len(r['unprepared']):10}  {str(r['needs_slots']):11}")
        if r['missing_files']:
            print('  MISSING:', ', '.join(r['missing_files']))


if __name__ == '__main__':
    main()
