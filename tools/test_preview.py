"""Ensure the static preview works under a GitHub Pages project subdirectory."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from build_preview import ROOT, build, render_pinball_motion_css

class Images(HTMLParser):
    def __init__(self):
        super().__init__(); self.sources=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'img': self.sources.extend(v for k,v in attrs if k=='src')

class PreviewControls(HTMLParser):
    def __init__(self):
        super().__init__(); self.styles=[]; self.scenes=[]; self.style_select=None; self._in_style_select=False; self._option=None
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'select' and attrs.get('id') == 'styleSelect':
            self.style_select=attrs; self._in_style_select=True
        if tag == 'option' and self._in_style_select: self._option=[attrs.get('value'), '']
        if tag == 'button' and 'scene-card' in attrs.get('class', '').split(): self.scenes.append(attrs.get('data-scene'))
    def handle_data(self, data):
        if self._option is not None: self._option[1] += data.strip()
    def handle_endtag(self, tag):
        if tag == 'option' and self._option is not None:
            self.styles.append(tuple(self._option)); self._option=None
        if tag == 'select': self._in_style_select=False

class PreviewTest(unittest.TestCase):
    def test_site_is_self_contained_and_has_no_baking_images(self):
        with tempfile.TemporaryDirectory() as folder:
            output=build(Path(folder))
            html=(output/'index.html').read_text()
            images=Images();images.feed(html)
            for src in images.sources:
                self.assertTrue(src.startswith('./assets/') or src.startswith('assets/'),src)
                self.assertTrue((output/src).is_file(),src)
            names={p.name for p in (output/'assets').glob('*.png')}
            self.assertFalse(any('koi' in name.lower() for name in names))
            self.assertIn('scene_forest.png',names)
            self.assertIn('origami_ambient.png',names)
            self.assertIn('clock_origami_0.png',names)
            self.assertIn('clock_origami_colon.png',names)
            self.assertIn('woodblock_ambient.png',names)
            self.assertIn('clock_woodblock_0.png',names)
            self.assertIn('clock_woodblock_colon.png',names)
            self.assertIn('flipper_pixel_art_pinball_left.png', names)
            self.assertIn('flipper_pixel_art_pinball_right.png', names)
            for scene in ('bicycle', 'crane', 'kitten', 'torii', 'lanterns', 'sailboat', 'moon_rabbit'):
                for layer in ('scene', 'motion', 'drift', 'glass', 'icon_scene'):
                    self.assertIn(f'{layer}_woodblock_{scene}.png', names)
            for scene in ('bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora'):
                for layer in ('scene', 'motion', 'drift', 'glass', 'icon_scene'):
                    self.assertIn(f'{layer}_bioluminescent_{scene}.png', names)
            for scene in ('velodrome', 'laundry_kitten', 'ramen', 'pinball', 'airship', 'vinyl'):
                for layer in ('scene', 'motion', 'drift', 'glass', 'icon_scene'):
                    self.assertIn(f'{layer}_pixel_art_{scene}.png', names)
            self.assertFalse(any('orrery' in name.lower() for name in names))
            self.assertFalse(any('baking' in n for n in names))
            self.assertIn('releases/latest/download/Fold-and-Tick.apk',html)
            self.assertNotIn('Eight tiny worlds orbit a calm',html)
            self.assertIn('adb install -r Fold-and-Tick.apk',html)
    def test_rebuild_prunes_retired_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            output=build(Path(folder)); old=output/'assets/scene_baking.png';old.write_bytes(b'old')
            build(output);self.assertFalse(old.exists())

    def test_pinball_preview_embeds_shared_motion_and_contact_frames(self):
        motion_path = ROOT / 'artwork/packs/pixel_art/pinball-motion.json'
        motion = json.loads(motion_path.read_text(encoding='utf-8'))
        duration = float(motion['duration'])
        fps = float(motion['fps'])
        samples = motion['samples']
        events = motion['events']
        self.assertGreater(duration, 0)
        self.assertEqual(samples[0]['t'], 0)
        self.assertAlmostEqual(samples[-1]['t'], duration)
        self.assertGreater(len(samples), 2)
        for before, after in zip(samples, samples[1:]):
            self.assertAlmostEqual(float(after['t']) - float(before['t']), 1 / fps, places=6)
        for key, rest in (('x', 225), ('y', 350), ('leftAngle', 20), ('rightAngle', 160)):
            self.assertAlmostEqual(float(samples[0][key]), rest)
            self.assertAlmostEqual(float(samples[-1][key]), rest)

        event_types = {event['type'] for event in events}
        self.assertTrue({'bumper_1', 'bumper_2', 'bumper_3', 'rail', 'left_flipper', 'right_flipper'} <= event_types)
        self.assertTrue(all(0 <= float(event['t']) <= duration for event in events))

        css = render_pinball_motion_css(motion)
        self.assertIn(f'--pinball-duration: {duration:g}s', css)
        self.assertIn('.watch-screen.motion-on:not(.ambient)', css)
        self.assertIn('.pinball-flipper-left { animation: pixel-pinball-left', css)
        self.assertIn('.pinball-flipper-right { animation: pixel-pinball-right', css)
        self.assertIn('.scene-drift { animation: pixel-pinball-impact', css)
        self.assertIn('@keyframes pixel-pinball-impact {', css)
        self.assertIn('0% { transform: translate3d(0cqw, 0cqw, 0); }', css)
        self.assertIn('100% { transform: translate3d(0cqw, 0cqw, 0); }', css)
        for event_type in event_types:
            self.assertIn(f'pinball event: {event_type}', css)
        ball_css = css.split('@keyframes pixel-pinball-ball {', 1)[1].split('@keyframes pixel-pinball-left {', 1)[0]
        impact_css = css.split('@keyframes pixel-pinball-impact {', 1)[1]
        for event in events:
            event_time = f'{float(event["t"]):.6f}'.rstrip('0').rstrip('.')
            event_x = f'{float(event["x"]):.3f}'.rstrip('0').rstrip('.')
            event_y = f'{float(event["y"]):.3f}'.rstrip('0').rstrip('.')
            note = f'pinball event: {event["type"]} t={event_time}s source=({event_x},{event_y})'
            ball_line = next((line for line in ball_css.splitlines() if note in line), None)
            impact_line = next((line for line in impact_css.splitlines() if note in line), None)
            self.assertIsNotNone(ball_line, note)
            self.assertIsNotNone(impact_line, note)
            ball_transform = re.search(r'transform: ([^;]+);', ball_line).group(1)
            impact_transform = re.search(r'transform: ([^;]+);', impact_line).group(1)
            self.assertEqual(impact_transform, ball_transform)
            self.assertIn('opacity: 1;', impact_line)
            flash_end = f'pinball flash end: {event["type"]} start={event_time}s after=0.1s'
            self.assertIn(flash_end, impact_css)
        source_html = (ROOT / 'preview/index.html').read_text(encoding='utf-8')
        self.assertIn('.scene-layer[data-style="pixel_art"][data-scene="pinball"] .scene-drift { opacity: 0; }', source_html)

        with tempfile.TemporaryDirectory() as folder:
            output = build(Path(folder))
            html = (output / 'index.html').read_text(encoding='utf-8')
        self.assertIn(css, html)
        self.assertIn('flipper_pixel_art_pinball_left.png', html)
        self.assertIn('flipper_pixel_art_pinball_right.png', html)

    def test_style_picker_keeps_scene_catalog_and_asset_contract(self):
        html=(ROOT/'preview/index.html').read_text()
        controls=PreviewControls(); controls.feed(html)
        self.assertEqual(controls.styles, [
            ('origami', 'Origami'), ('woodblock', 'Woodblock'), ('risograph', 'Risograph'),
            ('bioluminescent', 'Bioluminescent'), ('pixel_art', 'Pixel art'), ('all', 'Shuffle all styles')
        ])
        self.assertEqual(controls.scenes, [
            'bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora'
        ])
        self.assertEqual(html.count('class="favorite-toggle"'), 8)
        self.assertEqual(html.count('type="checkbox" checked'), 8)
        self.assertEqual(controls.style_select.get('aria-describedby'), 'styleDescription')
        self.assertIn('label for="styleSelect">Art style</label>', html)
        self.assertIn('style: "origami"', html)
        self.assertIn('hasOwnProperty.call(artStyles, saved.style)', html)
        self.assertIn('kind + "_" + style + "_" + scene.id', html)
        self.assertIn('style === "woodblock" ? "?v=woodblock-2026-10-kitten-butterfly" : ""', html)
        self.assertIn('sceneAssetPaths[style + ":" + kind + ":" + scene.id]', html)
        self.assertIn('hasOwnProperty.call(sceneAssetPaths, key)', html)
        self.assertIn('favorites: [true, true, true, true, true, true, true, true]', html)
        self.assertIn('woodblockFavorites: [true, true, true, true, true, true, true]', html)
        self.assertIn('woodScene: 0', html)
        self.assertIn('var woodblockScenes = [', html)
        self.assertIn('var pixelArtScenes = [', html)
        for scene_id, label in (
            ('velodrome', 'Velodrome'), ('laundry_kitten', 'Laundry Kitten'), ('ramen', 'Ramen Bar'),
            ('pinball', 'Pinball'), ('airship', 'Airship Dock'), ('vinyl', 'Vinyl Lounge')
        ):
            self.assertIn('id: "' + scene_id + '"', html)
            self.assertIn('label: "' + label + '"', html)
        self.assertIn('pixel_art: pixelArtScenes', html)
        self.assertIn('pixelScene: 0', html)
        self.assertIn('saved.pixelScene', html)
        self.assertIn('state.pixelScene = index;', html)
        self.assertIn('state.pixelScene = nextIndex;', html)
        self.assertIn('sceneCatalogs[style] || origamiScenes', html)
        self.assertNotIn('orrery', html.lower())
        self.assertIn('.scene-card[hidden], .favorite-option[hidden] { display: none !important; }', html)
        for scene_id in ('bicycle', 'crane', 'kitten', 'torii', 'lanterns', 'sailboat', 'moon_rabbit'):
            self.assertIn('id: "' + scene_id + '"', html)
        self.assertNotIn('id: "koi"', html)
        self.assertIn('saved.woodScene - 1', html)
        self.assertIn('saved.woodblockFavorites.length === 8', html)
        self.assertIn('woodblock-2026-10-kitten-butterfly', html)
        self.assertIn('getRotationSequence()', html)
        self.assertIn('if (enabled.length === 0) return [getCurrentSceneIndex()];', html)
        self.assertIn('enabled.findIndex(function (index) { return index >= getCurrentSceneIndex(); })', html)
        self.assertIn('var scheduledIndex = sequence.indexOf(getScheduledScene(now));', html)
        self.assertIn('state.woodScene = nextIndex;', html)
        self.assertIn('clockGlyphPaths[displayStyle][character]', html)
        self.assertIn('var clockKey = displayStyle + ":" + timeValue;', html)
        self.assertIn('clock_origami_9.png', html)
        self.assertIn('clock_woodblock_9.png', html)
        self.assertIn('clock_woodblock_colon.png', html)
        self.assertIn('24 + date.length * 20', html)
        self.assertIn('chip.querySelector(".chip-value").textContent.length * 18.5', html)
        self.assertIn('Math.min(169, 50 + valueWidth)', html)
        self.assertIn('grid-template-columns: repeat(2, 45.187%)', html)
        self.assertIn('width: 83.111%', html)
        self.assertIn('font-size: 7.111cqw', html)
        self.assertIn('linear-gradient(rgba(255, 233, 191, .2196), rgba(232, 188, 149, .1412))', html)
        self.assertIn('linear-gradient(rgba(233, 223, 192, .2196), rgba(163, 188, 190, .1412))', html)
        self.assertIn('color: #fff4e8;', html)
        self.assertIn('rgba(223, 235, 247, .2196)', html)
        self.assertIn('stroke: #fff4e8;', html)
        self.assertIn('filter: brightness(0) invert(97%) sepia(4%)', html)
        self.assertNotIn('backdrop-filter: blur(7px)', html)
        self.assertNotIn('filter: blur(1px)', html)
        self.assertIn('origami_ambient.png', html)
        self.assertIn('woodblock_ambient.png', html)
        self.assertIn('scene-arrive .8s linear', html)
        self.assertIn('state.style === "origami" || state.style === "woodblock"', html)
        self.assertIn('(state.style === "origami" || state.style === "woodblock")', html)
        self.assertIn('state.motion && !motionPreference.matches', html)
        self.assertIn('Folded paper worlds, warm colors, and playful character motion.', html)
        self.assertIn('--actor-animation: forest-hop-origami', html)
        self.assertIn('--actor-animation: landscape-sun-origami; --actor-duration: 6s', html)
        self.assertIn('--actor-animation: ocean-whale-traverse; --actor-duration: 14s', html)
        self.assertIn('--actor-animation: aurora-breathe; --actor-duration: 4s', html)
        self.assertIn('animation: mouse-run-origami 8s linear infinite', html)
        self.assertIn('animation: landscape-cloud-origami 10s linear infinite', html)
        self.assertIn('translate3d(-71.111cqw, 0, 0)', html)
        self.assertIn('translate3d(93.333cqw, 0, 0)', html)
        self.assertIn('translate3d(-30cqw, 1.778cqw, 0)', html)
        self.assertIn('animation: aurora-curtains-origami 10s linear infinite', html)
        self.assertIn('animation: forest-firefly-origami 10s linear infinite', html)
        self.assertIn('scene-pan 24s ease-in-out infinite alternate', html)
        for choreography in (
            'pixel-velodrome 10s linear infinite',
            'pixel-laundry-kitten 3s linear infinite',
            'pixel-ramen 5s linear infinite',
            'pixel-airship 12s linear infinite',
            'pixel-vinyl 4s linear infinite',
            'translateX(-73.333cqw)',
            'translateY(-6.667cqw)',
            'translateY(-8.444cqw)',
            'translate3d(2.667cqw, -2.222cqw, 0)',
        ):
            self.assertIn(choreography, html)
        for choreography in (
            'woodblock-bicycle-traverse 10s linear infinite',
            'woodblock-bicycle-drift 10s linear infinite',
            'woodblock-crane 12s linear infinite',
            'woodblock-crane-drift 9s linear infinite',
            'woodblock-kitten-x 6s linear infinite',
            'woodblock-kitten-y 3s linear infinite',
            'woodblock-torii 11s linear infinite',
            'woodblock-torii-drift 8s linear infinite',
            'woodblock-lanterns 9s linear infinite',
            'woodblock-lantern-rise 5s linear infinite',
            'woodblock-lantern-pulse 2s linear infinite',
            'woodblock-sailboat-x 14s linear infinite',
            'woodblock-sailboat-y 5s linear infinite',
            'woodblock-moon-rabbit 3s linear infinite',
            'translateX(100.222cqw)',
        ):
            self.assertIn(choreography, html)
        self.assertIn('prefers-reduced-motion: reduce', html)
        self.assertIn('.watch-screen.motion-on:not(.ambient) .scene-layer .scene-motion', html)
        self.assertIn('.watch-screen.motion-on:not(.ambient) .scene-layer .scene-drift', html)
        self.assertIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-cursor', html)
        self.assertNotIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-motion-wrap', html)
        self.assertNotIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-drift', html)
        self.assertIn('.scene-layer[data-scene="kitten"] .scene-motion-wrap', html)
        self.assertIn('.scene-layer[data-style="origami"][data-scene="kitten"] .scene-motion-wrap', html)
        self.assertIn('kitten-lunge 3s linear infinite', html)
        self.assertIn('.scene-layer[data-scene="cosmos"] .scene-drift', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="crane"]', html)
        self.assertNotIn('.scene-layer[data-style="woodblock"][data-scene="koi"]', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="torii"]', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="lanterns"]', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="sailboat"]', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="moon_rabbit"]', html)
        self.assertIn('.scene-layer[data-style="woodblock"][data-scene="sailboat"] .scene-motion-wrap[data-static-offset="true"]', html)
        self.assertIn('transform: translateX(33.333cqw);', html)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is unavailable for JavaScript syntax validation')
    def test_preview_javascript_parses(self):
        html=(ROOT/'preview/index.html').read_text()
        script=re.search(r'<script\b[^>]*>(.*?)</script\b[^>]*>', html, re.S | re.I).group(1)
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8') as source:
            source.write(script); source.flush()
            result=subprocess.run(['node', '--check', source.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is unavailable for preview interaction checks')
    def test_style_switch_and_cycle_preserve_scene_selection_and_rotation(self):
        html=(ROOT/'preview/index.html').read_text()
        script=re.search(r'<script\b[^>]*>(.*?)</script\b[^>]*>', html, re.S | re.I).group(1)
        harness=r'''const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const previewScript = fs.readFileSync(process.argv[1], 'utf8');
class Element {
  constructor(attrs = {}) {
    this.attrs = { ...attrs }; this.style = {}; this.listeners = {}; this.children = [];
    this.hidden = Object.prototype.hasOwnProperty.call(attrs, 'hidden');
    this.checked = Object.prototype.hasOwnProperty.call(attrs, 'checked');
    this.disabled = false; this.value = attrs.value || ''; this.textContent = ''; this.parentElement = null;
    this.src = attrs.src || '';
    const classes = new Set((attrs.class || '').split(/\s+/).filter(Boolean));
    this.classList = {
      add: name => classes.add(name), remove: name => classes.delete(name),
      toggle: (name, on) => on ? classes.add(name) : classes.delete(name),
      contains: name => classes.has(name)
    };
  }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return name === 'src' ? this.src : (this.attrs[name] ?? null); }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  dispatch(name) { for (const fn of this.listeners[name] || []) fn({}); }
  querySelector(selector) { return (this.queries || {})[selector]; }
  replaceChildren() { this.children = []; }
  appendChild(child) { this.children.push(child); }
}
const sceneIds = ['bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora'];
const cardImages = sceneIds.map(() => new Element({ src: '' }));
const cardNames = sceneIds.map(() => new Element({}));
const cards = sceneIds.map((id, index) => {
  const image = cardImages[index];
  const card = new Element({ class: 'scene-card', 'data-scene': id });
  card.queries = { '.scene-thumb img': image, '.scene-name': cardNames[index] };
  return card;
});
const sceneArt = new Element({});
const ambientMotif = new Element({ src: './assets/origami_ambient.png', hidden: true });
const artImages = {
  '.scene-background': new Element({ src: './assets/scene_bicycle.png' }),
  '.scene-motion': new Element({ src: './assets/motion_bicycle.png' }),
  '.scene-cursor': new Element({ src: './assets/blink_coding.png', hidden: true }),
  '.scene-drift': new Element({ src: './assets/drift_bicycle.png' }),
  '.scene-glass': new Element({ src: './assets/glass_bicycle.png' }),
  '.pinball-flipper-left': new Element({ src: './assets/flipper_pixel_art_pinball_left.png', hidden: true }),
  '.pinball-flipper-right': new Element({ src: './assets/flipper_pixel_art_pinball_right.png', hidden: true }),
  '.scene-motion-wrap': new Element({})
};
sceneArt.queries = artImages;
const ids = {};
for (const id of ['watchCase', 'watchScreen', 'timeText', 'dateText', 'activeSceneLabel',
  'rotationStatus', 'modeBadge', 'modeNote', 'rotationSelect', 'styleSelect',
  'styleDescription', 'ambientToggle', 'motionToggle', 'cycleButton', 'resetButton',
  'favoritesGroup', 'favoritesTitle', 'favoritesHint']) ids[id] = new Element({});
ids.sceneArt = sceneArt;
ids.ambientMotif = ambientMotif;
const favoriteNames = sceneIds.map(() => new Element({}));
const favoriteOptions = sceneIds.map((id, index) => {
  const option = new Element({});
  option.queries = { '.favorite-name': favoriteNames[index] };
  const toggle = new Element({ 'data-scene': id, type: 'checkbox', checked: '' });
  toggle.parentElement = option;
  return { option, toggle };
});
const favoriteToggles = favoriteOptions.map(option => option.toggle);
const chips = ['82%', '6,248'].map(value => {
  const chip = new Element({});
  chip.queries = { '.chip-value': new Element({}), '.chip-copy': new Element({}) };
  chip.queries['.chip-value'].textContent = value;
  return chip;
});
ids.rotationSelect.value = '60'; ids.styleSelect.value = 'origami';
ids.watchScreen.classList.add('motion-on');
const modes = ['auto', 'manual'].map(value => new Element({ 'data-mode': value }));
const hours = [12, 24].map(value => new Element({ 'data-hours': String(value) }));
const sizes = [41, 45].map(value => new Element({ 'data-size': String(value) }));
const allImages = [...Object.values(artImages).filter(image => image instanceof Element && image.src !== undefined), ...cardImages, ambientMotif];
const previewColumn = new Element({});
const sceneGrid = new Element({});
let fixedNow = new Date(2026, 9, 25, 12, 14, 0);
let intervalCallback = null;
const document = {
  getElementById: id => ids[id],
  createElement: () => new Element({}),
  querySelector: selector => selector === '.preview-column' ? previewColumn : (selector === '.scene-grid' ? sceneGrid : null),
  querySelectorAll: selector => ({
    '.mode-option': modes, '.hour-option': hours, '.size-option': sizes,
    '.scene-card': cards, '.complication': chips,
    '.favorite-toggle': favoriteToggles,
    '.scene-layer img, .scene-thumb img, #ambientMotif': allImages
  })[selector] || []
};
const data = { mode: 'manual', scene: 2, rotation: 30, favorites: [true, false, true, false, true, true, false, true], hours: 24, size: 41 };
let saved = JSON.stringify(data);
const motionPreference = { matches: false };
const window = {
  matchMedia: () => motionPreference, setInterval: fn => { intervalCallback = fn; return 0; }, setTimeout: () => 1, clearTimeout: () => {},
  localStorage: { getItem: () => saved, setItem: (_key, value) => { saved = value; } }
};
class FixedDate extends Date {
  constructor(...args) { super(...(args.length ? args : [fixedNow.getTime()])); }
}
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(ids.styleSelect.value, 'origami');
assert.equal(cards[2].getAttribute('aria-pressed'), 'true');
assert.equal(artImages['.scene-background'].src, './assets/scene_coding.png');
assert.equal(ids.favoritesGroup.hidden, false);
assert.deepEqual(favoriteToggles.map(toggle => toggle.checked), [true, false, true, false, true, true, false, true]);
assert.equal(ambientMotif.hidden, true);
assert.equal(ids.timeText.children[0].src, './assets/clock_origami_1.png');
assert.equal(ids.timeText.children[2].src, './assets/clock_origami_colon.png');
assert.equal(ids.watchCase.getAttribute('data-size'), '41');
ids.motionToggle.dispatch('click');
assert.equal(JSON.parse(saved).motion, false); assert.equal(ids.watchScreen.classList.contains('motion-on'), false);
ids.motionToggle.dispatch('click');
assert.equal(JSON.parse(saved).motion, true); assert.equal(ids.watchScreen.classList.contains('motion-on'), true);
motionPreference.matches = true;
ids.motionToggle.dispatch('click');
assert.equal(JSON.parse(saved).motion, true);
motionPreference.matches = false;
ids.ambientToggle.dispatch('click');
assert.equal(JSON.parse(saved).ambient, true); assert.equal(ids.watchScreen.classList.contains('ambient'), true);
assert.equal(ambientMotif.hidden, false);
ids.ambientToggle.dispatch('click');
assert.equal(JSON.parse(saved).ambient, false); assert.equal(ids.watchScreen.classList.contains('ambient'), false);
assert.equal(ambientMotif.hidden, true);
ids.styleSelect.value = 'woodblock'; ids.styleSelect.dispatch('change');
let state = JSON.parse(saved);
assert.equal(state.style, 'woodblock'); assert.equal(state.scene, 2); assert.equal(state.woodScene, 0); assert.equal(state.rotation, 30);
assert.equal(ids.favoritesGroup.hidden, false);
assert.equal(ids.favoritesTitle.textContent, 'Woodblock rotation');
assert.equal(ids.favoritesHint.textContent, 'Scenes included in auto mode');
assert.equal(favoriteToggles.slice(0, 7).every(toggle => toggle.checked), true);
assert.equal(favoriteToggles[7].checked, false);
assert.equal(ids.timeText.children[0].src, './assets/clock_woodblock_1.png');
assert.equal(ids.timeText.children[2].src, './assets/clock_woodblock_colon.png');
const woodblockCache = '?v=woodblock-2026-10-kitten-butterfly';
assert.equal(artImages['.scene-background'].src, './assets/scene_woodblock_bicycle.png' + woodblockCache);
assert.equal(artImages['.scene-glass'].src, './assets/glass_woodblock_bicycle.png' + woodblockCache);
assert.equal(artImages['.scene-motion'].src, './assets/motion_woodblock_bicycle.png' + woodblockCache);
assert.equal(artImages['.scene-drift'].src, './assets/drift_woodblock_bicycle.png' + woodblockCache);
assert.equal(cardImages[0].src, './assets/icon_scene_woodblock_bicycle.png' + woodblockCache);
assert.deepEqual(cardNames.slice(0, 7).map(name => name.textContent), ['Bicycle', 'Crane', 'Kitten', 'Torii', 'Lanterns', 'Sailboat', 'Moon rabbit']);
assert.deepEqual(favoriteNames.slice(0, 7).map(name => name.textContent), ['Bicycle', 'Crane', 'Kitten', 'Torii', 'Lanterns', 'Sailboat', 'Moon rabbit']);
assert.equal(cards.filter(card => !card.hidden).length, 7);
assert.equal(favoriteOptions.filter(option => !option.option.hidden).length, 7);
assert.equal(sceneGrid.getAttribute('aria-label'), 'Choose a Woodblock scene');
for (const [index, id] of ['bicycle', 'crane', 'kitten', 'torii', 'lanterns', 'sailboat', 'moon_rabbit'].entries()) {
  cards[index].dispatch('click');
  assert.equal(sceneArt.getAttribute('data-scene'), id);
  assert.equal(artImages['.scene-background'].src, './assets/scene_woodblock_' + id + '.png' + woodblockCache);
  assert.equal(artImages['.scene-glass'].src, './assets/glass_woodblock_' + id + '.png' + woodblockCache);
  assert.equal(artImages['.scene-motion'].src, './assets/motion_woodblock_' + id + '.png' + woodblockCache);
  assert.equal(artImages['.scene-drift'].src, './assets/drift_woodblock_' + id + '.png' + woodblockCache);
  assert.equal(cardImages[index].src, './assets/icon_scene_woodblock_' + id + '.png' + woodblockCache);
  assert.equal(artImages['.scene-cursor'].hidden, true);
  if (id === 'sailboat') {
    assert.equal(artImages['.scene-motion-wrap'].getAttribute('data-static-offset'), 'false');
    ids.motionToggle.dispatch('click');
    assert.equal(JSON.parse(saved).motion, false);
    assert.equal(artImages['.scene-motion-wrap'].getAttribute('data-static-offset'), 'true');
    ids.motionToggle.dispatch('click');
    assert.equal(JSON.parse(saved).motion, true);
    assert.equal(artImages['.scene-motion-wrap'].getAttribute('data-static-offset'), 'false');
  }
}
assert.equal(JSON.parse(saved).woodScene, 6);
assert.equal(ids.activeSceneLabel.textContent, 'Moon rabbit');
ids.styleSelect.value = 'origami'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'coding');
assert.equal(cards[2].getAttribute('aria-pressed'), 'true');
assert.equal(favoriteToggles[1].checked, false);
cards[3].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
assert.equal(JSON.parse(saved).scene, 3);
favoriteToggles.forEach(toggle => { toggle.checked = false; toggle.dispatch('change'); });
modes[0].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
assert.match(ids.modeNote.textContent, /No Origami scenes/);
assert.equal(ids.cycleButton.disabled, true);
favoriteToggles[5].checked = true; favoriteToggles[5].dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'cosmos');
assert.match(ids.modeNote.textContent, /One Origami scene/);
favoriteToggles[2].checked = true; favoriteToggles[2].dispatch('change');
assert.equal(ids.cycleButton.disabled, false);
ids.cycleButton.dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'coding');
for (const [index, favorite] of [true, false, true, false, true, true, false, true].entries()) {
  if (favoriteToggles[index].checked !== favorite) {
    favoriteToggles[index].checked = favorite; favoriteToggles[index].dispatch('change');
  }
}
modes[1].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
ids.styleSelect.value = 'risograph'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
assert.equal(ids.favoritesGroup.hidden, true);
assert.equal(artImages['.scene-background'].src, './assets/scene_risograph_kitten.png');
modes[0].dispatch('click');
const risoScene = sceneArt.getAttribute('data-scene');
ids.cycleButton.dispatch('click');
assert.notEqual(sceneArt.getAttribute('data-scene'), risoScene);
for (let i = 0; i < sceneIds.length - 1; i++) ids.cycleButton.dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), risoScene);
assert.equal(artImages['.scene-background'].src, './assets/scene_risograph_' + risoScene + '.png');
for (const style of ['bioluminescent']) {
  ids.styleSelect.value = style; ids.styleSelect.dispatch('change');
  assert.equal(ids.favoritesGroup.hidden, true);
  modes[1].dispatch('click');
  for (const [index, id] of sceneIds.entries()) {
    cards[index].dispatch('click');
    assert.equal(sceneArt.getAttribute('data-scene'), id);
    assert.equal(artImages['.scene-background'].src, './assets/scene_' + style + '_' + id + '.png');
    assert.equal(artImages['.scene-motion'].src, './assets/motion_' + style + '_' + id + '.png');
  }
  cards[3].dispatch('click');
  modes[0].dispatch('click');
  const minute = Math.floor(Date.UTC(2026, 9, 25) / 86400000) * 1440 + 12 * 60 + 14;
  assert.equal(sceneArt.getAttribute('data-scene'), sceneIds[(3 + Math.floor(minute / 30)) % sceneIds.length]);
  const first = sceneArt.getAttribute('data-scene');
  for (let i = 0; i < sceneIds.length; i++) ids.cycleButton.dispatch('click');
  assert.equal(sceneArt.getAttribute('data-scene'), first);
}
const pixelSceneIds = ['velodrome', 'laundry_kitten', 'ramen', 'pinball', 'airship', 'vinyl'];
const pixelSceneNames = ['Velodrome', 'Laundry Kitten', 'Ramen Bar', 'Pinball', 'Airship Dock', 'Vinyl Lounge'];
ids.styleSelect.value = 'pixel_art'; ids.styleSelect.dispatch('change');
assert.equal(ids.favoritesGroup.hidden, true);
assert.equal(cards.filter(card => !card.hidden).length, 6);
assert.equal(cards.filter(card => card.hidden).length, 2);
assert.deepEqual(cardNames.slice(0, 6).map(name => name.textContent), pixelSceneNames);
assert.equal(sceneArt.getAttribute('data-scene'), 'velodrome');
assert.equal(artImages['.scene-background'].src, './assets/scene_pixel_art_velodrome.png');
assert.equal(artImages['.scene-motion'].src, './assets/motion_pixel_art_velodrome.png');
assert.equal(artImages['.pinball-flipper-left'].hidden, true);
assert.equal(artImages['.pinball-flipper-right'].hidden, true);
cards[3].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'pinball');
assert.equal(artImages['.scene-motion'].src, './assets/motion_pixel_art_pinball.png');
assert.equal(artImages['.pinball-flipper-left'].src, './assets/flipper_pixel_art_pinball_left.png');
assert.equal(artImages['.pinball-flipper-right'].src, './assets/flipper_pixel_art_pinball_right.png');
assert.equal(artImages['.pinball-flipper-left'].hidden, false);
assert.equal(artImages['.pinball-flipper-right'].hidden, false);
cards[4].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'airship');
assert.equal(artImages['.pinball-flipper-left'].hidden, true);
assert.equal(artImages['.pinball-flipper-right'].hidden, true);
const origamiSelection = JSON.parse(saved).scene;
cards[4].dispatch('click');
assert.equal(JSON.parse(saved).pixelScene, 4);
assert.equal(JSON.parse(saved).scene, origamiSelection);
assert.equal(sceneArt.getAttribute('data-scene'), 'airship');
assert.equal(cards[4].getAttribute('aria-pressed'), 'true');
ids.styleSelect.value = 'origami'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), sceneIds[origamiSelection]);
ids.styleSelect.value = 'pixel_art'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'airship');
modes[0].dispatch('click');
const minute = Math.floor(Date.UTC(2026, 9, 25) / 86400000) * 1440 + 12 * 60 + 14;
const scheduledPixelScene = pixelSceneIds[(4 + Math.floor(minute / 30)) % pixelSceneIds.length];
assert.equal(sceneArt.getAttribute('data-scene'), scheduledPixelScene);
ids.cycleButton.dispatch('click');
assert.equal(JSON.parse(saved).pixelScene, 4);
const cycledPixelScene = pixelSceneIds[(pixelSceneIds.indexOf(scheduledPixelScene) + 1) % pixelSceneIds.length];
assert.equal(sceneArt.getAttribute('data-scene'), cycledPixelScene);
ids.styleSelect.value = 'woodblock'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
assert.equal(favoriteToggles.slice(0, 7).every(toggle => toggle.checked), true);
assert.equal(favoriteToggles[7].checked, false);
favoriteToggles.forEach(toggle => { toggle.checked = false; toggle.dispatch('change'); });
assert.equal(JSON.parse(saved).woodblockFavorites.every(favorite => !favorite), true);
assert.deepEqual(JSON.parse(saved).favorites, [true, false, true, false, true, true, false, true]);
modes[0].dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
assert.match(ids.modeNote.textContent, /No Woodblock scenes/);
assert.equal(ids.cycleButton.disabled, true);
ids.cycleButton.dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
favoriteToggles[1].checked = true; favoriteToggles[1].dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'crane');
assert.equal(ids.cycleButton.disabled, true);
favoriteToggles[6].checked = true; favoriteToggles[6].dispatch('change');
assert.equal(ids.cycleButton.disabled, false);
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
ids.cycleButton.dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), 'crane');
ids.rotationSelect.value = '15'; ids.rotationSelect.dispatch('change');
fixedNow = new Date(2026, 9, 25, 12, 15, 0); intervalCallback();
assert.equal(sceneArt.classList.contains('scheduled-transition'), true);
ids.ambientToggle.dispatch('click');
assert.equal(ambientMotif.src, './assets/woodblock_ambient.png');
assert.equal(ambientMotif.hidden, false);
assert.equal(JSON.parse(saved).woodScene, 6);
modes[1].dispatch('click');
ids.styleSelect.value = 'origami'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
assert.deepEqual(JSON.parse(saved).favorites, [true, false, true, false, true, true, false, true]);
ids.styleSelect.value = 'woodblock'; ids.styleSelect.dispatch('change');
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
assert.equal(ambientMotif.hidden, false);
state = JSON.parse(saved);
assert.equal(state.scene, 3); assert.equal(state.woodScene, 6);
assert.equal(state.favorites.filter(Boolean).length, 5);
assert.deepEqual(state.woodblockFavorites, [false, true, false, false, false, false, true]);
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(favoriteToggles[1].checked, true);
assert.equal(favoriteToggles[6].checked, true);
assert.equal(favoriteToggles.filter(toggle => toggle.checked).length, 2);
assert.equal(sceneArt.getAttribute('data-scene'), 'moon_rabbit');
saved = JSON.stringify({ style: 'woodblock', mode: 'manual', scene: 3, rotation: 60, favorites: [true, false, false, true, true, true, true, true] });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(sceneArt.getAttribute('data-scene'), 'bicycle');
assert.equal(JSON.parse(saved).woodScene, undefined);
assert.equal(favoriteToggles.slice(0, 7).every(toggle => toggle.checked), true);
assert.equal(favoriteToggles[7].checked, false);
assert.equal(ids.styleSelect.value, 'woodblock');
saved = JSON.stringify({ style: 'woodblock', mode: 'manual', woodScene: 6, woodblockFavorites: [true, false, true, false, true, false, true, false] });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(sceneArt.getAttribute('data-scene'), 'sailboat');
assert.equal(JSON.parse(saved).woodScene, 5);
assert.deepEqual(JSON.parse(saved).woodblockFavorites, [true, false, false, true, false, true, false]);
saved = JSON.stringify({ style: 'woodblock', mode: 'manual', woodScene: 2, woodblockFavorites: [true, true, false, true, true, true, true, true] });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(sceneArt.getAttribute('data-scene'), 'kitten');
assert.equal(JSON.parse(saved).woodScene, 2);
assert.deepEqual(JSON.parse(saved).woodblockFavorites, [true, true, true, true, true, true, true]);
saved = JSON.stringify({ style: 'woodblock', mode: 'manual', woodScene: 4, woodblockFavorites: [true, false, true, false, true, false, true] });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(sceneArt.getAttribute('data-scene'), 'lanterns');
assert.equal(JSON.parse(saved).woodScene, 4);
assert.deepEqual(JSON.parse(saved).woodblockFavorites, [true, false, true, false, true, false, true]);
saved = JSON.stringify({ style: 'pixel_art', mode: 'manual', scene: 2, pixelScene: 4, rotation: 60 });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(ids.styleSelect.value, 'pixel_art');
assert.equal(sceneArt.getAttribute('data-scene'), 'airship');
assert.equal(cards.filter(card => !card.hidden).length, 6);
assert.equal(JSON.parse(saved).scene, 2);
assert.equal(JSON.parse(saved).pixelScene, 4);
saved = JSON.stringify({ style: 'orrery', mode: 'manual', scene: 4, rotation: 60 });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(ids.styleSelect.value, 'origami');
assert.equal(sceneArt.getAttribute('data-style'), 'origami');
assert.equal(sceneArt.getAttribute('data-scene'), 'landscape');
saved = JSON.stringify({ style: 'all', mode: 'manual', rotation: 15,
  favorites: Array(8).fill(false), woodblockFavorites: Array(7).fill(false) });
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(ids.styleSelect.value, 'all');
assert.equal(modes[1].disabled, true);
assert.equal(sceneGrid.hidden, true);
assert.equal(ids.favoritesGroup.hidden, true);
assert.equal(ids.rotationSelect.disabled, false);
const shuffled = JSON.parse(previewScript.match(/var allStyleScenes = (.*?);/)[1]);
const localMinute = Math.floor(Date.UTC(fixedNow.getFullYear(), fixedNow.getMonth(), fixedNow.getDate()) / 86400000) * 1440 + fixedNow.getHours() * 60 + fixedNow.getMinutes();
const startSlot = Math.floor(localMinute / 15);
for (let offset = 0; offset < 37; offset++) {
  const slot = startSlot + offset;
  const expected = shuffled[(slot * 17 + Math.floor(slot / 37) * 13) % 37];
  assert.equal(sceneArt.getAttribute('data-style'), expected.style);
  assert.equal(sceneArt.getAttribute('data-scene'), expected.scene);
  assert.equal(ids.watchScreen.getAttribute('data-style'), expected.style);
  const clockPrefix = ['origami', 'woodblock'].includes(expected.style) ? `clock_${expected.style}_` : 'clock_';
  assert.ok(ids.timeText.children[0].src.includes(clockPrefix));
  if (offset < 36) ids.cycleButton.dispatch('click');
}
'''
        with tempfile.TemporaryDirectory() as folder:
            script_path=Path(folder)/'preview.js'; script_path.write_text(script)
            result=subprocess.run(['node', '-e', harness, str(script_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__=='__main__':unittest.main()
