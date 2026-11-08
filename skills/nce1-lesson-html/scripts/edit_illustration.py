#!/usr/bin/env python3
"""Edit a local candidate with the same FLUX.2 model, retaining provenance for review."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
from illustrate_lessons import MODEL_ID, MODEL_PATH, digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--lesson', type=int, required=True)
    p.add_argument('--slot', required=True)
    p.add_argument('--instruction', required=True)
    p.add_argument('--seed', type=int, required=True)
    a = p.parse_args()
    root = a.repo.resolve()
    image_path = root / f'illustrations/work/candidates/{a.lesson:03}/{a.slot}.png'
    metadata = image_path.with_suffix('.json')
    recorded = json.loads(metadata.read_text())
    assert digest(image_path) == recorded['sha256'], 'Candidate hash changed'
    source = root / f'illustrations/work/originals/{a.lesson:03}-{a.slot}-before-edit-{a.seed}.png'
    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image_path, source)
    from PIL import Image
    with Image.open(source) as opened:
        width, height = opened.size
    if width % 16 or height % 16:
        raise SystemExit('Model editing requires dimensions divisible by 16; edit before cropping')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import mlx.core as mx
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2KleinEdit
    mx.set_cache_limit(256*1024**2)
    model = Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(), model_path=str(MODEL_PATH), quantize=4)
    start = time.monotonic()
    result = model.generate_image(seed=a.seed, prompt=a.instruction, num_inference_steps=4,
                                  width=width, height=height, guidance=1.0, image_paths=[source])
    temporary = image_path.with_name(image_path.stem+'.edit.png')
    result.save(str(temporary))
    temporary.replace(image_path)
    edits = recorded.setdefault('postprocess', {}).setdefault('model_edits', [])
    edits.append({'model':MODEL_ID, 'instruction':a.instruction, 'seed':a.seed,
                  'input_sha256':digest(source), 'output_sha256':digest(image_path),
                  'seconds':round(time.monotonic()-start, 2)})
    recorded['sha256'] = digest(image_path)
    recorded['status'] = 'candidate'
    write_json(metadata, recorded)
    print('EDITED_CANDIDATE_REQUIRES_VISUAL_REVIEW', image_path, flush=True)


if __name__ == '__main__':
    main()
