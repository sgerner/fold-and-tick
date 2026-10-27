#!/usr/bin/env python3
"""Build watch resources and labeled proofs from the checked-in style artwork.

Image generation is a separate creative step. This deterministic importer
resizes saved artwork and assembles transparent actors into watch layers.
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
STYLE_SCENES = {
    'woodblock': ('bicycle', 'crane', 'kitten', 'torii', 'lanterns',
                  'sailboat', 'moon_rabbit'),
    'risograph': tuple(SCENES),
}

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


def fitted_background(path):
    with Image.open(path) as image:
        return ImageOps.fit(image.convert('RGB'), (SIZE, SIZE),
                            method=Image.Resampling.LANCZOS)


def sprite_at(sheet, boxes, cell, placement):
    """Place one reviewed atlas sprite in an explicit woodblock-safe region."""
    art = sprite(sheet, boxes, cell)
    left, top, width, height = placement
    art.thumbnail((width, height), Image.Resampling.LANCZOS)
    result = Image.new('RGBA', (SIZE, SIZE))
    result.alpha_composite(art, (left + (width - art.width) // 2,
                                 top + (height - art.height) // 2))
    return result


def generated_sprite(path, placement, crop=None, opacity=1.0, threshold=12):
    """Fit a generated transparent sprite onto the renderer's 450px canvas."""
    with Image.open(path) as source:
        art = source.convert('RGBA')
    if crop:
        art = art.crop(crop)
    alpha = art.getchannel('A')
    # Ignore near-transparent fringe when finding bounds, while preserving
    # the generated alpha values in the cropped artwork itself.
    visible = alpha.point(lambda value: 255 if value >= threshold else 0).getbbox()
    if visible is None:
        raise ValueError(f'No visible sprite pixels in {path}')
    art = art.crop(visible)
    left, top, width, height = placement
    art.thumbnail((width, height), Image.Resampling.LANCZOS)
    if opacity != 1.0:
        art.putalpha(art.getchannel('A').point(lambda value: round(value * opacity)))
    result = Image.new('RGBA', (SIZE, SIZE))
    result.alpha_composite(art, (left, top))
    return result


def woodblock_details(name):
    """Draw sparse carved-paper motion accents as transparent detail layers."""
    layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    gold = (241, 189, 105, 175)
    parchment = (225, 210, 168, 145)
    vermilion = (218, 93, 72, 190)

    if name == 'crane':
        # Two carved maple leaves ride the high wind along the lower corners.
        for x, y, size, color in [(44, 345, 15, vermilion),
                                  (390, 365, 12, gold)]:
            d.polygon([(x, y-size), (x+size, y-2), (x+5, y+size),
                       (x-size, y+4)], fill=color)
            d.line((x-size+2, y+4, x+4, y-5), fill=(29, 39, 48, 185), width=2)
    elif name == 'torii':
        # A few small maple leaves sweep across the lower shoreline.
        for x, y, size, color in [(60, 390, 10, vermilion),
                                  (384, 368, 8, gold),
                                  (415, 410, 9, vermilion)]:
            d.polygon([(x, y-size), (x+size, y-2), (x+4, y+size),
                       (x-size, y+3)], fill=color)
    elif name == 'lanterns':
        # Fireflies stay in the central lower gap between complication slots.
        for x, y, radius in [(218, 349, 3), (232, 370, 2),
                             (210, 392, 2), (240, 408, 3)]:
            d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=gold)
            d.ellipse((x-radius-3, y-radius-3, x+radius+3, y+radius+3),
                      outline=(241, 189, 105, 58), width=1)
    elif name == 'sailboat':
        # Narrow foam crests echo the background's carved wave pattern.
        for points in [[(30, 398), (54, 393), (78, 398), (103, 393)],
                       [(338, 410), (362, 405), (387, 410), (412, 405)]]:
            d.line(points, fill=parchment, width=2, joint='curve')
            d.line([(x, y+4) for x, y in points],
                   fill=(213, 219, 199, 96), width=1, joint='curve')
    elif name == 'moon_rabbit':
        # Small pale petals drift around the meadow's outer edge.
        for x, y in [(37, 390), (79, 416), (385, 376), (421, 408)]:
            d.ellipse((x-5, y-2, x+5, y+2), fill=parchment)
            d.ellipse((x-2, y-5, x+2, y+5), fill=(239, 202, 151, 155))
    return layer


