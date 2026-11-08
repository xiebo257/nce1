#!/usr/bin/env python3
"""Transfer local-model colors to source ink regions without changing teaching cues.

Requires a generated shared atlas. Produces candidates only; inspect colors before
publishing. --region SLOT:X:Y:COLOR corrects an observed fill at a tile pixel.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageColor

from illustrate_lessons import candidate_paths, digest, lesson_jobs, write_json


def transfer(source, guide, overrides):
    gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    dark = gray < 90
    paper = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    gray = np.minimum(255, gray.astype(float) * 255 / np.maximum(paper, 1)).astype(np.uint8)
    gray[dark] = 0
    ink = (gray < 150).astype(np.uint8)
    closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(1 - closed, connectivity=4)
    fills = np.full_like(source, 255)
    height, width = gray.shape
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area < 12 or area > gray.size * .23 or x == 0 or y == 0 or x+w >= width or y+h >= height:
            continue
        mask = labels == label
        colors = guide[mask].astype(float)
        saturation = colors.max(axis=1) - colors.min(axis=1)
        colored = colors[(saturation > 30) & (colors.max(axis=1) > 80)]
        if len(colored) < max(6, area * .15):
            continue
        skin = colors[(colors[:, 0] > colors[:, 1]+12) &
                      (colors[:, 1] > colors[:, 2]+6) & (colors[:, 0] > 130)]
        selected = skin if len(skin) > max(8, area * .12) else colored
        fills[mask] = np.minimum(255, np.median(selected, axis=0) * .7 + 255 * .3)
    for x, y, color in overrides:
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f'Fill point outside tile: {(x, y)}')
        label = labels[y, x]
        if label == 0:
            raise ValueError(f'Fill point lies on source ink: {(x, y)}')
        fills[labels == label] = ImageColor.getrgb(color)
    alpha = np.clip((200 - gray.astype(float)) / 100, 0, 1)[..., None]
    return (fills * (1-alpha)).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--lesson', type=int, required=True)
    parser.add_argument('--region', action='append', default=[])
    args = parser.parse_args()
    repo = args.repo.resolve()
    regions = {}
    for value in args.region:
        slot, x, y, color = value.split(':', 3)
        regions.setdefault(slot, []).append((int(x), int(y), color))
    atlas = repo / f'illustrations/work/atlases/{args.lesson:03}'
    source = np.array(Image.open(atlas/'source.png').convert('RGB'))
    guide = np.array(Image.open(atlas/'colored.png').convert('RGB'))
    if source.shape != guide.shape:
        raise ValueError('Source and generated atlas dimensions differ')
    result = np.full_like(source, 255)
    jobs = [job for job in lesson_jobs(repo, args.lesson, 768, 512)
            if job.get('source_reference') and not job.get('exact_diagram')]
    for job in jobs:
        image, metadata = candidate_paths(repo, job)
        record = json.loads(metadata.read_text())
        left, top, right, bottom = record['postprocess']['crop_box']
        tile = transfer(source[top:bottom, left:right], guide[top:bottom, left:right],
                        regions.get(job['slot'], []))
        result[top:bottom, left:right] = tile
        Image.fromarray(tile).save(image)
        record['sha256'] = digest(image)
        record['status'] = 'candidate'
        record['postprocess'].update(
            method='model-color-transfer-preserving-source-lineart-v2',
            output_size=[right-left, bottom-top],
            source_atlas_sha256=digest(atlas/'source.png'),
            color_guide_sha256=digest(atlas/'colored.png'),
            region_overrides=regions.get(job['slot'], []))
        write_json(metadata, record)
    Image.fromarray(result).save(atlas/'lineart-preserved.png')
    print('SOURCE_LINEART_CANDIDATES_REQUIRE_REVIEW', args.lesson, len(jobs))


if __name__ == '__main__':
    main()
