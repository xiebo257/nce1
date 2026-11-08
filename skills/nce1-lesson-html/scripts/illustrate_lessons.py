#!/usr/bin/env python3
"""Local FLUX.2 lesson illustrations: plan, generate candidates, publish reviewed lessons.

Generate with the MFLUX environment; plan/publish need only Pillow. The canonical
JSON contains cast/scene decisions. Generated files remain candidates until a
human/agent has visually checked them and explicitly invokes publish.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

MODEL_ID = 'mlx-community/FLUX.2-Klein-4B-4bit'
MODEL_PATH = Path.home() / '.cache/nce1-models/FLUX.2-Klein-4B-4bit'
RECIPE = 'flux2-klein-4b-reference-v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def lesson_jobs(repo, number, width, height):
    data = json.loads((repo / f'lessons/lesson-{number:03}.json').read_text())
    slots = [b['image'] for b in data['sections']['lesson'] if b.get('image')]
    if not slots:
        return []
    cast = data.get('characters', {})
    if not data.get('illustration_style') or any(not data['images'][key].get('illustration_scene') for key in slots):
        raise ValueError(f'Lesson {number:03}: prepare and review Lesson scene descriptions before generation')
    style = data['illustration_style']
    used = list(dict.fromkeys(c for key in slots for c in data['images'][key].get('characters', [])))
    # Anonymous crowds are not identity references.
    used = [c for c in used if c not in {'crowd', 'passengers', 'thieves'}]
    reference = len(slots) > 1 and bool(used)
    jobs = []
    if reference:
        descriptions = ' '.join(f'{i+1}. {c}: {cast[c]["illustration_appearance"]}' for i, c in enumerate(used))
        prompt = (f'{style} A cast reference portrait for a language textbook story. '
                  f'Exactly {len(used)} distinct people standing side by side, waist-up, '
                  f'all faces clearly visible, neutral warm gray studio background. '
                  f'From left to right: {descriptions} '
                  'Natural relaxed poses, distinct silhouettes, consistent realistic anatomy. '
                  'No lettering, names, numbers or panels printed in the image.')
        if data.get('illustration_cast_layout') == 'portrait-strip':
            prompt = (f'A horizontal character reference sheet with exactly {len(used)} equal-width vertical panels in ONE row. '
                      f'Each panel contains ONE separate head-and-shoulders portrait on a plain warm gray background. '
                      f'Exactly one face per panel, fully visible and centered. Thin vertical dividers separate the portraits. '
                      f'Left to right: {descriptions} {style} Portraits only, no scene or props.')
        jobs.append(dict(slot='cast', prompt=prompt, cast=used, reference=None))
    scene_style = data.get('illustration_scene_style', style)
    for key in slots:
        scene = data['images'][key]
        people = scene.get('characters', [])
        descriptions = ' '.join(f'{c}: {cast[c]["illustration_appearance"]}' for c in people)
        use_reference = reference and any(c in used for c in people)
        reference_people = [c for c in people if c in used]
        reference_labels = ', '.join(f'reference {i+1} is {c}' for i,c in enumerate(reference_people))
        condition = (f'Use the supplied individual character references for identities ONLY ({reference_labels}). Preserve the exact faces, hair, '
                     'ages and clothing colors of the named people. Create a NEW scene with a new pose '
                     'and background. Include only the characters named below, not the entire reference cast. ') if use_reference else ''
        count_hint = f"Exactly {scene['illustration_person_count']} people appear in the entire image. " if scene.get('illustration_person_count') else ''
        prompt = (f'{count_hint}{scene.get("illustration_style", scene_style)} {condition}Scene: {scene["illustration_scene"]} '
                  f'Characters in this scene: {descriptions or "No recurring characters."} '
                  'Readable composition, expressive natural interaction, plausible hands and props. '
                  'One continuous scene unless the scene explicitly requests two telephone locations. '
                  'No speech bubbles, captions, watermark or extra panels.')
        if scene.get('illustration_prompt_version') == 2:
            refs_text = (' '.join(f'Image {i+1} is the appearance reference for {c}.' for i,c in enumerate(reference_people)) +
                         ' Keep their same faces, hairstyles and clothing.') if use_reference else ''
            person_count = scene.get('illustration_person_count')
            precise_count = (f'Only {person_count} person appears, alone.' if person_count == 1 else
                             f'Exactly {person_count} people appear.' if person_count else '')
            prompt = (f"{scene['illustration_scene']} {precise_count} {refs_text} "
                      f"Appearance: {descriptions} {scene.get('illustration_style', scene_style)}")
        jobs.append(dict(slot=key, prompt=prompt, cast=people, reference='cast' if use_reference else None,
                         reference_people=reference_people if use_reference else [],
                         cast_layout=used if use_reference else []))
        if use_reference and data.get('illustration_cast_layout'):
            jobs[-1]['reference_layout'] = data['illustration_cast_layout']
        if scene.get('illustration_reference_crop'):
            jobs[-1]['reference_crop'] = scene['illustration_reference_crop']
    for index, job in enumerate(jobs):
        size = data['images'].get(job['slot'], {})
        job.update(lesson=number, seed=number * 1000 + index + 17 + (data['images'][job['slot']].get('illustration_seed_offset', 0) if job['slot']!='cast' else 0), width=width, height=height,
                   steps=4, guidance=1.0, model=MODEL_ID, recipe=RECIPE if job['slot']=='cast' else RECIPE+'-individual-refs')
        job['width'] = size.get('illustration_width', width)
        job['height'] = size.get('illustration_height', height)
        if any(not isinstance(job[k], int) or job[k] < 256 or job[k] % 16 for k in ('width', 'height')):
            raise ValueError(f'Lesson {number:03}, {job["slot"]}: dimensions must be multiples of 16, at least 256')
    return jobs


def candidate_paths(repo, job):
    root = repo / f'illustrations/work/candidates/{job["lesson"]:03}'
    return root / f'{job["slot"]}.png', root / f'{job["slot"]}.json'


def specification(repo, job):
    spec = dict(job)
    if job['reference']:
        ref = repo / f'illustrations/work/candidates/{job["lesson"]:03}/cast.png'
        spec['reference_sha256'] = digest(ref)
    spec['fingerprint'] = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    return spec


def generate(args, repo, jobs):
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import mlx.core as mx
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2Klein, Flux2KleinEdit
    mx.set_cache_limit(256 * 1024**2)
    model = None
    model_class = None
    count = 0
    for job in jobs:
        image_path, metadata_path = candidate_paths(repo, job)
        spec = specification(repo, job)
        if image_path.exists() and metadata_path.exists():
            old = json.loads(metadata_path.read_text())
            if old.get('fingerprint') == spec['fingerprint'] and old.get('sha256') == digest(image_path):
                print('CACHED', job['lesson'], job['slot'], flush=True)
                continue
        if args.limit is not None and count >= args.limit:
            break
        if job['reference']:
            approval_path = image_path.parent / 'cast.approved.json'
            approved = json.loads(approval_path.read_text()) if approval_path.exists() else {}
            if approved.get('sha256') != spec['reference_sha256']:
                print('REFERENCE_REVIEW_REQUIRED', job['lesson'], image_path.parent / 'cast.png', flush=True)
                return
        wanted_class = Flux2KleinEdit if job['reference'] else Flux2Klein
        if model_class is not wanted_class:
            import gc
            del model
            gc.collect()
            mx.clear_cache()
            start = time.monotonic()
            model_class = wanted_class
            model = wanted_class(model_config=ModelConfig.flux2_klein_4b(),
                                   model_path=str(args.model_path), quantize=4)
            print('MODEL_LOADED seconds', round(time.monotonic() - start, 2), flush=True)
        print('GENERATING', job['lesson'], job['slot'], flush=True)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        refs = None
        if job['reference']:
            from PIL import Image
            refs = []
            with Image.open(image_path.parent / 'cast.png') as cast_image:
                for index, character in enumerate(job['reference_people']):
                    position = job['cast_layout'].index(character)
                    columns = len(job['cast_layout'])
                    bounds = (round(cast_image.width*position/columns), 0,
                              round(cast_image.width*(position+1)/columns),
                              round(cast_image.height*0.62) if job.get('reference_crop')=='portrait' and job.get('reference_layout')!='portrait-strip' else cast_image.height)
                    target = image_path.parent / f'{job["slot"]}-ref-{index+1}.webp'
                    reference_image = cast_image.crop(bounds).convert('RGB')
                    if job.get('reference_crop') == 'panel':
                        from PIL import ImageChops
                        mask = ImageChops.difference(reference_image, Image.new('RGB', reference_image.size, 'white')).convert('L').point(lambda value: 255 if value > 20 else 0)
                        nonwhite = mask.getbbox()
                        if nonwhite:
                            reference_image = reference_image.crop(nonwhite)
                    reference_image.save(target, 'WEBP', lossless=True)
                    refs.append(target)
        start = time.monotonic()
        mx.reset_peak_memory()
        result = model.generate_image(seed=job['seed'], prompt=job['prompt'],
            num_inference_steps=job['steps'], width=job['width'], height=job['height'],
            guidance=job['guidance'], **({'image_paths':refs} if refs else {}))
        temporary = image_path.with_name(image_path.stem + '.tmp.png')
        result.save(str(temporary))
        temporary.replace(image_path)
        elapsed = round(time.monotonic() - start, 2)
        spec.update(sha256=digest(image_path), seconds=elapsed,
                    peak_mlx_gb=round(mx.get_peak_memory()/1e9, 3), status='candidate')
        write_json(metadata_path, spec)
        print('GENERATED', job['lesson'], job['slot'], elapsed, 'seconds',
              spec['peak_mlx_gb'], 'GB MLX peak', flush=True)
        del result
        mx.clear_cache()
        count += 1


def publish(args, repo, jobs):
    from PIL import Image
    if not args.review_notes:
        raise SystemExit('publish requires --review-notes after visually checking every image in the lesson')
    numbers = sorted({j['lesson'] for j in jobs})
    for number in numbers:
        current = [j for j in jobs if j['lesson'] == number]
        # Validate all files before publishing any image in this lesson.
        checked = []
        for job in current:
            img, metadata = candidate_paths(repo, job)
            recorded = json.loads(metadata.read_text())
            assert recorded['fingerprint'] == specification(repo, job)['fingerprint'], f'Stale prompt: {metadata}'
            assert recorded['sha256'] == digest(img), f'Changed candidate: {img}'
            with Image.open(img) as opened:
                assert opened.size == tuple(recorded.get('postprocess', {}).get('output_size', [job['width'], job['height']]))
                opened.verify()
            checked.append((job, img, recorded))
        path = repo / f'lessons/lesson-{number:03}.json'
        data = json.loads(path.read_text())
        for job, img, recorded in checked:
            is_cast = job['slot'] == 'cast'
            relative = (f'illustrations/references/{number:03}-cast.webp' if is_cast else
                        f'html/assets/lesson-{number:03}/{job["slot"]}-color.webp')
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(img) as opened:
                opened.convert('RGB').save(destination, 'WEBP', quality=92, method=6)
            if is_cast:
                import shutil
                source_relative = f'illustrations/references/{number:03}-cast-source.png'
                shutil.copyfile(img, repo / source_relative)
                recorded['reference_source'] = source_relative
                approval_path = img.parent / 'cast.approved.json'
                if approval_path.exists():
                    approval = json.loads(approval_path.read_text())
                    assert approval['sha256'] == recorded['sha256'], 'Stale cast approval'
                    recorded['reference_review'] = approval
            provenance = {**recorded, 'status':'visually-reviewed',
                          'review_notes':args.review_notes, 'published_sha256':digest(destination)}
            write_json(repo / f'illustrations/manifests/{number:03}-{job["slot"]}.json', provenance)
            if is_cast:
                data['illustration_reference'] = relative
            else:
                slot = data['images'][job['slot']]
                slot.update(status='ready', src=relative.removeprefix('html/'),
                            width=recorded.get('postprocess', {}).get('output_size', [job['width'], job['height']])[0],
                            height=recorded.get('postprocess', {}).get('output_size', [job['width'], job['height']])[1], origin='local-model',
                            caption=data['title'], alt=slot['illustration_scene'].replace('Mrs. ', 'Mrs ').replace('Mr. ', 'Mr ').split('. ')[0].rstrip('.') + '.',
                            generation={'model':MODEL_ID, 'seed':job['seed'],
                                        'manifest':f'illustrations/manifests/{number:03}-{job["slot"]}.json'})
                block = next(b for b in data['sections']['lesson'] if b.get('image') == job['slot'])
                if len(block.get('lines', [])) > 8 or len(block.get('text', '')) > 700:
                    slot['layout'] = 'above'
                slot.pop('reason', None)
        write_json(path, data)
        print('PUBLISHED', number, len(current) - int(current[0]['slot']=='cast'), 'lesson images')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan','generate','approve-reference','publish'])
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--from', dest='start', type=int, default=45)
    parser.add_argument('--to', dest='end', type=int, default=144)
    parser.add_argument('--parity', choices=['all', 'odd', 'even'], default='all', help='Select lesson numbers; section scope is always Lesson only')
    parser.add_argument('--width', type=int, default=768)
    parser.add_argument('--height', type=int, default=512)
    parser.add_argument('--model-path', type=Path, default=MODEL_PATH)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--slot', help='Generate one scene slot plus its cast reference')
    parser.add_argument('--review-notes')
    args = parser.parse_args()
    if args.start > args.end or args.start < 45 or args.end > 144:
        parser.error('Supported range is 45–144; first must not exceed last')
    repo = args.repo.resolve()
    jobs = [job for n in range(args.start, args.end+1) if args.parity == 'all' or n % 2 == (1 if args.parity == 'odd' else 0)
            for job in lesson_jobs(repo, n, args.width, args.height)]
    if args.slot:
        if args.action == 'publish':
            parser.error('Publish a complete reviewed lesson, not an isolated slot')
        jobs = [j for j in jobs if j['slot'] in {'cast', args.slot}]
    if args.action == 'plan':
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
    elif args.action == 'approve-reference':
        if not args.review_notes:
            parser.error('Reference approval requires visual inspection and --review-notes')
        for job in jobs:
            if job['slot'] != 'cast':
                continue
            img, metadata = candidate_paths(repo, job)
            record = json.loads(metadata.read_text())
            assert record['fingerprint'] == specification(repo, job)['fingerprint'], 'Stale cast prompt'
            assert record['sha256'] == digest(img), 'Changed cast image'
            write_json(img.parent / 'cast.approved.json', {'sha256':digest(img), 'review_notes':args.review_notes})
            print('REFERENCE_APPROVED', job['lesson'])
    elif args.action == 'generate':
        generate(args, repo, jobs)
    else:
        publish(args, repo, jobs)


if __name__ == '__main__':
    main()
