#!/usr/bin/env python3
"""Rebuild the ombré clock and its Origami and Woodblock variants."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'watchface/src/main/res/drawable-nodpi'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', default='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    scale = 4
    font = ImageFont.truetype(args.font, 128 * scale)
    for char in '0123456789:':
        width, height = (20 if char == ':' else 60), 96
        mask = Image.new('L', (width * scale, height * scale))
        if char == ':':
            draw = ImageDraw.Draw(mask)
            for y in (34, 61):
                draw.rounded_rectangle((7*scale,y*scale,13*scale,(y+7)*scale),radius=2*scale,fill=255)
        else:
            box = font.getbbox(char)
            glyph = Image.new('L', (box[2]-box[0],box[3]-box[1]))
            ImageDraw.Draw(glyph).text((-box[0],-box[1]),char,font=font,fill=255)
            glyph = glyph.resize((52*scale,84*scale),Image.Resampling.LANCZOS)
            mask.paste(glyph,(4*scale,6*scale))
        image = Image.new('RGBA',mask.size)
        draw = ImageDraw.Draw(image)
        # Deliberately restrained gradient keeps every digit readable over navy.
        stops = [(255,246,221),(255,221,216),(211,202,255)]
        for y in range(height*scale):
            t=y/(height*scale-1)*2; k=min(int(t),1);f=t-k
            color=tuple(round(stops[k][i]*(1-f)+stops[k+1][i]*f) for i in range(3))
            draw.line((0,y,width*scale,y),fill=(*color,255))
        image.putalpha(mask)
        image.resize((width,height),Image.Resampling.LANCZOS).save(OUT / f'clock_{"colon" if char == ":" else char}.png')

        paper = Image.new('RGBA', mask.size)
        paper_draw = ImageDraw.Draw(paper)
        paper_stops = [(255,248,225),(255,225,178),(255,195,153)]
        for y in range(height*scale):
            t=y/(height*scale-1)*2; k=min(int(t),1);f=t-k
            color=tuple(round(paper_stops[k][i]*(1-f)+paper_stops[k+1][i]*f) for i in range(3))
            paper_draw.line((0,y,width*scale,y),fill=(*color,255))
        crease = Image.new('RGBA', mask.size)
        crease_draw = ImageDraw.Draw(crease)
        crease_draw.polygon([(0,44*scale),(width*scale,34*scale),
                             (width*scale,38*scale),(0,48*scale)], fill=(113,65,39,22))
        crease_draw.line([(0,44*scale),(width*scale,34*scale)],
                         fill=(255,255,241,105),width=2*scale)
        paper = Image.alpha_composite(paper, crease)
        paper.putalpha(mask)
        paper.resize((width,height),Image.Resampling.LANCZOS).save(OUT / f'clock_origami_{"colon" if char == ":" else char}.png')

        wood = Image.new('RGBA', mask.size)
        wood_draw = ImageDraw.Draw(wood)
        wood_stops = [(255,249,229),(246,233,204),(222,218,199)]
        for y in range(height*scale):
            t=y/(height*scale-1)*2; k=min(int(t),1);f=t-k
            color=tuple(round(wood_stops[k][i]*(1-f)+wood_stops[k+1][i]*f) for i in range(3))
            wood_draw.line((0,y,width*scale,y),fill=(*color,255))
        grain = Image.new('RGBA', mask.size)
        grain_draw = ImageDraw.Draw(grain)
        for y in range(12 + ord(char) % 7, height, 16):
            grain_draw.line((0,y*scale,width*scale,(y-2)*scale),fill=(98,78,51,22),width=scale)
        wood = Image.alpha_composite(wood, grain)
        wood.putalpha(mask)
        wood.resize((width,height),Image.Resampling.LANCZOS).save(OUT / f'clock_woodblock_{"colon" if char == ":" else char}.png')
    print(f'Generated 33 clock glyphs in {OUT}')

if __name__ == '__main__':
    main()
