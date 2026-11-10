#!/usr/bin/env python3
"""Redraw small Lesson pictures locally, with resumable candidates and manual review.

Each model cell has 512x320 native pixels. The old artwork is a composition
reference, never an ink overlay. Publishing only changes referenced image slots.
Run from the repository root. Model weights and temporary candidates stay local.
"""
import argparse
import copy
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageOps, ImageDraw, ImageFont

REPORT = Path('reports/even-illustration-redraw')
WORK = Path('illustrations/work/redraw-even')
MODEL = 'mlx-community/FLUX.2-Klein-4B-4bit'
CELL = (512, 320)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def slots(data):
    return list(dict.fromkeys(b['image'] for b in data['sections']['lesson'] if b.get('image')))


def plan():
    path = REPORT / 'plan.json'
    if path.exists():
        raise SystemExit('Plan already exists; preserve its immutable input references.')
    result = {'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'cell': list(CELL), 'lessons': {}}
    for number in range(52, 145, 2):
        data = read(f'lessons/lesson-{number:03}.json')
        items = []
        for slot in slots(data):
            im = data['images'][slot]
            source = 'html/' + im['src']
            blocks = [b for b in data['sections']['lesson'] if b.get('image') == slot]
            exact = im.get('illustration_exact_diagram') or im.get('origin') == 'exact-clock-diagram'
            # Clock-only rows must be transcribed and drawn exactly, never inferred by diffusion.
            if number == 78 or (number == 96 and len(items) < 12):
                exact = True
            items.append({'slot': slot, 'reference': source, 'reference_sha256': digest(source),
                          'source_photo': f'img/lesson-{number:03}-01-text.jpg',
                          'source_photo_sha256': digest(f'img/lesson-{number:03}-01-text.jpg'),
                          'previous': im, 'cue': im['description'],
                          'text': ' '.join(b.get('text', '') for b in blocks),
                          'mode': 'exact-clock' if exact else 'model-redraw'})
        result['lessons'][str(number)] = {
            'sections_sha256': fingerprint(data['sections']),
            'palette': data.get('illustration_palette', ''), 'items': items}
    write(path, result)
    print('PLANNED', len(result['lessons']), 'lessons',
          sum(len(x['items']) for x in result['lessons'].values()), 'pictures')


def groups(lesson):
    items = [x for x in lesson['items'] if x['mode'] == 'model-redraw']
    # Keep reported-speech triplets together when recorded as nine/twelve portraits.
    count = lesson.get('group_size', 1)
    return [items[i:i + count] for i in range(0, len(items), count)]


def specification(number, lesson, index, items):
    cols = min(2, len(items)); rows = math.ceil(len(items) / cols)
    positions = ['top left', 'top right', 'bottom left', 'bottom right']
    if rows == 1:
        positions = ['left', 'right'] if cols == 2 else ['only picture']
    instructions = ' '.join(f'{positions[i]}: {item.get("redraw_cue", item["cue"])}.' for i, item in enumerate(items))
    palette = lesson.get('palette', '')
    if palette.startswith('Source black ink'):
        palette = 'Recurring men wear blue, recurring women wear teal green. Keep each hairstyle, face and clothing identical across pictures.'
    prompt = (
        f'Redraw the {len(items)} reference pictures as NEW crisp full-color educational cartoon illustrations. '
        f'EXACT layout: {cols} columns and {rows} rows, each cell is a separate picture. '
        'Smooth precise clean outlines, clear expressive faces, solid warm colors, subtle cel shading, white backgrounds. '
        'Completely redraw fuzzy ink into sharp confident lines; remove scan noise, hatching and paper texture. '
        'Preserve the exact people count, identities, actions, objects, quantities and relative positions in each reference cell. '
        'Keep repeated characters identical in face, hairstyle and clothing color. '
        + palette + ' ' + instructions + ' '
        'Keep complete subjects inside their own cell with white margins. No panel borders. '
        'Retain meaningful object labels, numbers, clock hands and pictorial thought bubbles from the reference, '
        'but add no captions, dialogue, new objects, or new lettering. Do not combine cells. '
        'Do not copy the blur or coarse scan lines. '
        + lesson.get('extra_instruction', '')
    )
    if len(items) == 1:
        item = items[0]
        prompt = (
            'Redraw this reference as ONE single clean full-color cartoon illustration. '
            + item.get('redraw_cue', item['cue']) + '. '
            'Match the reference composition, people count, faces, hairstyles, poses and objects. '
            'Replace fuzzy rough scan ink with smooth sharp outlines, clear faces, solid colors and subtle shading. '
            'Keep the same clothing colors. White background, complete subjects, small white margin. '
            'No grid, no multiple copies, no captions. '
            + item.get('extra_instruction', '')
        )
        if item.get('edit_instruction'):
            prompt = item['edit_instruction']
    return {'model': MODEL, 'prompt': prompt, 'seed': number * 10000 + 1110 + index,
            'steps': 4, 'guidance': 1.0, 'width': cols * CELL[0], 'height': rows * CELL[1],
            'cell': list(CELL), 'columns': cols,
            'inputs': [{'slot': x['slot'], 'path': x['reference'], 'sha256': x['reference_sha256']} for x in items]}


def generate(numbers, selected_groups):
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import mlx.core as mx
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2KleinEdit
    model = None
    mx.set_cache_limit(256 * 1024**2)
    pending = list(numbers)
    while pending:
        number = pending.pop(0)
        lesson = read(REPORT / 'plan.json')['lessons'][str(number)]
        for index, items in enumerate(groups(lesson), 1):
            if selected_groups and index not in selected_groups:
                continue
            directory = WORK / f'{number:03}' / f'group-{index:02}'
            directory.mkdir(parents=True, exist_ok=True)
            spec = specification(number, lesson, index, items)
            key = fingerprint(spec)
            record_path = directory / 'generation.json'
            output = directory / 'redrawn.png'
            if record_path.exists() and output.exists():
                old = read(record_path)
                if old.get('fingerprint') == key and old.get('sha256') == digest(output):
                    print('CACHED', number, index, flush=True)
                    continue
            reference = Image.new('RGB', (spec['width'], spec['height']), 'white')
            for i, item in enumerate(items):
                if digest(item['reference']) != item['reference_sha256']:
                    raise ValueError('Input changed: ' + item['reference'])
                with Image.open(item['reference']) as source:
                    tile = ImageOps.contain(source.convert('RGB'), (CELL[0] - 24, CELL[1] - 24))
                reference.paste(tile, (i % spec['columns'] * CELL[0] + (CELL[0] - tile.width) // 2,
                                      i // spec['columns'] * CELL[1] + (CELL[1] - tile.height) // 2))
            reference_path = directory / 'reference.png'
            reference.save(reference_path)
            if model is None:
                model = Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(),
                                      model_path=str(Path.home() / '.cache/nce1-models/FLUX.2-Klein-4B-4bit'), quantize=4)
            print('START', number, index, len(items), flush=True)
            start = time.monotonic()
            result = model.generate_image(seed=spec['seed'], prompt=spec['prompt'], num_inference_steps=4,
                                          width=spec['width'], height=spec['height'], guidance=1.0,
                                          image_paths=[reference_path])
            result.save(str(output), overwrite=True)
            with Image.open(output) as im:
                assert im.size == (spec['width'], spec['height'])
                for i, item in enumerate(items):
                    x = i % spec['columns'] * CELL[0]; y = i // spec['columns'] * CELL[1]
                    im.crop((x, y, x + CELL[0], y + CELL[1])).save(directory / f'{item["slot"]}.png')
            write(record_path, dict(spec, fingerprint=key, sha256=digest(output),
                                    reference_sha256=digest(reference_path), seconds=round(time.monotonic() - start, 2),
                                    status='candidate-needs-visual-review'))
            print('CANDIDATE', number, index, flush=True)
            del result
            mx.clear_cache(); gc.collect()
        priority_path = WORK / 'priority.json'
        if priority_path.exists():
            priorities = read(priority_path)
            write(priority_path, [])
            pending = list(dict.fromkeys(priorities + pending))


def review(number, notes):
    lesson = read(REPORT / 'plan.json')['lessons'][str(number)]
    records = {}
    for index, items in enumerate(groups(lesson), 1):
        directory = WORK / f'{number:03}' / f'group-{index:02}'
        record = read(directory / 'generation.json')
        for item in items:
            if item.get('required_overlays'):
                assert lesson.get('candidate_edits', {}).get(item['slot'], {}).get('operations'), (
                    f"Complete exact overlays before review: {number} {item['slot']} {item['required_overlays']}")
                assert (directory / 'candidate-edits.json').exists(), 'Apply required overlays before review'
        assert record['fingerprint'] == fingerprint(specification(number, lesson, index, items))
        assert record['sha256'] == digest(directory / 'redrawn.png')
        records[str(index)] = {'sheet_sha256': record['sha256'],
                               'tiles': {x['slot']: digest(directory / f'{x["slot"]}.png') for x in items}}
        if (directory / 'candidate-edits.json').exists():
            edits = read(directory / 'candidate-edits.json')
            assert len(items) == 1, 'Refinement records currently apply to individual pictures'
            assert edits['output_sha256'] == digest(directory / f'{items[0]["slot"]}.png'), 'Reapply stale refinements before review'
            assert edits['source_sha256'] == digest(edits['source']), 'Refinement source changed'
            records[str(index)]['edits_sha256'] = digest(directory / 'candidate-edits.json')
    others = {}
    for item in lesson['items']:
        if item['mode'] == 'exact-clock':
            candidate = WORK / f'{number:03}/diagrams/{item["slot"]}.png'
            others[item['slot']] = digest(candidate)
        elif item['mode'] == 'reuse':
            others[item['slot']] = digest(reuse_path(item))
    write(REPORT / f'reviews/{number:03}.json', {'lesson': number, 'notes': notes, 'groups': records,
                                               'other_assets': others})


def reuse_path(item):
    number = item['reuse_from']['lesson']; slot = item['reuse_from']['slot']
    metadata = read(f'lessons/lesson-{number:03}.json')['images'][slot]
    if metadata.get('origin') == 'local-model-redraw':
        return Path('html') / metadata['src']
    lesson = read(REPORT / 'plan.json')['lessons'][str(number)]
    for index, group in enumerate(groups(lesson), 1):
        if any(x['slot'] == slot for x in group):
            return WORK / f'{number:03}/group-{index:02}/{slot}.png'
    raise ValueError(f'Reuse source has not been redrawn: {number} {slot}')


def clock_diagram(clock_time, path):
    """Render a verified time for a standalone clock or an inset."""
    hour, minute = map(int, clock_time.split(':'))
    size = 1024; c = size / 2; radius = 440
    im = Image.new('RGB', (size, size), 'white'); draw = ImageDraw.Draw(im)
    draw.ellipse((c-radius, c-radius, c+radius, c+radius), fill='#fff9e7', outline='#27647a', width=24)
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 72)
    for tick in range(60):
        angle = tick * math.pi / 30 - math.pi / 2
        a = radius - 32; b = a - (32 if tick % 5 == 0 else 12)
        draw.line((c+math.cos(angle)*a, c+math.sin(angle)*a,
                   c+math.cos(angle)*b, c+math.sin(angle)*b), fill='#435c64', width=6)
    for value in range(1, 13):
        angle = value * math.pi / 6 - math.pi / 2; r = radius - 118
        draw.text((c+math.cos(angle)*r, c+math.sin(angle)*r), str(value), font=font, fill='#203d4b', anchor='mm')
    for angle, length, width in [((hour % 12 + minute/60)*math.pi/6, 205, 24),
                                 (minute*math.pi/30, 310, 16)]:
        angle -= math.pi/2
        draw.line((c, c, c+math.cos(angle)*length, c+math.sin(angle)*length), fill='#174d62', width=width)
    draw.ellipse((c-20, c-20, c+20, c+20), fill='#174d62')
    path.parent.mkdir(parents=True, exist_ok=True)
    im.resize((512, 512), Image.Resampling.LANCZOS).save(path)


def diagrams(numbers):
    """Rasterize verified standalone and inset clock readings."""
    queue = read(REPORT / 'plan.json')['lessons']
    for number in numbers:
        lesson = queue[str(number)]
        for item in lesson['items']:
            if item['mode'] != 'exact-clock':
                continue
            if not item.get('clock_time'):
                raise ValueError(f'Clock requires photo verification: {number} {item["slot"]}')
            clock_diagram(item['clock_time'], WORK / f'{number:03}/diagrams/{item["slot"]}.png')
        for clock_time in lesson.get('inset_clocks', []):
            clock_diagram(clock_time, WORK / f'{number:03}/diagrams/inset-{clock_time.replace(":", "-")}.png')
        print('DIAGRAMS', number)


def contact(numbers):
    queue = read(REPORT / 'plan.json')['lessons']
    for number in numbers:
        lesson = queue[str(number)]; pictures = []
        for index, group in enumerate(groups(lesson), 1):
            for item in group:
                path = WORK / f'{number:03}/group-{index:02}/{item["slot"]}.png'
                if path.exists():
                    pictures.append((item, path))
        for start in range(0, len(pictures), 12):
            batch = pictures[start:start+12]
            sheet = Image.new('RGB', (1536, 350 * math.ceil(len(batch)/3)), 'white')
            draw = ImageDraw.Draw(sheet)
            for index, (item, path) in enumerate(batch):
                x = index % 3 * 512; y = index // 3 * 350
                draw.text((x+4, y+4), item['slot'], fill='black')
                with Image.open(path) as im:
                    sheet.paste(ImageOps.contain(im, CELL), (x, y+25))
            path = WORK / f'{number:03}/contact-{start//12+1:02}.jpg'
            sheet.save(path, quality=95)
            print(path)


def replace_images_field(raw, images):
    # Preserve all unrelated JSON formatting, including compact answer rows.
    decoder = json.JSONDecoder()
    i = raw.index('{') + 1
    while True:
        while raw[i].isspace() or raw[i] == ',':
            i += 1
        if raw[i] == '}':
            raise ValueError('Missing images field')
        name, i = decoder.raw_decode(raw, i)
        while raw[i].isspace() or raw[i] == ':':
            i += 1
        start = i
        _, i = decoder.raw_decode(raw, i)
        if name == 'images':
            encoded = json.dumps(images, ensure_ascii=False, indent=2).replace('\n', '\n  ')
            return raw[:start] + encoded + raw[i:]


def publish(number):
    lesson = read(REPORT / 'plan.json')['lessons'][str(number)]
    approval = read(REPORT / f'reviews/{number:03}.json')
    path = Path(f'lessons/lesson-{number:03}.json')
    raw = path.read_text(); data = json.loads(raw)
    assert fingerprint(data['sections']) == lesson['sections_sha256'], 'Lesson text changed since planning'
    images = copy.deepcopy(data['images']); results = []
    for index, items in enumerate(groups(lesson), 1):
        directory = WORK / f'{number:03}' / f'group-{index:02}'
        record = read(directory / 'generation.json')
        assert record['fingerprint'] == fingerprint(specification(number, lesson, index, items))
        assert digest(directory / 'redrawn.png') == approval['groups'][str(index)]['sheet_sha256']
        archive = Path(f'illustrations/redraw-even/{number:03}/group-{index:02}')
        archive.mkdir(parents=True, exist_ok=True)
        (archive / 'reference.png').write_bytes((directory / 'reference.png').read_bytes())
        edits = directory / 'candidate-edits.json'
        if edits.exists():
            assert digest(edits) == approval['groups'][str(index)]['edits_sha256']
            record['postprocess'] = read(edits)
            assert record['postprocess']['source_sha256'] == digest(record['postprocess']['source'])
        write(archive / 'generation.json', dict(record, review=f'reports/even-illustration-redraw/reviews/{number:03}.json'))
        for item in items:
            slot = item['slot']; candidate = directory / f'{slot}.png'
            assert digest(candidate) == approval['groups'][str(index)]['tiles'][slot]
            target = Path(f'html/assets/lesson-{number:03}/{slot}-redrawn.webp')
            with Image.open(candidate) as im:
                im.save(target, format='WEBP', quality=95, method=6)
                width, height = im.size
            metadata = images[slot]
            metadata.update(src=str(target.relative_to('html')), width=width, height=height,
                            display_width=256, origin='local-model-redraw',
                            description=item.get('verified_description', item['cue']),
                            alt=item.get('verified_description', item['cue']),
                            generation={'model': MODEL, 'manifest': str(archive / 'generation.json')})
            if metadata.get('photo_verification'):
                metadata['photo_verification']['asset_sha256'] = digest(target)
                metadata['photo_verification']['redraw_manifest'] = str(archive / 'generation.json')
            results.append({'slot': slot, 'asset': str(target), 'sha256': digest(target),
                            'dimensions': [width, height], 'candidate_sha256': digest(candidate)})
    for item in lesson['items']:
        if item['mode'] not in ('reuse', 'exact-clock'):
            continue
        slot = item['slot']
        candidate = reuse_path(item) if item['mode'] == 'reuse' else WORK / f'{number:03}/diagrams/{slot}.png'
        assert digest(candidate) == approval['other_assets'][slot]
        target = Path(f'html/assets/lesson-{number:03}/{slot}-redrawn.webp')
        with Image.open(candidate) as im:
            width, height = im.size
            if item['mode'] == 'reuse' and candidate.suffix == '.webp':
                target.write_bytes(candidate.read_bytes())
            else:
                im.save(target, format='WEBP', quality=95, method=6)
        metadata = images[slot]
        origin = 'exact-clock-diagram' if item['mode'] == 'exact-clock' else 'local-model-redraw'
        manifest = {'model': None if item['mode'] == 'exact-clock' else MODEL,
                    'recipe': 'reports/even-illustration-redraw/plan.json', 'mode': item['mode']}
        if item.get('reuse_from'):
            manifest['reuse_from'] = item['reuse_from']
        metadata.update(src=str(target.relative_to('html')), width=width, height=height,
                        display_width=256, origin=origin, alt=item['cue'], generation=manifest)
        if metadata.get('photo_verification'):
            metadata['photo_verification']['asset_sha256'] = digest(target)
        results.append({'slot': slot, 'asset': str(target), 'sha256': digest(target),
                        'dimensions': [width, height], 'mode': item['mode']})
    updated = replace_images_field(raw, images)
    assert json.loads(updated)['sections'] == data['sections']
    path.write_text(updated)
    write(REPORT / f'published/{number:03}.json', {'lesson': number, 'images': results,
                                                'sections_sha256': lesson['sections_sha256']})
    subprocess.run(['python3', 'skills/nce1-lesson-html/scripts/render_lessons.py', '--repo', '.',
                    '--from', str(number), '--to', str(number)], check=True)
    print('PUBLISHED', number, len(results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'generate', 'diagrams', 'contact', 'review', 'publish'])
    parser.add_argument('--lessons', nargs='+', type=int)
    parser.add_argument('--groups', nargs='+', type=int)
    parser.add_argument('--notes')
    args = parser.parse_args()
    numbers = args.lessons or list(range(52, 145, 2))
    if any(n < 52 or n > 144 or n % 2 for n in numbers):
        parser.error('Only even lessons 52–144 are supported')
    if args.command == 'plan':
        plan()
    elif args.command == 'generate':
        generate(numbers, args.groups)
    elif args.command == 'diagrams':
        diagrams(numbers)
    elif args.command == 'contact':
        contact(numbers)
    elif args.command == 'review':
        if not args.notes:
            parser.error('Concrete visual inspection notes are required')
        for n in numbers:
            review(n, args.notes)
    else:
        for n in numbers:
            publish(n)


if __name__ == '__main__':
    main()
