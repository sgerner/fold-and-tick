#!/usr/bin/env python3
"""Build clean Pixel art layers from deliberately simplified source illustrations."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from generate_art import add_watch_content, circular_crop, native_clock, font

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'artwork/packs/pixel_art'
OUT = ROOT / 'watchface/src/main/res/drawable-nodpi'
SCENES = {
    'velodrome': ('Velodrome', (135, 310, 180, 115), (45, 355, 65, 30), 'cobalt / coral / lemon'),
    'laundry_kitten': ('Laundry Kitten', (140, 320, 170, 115), (300, 338, 70, 65), 'mint / apricot / petrol'),
    'ramen': ('Ramen Bar', (145, 325, 160, 120), (195, 320, 60, 60), 'vermilion / amber / charcoal'),
    'pinball': ('Pinball', (216, 341, 18, 18), (204, 329, 42, 42), 'violet / cyan / yellow'),
    'airship': ('Airship Dock', (105, 20, 240, 95), (55, 340, 85, 60), 'sage / cream / brass'),
    'vinyl': ('Vinyl Lounge', (125, 325, 200, 110), (300, 332, 65, 65), 'burgundy / ochre / walnut'),
}


def sprite(path, placement):
    with Image.open(path) as source:
        art = source.convert('RGBA')
    bounds = art.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
    if not bounds:
        raise ValueError(f'Empty sprite: {path}')
    art = art.crop(bounds)
    x, y, width, height = placement
    scale = min(width / art.width, height / art.height)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.Resampling.NEAREST)
    art.putalpha(art.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    layer = Image.new('RGBA', (450, 450))
    layer.alpha_composite(art, (x + (width-art.width)//2, y + (height-art.height)//2))
    return layer


def pinball_flippers():
    layers = []
    for side, pivot, angle in [('left', (60, 370), 20), ('right', (390, 370), 160)]:
        layer = Image.new('RGBA', (225, 225))
        draw = ImageDraw.Draw(layer)
        def points(vertices):
            c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            return [(round((pivot[0]+x*c-y*s)/2), round((pivot[1]+x*s+y*c)/2)) for x,y in vertices]
        draw.polygon(points([(-10,-14),(78,-11),(100,-5),(100,5),(78,11),(-10,14)]),fill='#291544')
        draw.polygon(points([(-7,-10),(77,-8),(96,-4),(96,3),(77,7),(-7,10)]),fill='#ffcf39')
        draw.polygon(points([(0,5),(77,4),(94,0),(96,4),(77,9),(0,11)]),fill='#ed7c30')
        draw.line(points([(0,-7),(76,-5)]),fill='#fff19a',width=2)
        x,y=round(pivot[0]/2),round(pivot[1]/2)
        draw.ellipse((x-6,y-6,x+6,y+6),fill='#291544')
        draw.ellipse((x-4,y-4,x+4,y+4),fill='#ffcc3b')
        draw.rectangle((x-2,y-2,x+2,y+2),fill='#ed4768')
        layer.save(OUT/f'flipper_pixel_art_pinball_{side}.png',optimize=True)
        layers.append(layer.resize((450,450),Image.Resampling.NEAREST))
    return layers


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    flippers = pinball_flippers()
    clock = native_clock()
    proof = Image.new('RGB', (990, 740), '#10182c')
    draw = ImageDraw.Draw(proof)
    catalog = []
    for index, (scene_id, spec) in enumerate(SCENES.items()):
        label, actor_box, drift_box, palette = spec
        source = FOLDER / f'clean_sources/{scene_id}-background.png'
        if scene_id == 'pinball': source = FOLDER / 'clean_sources/pinball-playfield.png'
        with Image.open(source) as image:
            background = ImageOps.fit(image.convert('RGBA'), (225, 225), method=Image.Resampling.NEAREST)
        scene = background.resize((450, 450), Image.Resampling.NEAREST)
        actor = sprite(FOLDER / f'clean_sources/{scene_id}-actor.png', actor_box)
        drift = sprite(FOLDER / f'clean_sources/{scene_id}-detail.png', drift_box)
        # The art itself leaves a plain clock band; do not blur its pixel edges.
        glass = Image.new('RGBA', (450, 450))
        for prefix, image, size in (('scene',scene,225), ('motion',actor,225), ('drift',drift,225), ('glass',glass,112)):
            image.resize((size,size),Image.Resampling.NEAREST).save(OUT / f'{prefix}_pixel_art_{scene_id}.png',optimize=True)
        face = scene.copy()
        if scene_id == 'pinball':
            for flipper in flippers: face.alpha_composite(flipper)
        face.alpha_composite(actor)
        if scene_id != 'pinball': face.alpha_composite(drift)
        face.resize((160,160),Image.Resampling.NEAREST).save(OUT / f'icon_scene_pixel_art_{scene_id}.png',optimize=True)
        # Scale artwork and text separately: sharp art, smooth readable typography.
        dial = face.resize((310,310),Image.Resampling.NEAREST)
        content = add_watch_content(Image.new('RGBA',(450,450)),glass,clock,style='pixel_art')
        dial.alpha_composite(content.resize((310,310),Image.Resampling.LANCZOS))
        dial = circular_crop(dial)
        x,y=(index%3)*330+10,(index//3)*370
        draw.text((x+155,y+17),label,font=font(16,True),fill='#f2e9df',anchor='mt')
        proof.paste(dial,(x,y+47),dial)
        catalog.append({'id':scene_id,'label':label,'palette':palette,'background':str(source.relative_to(ROOT)),'actor_placement':actor_box,'drift_placement':drift_box,'sampling':'nearest-neighbor; no averaging or palette remapping'})
    active = {f'{prefix}_pixel_art_{scene}.png' for scene in SCENES for prefix in ('scene','motion','drift','glass','icon_scene')}
    active.update(f'flipper_pixel_art_pinball_{side}.png' for side in ('left','right'))
    for file in OUT.glob('*_pixel_art_*.png'):
        if file.name not in active: file.unlink()
    (FOLDER/'scene-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    proof.save(ROOT/'preview/styles/pixel_art.png',optimize=True)
    print('Built six clean Pixel art scenes and labeled watch proof')


if __name__ == '__main__':
    build()
