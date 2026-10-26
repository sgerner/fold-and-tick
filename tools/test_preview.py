"""Ensure the static preview works under a GitHub Pages project subdirectory."""
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

if __name__=='__main__':unittest.main()
