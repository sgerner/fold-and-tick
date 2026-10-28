#!/usr/bin/env python3
"""Render a compact motion proof from the new packs' actual WFF transforms."""
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from generate_art import ROOT, OUT, add_watch_content, circular_crop, font, native_clock
from render_style_motion import evaluate

STYLES = {
    'bioluminescent': 'Bioluminescent',
    'pixel_art': 'Pixel art',
}
SAMPLES = {
    'bioluminescent': (('bicycle', 'bicycle', 'Bicycle'), ('kitten', 'kitten', 'Kitten')),
    'pixel_art': (('velodrome', 'bicycle', 'Velodrome'), ('laundry_kitten', 'forest', 'Laundry Kitten')),
}


def render():
    face = ET.parse(ROOT / 'watchface/src/main/res/raw/watchface.xml')
    layers = {}
    for style in STYLES:
        for scene, slot, _ in SAMPLES[style]:
            branch = face.find(f'./Scene/Condition/Compare[@expression="show_{slot}"]'
                               f'/Condition/Compare[@expression="style_{style}"]')
            if branch is None:
                raise ValueError(f'Missing {style}/{scene} watch-face branch')
            parts = []
            for part in branch.findall('.//PartImage'):
                name = part.find('Image').attrib['resource']
                image = Image.open(OUT / f'{name}.png').convert('RGBA')
                sampling = Image.Resampling.NEAREST if style == 'pixel_art' and not name.startswith('glass_') else Image.Resampling.LANCZOS
                image = image.resize((int(part.attrib['width']), int(part.attrib['height'])), sampling)
                parts.append((part, image, name))
            layers[style, scene] = parts

    clock = native_clock()
    frames = []
    for frame_index in range(40):
        seconds = frame_index / 4
        page = Image.new('RGB', (440, 520), '#10182c')
        draw = ImageDraw.Draw(page)
        for row, (style, label) in enumerate(STYLES.items()):
            for column, (scene, _, scene_label) in enumerate(SAMPLES[style]):
                dial = Image.new('RGBA', (450, 450), '#10182c')
                glass = None
                for part, source, name in layers[style, scene]:
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
                        glass = source
                        continue
                    image = source
                    if alpha != 255:
                        image = source.copy()
                        image.putalpha(image.getchannel('A').point(lambda a: round(a * alpha / 255)))
                    dial.alpha_composite(image, (round(position['x']), round(position['y'])))
                if style == 'pixel_art':
                    artwork = dial.resize((210, 210), Image.Resampling.NEAREST)
                    content = add_watch_content(Image.new('RGBA', (450, 450)), glass, clock, style=style)
                    artwork.alpha_composite(content.resize((210, 210), Image.Resampling.LANCZOS))
                    dial = circular_crop(artwork)
                else:
                    dial = circular_crop(add_watch_content(dial, glass, clock, style=style))
                    dial = dial.resize((210, 210), Image.Resampling.LANCZOS)
                x, y = column * 220 + 5, row * 260
                draw.text((x + 105, y + 8), f'{label} · {scene_label}',
                          font=font(12, True), fill='#f2e9df', anchor='mt')
                page.paste(dial, (x, y + 35), dial)
        frames.append(page)
    path = ROOT / 'preview/styles/new-packs-motion.gif'
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=250, loop=0, optimize=True, disposal=2)
    print(f'Wrote WFF motion proof: {path}')


if __name__ == '__main__':
    render()
