#!/usr/bin/env python3
"""Build a self-contained static preview, safe under a GitHub Pages project path."""
from pathlib import Path
import argparse
import bisect
import json
import math
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
PINBALL_MOTION = ROOT / 'artwork/packs/pixel_art/pinball-motion.json'
PINBALL_CSS_MARKERS = ('/* PINBALL_MOTION_CSS_START */', '/* PINBALL_MOTION_CSS_END */')

def css_number(value, places=6):
    text = f'{value:.{places}f}'.rstrip('0').rstrip('.')
    return '0' if text in ('', '-0') else text

def render_pinball_motion_css(motion):
    """Render the shared pinball samples and exact contacts as offline CSS keyframes."""
    duration = float(motion['duration'])
    samples = motion['samples']
    events = motion.get('events', [])
    if not math.isfinite(duration) or duration <= 0 or len(samples) < 2:
        raise ValueError('Pinball motion needs a positive duration and at least two samples')

    sample_times = [float(sample['t']) for sample in samples]
    if sample_times[0] != 0 or not math.isclose(sample_times[-1], duration, abs_tol=1e-8):
        raise ValueError('Pinball samples must include t=0 and t=duration')
    if any(b <= a for a, b in zip(sample_times, sample_times[1:])):
        raise ValueError('Pinball sample times must be strictly increasing')
    for sample in samples:
        if not all(math.isfinite(float(sample[key])) for key in ('x', 'y', 'leftAngle', 'rightAngle')):
            raise ValueError('Pinball samples must contain finite positions and angles')

    frames = {float(sample['t']): dict(sample) for sample in samples}
    events_by_time = {}

    def interpolate_angle(field, t):
        right = bisect.bisect_left(sample_times, t)
        if right == 0:
            return float(samples[0][field])
        if right == len(samples):
            return float(samples[-1][field])
        before, after = samples[right - 1], samples[right]
        span = float(after['t']) - float(before['t'])
        ratio = (t - float(before['t'])) / span
        return float(before[field]) + (float(after[field]) - float(before[field])) * ratio

    for event in events:
        t = float(event['t'])
        if not math.isfinite(t) or t < 0 or t > duration:
            raise ValueError('Pinball contact times must lie inside the motion duration')
        frame = frames.setdefault(t, {})
        frame['t'] = t
        frame['x'] = float(event['x'])
        frame['y'] = float(event['y'])
        frame['leftAngle'] = interpolate_angle('leftAngle', t)
        frame['rightAngle'] = interpolate_angle('rightAngle', t)
        events_by_time.setdefault(t, []).append(event)

    timeline = sorted(frames.values(), key=lambda frame: float(frame['t']))
    timeline_times = [float(frame['t']) for frame in timeline]

    def interpolate_ball(t):
        right = bisect.bisect_left(timeline_times, t)
        if right == 0:
            return float(timeline[0]['x']), float(timeline[0]['y'])
        if right == len(timeline):
            return float(timeline[-1]['x']), float(timeline[-1]['y'])
        before, after = timeline[right - 1], timeline[right]
        if float(after['t']) == t:
            return float(after['x']), float(after['y'])
        ratio = (t - float(before['t'])) / (float(after['t']) - float(before['t']))
        x = float(before['x']) + (float(after['x']) - float(before['x'])) * ratio
        y = float(before['y']) + (float(after['y']) - float(before['y'])) * ratio
        return x, y

    def frame_percentage(frame):
        return css_number(100 * float(frame['t']) / duration, places=8) + '%'

    def ball_transform(frame):
        dx = (float(frame['x']) - 225) / 4.5
        dy = (float(frame['y']) - 350) / 4.5
        return f'translate3d({css_number(dx)}cqw, {css_number(dy)}cqw, 0)'

    def flipper_transform(frame, field, rest_angle):
        return f'rotate({css_number(float(frame[field]) - rest_angle)}deg)'

    def keyframes(name, transform):
        lines = [f'@keyframes {name} {{']
        for frame in timeline:
            t = float(frame['t'])
            contact_notes = events_by_time.get(t, [])
            note = ''.join(
                f" /* pinball event: {event['type']} t={css_number(t, 6)}s source=({css_number(float(event['x']), 3)},{css_number(float(event['y']), 3)}) */"
                for event in contact_notes
            )
            lines.append(f'  {frame_percentage(frame)} {{ transform: {transform(frame)}; }}{note}')
        lines.append('}')
        return '\n'.join(lines)

    impact_times = set(timeline_times)
    flash_ends = {}
    for event in events:
        impact_times.add(float(event['t']))
        end_time = (float(event['t']) + 0.1) % duration
        impact_times.add(end_time)
        flash_ends.setdefault(end_time, []).append(event)

    def impact_opacity(t):
        return max((
            max(0.0, 1.0 - ((t - float(event['t'])) % duration) / 0.1)
            for event in events
            if ((t - float(event['t'])) % duration) < 0.1
        ), default=0.0)

    impact_lines = ['@keyframes pixel-pinball-impact {']
    for t in sorted(impact_times):
        x, y = interpolate_ball(t)
        frame = {'t': t, 'x': x, 'y': y}
        note = ''.join(
            f" /* pinball event: {event['type']} t={css_number(t, 6)}s source=({css_number(float(event['x']), 3)},{css_number(float(event['y']), 3)}) */"
            for event in events_by_time.get(t, [])
        )
        note += ''.join(
            f" /* pinball flash end: {event['type']} start={css_number(float(event['t']), 6)}s after=0.1s */"
            for event in flash_ends.get(t, [])
        )
        impact_lines.append(
            f'  {frame_percentage(frame)} {{ transform: {ball_transform(frame)}; opacity: {css_number(impact_opacity(t))}; }}{note}'
        )
    impact_lines.append('}')

    return '\n'.join((
        f'.scene-layer[data-style="pixel_art"][data-scene="pinball"] {{ --pinball-duration: {css_number(duration, 6)}s; }}',
        '.watch-screen.motion-on:not(.ambient) .scene-layer[data-style="pixel_art"][data-scene="pinball"] .scene-motion { animation: pixel-pinball-ball var(--pinball-duration) linear infinite; }',
        '.watch-screen.motion-on:not(.ambient) .scene-layer[data-style="pixel_art"][data-scene="pinball"] .pinball-flipper-left { animation: pixel-pinball-left var(--pinball-duration) linear infinite; }',
        '.watch-screen.motion-on:not(.ambient) .scene-layer[data-style="pixel_art"][data-scene="pinball"] .pinball-flipper-right { animation: pixel-pinball-right var(--pinball-duration) linear infinite; }',
        '.watch-screen.motion-on:not(.ambient) .scene-layer[data-style="pixel_art"][data-scene="pinball"] .scene-drift { animation: pixel-pinball-impact var(--pinball-duration) linear infinite; }',
        keyframes('pixel-pinball-ball', ball_transform),
        keyframes('pixel-pinball-left', lambda frame: flipper_transform(frame, 'leftAngle', 20)),
        keyframes('pixel-pinball-right', lambda frame: flipper_transform(frame, 'rightAngle', 160)),
        '\n'.join(impact_lines),
    ))

