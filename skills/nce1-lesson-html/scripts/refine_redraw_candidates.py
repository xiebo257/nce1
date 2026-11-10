#!/usr/bin/env python3
"""Apply reviewed, recorded exact-diagram overlays to model redraw candidates."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from redraw_even_illustrations import REPORT, WORK, digest, groups, read, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lessons', type=int, nargs='+', required=True)
    args = parser.parse_args()
    plan = read(REPORT / 'plan.json')['lessons']
    for number in args.lessons:
        lesson = plan[str(number)]
        locations = {item['slot']: WORK / f'{number:03}/group-{index:02}'
                     for index, group in enumerate(groups(lesson), 1) for item in group}
        for slot, recipe in lesson.get('candidate_edits', {}).items():
            directory = locations[slot]
            source = (Path(recipe['source_asset']) if recipe.get('source_asset') else
                      locations[recipe.get('copy_scene_from', slot)] / 'redrawn.png')
            with Image.open(source) as original:
                image = original.convert('RGB')
            record = {'source': str(source), 'source_sha256': digest(source), 'operations': []}
            for operation in recipe['operations']:
                if operation['type'] == 'fit-content':
                    resized = image.resize(tuple(operation['size']), Image.Resampling.LANCZOS)
                    image = Image.new('RGB', image.size, operation.get('background', 'white'))
                    image.paste(resized, tuple(operation['position']))
                    record['operations'].append(operation)
                    continue
                if operation['type'] == 'text-overlay':
                    draw = ImageDraw.Draw(image)
                    box = operation['box']
                    draw.rectangle(box, fill=operation.get('background', 'white'))
                    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', operation['font_size'])
                    draw.text(((box[0]+box[2])/2, (box[1]+box[3])/2), operation['text'],
                              font=font, fill=operation.get('color', 'black'), anchor='mm')
                    record['operations'].append(operation)
                    continue
                if operation['type'] == 'hue-shift':
                    box = operation['box']; region = image.crop(box).convert('HSV')
                    pixels = list(region.getdata()); low, high = operation['hue_range']
                    region.putdata([(operation['to_hue'],
                                     max(0, min(255, s + operation.get('saturation_delta', 0))),
                                     max(0, min(255, v + operation.get('value_delta', 0))))
                                    if low <= h <= high and s >= operation['min_saturation']
                                    and v >= operation.get('min_value', 0) else (h, s, v)
                                    for h, s, v in pixels])
                    image.paste(region.convert('RGB'), (box[0], box[1]))
                    record['operations'].append(operation)
                    continue
                if operation['type'] == 'erase-polygons':
                    draw = ImageDraw.Draw(image)
                    for polygon in operation['polygons']:
                        draw.polygon([tuple(p) for p in polygon], fill=operation.get('fill', 'white'))
                    record['operations'].append(operation)
                    continue
                if operation['type'] != 'exact-diagram-overlay':
                    raise ValueError('Unknown refinement: ' + operation['type'])
                draw = ImageDraw.Draw(image)
                draw.rectangle(operation['clear_box'], fill='white')
                with Image.open(operation['asset']) as overlay:
                    x, y, width, height = operation['placement']
                    image.paste(overlay.convert('RGB').resize((width, height), Image.Resampling.LANCZOS), (x, y))
                record['operations'].append(dict(operation, sha256=digest(operation['asset'])))
            target = directory / f'{slot}.png'
            image.save(target)
            record['output_sha256'] = digest(target)
            write(directory / 'candidate-edits.json', record)
            print('REFINED_REQUIRES_REVIEW', number, slot)


if __name__ == '__main__':
    main()
