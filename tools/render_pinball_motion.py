#!/usr/bin/env python3
"""Render the shared pinball timeline for visual review."""
import json
from pathlib import Path
from PIL import Image
from bisect import bisect_right
from generate_art import add_watch_content, circular_crop, native_clock
ROOT=Path(__file__).resolve().parents[1]

def build():
    data=json.loads((ROOT/'artwork/packs/pixel_art/pinball-motion.json').read_text())
    folder=ROOT/'watchface/src/main/res/drawable-nodpi'
    def asset(name):
        return Image.open(folder/f'{name}.png').convert('RGBA').resize((450,450),Image.Resampling.NEAREST)
    background=asset('scene_pixel_art_pinball')
    ball=asset('motion_pixel_art_pinball')
    star=asset('drift_pixel_art_pinball')
    flippers=[asset(f'flipper_pixel_art_pinball_{side}') for side in ('left','right')]
    content=add_watch_content(Image.new('RGBA',(450,450)),Image.new('RGBA',(450,450)),native_clock(),style='pixel_art')
    frames=[]
    from embed_pinball_watchface import merge_timeline
    timeline=merge_timeline(data)
    timeline_times=[float(point['t']) for point in timeline]
    for sample in data['samples'][:-1]:
        t=float(sample['t'])
        right=bisect_right(timeline_times,t)
        a,b=timeline[max(0,right-1)],timeline[min(right,len(timeline)-1)]
        span=float(b['t'])-float(a['t'])
        ratio=0 if span<=0 else (t-float(a['t']))/span
        interp=lambda key: float(a[key])+(float(b[key])-float(a[key]))*ratio
        face=background.copy()
        for image,angle,rest,pivot in zip(flippers,[interp('leftAngle'),interp('rightAngle')],[20,160],[(60,370),(390,370)]):
            face.alpha_composite(image.rotate(-(angle-rest),resample=Image.Resampling.NEAREST,center=pivot))
        offset=(round(interp('x')-225),round(interp('y')-350))
        face.alpha_composite(ball,offset)
        if any(0 <= t-event['t'] < .1 for event in data['events']): face.alpha_composite(star,offset)
        face.alpha_composite(content)
        dial=circular_crop(face)
        frame=Image.new('RGB',(450,450),'#10182c'); frame.paste(dial,(0,0),dial)
        frames.append(frame)
    # One shared palette keeps the watch-like colors crisp and the GIF compact.
    sample_frames=frames[::10]
    palette_source=Image.new('RGB',(450,450*len(sample_frames)))
    for index,frame in enumerate(sample_frames): palette_source.paste(frame,(0,index*450))
    palette=palette_source.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(ROOT/'preview/styles/pinball-motion.gif',save_all=True,append_images=indexed[1:],duration=round(1000/data['fps']),loop=0,optimize=True)
    print('Rendered synchronized pinball motion proof')
if __name__=='__main__': build()
