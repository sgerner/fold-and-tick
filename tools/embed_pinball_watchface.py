#!/usr/bin/env python3
"""Embed the generated pinball path in the WFF2 pixel-art scene branch."""
import bisect
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOTION = ROOT / 'artwork/packs/pixel_art/pinball-motion.json'
WATCHFACE = ROOT / 'watchface/src/main/res/raw/watchface.xml'
START = '<!-- GENERATED PINBALL MOTION START -->'
END = '<!-- GENERATED PINBALL MOTION END -->'


def number(value):
    return f'{float(value):.6f}'.rstrip('0').rstrip('.') or '0'


def xml_expression(value):
    return value.replace('&', '&amp;').replace('<', '&lt;')


def expression(frames, field, phase, offset=0):
    """Create a balanced piecewise-linear expression for the shared path."""
    times = [float(frame['t']) for frame in frames]
    values = [float(frame[field]) + offset for frame in frames]
    time_expr = f'([SECOND_MILLISECOND] % {phase})'

    def interval(low, high):
        if high - low == 1:
            t0, t1 = times[low], times[high]
            v0, v1 = values[low], values[high]
            slope = (v1 - v0) / (t1 - t0)
            return f'({number(v0)}+({time_expr}-{number(t0)})*{number(slope)})'
        middle = (low + high) // 2
        return f'({time_expr}<{number(times[middle])}?{interval(low,middle)}:{interval(middle,high)})'

    return interval(0, len(frames)-1)


def merge_timeline(motion):
    samples = motion['samples']
    times = [float(sample['t']) for sample in samples]
    frames = {float(sample['t']): dict(sample) for sample in samples}
    for event in motion['events']:
        t = float(event['t'])
        frame = frames.setdefault(t, {'t': t})
        frame.update({'x': float(event['x']), 'y': float(event['y'])})
        right = bisect.bisect_left(times, t)
        if right == 0:
            left_angle, right_angle = samples[0]['leftAngle'], samples[0]['rightAngle']
        elif right == len(times):
            left_angle, right_angle = samples[-1]['leftAngle'], samples[-1]['rightAngle']
        else:
            a, b = samples[right-1], samples[right]
            ratio = (t-float(a['t']))/(float(b['t'])-float(a['t']))
            left_angle = float(a['leftAngle'])+(float(b['leftAngle'])-float(a['leftAngle']))*ratio
            right_angle = float(a['rightAngle'])+(float(b['rightAngle'])-float(a['rightAngle']))*ratio
        frame['leftAngle'], frame['rightAngle'] = left_angle, right_angle
    return sorted(frames.values(), key=lambda frame: float(frame['t']))


def build_branch(motion):
    frames = merge_timeline(motion)
    duration = float(motion['duration'])
    time = f'([SECOND_MILLISECOND] % {number(duration)})'
    enabled = '[CONFIGURATION.motion_enabled] == "TRUE"'
    children = [
        '                        <PartImage x="0" y="0" width="450" height="450">',
        '                            <Image resource="scene_pixel_art_pinball" />',
        '                            <Variant target="alpha" value="0" mode="AMBIENT" />',
        '                        </PartImage>',
    ]
    for side, pivot, rest, field in (
            ('left', (60,370), 20, 'leftAngle'),
            ('right', (390,370), 160, 'rightAngle')):
        x, y = pivot
        children.extend([
            f'                        <PartImage x="0" y="0" width="450" height="450" pivotX="{number(x/450)}" pivotY="{number(y/450)}">',
            f'                            <Image resource="flipper_pixel_art_pinball_{side}" />',
            f'                            <Transform target="angle" value=\'{xml_expression(enabled + ' ? ' + expression(frames,field,duration,-rest) + ' : 0')}\' mode="TO" />',
            '                            <Variant target="alpha" value="0" mode="AMBIENT" />',
            '                        </PartImage>',
        ])
    children.extend([
        '                        <PartImage x="0" y="0" width="450" height="450">',
        '                            <Image resource="drift_pixel_art_pinball" />',
        f'                            <Transform target="x" value=\'{xml_expression(enabled + ' ? ' + expression(frames,"x",duration,-225) + ' : 0')}\' mode="TO" />',
        f'                            <Transform target="y" value=\'{xml_expression(enabled + ' ? ' + expression(frames,"y",duration,-350) + ' : 0')}\' mode="TO" />',
        f'                            <Transform target="alpha" value=\'{xml_expression(enabled + ' ? ' + flash_expression(motion) + ' : 0')}\' mode="TO" />',
        '                            <Variant target="alpha" value="0" mode="AMBIENT" />',
        '                        </PartImage>',
        '                        <PartImage x="0" y="0" width="450" height="450">',
        '                            <Image resource="motion_pixel_art_pinball" />',
        f'                            <Transform target="x" value=\'{xml_expression(enabled + ' ? ' + expression(frames,"x",duration,-225) + ' : 0')}\' mode="TO" />',
        f'                            <Transform target="y" value=\'{xml_expression(enabled + ' ? ' + expression(frames,"y",duration,-350) + ' : 0')}\' mode="TO" />',
        '                            <Variant target="alpha" value="0" mode="AMBIENT" />',
        '                        </PartImage>',
        '                        <PartImage x="0" y="0" width="450" height="450">',
        '                            <Image resource="glass_pixel_art_pinball" />',
        '                            <Variant target="alpha" value="0" mode="AMBIENT" />',
        '                        </PartImage>',
    ])
    return '\n'.join(children)


def flash_expression(motion):
    t = '([SECOND_MILLISECOND] % 10)'
    pulse = '0'
    # A collision spark begins at each measured contact and fades over 100ms.
    for event in reversed(motion['events']):
        start = float(event['t'])
        end = start + 0.1
        fade = f'clamp(({t}-{number(start)})*2550,0,255)'
        pulse = f'({t}>={number(start)}&&{t}<{number(end)}?{fade}:{pulse})'
    return pulse


def write():
    motion = json.loads(MOTION.read_text())
    xml = WATCHFACE.read_text()
    generated = f'{START}\n{build_branch(motion)}\n{END}'
    if START in xml and END in xml:
        xml = re.sub(re.escape(START)+r'.*?'+re.escape(END), generated, xml, count=1, flags=re.S)
    else:
        pattern = re.compile(r'<Compare expression="style_pixel_art">(?:(?!<Compare expression=|</Compare>).)*?<Image resource="scene_pixel_art_pinball" />.*?</Compare>', re.S)
        matches = list(pattern.finditer(xml))
        if len(matches) != 1:
            raise RuntimeError(f'Expected one Pixel pinball branch, found {len(matches)}')
        xml = xml[:matches[0].start()] + '<Compare expression="style_pixel_art">\n' + generated + '\n                    </Compare>' + xml[matches[0].end():]
    WATCHFACE.write_text(xml)


if __name__ == '__main__':
    write()
    print('Embedded the shared pinball motion path in watchface.xml')