def embed_pinball_motion_css(html):
    start, end = PINBALL_CSS_MARKERS
    marker_pattern = re.compile(re.escape(start) + r'.*?' + re.escape(end), re.S)
    if len(marker_pattern.findall(html)) != 1:
        raise ValueError('Preview must contain exactly one pinball motion CSS marker pair')
    css = render_pinball_motion_css(json.loads(PINBALL_MOTION.read_text(encoding='utf-8')))
    return marker_pattern.sub(start + '\n' + css + '\n    ' + end, html)

def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'preview/index.html'
    target = output / 'index.html'
    html = embed_pinball_motion_css(source.read_text(encoding='utf-8'))
    target.write_text(html, encoding='utf-8')
    favicon = ROOT / 'preview/favicon.svg'
    if favicon.resolve() != (output / 'favicon.svg').resolve():
        shutil.copy2(favicon, output / 'favicon.svg')
    assets = output / 'assets'
    assets.mkdir(exist_ok=True)
    sources = list((ROOT / 'watchface/src/main/res/drawable-nodpi').glob('*.png'))
    expected = {p.name for p in sources}
    for old in assets.glob('*.png'):
        if old.name not in expected:
            old.unlink()
    for asset in sources:
        shutil.copy2(asset, assets / asset.name)
    for name in ('LICENSE', 'NOTICE.md'):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / 'licenses', output / 'licenses', dirs_exist_ok=True)
    (output / '.nojekyll').write_text('')
    print(f'Staged {len(sources)} image assets in {output}')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'site')
    build(parser.parse_args().output)
