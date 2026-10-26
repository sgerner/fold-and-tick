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
STYLES = ('origami', 'woodblock', 'risograph')
SCENES = ('bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora')


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
            for part in scene.findall('.//PartImage'):
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
                    self.assertEqual(float(stopped), float(part.attrib[transform.attrib['target']]))
                    self.assertEqual(part.find('Variant[@mode="AMBIENT"]').attrib['value'], '0')
            self.assertGreaterEqual(max(ranges), 20, scene.attrib['expression'])

    def test_bike_and_rocket_cross_both_dial_edges(self):
        for scene_id in ('bicycle', 'cosmos'):
            scene = FACE.find(f'./Scene/Condition/Compare[@expression="show_{scene_id}"]')
            actor = next(part for part in scene.findall('.//PartImage')
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
        parts = {part.find('Image').attrib['resource']: part for part in scene.findall('.//PartImage')}
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

    def test_style_selector_precedes_scene_and_keeps_all_scene_ids(self):
        configurations = FACE.findall('./UserConfigurations/ListConfiguration')
        self.assertEqual([configuration.attrib['id'] for configuration in configurations[:2]],
                         ['art_style', 'scene'])

        style = configurations[0]
        self.assertEqual(style.attrib['defaultValue'], 'origami')
        self.assertEqual([option.attrib['id'] for option in style], list(STYLES))
        self.assertEqual([option.attrib['icon'] for option in style],
                         ['icon_scene_cosmos'] + [f'icon_scene_{name}_cosmos' for name in STYLES[1:]])
        for option in style:
            icon_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{option.attrib['icon']}.png"
            width, height = struct.unpack('>II', icon_path.read_bytes()[16:24])
            self.assertEqual((width, height), (160, 160), option.attrib['icon'])

        scene = configurations[1]
        self.assertEqual([option.attrib['id'] for option in scene], [str(i) for i in range(8)])

    def test_scene_rotation_selects_one_scene_then_only_one_style_pack(self):
        scene_compares = FACE.findall('./Scene/Condition/Compare')
        self.assertEqual(len(scene_compares), len(SCENES))
        dates = (datetime(2024, 2, 29, 23, 59), datetime(2026, 10, 25, 16, 0))

        for selected_style in STYLES:
            for period in ('FIXED', 15, 60, 1440):
                for date in dates:
                    for selected_scene in range(len(SCENES)):
                        now = date + timedelta(minutes=period if period != 'FIXED' else 0)
                        minutes = (now - datetime(1970, 1, 1)) // timedelta(minutes=1)
                        values = {'YEAR': now.year, 'DAY_OF_YEAR': now.timetuple().tm_yday,
                                  'HOUR_0_23': now.hour, 'MINUTE': now.minute,
                                  'CONFIGURATION.rotation_period': period,
                                  'CONFIGURATION.scene': selected_scene}
                        if period == 'FIXED':
                            values['CONFIGURATION.scene'] = str(selected_scene)
                        active_scenes = [i for i, expression in enumerate(EXPRESSIONS)
                                         if evaluate_branch(expression, period != 'FIXED', values)]
                        expected_scene = (selected_scene if period == 'FIXED'
                                          else (minutes // period + selected_scene) % len(SCENES))
                        self.assertEqual(active_scenes, [expected_scene])

                        scene = scene_compares[expected_scene]
                        self.assertEqual(scene.attrib['expression'], f'show_{SCENES[expected_scene]}')
                        style_condition = scene.find('Condition')
                        style_expressions = {expression.attrib['name']: expression.text
                                             for expression in style_condition.findall('./Expressions/Expression')}
                        active_styles = [compare.attrib['expression'] for compare in style_condition.findall('Compare')
                                         if eval(re.sub(r'\[([^\]]+)\]',
                                                        lambda match: repr(selected_style),
                                                        style_expressions[compare.attrib['expression']].strip()),
                                                 {'__builtins__': {}})]
                        self.assertEqual(active_styles, [f'style_{selected_style}'])

                        branch = style_condition.find(f'Compare[@expression="style_{selected_style}"]')
                        resources = [part.find('Image').attrib['resource']
                                     for part in branch.findall('.//PartImage')]
                        scene_id = SCENES[expected_scene]
                        if selected_style == 'origami':
                            self.assertIn(f'scene_{scene_id}', resources)
                            self.assertIn(f'glass_{scene_id}', resources)
                        else:
                            origami = scene.find('./Condition/Compare[@expression="style_origami"]')
                            overlay_order = [part.find('Image').attrib['resource'].split('_', 1)[0]
                                            for part in origami.findall('PartImage')
                                            if part.find('Image').attrib['resource'].startswith(('motion_', 'drift_'))]
                            expected_resources = [f'scene_{selected_style}_{scene_id}']
                            expected_resources.extend(f'{kind}_{selected_style}_{scene_id}'
                                                      for kind in overlay_order)
                            expected_resources.append(f'glass_{selected_style}_{scene_id}')
                            self.assertEqual(resources, expected_resources)

    def test_new_style_art_pans_as_one_ambient_safe_canvas(self):
        for style in STYLES[1:]:
            for scene_id in SCENES:
                scene = FACE.find(f'./Scene/Condition/Compare[@expression="show_{scene_id}"]')
                branch = scene.find(f'./Condition/Compare[@expression="style_{style}"]')
                parts = {part.find('Image').attrib['resource']: part
                         for part in branch.findall('PartImage')}
                background = parts[f'scene_{style}_{scene_id}']
                motion = parts[f'motion_{style}_{scene_id}']
                drift = parts[f'drift_{style}_{scene_id}']
                glass = parts[f'glass_{style}_{scene_id}']

                self.assertEqual((background.attrib['x'], background.attrib['y'],
                                  background.attrib['width'], background.attrib['height']),
                                 ('-25', '-25', '500', '500'))
                self.assertEqual((glass.attrib['x'], glass.attrib['y'],
                                  glass.attrib['width'], glass.attrib['height']),
                                 ('0', '0', '450', '450'))
                self.assertEqual(len(parts), 4)

                origami = scene.find('./Condition/Compare[@expression="style_origami"]')
                original_parts = {part.find('Image').attrib['resource']: part
                                  for part in origami.findall('PartImage')}
                for kind, part in (('motion', motion), ('drift', drift)):
                    original = original_parts[f'{kind}_{scene_id}']
                    transforms = lambda image: {transform.attrib['target']: transform.attrib['value']
                                                for transform in image.findall('Transform')}
                    actual_transforms = transforms(part)
                    if scene_id != 'coding':
                        self.assertEqual(actual_transforms, transforms(original), (style, scene_id, kind))
                    self.assertEqual((part.attrib['x'], part.attrib['y'],
                                      part.attrib['width'], part.attrib['height']),
                                     ('0', '0', '450', '450'))
                    self.assertEqual(part.find('Variant[@target="alpha"][@mode="AMBIENT"]')
                                     .attrib['value'], '0')
                    for axis, expression in actual_transforms.items():
                        if axis not in ('x', 'y'):
                            continue
                        self.assertIn('[CONFIGURATION.motion_enabled] == "TRUE"', expression)
                        moving, frozen = expression.split('?', 1)[1].split(':', 1)
                        self.assertEqual(float(frozen), float(part.attrib[axis]))
                        positions = [eval(moving.replace('[SECOND_MILLISECOND]', str(sample / 10)).strip(),
                                          {'__builtins__': {}, 'sin': sin, 'cos': cos, 'rad': radians})
                                     for sample in range(200)]
                        self.assertGreaterEqual(max(positions) - min(positions), 12,
                                                (style, scene_id, kind, axis))

                if scene_id == 'bicycle' or (style, scene_id) == ('woodblock', 'coding'):
                    self.assertEqual(background.findall('Transform'), [])
                    continue
                for axis in ('x', 'y'):
                    transform = background.find(f'Transform[@target="{axis}"]')
                    expression = transform.attrib['value']
                    self.assertEqual(transform.attrib['mode'], 'TO')
                    self.assertIn('[CONFIGURATION.motion_enabled] == "TRUE"', expression)
                    moving, frozen = expression.split('?', 1)[1].split(':', 1)
                    self.assertEqual(float(frozen), -25)
                    positions = [eval(moving.replace('[SECOND_MILLISECOND]', str(sample / 10)).strip(),
                                      {'__builtins__': {}, 'sin': sin, 'cos': cos, 'rad': radians})
                                 for sample in range(180)]
                    self.assertGreaterEqual(max(positions) - min(positions), 23.9,
                                            (style, scene_id, axis))
                    self.assertLessEqual(min(positions), -36.9, (style, scene_id, axis))
                    self.assertGreaterEqual(max(positions), -13.1, (style, scene_id, axis))
                    self.assertEqual(background.find('Variant[@target="alpha"][@mode="AMBIENT"]')
                                     .attrib['value'], '0')
                self.assertEqual(glass.find('Variant[@target="alpha"][@mode="AMBIENT"]')
                                 .attrib['value'], '0')

    def test_new_style_assets_use_expected_texture_resolutions(self):
        for style in STYLES[1:]:
            for scene_id in SCENES:
                for kind in ('scene', 'motion', 'drift', 'glass'):
                    resource = f'{kind}_{style}_{scene_id}'
                    image_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f'{resource}.png'
                    data = image_path.read_bytes()
                    self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n', resource)
                    size = 225 if kind in ('drift', 'glass') else 450
                    self.assertEqual(struct.unpack('>II', data[16:24]), (size, size), resource)

    def test_road_camera_and_laptop_cursor_stay_attached(self):
        for style in STYLES[1:]:
            branch = FACE.find('./Scene/Condition/Compare[@expression="show_bicycle"]'
                               f'/Condition/Compare[@expression="style_{style}"]')
            background, actor = branch.findall('PartImage')[:2]
            self.assertEqual(background.findall('Transform'), [])
            self.assertIsNone(actor.find('Transform[@target="y"]'))
            self.assertIsNotNone(actor.find('Transform[@target="x"]'))
        branch = FACE.find('./Scene/Condition/Compare[@expression="show_coding"]'
                           '/Condition/Compare[@expression="style_woodblock"]')
        cursor = next(p for p in branch.findall('PartImage')
                      if p.find('Image').attrib['resource'] == 'drift_woodblock_coding')
        self.assertEqual([t.attrib['target'] for t in cursor.findall('Transform')], ['alpha'])
        expression = cursor.find('Transform').attrib['value'].split('?', 1)[1].split(':', 1)[0]
        values = [eval(expression.replace('[SECOND_MILLISECOND]', str(t)),
                       {'__builtins__': {}, 'floor': floor}) for t in (0, .5, 1, 1.5)]
        self.assertEqual(values, [0, 255, 0, 255])

    def test_available_intervals_match_contract(self):
        rotation = FACE.find("./UserConfigurations/ListConfiguration[@id='rotation_period']")
        self.assertEqual(rotation.attrib['defaultValue'], '60')
        self.assertEqual({o.attrib['id'] for o in rotation}, {'FIXED', *map(str, PERIODS)})

    def test_complication_rows_stay_centered_with_adaptive_padding(self):
        # Evaluate the expressions using WFF-supported functions only: Python's
        # min/max are deliberately unavailable (WFF provides clamp instead).
        for slot_id in (1, 2):
            complication = FACE.find(f'.//ComplicationSlot[@slotId="{slot_id}"]/Complication[@type="SHORT_TEXT"]')
            icon = complication.find('PartImage')
            text = complication.find('PartText')
            plate = complication.find('PartDraw/RoundRectangle')
            def attribute(element, name, value):
                transform = element.find(f'Transform[@target="{name}"]')
                if transform is None:
                    return float(element.attrib[name])
                expression = transform.attrib['value'].replace('[COMPLICATION.TEXT]', repr(value))
                return eval(expression, {'__builtins__': {}, 'textLength': len,
                                        'clamp': lambda x, lo, hi: max(lo, min(x, hi))})
            previous_width = 0
            for value in ('', '8', '80', '67°', '100%', '6,248', '1234567890'):
                ix, tx = attribute(icon, 'x', value), attribute(text, 'x', value)
                tw, px, pw = (attribute(text, 'width', value),
                              attribute(plate, 'x', value), attribute(plate, 'width', value))
                self.assertAlmostEqual(tx - ix - 24, 8)
                self.assertAlmostEqual((ix + tx + tw) / 2, 72.5)
                self.assertAlmostEqual(ix - px, 8)
                self.assertAlmostEqual(px + pw - tx - tw, 8)
                self.assertLessEqual(pw, 145)
                self.assertGreaterEqual(pw, previous_width)
                previous_width = pw

    def test_date_glass_stays_centered_and_caps_long_provider_text(self):
        for kind in ('SHORT_TEXT', 'LONG_TEXT'):
            plate = FACE.find(f'.//ComplicationSlot[@slotId="0"]/Complication[@type="{kind}"]/PartDraw/RoundRectangle')
            for title, value in [('', ''), ('SUN', 'OCT 25'), ('WED', 'SEPT 30'), ('', 'A'*100)]:
                def evaluate(target):
                    code = plate.find(f'Transform[@target="{target}"]').attrib['value']
                    code = code.replace('[COMPLICATION.TITLE]', repr(title)).replace('[COMPLICATION.TEXT]', repr(value))
                    return eval(code, {'__builtins__': {}, 'textLength': len,
                                       'clamp': lambda x, lo, hi: max(lo, min(x, hi))})
                width, x = evaluate('width'), evaluate('x')
                self.assertTrue(58 <= width <= 380)
                self.assertAlmostEqual(x + width / 2, 190)
                if len(value) == 100:
                    self.assertEqual(width, 380)


if __name__ == '__main__':
    unittest.main()
