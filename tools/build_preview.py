#!/usr/bin/env python3
"""Build a self-contained static preview, safe under a GitHub Pages project path."""
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]

def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'preview/index.html'
    target = output / 'index.html'
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
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
