#!/usr/bin/env python3
"""Check that a built WFF APK has no bytecode and contains one face definition."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import argparse


def check(path):
    with ZipFile(path) as apk:
        names = apk.namelist()
        assert not any(n.endswith('.dex') for n in names), 'WFF APK must contain no executable DEX'
        # AAPT shortens physical res/ paths in release APKs. Discover the raw
        # document by its XML root rather than relying on its ZIP filename.
        faces=[]
        for name in names:
            if not name.endswith('.xml'):
                continue
            try:
                document=ET.fromstring(apk.read(name))
            except ET.ParseError:
                continue
            if document.tag=='WatchFace':
                faces.append(document)
        assert len(faces)==1, 'Exactly one WFF definition is required'
        assert 'resources.arsc' in names, 'Android resource table is required'
    print('Resource-only APK verified: no DEX; one WFF definition')
    # Google's memory evaluator resolves image names through the resource table
    # and checks resource retention for both normal and shortened APK paths.

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    check(parser.parse_args().apk)
