#!/usr/bin/env python3
"""Build watch resources and labeled proofs from the checked-in style artwork.

Image generation is a separate creative step. This deterministic importer only
resizes sources, slices transparent sprite sheets, and assembles watch layers.
"""
from pathlib import Path
import argparse
import json

from PIL import Image, ImageDraw, ImageOps

from generate_art import (OUT, ROOT, SCENES, SIZE, assemble, feathered_glass,
                          font, native_clock, picker_preview)

STYLES = {
    'woodblock': 'Woodblock',
    'risograph': 'Risograph',
}
SOURCES = ROOT / 'artwork/packs'
PROOFS = ROOT / 'preview/styles'
SEPARATE_SUBJECTS = {'bicycle', 'kitten', 'cosmos', 'ocean'}

# Sprite sheet: four columns, four rows; actors first, then small details.
# All boxes use the same 450px coordinate space as WFF and the browser demo.
ACTORS = {
    'bicycle': (0, (130, 268, 320, 396)),
    'forest': (1, (153, 301, 297, 410)),
    'coding': (10, (280, 62, 392, 145)),
    'kitten': (3, (125, 232, 325, 422)),
    'landscape': (4, (210, 45, 393, 132)),
    'cosmos': (5, (165, 165, 285, 285)),
    'ocean': (6, (96, 276, 354, 412)),
    'aurora': (7, (251, 315, 388, 410)),
}
DETAILS = {
    'bicycle': (8, (72, 68, 123, 115)),
    'forest': (9, (70, 68, 170, 158)),
    'coding': (10, (56, 336, 127, 389)),
    'kitten': (11, (189, 361, 249, 401)),
    'landscape': (12, (51, 58, 213, 120)),
    'cosmos': (13, (119, 243, 197, 320)),
    'ocean': (14, (318, 58, 398, 137)),
    'aurora': (15, (37, 28, 414, 135)),
}


def sprite(sheet, boxes, cell):
    # Generated rows are not a mathematically exact grid. The reviewed alpha
    # bounds preserve complete paws, wheels, and flames without neighboring art.
    tile = sheet.crop(boxes[cell])
    bounds = tile.getchannel('A').getbbox()
    if bounds is None:
        raise ValueError(f'Empty sprite cell {cell}')
    return tile.crop(bounds)


def layer(sheet, boxes, spec):
    cell, box = spec
    art = sprite(sheet, boxes, cell)
    x, y, right, bottom = box
    art.thumbnail((right - x, bottom - y), Image.Resampling.LANCZOS)
    result = Image.new('RGBA', (SIZE, SIZE))
    result.alpha_composite(art, (x + (right - x - art.width) // 2,
                                 y + (bottom - y - art.height) // 2))
    return result


def background_at_rest(scene):
    # The new art overscans the dial while it pans. Match its frozen WFF pose.
    return scene.resize((500, 500), Image.Resampling.LANCZOS).crop((25, 25, 475, 475))


def build_style(style, label):
    folder = SOURCES / style
    sheet = Image.open(folder / 'sprites.png').convert('RGBA')
    boxes = json.loads((folder / 'sprites-prompts.json').read_text())[0]['sprite_boxes']
    if len(boxes) != 16:
        raise ValueError(f'{style}: expected sixteen reviewed sprite bounds')
    if sheet.getchannel('A').getextrema() != (0, 255):
        raise ValueError(f'{style}: sprite sheet must include transparent and opaque pixels')
    clock = native_clock()
    proof = Image.new('RGB', (4 * 330, 2 * 370), '#10182c')
    draw = ImageDraw.Draw(proof)
    for index, name in enumerate(SCENES):
        source = folder / (f'{name}-fresh.png' if style == 'risograph' else
                           f'{name}-background.png' if name in SEPARATE_SUBJECTS else f'{name}.png')
        with Image.open(source) as image:
            scene = ImageOps.fit(image.convert('RGB'), (SIZE, SIZE), method=Image.Resampling.LANCZOS)
        actor_spec = ACTORS[name]
        if style == 'risograph':
            actor_spec = {'coding': (2, (235, 255, 405, 405)),
                          'aurora': (7, (280, 48, 395, 155))}.get(name, actor_spec)
        actor = layer(sheet, boxes, actor_spec)
        details = layer(sheet, boxes, DETAILS[name])
        if style == 'woodblock' and name == 'coding':
            # The laptop is painted into one cohesive still life. Only its
            # typing cursor blinks; there are no disconnected floating brackets.
            actor = Image.new('RGBA', (SIZE, SIZE))
            details = Image.new('RGBA', (SIZE, SIZE))
            ImageDraw.Draw(details).rectangle((229, 276, 234, 287), fill='#f8c46b')
        elif style == 'risograph' and name == 'coding':
            details = layer(sheet, boxes, (10, (328, 318, 340, 337)))
        glass = feathered_glass(background_at_rest(scene))
        for prefix, image in [('scene', scene), ('motion', actor), ('drift', details), ('glass', glass)]:
            # Blurred glass and small floating accents do not need full-dial
            # texture resolution. WFF still renders their 450px logical canvas.
            # This keeps the designs within Wear OS's 100MB active budget.
            texture = image.resize((225, 225), Image.Resampling.LANCZOS) if prefix in ('drift', 'glass') else image
            texture.save(OUT / f'{prefix}_{style}_{name}.png', optimize=True)
        composed = assemble(background_at_rest(scene), actor, details,
                            drift_below=name in ('cosmos', 'aurora'))
        composed.resize((160, 160), Image.Resampling.LANCZOS).save(
            OUT / f'icon_scene_{style}_{name}.png', optimize=True)
        dial = picker_preview(composed, glass, clock).resize((310, 310), Image.Resampling.LANCZOS)
        x, y = (index % 4) * 330 + 10, (index // 4) * 370
        draw.text((x + 155, y + 18), f'{label} · {name.title()}',
                  font=font(16, True), fill='#f2e9df', anchor='mt')
        proof.paste(dial, (x, y + 47), dial)
    proof.save(PROOFS / f'{style}.png', optimize=True)
    return proof


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    PROOFS.mkdir(parents=True, exist_ok=True)
    proofs = [build_style(style, label) for style, label in STYLES.items()]
    overview = Image.new('RGB', (1320, 385 * ((len(proofs) + 1) // 2)), '#10182c')
    for index, proof in enumerate(proofs):
        # Four columns × two rows per pack, scaled together for a readable index.
        overview.paste(proof.resize((660, 370), Image.Resampling.LANCZOS),
                       ((index % 2) * 660, (index // 2) * 385))
    overview.save(PROOFS / 'all-packs.png', optimize=True)
    print(f'Built {len(STYLES) * len(SCENES)} layered scenes and {len(STYLES)} labeled proofs')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
