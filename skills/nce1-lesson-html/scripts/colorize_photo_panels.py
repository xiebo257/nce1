#!/usr/bin/env python3
"""Color reviewed photograph atlases locally; write candidates, never publish."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lessons', nargs='*', type=int)
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import mlx.core as mx
    import numpy as np
    from PIL import Image
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2.variants import Flux2KleinEdit
    from preserve_panel_lineart import transfer
    specs = json.loads(Path('reports/photo-layout-audit/photo-frame-regions.json').read_text())
    mx.set_cache_limit(256 * 1024**2)
    model = None
    for n in args.lessons or sorted(map(int, specs)):
        directory = Path(f'illustrations/work/photo-audit/panels/{n:03}')
        source_path = directory / 'source.png'
        metadata = json.loads((directory / 'source.json').read_text())
        record_path = directory / 'generation.json'
        output = directory / 'colored.png'
        if record_path.exists() and output.exists():
            previous = json.loads(record_path.read_text())
            if previous['source_atlas_sha256'] == digest(source_path) and previous['output_sha256'] == digest(output):
                print('CACHED', n, flush=True)
                continue
        source = Image.open(source_path).convert('RGB')
        width, height = source.size
        prompt = (
            f'Colorize these {len(metadata["tiles"])} textbook cartoon pictures in exactly the same '
            f'{metadata["cols"]}-column layout. Preserve every face, pose, object, number, word and panel. '
            'Use warm natural skin, vivid but soft clothing colors and white backgrounds. '
            'The same recurring person must have identical hair color and clothing colors in every panel. '
            'Keep black hair black; light-haired women have golden blonde hair. '
            'Keep all original black lines, do not redraw, add, remove or rearrange anything. '
            'Color only the existing drawings; leave empty cells white.'
        )
        if model is None:
            model = Flux2KleinEdit(model_config=ModelConfig.flux2_klein_4b(),
                                  model_path=str(Path.home()/'.cache/nce1-models/FLUX.2-Klein-4B-4bit'), quantize=4)
        print('START', n, width, height, flush=True)
        start = time.monotonic()
        result = model.generate_image(seed=n*1000+926, prompt=prompt, num_inference_steps=4,
                                      width=width, height=height, guidance=1.0, image_paths=[source_path])
        result.save(str(output), overwrite=True)
        guide = np.array(Image.open(output).convert('RGB'))
        original = np.array(source)
        assert guide.shape == original.shape
        preserved = np.full_like(original, 255)
        cw, ch = metadata['cell']; cols = metadata['cols']
        for i in range(len(metadata['tiles'])):
            x, y = i%cols*cw, i//cols*ch
            tile = transfer(original[y:y+ch,x:x+cw], guide[y:y+ch,x:x+cw], [])
            preserved[y:y+ch,x:x+cw] = tile
            Image.fromarray(tile).save(directory/f'candidate-{i+1:02}.png')
        Image.fromarray(preserved).save(directory/'preserved.png')
        record = dict(metadata, model='FLUX.2-Klein-4B-4bit', prompt=prompt, seed=n*1000+926,
                      steps=4, seconds=round(time.monotonic()-start,2), output_sha256=digest(output),
                      preserved_sha256=digest(directory/'preserved.png'), status='candidate-needs-visual-review')
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        print('CANDIDATE', n, record['seconds'], flush=True)
        del result
        mx.clear_cache(); gc.collect()


if __name__ == '__main__':
    main()
