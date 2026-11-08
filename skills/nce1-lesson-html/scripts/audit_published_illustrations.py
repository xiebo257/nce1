#!/usr/bin/env python3
"""Verify published Lesson assets, provenance and optional excluded-section baseline."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

from illustration_inventory import inventory


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--from', dest='start', type=int, default=45)
    parser.add_argument('--to', dest='end', type=int, default=144)
    parser.add_argument('--baseline', help='Git revision for Practice/Grammar comparison')
    args = parser.parse_args()
    repo = args.repo.resolve()
    rows = inventory(repo, args.start, args.end)
    errors, origins = [], {}
    checked = 0
    for row in rows:
        number = row['lesson']
        if (row['published'] != row['slots'] or row['needs_slots'] or
                row['missing_files'] or row['unprepared']):
            errors.append(f'{number:03}: incomplete inventory')
        path = f'lessons/lesson-{number:03}.json'
        data = json.loads((repo / path).read_text())
        if args.baseline:
            old = json.loads(subprocess.check_output(
                ['git', 'show', f'{args.baseline}:{path}'], cwd=repo))
            for section in ('practice', 'grammar'):
                if data['sections'].get(section) != old['sections'].get(section):
                    errors.append(f'{number:03}: changed {section} section')
        slots = dict.fromkeys(b['image'] for b in data['sections']['lesson'] if b.get('image'))
        for key in slots:
            label = f'{number:03}/{key}'
            slot = data['images'][key]
            try:
                asset = repo / 'html' / slot['src']
                manifest = json.loads((repo / slot['generation']['manifest']).read_text())
                assert manifest['status'] == 'visually-reviewed', 'missing visual review'
                assert manifest.get('review_notes'), 'empty visual review'
                assert sha(asset) == manifest['published_sha256'], 'published hash mismatch'
                with Image.open(asset) as image:
                    assert image.size == (slot['width'], slot['height']), 'slot size mismatch'
                    expected = manifest.get('postprocess', {}).get('output_size')
                    if expected:
                        assert image.size == tuple(expected), 'manifest size mismatch'
                    image.verify()
                if manifest.get('source_reference'):
                    assert sha(repo / manifest['source_reference']) == manifest['source_reference_sha256'], 'source hash mismatch'
                atlas = manifest.get('atlas_generation')
                if atlas:
                    prefix = repo / f'illustrations/references/atlas/{number:03}'
                    assert sha(Path(f'{prefix}-source.png')) == atlas['input_sha256'], 'atlas source mismatch'
                    assert sha(Path(f'{prefix}-colored.png')) == atlas['output_sha256'], 'atlas output mismatch'
                method = manifest.get('postprocess', {}).get('method', slot.get('origin'))
                origins[method] = origins.get(method, 0) + 1
                checked += 1
            except (KeyError, OSError, ValueError, AssertionError) as exc:
                errors.append(f'{label}: {exc}')
    print(json.dumps(dict(lessons=len(rows), assets_checked=checked,
                         methods=origins, baseline=args.baseline, errors=errors), indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
