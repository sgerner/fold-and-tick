"""Check the actual WFF schedule arithmetic against Python's calendar.

Run: python3 -m unittest discover -s tools -p 'test_*.py'
These tests cover math/selection; device rendering is checked separately.
"""
from datetime import datetime, timedelta
from pathlib import Path
from math import floor, sin, cos, radians
import re
import struct
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FACE = ET.parse(ROOT / 'watchface/src/main/res/raw/watchface.xml')
EXPRESSIONS = [e.text for e in FACE.findall('./Scene/Condition/Expressions/Expression')]
PERIODS = (15, 30, 60, 180, 360, 1440)


def evaluate_branch(expression, scheduled, values):
    _, branches = expression.split('?', 1)
    fixed, rotating = branches.split(':', 1)
    code = rotating if scheduled else fixed
    code = re.sub(r'\[([^\]]+)\]', lambda m: repr(values[m[1]]), code)
    return eval(code.strip(), {'__builtins__': {}, 'floor': floor})


class RotationTest(unittest.TestCase):
    def test_fixed_scene_selection(self):
        self.assertEqual(len(EXPRESSIONS), 8)
        for selected in range(8):
            actual = [i for i, e in enumerate(EXPRESSIONS)
                      if evaluate_branch(e, False, {'CONFIGURATION.scene': str(selected)})]
            self.assertEqual(actual, [selected])

    def test_calendar_and_interval_boundaries(self):
        # Leap days, Gregorian century exceptions, and midnight/year transitions.
        dates = [datetime(2000, 2, 29, 23, 59), datetime(2024, 2, 28, 23, 59),
                 datetime(2026, 10, 25, 16, 0), datetime(2026, 12, 31, 23, 59),
                 datetime(2100, 3, 1, 0, 0)]
        for period in PERIODS:
            for date in dates:
                for minutes in (-1, 0, 1, period - 1, period, period + 1):
                    now = date + timedelta(minutes=minutes)
                    absolute_minutes = (now - datetime(1970, 1, 1)) // timedelta(minutes=1)
                    for selected in range(8):
                        values = {'YEAR': now.year, 'DAY_OF_YEAR': now.timetuple().tm_yday,
                                  'HOUR_0_23': now.hour, 'MINUTE': now.minute,
                                  'CONFIGURATION.rotation_period': period,
                                  'CONFIGURATION.scene': selected}
                        actual = [i for i, e in enumerate(EXPRESSIONS)
                                  if evaluate_branch(e, True, values)]
                        self.assertEqual(actual, [(absolute_minutes // period + selected) % 8],
                                         (now, period, selected))

    def test_selector_icons_fit_runtime_limit(self):
        # Wear OS rejects the entire face if a list icon exceeds 400px.
        for option in FACE.findall('./UserConfigurations/ListConfiguration/ListOption'):
            if 'icon' not in option.attrib:
                continue
            name = option.attrib['icon']
            data = (ROOT / 'watchface/src/main/res/drawable-nodpi' / f'{name}.png').read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('>II', data[16:24])
            self.assertLessEqual(max(width, height), 400, name)

    def test_scene_motion_is_visible_and_can_freeze(self):
        for scene in FACE.findall('./Scene/Condition/Compare'):
            ranges = []
            for part in scene.findall('PartImage'):
                for transform in part.findall('Transform'):
                    if transform.attrib['target'] not in ('x', 'y'):
                        continue
                    expression = transform.attrib['value']
                    self.assertEqual(transform.attrib.get('mode', 'TO'), 'TO')
                    self.assertIn('[SECOND_MILLISECOND]', expression)
                    condition, branches = expression.split('?', 1)
                    self.assertEqual(condition.strip(), '[CONFIGURATION.motion_enabled] == "TRUE"')
                    moving, stopped = branches.split(':', 1)
                    positions = []
                    for sample in range(120):
                        code = moving.replace('[SECOND_MILLISECOND]', str(sample / 10))
                        positions.append(eval(code.strip(), {'__builtins__': {}, 'sin': sin,
                                                            'cos': cos, 'rad': radians}))
                    ranges.append(max(positions) - min(positions))
                    self.assertEqual(float(stopped), 0)
                    self.assertEqual(part.find('Variant[@mode="AMBIENT"]').attrib['value'], '0')
            self.assertGreaterEqual(max(ranges), 20, scene.attrib['expression'])

    def test_bike_and_rocket_cross_both_dial_edges(self):
        for scene_id in ('bicycle', 'cosmos'):
            scene = FACE.find(f'./Scene/Condition/Compare[@expression="show_{scene_id}"]')
            actor = next(part for part in scene.findall('PartImage')
                         if part.find('Image').attrib['resource'] == f'motion_{scene_id}')
            expression = actor.find('Transform[@target="x"]').attrib['value']
            moving = expression.split('?', 1)[1].split(':', 1)[0]
            positions = [eval(moving.replace('[SECOND_MILLISECOND]', str(i / 10)).strip(),
                              {'__builtins__': {}}, {}) for i in range(100)]
            self.assertLessEqual(min(positions), -280, scene_id)
            self.assertGreaterEqual(max(positions), 400, scene_id)
            if scene_id == 'cosmos':
                y_expr = actor.find('Transform[@target="y"]').attrib['value']
                y_moving = y_expr.split('?', 1)[1].split(':', 1)[0]
                ys = [eval(y_moving.replace('[SECOND_MILLISECOND]', str(i / 10)).strip(),
                           {'__builtins__': {}}, {}) for i in range(100)]
                self.assertGreaterEqual(ys[0], 300)
                self.assertLessEqual(min(ys), -400)


    def test_kitten_and_mouse_move_independently(self):
        scene = FACE.find('./Scene/Condition/Compare[@expression="show_kitten"]')
        parts = {part.find('Image').attrib['resource']: part for part in scene.findall('PartImage')}
        cat = parts['motion_kitten'].find('Transform[@target="x"]').attrib['value']
        mouse = parts['drift_kitten'].find('Transform[@target="x"]').attrib['value']
        self.assertNotEqual(cat, mouse)
        def positions(expression):
            moving = expression.split('?', 1)[1].split(':', 1)[0]
            return [eval(moving.replace('[SECOND_MILLISECOND]', str(i/10)).strip(),
                         {'__builtins__': {}, 'sin': sin, 'cos': cos, 'rad': radians})
                    for i in range(100)]
        cats, mice = positions(cat), positions(mouse)
        self.assertLess(max(cats)-min(cats), 60)
        self.assertGreater(max(mice)-min(mice), 600)

    def test_scene_choices_replace_baking_with_forest(self):
        choices = FACE.findall('./UserConfigurations/ListConfiguration[@id="scene"]/ListOption')
        self.assertEqual([c.attrib['displayName'] for c in choices],
                         ['scene_bicycle', 'scene_forest', 'scene_coding', 'scene_kitten',
                          'scene_landscape', 'scene_cosmos', 'scene_ocean', 'scene_aurora'])

    def test_available_intervals_match_contract(self):
        rotation = FACE.find("./UserConfigurations/ListConfiguration[@id='rotation_period']")
        self.assertEqual(rotation.attrib['defaultValue'], '60')
        self.assertEqual({o.attrib['id'] for o in rotation}, {'FIXED', *map(str, PERIODS)})


if __name__ == '__main__':
    unittest.main()
