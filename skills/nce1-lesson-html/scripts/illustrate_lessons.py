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
        jobs.append(dict(slot='cast', prompt=prompt, cast=used, reference=None))
    for key in slots:
        scene = data['images'][key]
        people = scene.get('characters', [])
        descriptions = ' '.join(f'{c}: {cast[c]["illustration_appearance"]}' for c in people)
        use_reference = reference and any(c in used for c in people)
        condition = ('Use the supplied cast reference for identities ONLY. Preserve the exact faces, hair, '
                     'ages and clothing colors of the named people. Create a NEW scene with a new pose '
                     'and background. Include only the characters named below, not the entire reference cast. ') if use_reference else ''
        prompt = (f'{style} {condition}Scene: {scene["illustration_scene"]} '
                  f'Characters in this scene: {descriptions or "No recurring characters."} '
                  'Readable composition, expressive natural interaction, plausible hands and props. '
                  'One continuous scene unless the scene explicitly requests two telephone locations. '
                  'No speech bubbles, captions, watermark or extra panels.')
        jobs.append(dict(slot=key, prompt=prompt, cast=people, reference='cast' if use_reference else None))
    for index, job in enumerate(jobs):
        job.update(lesson=number, seed=number * 1000 + index + 17, width=width, height=height,
                   steps=4, guidance=1.0, model=MODEL_ID, recipe=RECIPE)
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
    from mflux.models.flux2.variants import Flux2KleinEdit
    mx.set_cache_limit(256 * 1024**2)
    model = None
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
        if model is None:
            start = time.monotonic()
            model = Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(),
                                   model_path=str(args.model_path), quantize=4)
            print('MODEL_LOADED seconds', round(time.monotonic() - start, 2), flush=True)
        print('GENERATING', job['lesson'], job['slot'], flush=True)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        refs = [image_path.parent / 'cast.png'] if job['reference'] else None
        start = time.monotonic()
        mx.reset_peak_memory()
        result = model.generate_image(seed=job['seed'], prompt=job['prompt'],
            num_inference_steps=job['steps'], width=job['width'], height=job['height'],
            guidance=job['guidance'], image_paths=refs)
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
                assert opened.size == (job['width'], job['height'])
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
            provenance = {**recorded, 'status':'visually-reviewed',
                          'review_notes':args.review_notes, 'published_sha256':digest(destination)}
            write_json(repo / f'illustrations/manifests/{number:03}-{job["slot"]}.json', provenance)
            if is_cast:
                data['illustration_reference'] = relative
            else:
                slot = data['images'][job['slot']]
                slot.update(status='ready', src=relative.removeprefix('html/'),
                            width=job['width'], height=job['height'], origin='local-model',
                            caption=data['title'], alt=slot['illustration_scene'].split('. ')[0].rstrip('.') + '.',
                            generation={'model':MODEL_ID, 'seed':job['seed'],
                                        'manifest':f'illustrations/manifests/{number:03}-{job["slot"]}.json'})
                slot.pop('reason', None)
        write_json(path, data)
        print('PUBLISHED', number, len(current) - int(current[0]['slot']=='cast'), 'lesson images')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan','generate','publish'])
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--from', dest='start', type=int, default=45)
    parser.add_argument('--to', dest='end', type=int, default=143)
    parser.add_argument('--width', type=int, default=768)
    parser.add_argument('--height', type=int, default=512)
    parser.add_argument('--model-path', type=Path, default=MODEL_PATH)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--review-notes')
    args = parser.parse_args()
    if args.start > args.end or args.start < 45 or args.end > 143:
        parser.error('Supported range is 45–143; first must not exceed last')
    repo = args.repo.resolve()
    jobs = [job for n in range(args.start, args.end+1) if n % 2
            for job in lesson_jobs(repo, n, args.width, args.height)]
    if args.action == 'plan':
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
    elif args.action == 'generate':
        generate(args, repo, jobs)
    else:
        publish(args, repo, jobs)


if __name__ == '__main__':
    main()
