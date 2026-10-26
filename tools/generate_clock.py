#!/usr/bin/env python3
"""Rebuild the condensed, warm ombré bitmap clock (Pillow, DejaVu Sans Bold)."""
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
    print(f'Generated 11 clock glyphs in {OUT}')

if __name__ == '__main__':
    main()
