#!/usr/bin/env python3
"""Render local Qwen3-TTS CustomVoice dialogue with per-line style instructions."""

import argparse
import json
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model


def resolve_segments(data, script_path):
    """Resolve nonspoken character IDs before any model loading or output writes."""
    roles = data.get('roles', {})
    if 'roles_file' in data:
        if roles:
            raise ValueError('Use either roles or roles_file')
        roles = json.loads((script_path.parent / data['roles_file']).read_text(encoding='utf-8'))
    segments = []
    for index, item in enumerate(data['segments'], 1):
        segment = dict(item)
        if 'role' in segment:
            role = segment['role']
            if role not in roles:
                raise ValueError(f'Segment {index}: unknown role {role!r}')
            profile = roles[role]
            if 'speaker' in segment and segment['speaker'] != profile['speaker']:
                raise ValueError(f'Segment {index}: speaker conflicts with role {role!r}')
            segment['speaker'] = profile['speaker']
            segment['instructions'] = ' '.join(filter(None, [
                profile.get('instructions', ''), segment.get('instructions', '')]))
        if not segment.get('speaker') or not segment.get('text', '').strip():
            raise ValueError(f'Segment {index}: speaker and text are required')
        if float(segment.get('pause_after', 0.4)) < 0:
            raise ValueError(f'Segment {index}: negative pause')
        segment.setdefault('instructions', '')
        segments.append(segment)
    if not segments:
        raise ValueError('No speech segments')
    return segments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, help='Intermediate files; defaults to output-parent/work/output-stem')
    args = parser.parse_args()
    data = json.loads(args.script.read_text(encoding='utf-8'))
    segments = resolve_segments(data, args.script)
    started = time.monotonic()
    print('Loading local Qwen3-TTS model...', flush=True)
    model = load_model(str(args.model.expanduser().resolve()))
    supported = {name.lower() for name in model.supported_speakers}
    for segment in segments:
        if segment['speaker'].lower() not in supported:
            raise ValueError(f"Unsupported speaker: {segment['speaker']}")
    frames, timings = [], []
    sample_rate = None
    work_dir = args.work_dir or args.output.parent / 'work' / args.output.stem
    parts = work_dir / 'segments'
    parts.mkdir(parents=True, exist_ok=True)
    for index, segment in enumerate(segments, start=1):
        print(f"Segment {index}/{len(segments)}: {segment['speaker']} — {segment['text']}", flush=True)
        mx.random.seed(segment.get('generation_seed', data.get('seed', 42) + index))
        chunks = []
        for result in model.generate_custom_voice(
            text=segment['text'], speaker=segment['speaker'], language='English',
            instruct=segment['instructions'], temperature=segment.get('generation_temperature', 0.7), max_tokens=180,
        ):
            if sample_rate is not None and sample_rate != result.sample_rate:
                raise ValueError('Sample rate changed between segments')
            sample_rate = result.sample_rate
            chunks.append(np.asarray(result.audio, dtype=np.float32).reshape(-1))
        if not chunks:
            raise RuntimeError(f'No audio returned for segment {index}')
        audio = np.concatenate(chunks)
        if not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError(f'Invalid audio in segment {index}')
        sf.write(parts / f'{index:02d}.wav', audio, sample_rate, subtype='PCM_16')
        frames.extend([audio, np.zeros(round(segment.get('pause_after', 0.4) * sample_rate), dtype=np.float32)])
        timings.append({'segment': index, 'role': segment.get('role'), 'speaker': segment['speaker'], 'seconds': len(audio) / sample_rate})
        print(f'  {len(audio) / sample_rate:.2f}s generated; elapsed {time.monotonic() - started:.1f}s', flush=True)
        mx.clear_cache()
    sf.write(args.output, np.concatenate(frames), sample_rate, subtype='PCM_16')
    (work_dir / 'manifest.json').write_text(json.dumps({
        'model': str(args.model), 'script': str(args.script), 'sample_rate': sample_rate,
        'elapsed_seconds': time.monotonic() - started, 'segments': timings,
    }, indent=2) + '\n')
    print(f'Wrote {args.output}', flush=True)


if __name__ == '__main__':
    main()
