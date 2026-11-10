#!/usr/bin/env python3
"""Verify published redraw assets and unchanged lesson text against the audit baseline."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image
from redraw_even_illustrations import REPORT, digest, fingerprint, read, slots, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--complete', action='store_true', help='Fail if any planned picture is unpublished')
    args = parser.parse_args()
    plan = read(REPORT / 'plan.json')
    results = []; errors = []; pending = []
    for number, lesson in plan['lessons'].items():
        number = int(number)
        path = Path(f'lessons/lesson-{number:03}.json')
        data = read(path)
        baseline = json.loads(subprocess.check_output(['git', 'show', f'{plan["baseline"]}:{path}']))
        if {k: v for k, v in data.items() if k != 'images'} != {k: v for k, v in baseline.items() if k != 'images'}:
            errors.append(f'{number}: non-image content changed')
        if fingerprint(data['sections']) != lesson['sections_sha256']:
            errors.append(f'{number}: sections changed')
        active = set(slots(data))
        for key, im in data['images'].items():
            if key not in active and im != baseline['images'][key]:
                errors.append(f'{number}: image outside Lesson changed: {key}')
        report_path = REPORT / f'published/{number:03}.json'
        published = {im['slot']: im for im in read(report_path)['images']} if report_path.exists() else {}
        for item in lesson['items']:
            slot = item['slot']
            if digest(item['source_photo']) != item['source_photo_sha256']:
                errors.append(f'{number}: original photograph changed')
            if slot not in published:
                pending.append({'lesson': number, 'slot': slot, 'mode': item['mode']})
                continue
            im = data['images'][slot]; asset = Path('html') / im['src']; record = published[slot]
            if digest(asset) != record['sha256']:
                errors.append(f'{number}: asset hash mismatch: {slot}')
            with Image.open(asset) as image:
                if image.size != (im['width'], im['height']):
                    errors.append(f'{number}: dimensions mismatch: {slot}')
                if image.width < 2 * im.get('display_width', 256):
                    errors.append(f'{number}: inadequate native resolution: {slot}')
                image.verify()
            results.append({'lesson': number, **record})
    # The task excludes odd lessons, source photos and audio.
    changed = subprocess.check_output(['git', 'diff', '--name-only', plan['baseline'], '--', 'lessons', 'html', 'img']).decode().splitlines()
    for path in changed:
        if path.startswith('img/'):
            errors.append('Source photograph changed: ' + path)
        name = Path(path).stem
        if Path(path).parent.name in ('lessons', 'html') and name.startswith('lesson-'):
            try:
                number = int(name.split('-')[1])
            except ValueError:
                continue
            if number % 2 or not 52 <= number <= 144:
                errors.append('Out-of-scope lesson changed: ' + path)
    report = {'baseline': plan['baseline'], 'planned_lessons': len(plan['lessons']),
              'published_images': len(results), 'pending_images': len(pending),
              'errors': errors, 'assets': results, 'pending': pending}
    write(REPORT / 'verification.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('assets', 'pending')}, indent=2))
    if errors or (args.complete and pending):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