def woodblock_ambient():
    """Make a quiet low-light edge engraving; the center stays completely open."""
    image = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    ink = (132, 154, 160, 58)
    gold_ink = (197, 166, 112, 48)

    # Broken carved waves sit just inside the lower curve of the round dial.
    for left, right in ((75, 145), (305, 375)):
        for offset in (0, 10, 20):
            d.arc((left + offset // 2, 338 + offset,
                   right - offset // 2, 408 + offset),
                  198, 342, fill=ink, width=2)
    # Sparse bamboo stems and leaves mark the upper right edge without filling
    # the clock band or adding a bright central patch in ambient mode.
    d.line([(392, 48), (369, 95), (389, 142)], fill=ink, width=3)
    d.line([(370, 93), (399, 80)], fill=ink, width=2)
    d.line([(380, 69), (352, 56)], fill=ink, width=2)
    d.line([(382, 72), (404, 53)], fill=gold_ink, width=2)
    d.line([(381, 118), (352, 107)], fill=gold_ink, width=2)
    d.line([(383, 122), (405, 100)], fill=ink, width=2)
    return image


def build_woodblock_style(label):
    """Import the seven current Woodblock scenes without reviving retired art."""
    folder = SOURCES / 'woodblock'
    atlas = Image.open(folder / 'sprites.png').convert('RGBA')
    boxes = json.loads((folder / 'sprites-prompts.json').read_text())[0]['sprite_boxes']
    if len(boxes) != 16:
        raise ValueError('woodblock: expected sixteen reviewed atlas bounds')

    background_files = {
        'crane': 'crane_day_background_source.png',
        'torii': 'torii_background_source.png',
        'lanterns': 'lanterns_background_source.png',
        'sailboat': 'sailboat_sunset_background_source.png',
        'moon_rabbit': 'moon_rabbit_background_source.png',
    }
    sprite_files = {name: folder / f'{name}_motion_source.png'
                    for name in ('crane', 'torii', 'lanterns',
                                 'sailboat', 'moon_rabbit')}
    placements = {
        # Positions are chosen for their native XML motion ranges and clock
        # slots: upper sky, lower shoreline, and the outer top edge.
        'crane': (145, 8, 170, 130),
        'torii': (15, 355, 420, 76),
        'lanterns': (130, 0, 120, 110),
        'sailboat': (0, 329, 180, 112),
        'moon_rabbit': (115, 310, 130, 115),
    }
    proof = Image.new('RGB', (4 * 330, 2 * 370), '#10182c')
    draw = ImageDraw.Draw(proof)
    clock = native_clock(style='woodblock')
    if clock is None:
        raise FileNotFoundError('woodblock clock glyphs must exist before import')

    for index, name in enumerate(STYLE_SCENES['woodblock']):
        if name in ('bicycle', 'kitten'):
            scene = fitted_background(folder / f'{name}-background.png')
            cell = ACTORS[name][0]
            box = ((130, 302, 190, 128) if name == 'bicycle'
                   else (125, 288, 200, 142))
            actor = sprite_at(atlas, boxes, cell, box)
            # The Woodblock kitten reaches toward a butterfly. Keeping the
            # butterfly as a separate drift layer gives it independent,
            # non-mouse motion while preserving the same sprite contract.
            if name == 'kitten':
                detail_cell, detail_box = 8, (338, 334, 65, 52)
            else:
                detail_cell, detail_box = DETAILS[name][0], (72, 68, 51, 47)
            details = sprite_at(atlas, boxes, detail_cell, detail_box)
        else:
            scene = fitted_background(folder / background_files[name])
            if name == 'torii':
                # Use the clean upper mist ribbon only; lower rows are cropped
                # out to avoid opaque specks in the lake layer.
                actor = generated_sprite(sprite_files[name], placements[name],
                                         crop=(0, 430, 1254, 680), opacity=0.72)
            elif name == 'lanterns':
                # Trim excess cord above the lantern pair so both paper bodies
                # remain within the round dial and above the date complication.
                actor = generated_sprite(sprite_files[name], placements[name],
                                         crop=(285, 180, 968, 1155))
            else:
                actor = generated_sprite(sprite_files[name], placements[name])
            details = woodblock_details(name)

        glass = feathered_glass(scene, style='woodblock')
        # Match the native +150px resting position in the static proof and icon.
        proof_actor = actor
        if name == 'sailboat':
            proof_actor = Image.new('RGBA', (SIZE, SIZE))
            proof_actor.alpha_composite(actor, (150, 0))
        proof_composed = assemble(scene, proof_actor, details)

        scene.save(OUT / f'scene_woodblock_{name}.png', optimize=True)
        actor.save(OUT / f'motion_woodblock_{name}.png', optimize=True)
        details.resize((225, 225), Image.Resampling.LANCZOS).save(
            OUT / f'drift_woodblock_{name}.png', optimize=True)
        glass.resize((225, 225), Image.Resampling.LANCZOS).save(
            OUT / f'glass_woodblock_{name}.png', optimize=True)
        proof_composed.resize((160, 160), Image.Resampling.LANCZOS).save(
            OUT / f'icon_scene_woodblock_{name}.png', optimize=True)

        dial = picker_preview(proof_composed, glass, clock, style='woodblock')
        dial = dial.resize((310, 310), Image.Resampling.LANCZOS)
        row, column = divmod(index, 4)
        x = column * 330 + (10 if row == 0 else 175)
        y = row * 370
        draw.text((x + 155, y + 18), f'{label} · {name.replace("_", " ").title()}',
                  font=font(16, True), fill='#f2e9df', anchor='mt')
        proof.paste(dial, (x, y + 47), dial)

    woodblock_ambient().save(OUT / 'woodblock_ambient.png', optimize=True)
    # Remove generated layers left behind by older pack revisions.
    for prefix in ('scene', 'motion', 'drift', 'glass', 'icon_scene'):
        for resource in OUT.glob(f'{prefix}_woodblock_*.png'):
            if resource.stem.removeprefix(f'{prefix}_woodblock_') not in STYLE_SCENES['woodblock']:
                resource.unlink()
    proof.save(PROOFS / 'woodblock.png', optimize=True)
    return proof


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
        if style == 'risograph' and name == 'coding':
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


def build(styles=None):
    OUT.mkdir(parents=True, exist_ok=True)
    PROOFS.mkdir(parents=True, exist_ok=True)
    selected_styles = list(styles) if styles is not None else list(STYLES)
    proofs = []
    for style in selected_styles:
        label = STYLES[style]
        if style == 'woodblock':
            proofs.append(build_woodblock_style(label))
        else:
            proofs.append(build_style(style, label))
    # A targeted pack import does not rewrite the other style's resources.
    if styles is not None:
        if selected_styles == ['woodblock']:
            risograph_proof = PROOFS / 'risograph.png'
            if risograph_proof.exists():
                with Image.open(risograph_proof) as image:
                    other_proof = image.convert('RGB')
                overview = Image.new('RGB', (1320, 385), '#10182c')
                overview.paste(proofs[0].resize((660, 370), Image.Resampling.LANCZOS),
                               (0, 0))
                overview.paste(other_proof.resize((660, 370), Image.Resampling.LANCZOS),
                               (660, 0))
                overview.save(PROOFS / 'all-packs.png', optimize=True)
        total_scenes = sum(len(STYLE_SCENES[style]) for style in selected_styles)
        print(f'Built {total_scenes} layered {", ".join(selected_styles)} scenes')
        return

    overview = Image.new('RGB', (1320, 385 * ((len(proofs) + 1) // 2)), '#10182c')
    for index, proof in enumerate(proofs):
        # Four columns × two rows per pack, scaled together for a readable index.
        overview.paste(proof.resize((660, 370), Image.Resampling.LANCZOS),
                       ((index % 2) * 660, (index // 2) * 385))
    overview.save(PROOFS / 'all-packs.png', optimize=True)
    total_scenes = sum(len(STYLE_SCENES[style]) for style in selected_styles)
    print(f'Built {total_scenes} layered scenes and {len(STYLES)} labeled proofs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--style', choices=STYLES,
                        help='Import only this style pack without rebuilding the other pack')
    args = parser.parse_args()
    build([args.style] if args.style else None)
