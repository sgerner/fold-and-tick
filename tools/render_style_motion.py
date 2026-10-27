#!/usr/bin/env python3
"""Render a review GIF directly from the new packs' WFF motion expressions."""
from math import cos, floor, radians, sin
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from generate_art import ROOT, OUT, add_watch_content, circular_crop, font, native_clock
from import_style_packs import PROOFS, STYLES

# Each pair is (artwork name, shared WFF scene slot). Woodblock's six new
# stories occupy the same slots as the original themes in the other packs.
SAMPLES = {
    'woodblock': (('bicycle', 'bicycle'), ('kitten', 'kitten'), ('crane', 'forest')),
    'risograph': (('bicycle', 'bicycle'), ('kitten', 'kitten'), ('cosmos', 'cosmos')),
}


def evaluate(expression, seconds):
    # These are trusted local WFF expressions, evaluated only for a visual proof.
    moving = expression.split('?', 1)[1].split(':', 1)[0]
    code = moving.replace('[SECOND_MILLISECOND]', str(seconds))
    return eval(code, {'__builtins__': {}, 'sin': sin, 'cos': cos, 'rad': radians,
                       'floor': floor, 'min': min, 'max': max, 'abs': abs})


def render():
    face = ET.parse(ROOT / 'watchface/src/main/res/raw/watchface.xml')
    layers = {}
    for style in STYLES:
        for scene, slot in SAMPLES[style]:
            branch = face.find(f'./Scene/Condition/Compare[@expression="show_{slot}"]'
                               f'/Condition/Compare[@expression="style_{style}"]')
            images = []
            for part in branch.findall('.//PartImage'):
                name = part.find('Image').attrib['resource']
                if name == 'woodblock_ambient':
                    continue
                image = Image.open(OUT / f'{name}.png').convert('RGBA')
                image = image.resize((int(part.attrib['width']), int(part.attrib['height'])),
                                     Image.Resampling.LANCZOS)
                images.append((part, image, name))
            layers[style, scene] = images

    clocks = {style: native_clock(style='woodblock' if style == 'woodblock' else None)
              for style in STYLES}
    frames = []
    for frame_index in range(50):
        seconds = frame_index / 5
        page = Image.new('RGB', (660, 260 * len(STYLES)), '#10182c')
        draw = ImageDraw.Draw(page)
        for row, (style, label) in enumerate(STYLES.items()):
            for column, (scene, _) in enumerate(SAMPLES[style]):
                dial = Image.new('RGBA', (450, 450), '#10182c')
                glass = None
                for part, image, name in layers[style, scene]:
                    position = {key: float(part.attrib[key]) for key in ('x', 'y')}
                    alpha = 255
                    for transform in part.findall('Transform'):
                        key = transform.attrib['target']
                        value = evaluate(transform.attrib['value'], seconds)
                        if key == 'alpha':
                            alpha = value
                        else:
                            position[key] = value
                    if name.startswith('glass_'):
                        glass = image
                        continue
                    if alpha != 255:
                        image = image.copy()
                        image.putalpha(image.getchannel('A').point(lambda a: round(a * alpha / 255)))
                    dial.alpha_composite(image, (round(position['x']), round(position['y'])))
                dial = circular_crop(add_watch_content(
                    dial, glass, clocks[style], style='woodblock' if style == 'woodblock' else None))
                dial = dial.resize((210, 210), Image.Resampling.LANCZOS)
                x, y = column * 220 + 5, row * 260
                draw.text((x + 105, y + 8), f'{label} · {scene.title()}',
                          font=font(12, True), fill='#f2e9df', anchor='mt')
                page.paste(dial, (x, y + 35), dial)
        frames.append(page)
    PROOFS.mkdir(parents=True, exist_ok=True)
    path = PROOFS / 'motion.gif'
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=200, loop=0, optimize=True, disposal=2)
    print(f'Wrote native-expression motion proof: {path}')


if __name__ == '__main__':
    render()
