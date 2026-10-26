"""Ensure the static preview works under a GitHub Pages project subdirectory."""
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from build_preview import ROOT, build

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
            self.assertIn('scene_forest.png',names)
            self.assertFalse(any('baking' in n for n in names))
            self.assertIn('releases/latest/download/Fold-and-Tick.apk',html)
            self.assertNotIn('Eight tiny worlds orbit a calm',html)
            self.assertIn('adb install -r Fold-and-Tick.apk',html)
    def test_rebuild_prunes_retired_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            output=build(Path(folder)); old=output/'assets/scene_baking.png';old.write_bytes(b'old')
            build(output);self.assertFalse(old.exists())

    def test_style_picker_keeps_scene_catalog_and_asset_contract(self):
        html=(ROOT/'preview/index.html').read_text()
        controls=PreviewControls(); controls.feed(html)
        self.assertEqual(controls.styles, [
            ('origami', 'Origami'), ('woodblock', 'Woodblock'), ('risograph', 'Risograph')
        ])
        self.assertEqual(controls.scenes, [
            'bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora'
        ])
        self.assertEqual(controls.style_select.get('aria-describedby'), 'styleDescription')
        self.assertIn('label for="styleSelect">Art style</label>', html)
        self.assertIn('style: "origami"', html)
        self.assertIn('hasOwnProperty.call(artStyles, saved.style)', html)
        self.assertIn('kind + "_" + style + "_" + scene.id', html)
        self.assertIn('sceneAssetPaths[style + ":" + kind + ":" + scene.id]', html)
        self.assertIn('hasOwnProperty.call(sceneAssetPaths, key)', html)
        self.assertIn('getSceneAssetPath("icon_scene", state.style, scenes[index].id)', html)
        self.assertIn('return (getScheduledScene(now) + previewOffset) % scenes.length;', html)
        self.assertIn('state.scene = (state.scene + 1) % scenes.length;', html)
        self.assertIn('scene-pan 24s ease-in-out infinite alternate', html)
        self.assertIn('prefers-reduced-motion: reduce', html)
        self.assertIn('.watch-screen.motion-on:not(.ambient) .scene-layer .scene-motion', html)
        self.assertIn('.watch-screen.motion-on:not(.ambient) .scene-layer .scene-drift', html)
        self.assertIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-cursor', html)
        self.assertNotIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-motion-wrap', html)
        self.assertNotIn('.scene-layer[data-style]:not([data-style="origami"]) .scene-drift', html)
        self.assertIn('.scene-layer[data-scene="kitten"] .scene-motion-wrap', html)
        self.assertIn('.scene-layer[data-scene="cosmos"] .scene-drift', html)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is unavailable for JavaScript syntax validation')
    def test_preview_javascript_parses(self):
        html=(ROOT/'preview/index.html').read_text()
        script=re.search(r'<script\b[^>]*>(.*?)</script\s*>', html, re.S | re.I).group(1)
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8') as source:
            source.write(script); source.flush()
            result=subprocess.run(['node', '--check', source.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is unavailable for preview interaction checks')
    def test_style_switch_and_cycle_preserve_scene_selection_and_rotation(self):
        html=(ROOT/'preview/index.html').read_text()
        script=re.search(r'<script\b[^>]*>(.*?)</script\s*>', html, re.S | re.I).group(1)
        harness=r'''const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const previewScript = fs.readFileSync(process.argv[1], 'utf8');
class Element {
  constructor(attrs = {}) {
    this.attrs = { ...attrs }; this.style = {}; this.listeners = {}; this.children = [];
    this.hidden = Object.prototype.hasOwnProperty.call(attrs, 'hidden');
    this.disabled = false; this.value = attrs.value || ''; this.textContent = '';
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
const cards = sceneIds.map((id, index) => {
  const image = cardImages[index];
  const card = new Element({ class: 'scene-card', 'data-scene': id });
  card.queries = { '.scene-thumb img': image };
  return card;
});
const sceneArt = new Element({});
const artImages = {
  '.scene-background': new Element({ src: './assets/scene_bicycle.png' }),
  '.scene-motion': new Element({ src: './assets/motion_bicycle.png' }),
  '.scene-cursor': new Element({ src: './assets/blink_coding.png', hidden: true }),
  '.scene-drift': new Element({ src: './assets/drift_bicycle.png' }),
  '.scene-glass': new Element({ src: './assets/glass_bicycle.png' }),
  '.scene-motion-wrap': new Element({})
};
sceneArt.queries = artImages;
const ids = {};
for (const id of ['watchCase', 'watchScreen', 'timeText', 'dateText', 'activeSceneLabel',
  'rotationStatus', 'modeBadge', 'modeNote', 'rotationSelect', 'styleSelect',
  'styleDescription', 'ambientToggle', 'motionToggle', 'cycleButton', 'resetButton']) ids[id] = new Element({});
ids.sceneArt = sceneArt;
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
const allImages = [...Object.values(artImages).filter(image => image instanceof Element && image.src !== undefined), ...cardImages];
const previewColumn = new Element({});
const document = {
  getElementById: id => ids[id],
  createElement: () => new Element({}),
  querySelector: selector => selector === '.preview-column' ? previewColumn : null,
  querySelectorAll: selector => ({
    '.mode-option': modes, '.hour-option': hours, '.size-option': sizes,
    '.scene-card': cards, '.complication': chips,
    '.scene-layer img, .scene-thumb img': allImages
  })[selector] || []
};
const data = { mode: 'manual', scene: 2, rotation: 30 };
let saved = JSON.stringify(data);
const motionPreference = { matches: false };
const window = {
  matchMedia: () => motionPreference, setInterval: () => 0,
  localStorage: { getItem: () => saved, setItem: (_key, value) => { saved = value; } }
};
class FixedDate extends Date {
  constructor(...args) { super(...(args.length ? args : [2026, 9, 25, 12, 0, 0])); }
}
vm.runInNewContext(previewScript, { window, document, Date: FixedDate });
assert.equal(ids.styleSelect.value, 'origami');
assert.equal(cards[2].getAttribute('aria-pressed'), 'true');
assert.equal(artImages['.scene-background'].src, './assets/scene_coding.png');
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
ids.ambientToggle.dispatch('click');
assert.equal(JSON.parse(saved).ambient, false); assert.equal(ids.watchScreen.classList.contains('ambient'), false);
ids.styleSelect.value = 'woodblock'; ids.styleSelect.dispatch('change');
let state = JSON.parse(saved);
assert.equal(state.style, 'woodblock'); assert.equal(state.scene, 2); assert.equal(state.rotation, 30);
assert.equal(artImages['.scene-background'].src, './assets/scene_woodblock_coding.png');
assert.equal(artImages['.scene-glass'].src, './assets/glass_woodblock_coding.png');
assert.equal(artImages['.scene-motion'].src, './assets/motion_woodblock_coding.png');
assert.equal(artImages['.scene-drift'].src, './assets/drift_woodblock_coding.png');
assert.equal(artImages['.scene-motion-wrap'].hidden, false); assert.equal(artImages['.scene-motion'].hidden, false);
assert.equal(artImages['.scene-drift'].hidden, false); assert.equal(artImages['.scene-cursor'].hidden, true);
assert.equal(cardImages[7].src, './assets/icon_scene_woodblock_aurora.png');
ids.cycleButton.dispatch('click');
state = JSON.parse(saved);
assert.equal(state.scene, 3); assert.equal(state.style, 'woodblock');
assert.equal(artImages['.scene-background'].src, './assets/scene_woodblock_kitten.png');
assert.equal(cards[3].getAttribute('aria-pressed'), 'true');
modes[0].dispatch('click');
const scheduledScene = sceneArt.getAttribute('data-scene');
ids.cycleButton.dispatch('click');
assert.notEqual(sceneArt.getAttribute('data-scene'), scheduledScene);
ids.styleSelect.value = 'risograph'; ids.styleSelect.dispatch('change');
state = JSON.parse(saved);
assert.equal(state.style, 'risograph'); assert.equal(state.rotation, 30); assert.equal(state.scene, 3);
assert.equal(sceneArt.getAttribute('data-scene'), scheduledScene);
for (let i = 0; i < sceneIds.length; i++) ids.cycleButton.dispatch('click');
assert.equal(sceneArt.getAttribute('data-scene'), scheduledScene);
assert.equal(artImages['.scene-background'].src, './assets/scene_risograph_' + scheduledScene + '.png');
for (const style of ['origami', 'woodblock', 'risograph']) {
  ids.styleSelect.value = style; ids.styleSelect.dispatch('change');
  for (let index = 0; index < sceneIds.length; index++) {
    const sceneId = sceneIds[index];
    cards[index].dispatch('click');
    const prefix = style === 'origami' ? '' : style + '_';
    assert.equal(sceneArt.getAttribute('data-scene'), sceneId);
    assert.equal(artImages['.scene-motion'].src, './assets/motion_' + prefix + sceneId + '.png');
    assert.equal(artImages['.scene-drift'].src, './assets/drift_' + prefix + sceneId + '.png');
    assert.equal(artImages['.scene-motion-wrap'].hidden, false);
    assert.equal(artImages['.scene-motion'].hidden, false);
    assert.equal(artImages['.scene-drift'].hidden, false);
    assert.equal(artImages['.scene-cursor'].hidden, !(style === 'origami' && sceneId === 'coding'));
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            script_path=Path(folder)/'preview.js'; script_path.write_text(script)
            result=subprocess.run(['node', '-e', harness, str(script_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__=='__main__':unittest.main()
