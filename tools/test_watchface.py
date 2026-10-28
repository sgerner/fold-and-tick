"""Check the actual WFF schedule arithmetic against Python's calendar.

Run: python3 -m unittest discover -s tools -p 'test_*.py'
These tests cover math/selection; device rendering is checked separately.
"""
from datetime import datetime, timedelta
from pathlib import Path
from math import floor, sin, cos, radians
from functools import lru_cache
import json
import re
import struct
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FACE = ET.parse(ROOT / 'watchface/src/main/res/raw/watchface.xml')
EXPRESSIONS = [e.text for e in FACE.findall('./Scene/Condition/Expressions/Expression')[:8]]
PERIODS = (15, 30, 60, 180, 360, 1440)
STYLES = ('origami', 'woodblock', 'risograph', 'bioluminescent', 'pixel_art')
SCENES = ('bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora')
WOODBLOCK_SCENES = ('bicycle', 'crane', 'kitten', 'torii', 'lanterns', 'sailboat', 'moon_rabbit')
WOODBLOCK_SHOW_IDS = ('bicycle', 'forest', 'kitten', 'landscape', 'cosmos', 'ocean', 'aurora')
PIXEL_SCENES = ('velodrome', 'laundry_kitten', 'ramen', 'pinball', 'airship', 'vinyl')
PIXEL_SHOW_IDS = ('bicycle', 'forest', 'coding', 'kitten', 'landscape', 'cosmos')


def _complication_plate(complication, branch='Default'):
    return complication.find(f'Condition/{branch}/PartDraw/RoundRectangle')


def _strip_outer_parentheses(expression):
    expression = expression.strip()
    while expression.startswith('(') and expression.endswith(')'):
        depth = 0
        quoted = False
        wraps = True
        for index, character in enumerate(expression):
            if character == '"':
                quoted = not quoted
            if quoted:
                continue
            if character == '(':
                depth += 1
            elif character == ')':
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    wraps = False
                    break
        if not wraps:
            break
        expression = expression[1:-1].strip()
    return expression


def _pythonize_ternary(expression):
    expression = _strip_outer_parentheses(expression)
    depth = 0
    quoted = False
    question = None
    for index, character in enumerate(expression):
        if character == '"':
            quoted = not quoted
        if quoted:
            continue
        if character == '(':
            depth += 1
        elif character == ')':
            depth -= 1
        elif depth == 0 and character == '?' and question is None:
            question = index
            break
    if question is not None:
        depth = 0
        quoted = False
        nested_questions = 0
        for index in range(question + 1, len(expression)):
            character = expression[index]
            if character == '"':
                quoted = not quoted
            if quoted:
                continue
            if character == '(':
                depth += 1
            elif character == ')':
                depth -= 1
            elif depth == 0 and character == '?':
                nested_questions += 1
            elif depth == 0 and character == ':':
                if nested_questions:
                    nested_questions -= 1
                else:
                    condition = _pythonize_ternary(expression[:question])
                    positive = _pythonize_ternary(expression[question + 1:index])
                    negative = _pythonize_ternary(expression[index + 1:])
                    return f'({positive} if {condition} else {negative})'
        raise AssertionError(f'Unmatched ternary in WFF expression: {expression}')
    # Ternaries may sit inside arithmetic parentheses, such as each Boolean
    # favorite's 1-or-0 value. Convert those nested groups too.
    converted = []
    index = 0
    quoted = False
    while index < len(expression):
        character = expression[index]
        if character == '"':
            quoted = not quoted
        if character == '(' and not quoted:
            depth = 1
            end = index + 1
            nested_quoted = False
            while end < len(expression) and depth:
                nested_character = expression[end]
                if nested_character == '"':
                    nested_quoted = not nested_quoted
                if not nested_quoted:
                    if nested_character == '(':
                        depth += 1
                    elif nested_character == ')':
                        depth -= 1
                end += 1
            converted.append('(' + _pythonize_ternary(expression[index + 1:end - 1]) + ')')
            index = end
            continue
        converted.append(character)
        index += 1
    return ''.join(converted).replace('&&', ' and ').replace('||', ' or ')


def _reference_name(reference):
    return '__wff_' + re.sub(r'\W', '_', reference)


@lru_cache(maxsize=512)
def _compiled_expression(expression):
    references = set(re.findall(r'\[([^\]]+)\]', expression))
    substituted = re.sub(r'\[([^\]]+)\]', lambda match: _reference_name(match[1]), expression)
    substituted = re.sub(r'(__wff_CONFIGURATION_(?:scene|woodblock_scene))\s*\*\s*1', r'int(\1)', substituted)
    code = compile(_pythonize_ternary(substituted), '<watchface-expression>', 'eval')
    return code, references


def evaluate_expression(expression, values):
    code, references = _compiled_expression(expression)
    locals_ = {_reference_name(reference): values[reference] for reference in references}
    return eval(code, {'__builtins__': {}, 'int': int, 'floor': floor, 'sin': sin, 'cos': cos,
                       'rad': radians, 'abs': abs,
                       'clamp': lambda x, lo, hi: max(lo, min(x, hi))}, locals_)


def config_values(now, period, selected, style='origami', favorites=SCENES,
                  woodblock_favorites=WOODBLOCK_SCENES, second=0.0,
                  pixel_scene='velodrome'):
    lunar_favorites = set(woodblock_favorites) & {'sailboat', 'moon_rabbit'}
    lunar_choice = ({'sailboat': 'SAILBOAT', 'moon_rabbit': 'MOON_RABBIT'}[next(iter(lunar_favorites))]
                    if len(lunar_favorites) == 1 else 'BOTH' if len(lunar_favorites) == 2 else 'NONE')
    values = {'YEAR': now.year, 'DAY_OF_YEAR': now.timetuple().tm_yday,
              'HOUR_0_23': now.hour, 'MINUTE': now.minute,
              'SECOND_MILLISECOND': second,
              'CONFIGURATION.rotation_period': period,
              'CONFIGURATION.scene': str(selected),
              'CONFIGURATION.woodblock_scene': str(selected),
              'CONFIGURATION.pixel_scene': pixel_scene,
              'CONFIGURATION.woodblock_lunar_favorites': lunar_choice,
              'CONFIGURATION.art_style': style,
              'CONFIGURATION.motion_enabled': 'TRUE'}
    for scene in SCENES:
        values[f'CONFIGURATION.favorite_{scene}'] = 'TRUE' if scene in favorites else 'FALSE'
    for scene in WOODBLOCK_SCENES:
        if scene not in {'sailboat', 'moon_rabbit'}:
            values[f'CONFIGURATION.favorite_woodblock_{scene}'] = (
                'TRUE' if scene in woodblock_favorites else 'FALSE')
    return values


def expected_scene_for_config(now, period, selected, style, favorites,
                              woodblock_favorites=WOODBLOCK_SCENES):
    if style == 'pixel_art':
        selected_index = PIXEL_SCENES.index(selected) if isinstance(selected, str) else selected
        if period == 'FIXED':
            return selected_index
        absolute_minutes = int((now - datetime(1970, 1, 1)) // timedelta(minutes=1))
        return (absolute_minutes // period + selected_index) % len(PIXEL_SCENES)
    if period == 'FIXED':
        return selected
    absolute_minutes = int((now - datetime(1970, 1, 1)) // timedelta(minutes=1))
    if style not in ('origami', 'woodblock'):
        return (absolute_minutes // period + selected) % len(SCENES)
    scenes, favorites = (SCENES, favorites) if style == 'origami' else (WOODBLOCK_SCENES, woodblock_favorites)
    enabled = [index for index, scene in enumerate(scenes) if scene in favorites]
    if not enabled:
        return selected
    start_rank = sum(index < selected for index in enabled)
    return enabled[(absolute_minutes // period + start_rank) % len(enabled)]


class RotationTest(unittest.TestCase):
    def test_fixed_scene_selection(self):
        self.assertEqual(len(EXPRESSIONS), 8)
        now = datetime(2026, 10, 25, 16, 0)
        for selected in range(8):
            for favorites in ((), SCENES):
                values = config_values(now, 'FIXED', selected, favorites=favorites)
                actual = [i for i, expression in enumerate(EXPRESSIONS)
                          if evaluate_expression(expression, values)]
                self.assertEqual(actual, [selected], (selected, favorites))

    def test_all_favorite_subsets_and_start_scenes_use_filtered_rotation(self):
        now = datetime(2026, 10, 25, 16, 0)
        period = 60
        for mask in range(1 << len(SCENES)):
            favorites = {scene for i, scene in enumerate(SCENES) if mask & (1 << i)}
            for selected in range(len(SCENES)):
                values = config_values(now, period, selected, favorites=favorites)
                actual = [i for i, expression in enumerate(EXPRESSIONS)
                          if evaluate_expression(expression, values)]
                self.assertEqual(actual, [expected_scene_for_config(now, period, selected, 'origami', favorites)],
                                 (mask, selected, favorites))

    def test_single_favorite_and_all_false_fall_back_without_rotation(self):
        now = datetime(2026, 10, 25, 16, 0)
        for selected in range(len(SCENES)):
            for favorites in ((), {'ocean'}):
                values = config_values(now, 15, selected, favorites=favorites)
                actual = [i for i, expression in enumerate(EXPRESSIONS)
                          if evaluate_expression(expression, values)]
                expected = selected if not favorites else 6
                self.assertEqual(actual, [expected], (selected, favorites))

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
                        values = config_values(now, period, selected, style='origami')
                        actual = [i for i, expression in enumerate(EXPRESSIONS)
                                  if evaluate_expression(expression, values)]
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
        scene_comps = [compare for compare in FACE.findall('./Scene/Condition/Compare')
                       if compare.attrib.get('expression', '').startswith('show_')]
        for scene in scene_comps:
            ranges = []
            for part in scene.findall('.//PartImage'):
                for transform in part.findall('Transform'):
                    if transform.attrib['target'] not in ('x', 'y'):
                        continue
                    expression = transform.attrib['value']
                    self.assertEqual(transform.attrib.get('mode', 'TO'), 'TO')
                    self.assertIn('[SECOND_MILLISECOND]', expression)
                    positions = [evaluate_expression(expression, {
                        'CONFIGURATION.motion_enabled': 'TRUE',
                        'SECOND_MILLISECOND': sample / 10,
                    }) for sample in range(120)]
                    ranges.append(max(positions) - min(positions))
                    stopped = evaluate_expression(expression, {
                        'CONFIGURATION.motion_enabled': 'FALSE',
                        'SECOND_MILLISECOND': 0.6,
                    })
                    self.assertAlmostEqual(float(stopped), float(part.attrib[transform.attrib['target']]))
                    self.assertEqual(part.find('Variant[@mode="AMBIENT"]').attrib['value'], '0')
            self.assertGreaterEqual(max(ranges), 20, scene.attrib['expression'])

    def test_pixel_scene_motion_stays_inside_its_scene_story(self):
        routes = {
            'velodrome': [('x', -330, 323.4)],
            'laundry_kitten': [('y', -29.7, 0)],
            'pinball': [('x', -177.5, 193.1), ('y', -309.8, 58.9)],
            'airship': [('x', -330, 324.5)],
        }
        for pixel_scene, show_id in zip(PIXEL_SCENES, PIXEL_SHOW_IDS):
            branch = FACE.find(f'./Scene/Condition/Compare[@expression="show_{show_id}"]'
                               '/Condition/Compare[@expression="style_pixel_art"]')
            parts = {part.find('Image').attrib['resource']: part for part in branch.findall('PartImage')}
            actor = parts[f'motion_pixel_art_{pixel_scene}']
            if pixel_scene in {'ramen', 'vinyl'}:
                self.assertFalse(actor.findall('Transform'), pixel_scene)
                drift = parts[f'drift_pixel_art_{pixel_scene}']
                targets = {transform.attrib['target'] for transform in drift.findall('Transform')}
                expected_targets = {'y', 'alpha'} if pixel_scene == 'ramen' else {'x', 'y', 'alpha'}
                self.assertEqual(targets, expected_targets, pixel_scene)
                sample_count = 50 if pixel_scene == 'ramen' else 40
                values = {}
                for target in expected_targets:
                    expression = drift.find(f'Transform[@target="{target}"]').attrib['value']
                    values[target] = [evaluate_expression(expression, {
                        'CONFIGURATION.motion_enabled': 'TRUE',
                        'SECOND_MILLISECOND': sample / 10,
                    }) for sample in range(sample_count)]
                    stopped = evaluate_expression(expression, {
                        'CONFIGURATION.motion_enabled': 'FALSE',
                        'SECOND_MILLISECOND': 0.6,
                    })
                    self.assertEqual(stopped, 255 if target == 'alpha' else 0, (pixel_scene, target))
                if pixel_scene == 'ramen':
                    self.assertAlmostEqual(min(values['y']), -37.24, delta=0.01)
                    self.assertAlmostEqual(max(values['y']), 0)
                    self.assertAlmostEqual(min(values['alpha']), 5.1, delta=0.01)
                    self.assertAlmostEqual(max(values['alpha']), 255)
                else:
                    self.assertAlmostEqual(min(values['y']), -39)
                    self.assertAlmostEqual(max(values['y']), 0)
                    self.assertAlmostEqual(min(values['x']), -12)
                    self.assertAlmostEqual(max(values['x']), 12)
                    self.assertAlmostEqual(min(values['alpha']), 6.375)
                    self.assertAlmostEqual(max(values['alpha']), 255)
                continue
            for target, minimum, maximum in routes[pixel_scene]:
                expression = actor.find(f'Transform[@target="{target}"]').attrib['value']
                positions = [evaluate_expression(expression, {
                    'CONFIGURATION.motion_enabled': 'TRUE',
                    'SECOND_MILLISECOND': sample / 10,
                }) for sample in range(120)]
                self.assertAlmostEqual(min(positions), minimum, delta=12.0 if pixel_scene == 'pinball' else 1.2, msg=pixel_scene)
                self.assertAlmostEqual(max(positions), maximum, delta=12.0 if pixel_scene == 'pinball' else 1.2, msg=pixel_scene)
                self.assertEqual(evaluate_expression(expression, {
                    'CONFIGURATION.motion_enabled': 'FALSE',
                    'SECOND_MILLISECOND': 0.6,
                }), 0)

    def test_pinball_flippers_follow_impacts_and_pause_together(self):
        branch = FACE.find('./Scene/Condition/Compare[@expression="show_kitten"]'
                           '/Condition/Compare[@expression="style_pixel_art"]')
        parts = {part.find('Image').attrib['resource']: part for part in branch.findall('PartImage')}
        for side, rest in (('left', 20), ('right', 160)):
            part = parts[f'flipper_pixel_art_pinball_{side}']
            transform = part.find('Transform[@target="angle"]')
            self.assertIsNotNone(transform)
            expression = transform.attrib['value']
            angles = [evaluate_expression(expression, {
                'CONFIGURATION.motion_enabled': 'TRUE',
                'SECOND_MILLISECOND': tick / 20,
            }) for tick in range(200)]
            self.assertGreater(max(angles) - min(angles), 40)
            self.assertAlmostEqual(evaluate_expression(expression, {
                'CONFIGURATION.motion_enabled': 'TRUE', 'SECOND_MILLISECOND': 0,
            }), 0)
            self.assertEqual(evaluate_expression(expression, {
                'CONFIGURATION.motion_enabled': 'FALSE', 'SECOND_MILLISECOND': 4.5,
            }), 0)
            self.assertEqual(part.find('Variant[@mode="AMBIENT"]').attrib['value'], '0')

        ball = parts['motion_pixel_art_pinball']
        spark = parts['drift_pixel_art_pinball']
        for target in ('x', 'y'):
            self.assertEqual(ball.find(f'Transform[@target="{target}"]').attrib['value'],
                             spark.find(f'Transform[@target="{target}"]').attrib['value'])
        events = json.loads((ROOT / 'artwork/packs/pixel_art/pinball-motion.json').read_text())['events']
        first = next(event for i, event in enumerate(events)
                     if i + 1 < len(events) and events[i + 1]['t'] - event['t'] > 0.3)
        flash = spark.find('Transform[@target="alpha"]').attrib['value']
        visible = evaluate_expression(flash, {
            'CONFIGURATION.motion_enabled': 'TRUE', 'SECOND_MILLISECOND': first['t'] + 0.05,
        })
        ended = evaluate_expression(flash, {
            'CONFIGURATION.motion_enabled': 'TRUE', 'SECOND_MILLISECOND': first['t'] + 0.11,
        })
        self.assertGreater(visible, 100)
        self.assertEqual(ended, 0)

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
                ys = [evaluate_expression(y_expr, {
                    'CONFIGURATION.motion_enabled': 'TRUE',
                    'SECOND_MILLISECOND': i / 10,
                }) for i in range(100)]
                self.assertAlmostEqual(ys[0], 180)
                self.assertLessEqual(min(ys), -550)


    def test_kitten_and_mouse_move_independently(self):
        scene = FACE.find('./Scene/Condition/Compare[@expression="show_kitten"]')
        parts = {part.find('Image').attrib['resource']: part for part in scene.findall('.//PartImage')}
        cat = parts['motion_kitten'].find('Transform[@target="x"]').attrib['value']
        mouse = parts['drift_kitten'].find('Transform[@target="x"]').attrib['value']
        self.assertNotEqual(cat, mouse)
        def positions(expression):
            return [evaluate_expression(expression, {
                'CONFIGURATION.motion_enabled': 'TRUE',
                'SECOND_MILLISECOND': i / 10,
            }) for i in range(100)]
        cats, mice = positions(cat), positions(mouse)
        self.assertAlmostEqual(max(cats), 10)
        self.assertAlmostEqual(min(cats), 0)
        self.assertAlmostEqual(min(positions(parts['motion_kitten'].find('Transform[@target="y"]').attrib['value'])), -5)
        self.assertGreater(max(mice)-min(mice), 600)

    def test_woodblock_kitten_keeps_cat_and_drifting_character_layers_without_mouse(self):
        scene = FACE.find('./Scene/Condition/Compare[@expression="show_kitten"]')
        group = scene.find('./Condition/Compare[@expression="style_woodblock"]/Group')
        parts = {part.find('Image').attrib['resource']: part for part in group.findall('PartImage')}
        self.assertEqual(set(parts), {
            'scene_woodblock_kitten', 'motion_woodblock_kitten',
            'drift_woodblock_kitten', 'glass_woodblock_kitten',
        })
        self.assertTrue(all('mouse' not in resource for resource in parts))
        for resource in ('motion_woodblock_kitten', 'drift_woodblock_kitten'):
            self.assertIsNotNone(parts[resource].find('Transform[@target="x"]'))
        self.assertIsNotNone(parts['motion_woodblock_kitten'].find('Transform[@target="y"]'))

    def test_origami_scene_motion_stories_have_distinct_routes(self):
        def transform(scene_id, resource, target):
            part = next(part for part in FACE.findall(
                f'./Scene/Condition/Compare[@expression="show_{scene_id}"]'
                '/Condition/Compare[@expression="style_origami"]//PartImage')
                        if part.find('Image').attrib['resource'] == resource)
            return part.find(f'Transform[@target="{target}"]').attrib['value']

        def sample(expression, seconds):
            return evaluate_expression(expression, {
                'CONFIGURATION.motion_enabled': 'TRUE',
                'SECOND_MILLISECOND': seconds,
            })

        frog = transform('forest', 'motion_forest', 'y')
        self.assertAlmostEqual(sample(frog, 0), 0)
        self.assertAlmostEqual(sample(frog, .6), -18)
        self.assertAlmostEqual(sample(frog, 1.2), 0)
        whale = transform('ocean', 'motion_ocean', 'x')
        self.assertAlmostEqual(sample(whale, 0), -320)
        self.assertAlmostEqual(sample(whale, 7), 50)
        self.assertGreater(sample(whale, 13.9), 400)
        cloud = transform('landscape', 'drift_landscape', 'x')
        self.assertAlmostEqual(sample(cloud, 2.5), 40)
        curtains = transform('aurora', 'drift_aurora', 'x')
        self.assertAlmostEqual(sample(curtains, 2.5), 22)
        fox = transform('aurora', 'motion_aurora', 'y')
        self.assertAlmostEqual(sample(fox, 1), 2)
        rocket_y = transform('cosmos', 'motion_cosmos', 'y')
        self.assertAlmostEqual(sample(rocket_y, 0), 180)
        self.assertAlmostEqual(sample(rocket_y, 9.9), -552.6)

    def test_origami_scene_fade_is_only_for_moving_auto_rotation_with_multiple_favorites(self):
        now = datetime(2026, 10, 25, 16, 0)
        group = FACE.find('./Scene/Condition/Compare[@expression="show_bicycle"]'
                          '/Condition/Compare[@expression="style_origami"]/Group')
        fade = group.find('Transform[@target="alpha"]').attrib['value']
        for second, expected in ((0, 0), (.4, 127.5), (1, 255)):
            values = config_values(now, 60, 0, second=second)
            self.assertAlmostEqual(evaluate_expression(fade, values), expected)
        for values in (
            config_values(now, 'FIXED', 0, second=.2),
            config_values(now, 60, 0, favorites=(), second=.2),
            config_values(now, 60, 0, favorites={'bicycle'}, second=.2),
            {**config_values(now, 60, 0, second=.2), 'CONFIGURATION.motion_enabled': 'FALSE'},
        ):
            self.assertAlmostEqual(evaluate_expression(fade, values), 255)

    def test_scene_choices_replace_baking_with_forest(self):
        choices = FACE.findall('./UserConfigurations/ListConfiguration[@id="scene"]/ListOption')
        self.assertEqual([c.attrib['displayName'] for c in choices],
                         ['scene_bicycle', 'scene_forest', 'scene_coding', 'scene_kitten',
                          'scene_landscape', 'scene_cosmos', 'scene_ocean', 'scene_aurora'])

    def test_style_selector_precedes_scene_and_keeps_all_scene_ids(self):
        self.assertEqual([configuration.attrib['id'] for configuration in FACE.find('./UserConfigurations')],
                         ['art_style', 'scene', 'woodblock_scene', 'pixel_scene', 'rotation_period', 'motion_enabled',
                          *[f'favorite_{scene}' for scene in SCENES],
                          'favorite_woodblock_bicycle', 'favorite_woodblock_crane',
                          'favorite_woodblock_kitten',
                          'favorite_woodblock_torii', 'favorite_woodblock_lanterns',
                          'woodblock_lunar_favorites'])
        configurations = FACE.findall('./UserConfigurations/ListConfiguration')
        self.assertEqual([configuration.attrib['id'] for configuration in configurations[:4]],
                         ['art_style', 'scene', 'woodblock_scene', 'pixel_scene'])

        style = configurations[0]
        self.assertEqual(style.attrib['defaultValue'], 'origami')
        self.assertEqual([option.attrib['id'] for option in style], list(STYLES))
        self.assertEqual([option.attrib['icon'] for option in style],
                         ['icon_scene_cosmos', 'icon_scene_woodblock_bicycle',
                          'icon_scene_risograph_cosmos', 'icon_scene_bioluminescent_bicycle',
                          'icon_scene_pixel_art_velodrome'])
        for option in style:
            icon_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{option.attrib['icon']}.png"
            width, height = struct.unpack('>II', icon_path.read_bytes()[16:24])
            self.assertEqual((width, height), (160, 160), option.attrib['icon'])

        scene = configurations[1]
        self.assertEqual([option.attrib['id'] for option in scene], [str(i) for i in range(8)])

        pixel_scene = configurations[3]
        self.assertEqual(pixel_scene.attrib['defaultValue'], 'velodrome')
        self.assertEqual([option.attrib['id'] for option in pixel_scene], list(PIXEL_SCENES))
        self.assertEqual([option.attrib['displayName'] for option in pixel_scene],
                         [f'pixel_scene_{name}' for name in PIXEL_SCENES])
        self.assertEqual([option.attrib['icon'] for option in pixel_scene],
                         [f'icon_scene_pixel_art_{name}' for name in PIXEL_SCENES])
        strings = {string.attrib['name']: string.text
                   for string in ET.parse(ROOT / 'watchface/src/main/res/values/strings.xml').getroot()}
        self.assertEqual([strings[f'pixel_scene_{name}'] for name in PIXEL_SCENES],
                         ['Pixel art: Velodrome', 'Pixel art: Laundry Kitten', 'Pixel art: Ramen Bar',
                          'Pixel art: Pinball', 'Pixel art: Airship Dock', 'Pixel art: Vinyl Lounge'])
        for option in pixel_scene:
            icon_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{option.attrib['icon']}.png"
            width, height = struct.unpack('>II', icon_path.read_bytes()[16:24])
            self.assertEqual((width, height), (160, 160), option.attrib['icon'])

    def test_origami_favorite_toggles_default_on_and_are_accessibly_labeled(self):
        favorite_ids = [f'favorite_{scene}' for scene in SCENES]
        favorites = [favorite for favorite in FACE.findall('./UserConfigurations/BooleanConfiguration')
                     if favorite.attrib['id'] in favorite_ids]
        self.assertEqual([favorite.attrib['id'] for favorite in favorites], favorite_ids)
        self.assertTrue(all(favorite.attrib['defaultValue'] == 'TRUE' for favorite in favorites))
        strings = {string.attrib['name']: string.text
                   for string in ET.parse(ROOT / 'watchface/src/main/res/values/strings.xml').getroot()}
        for scene, favorite in zip(SCENES, favorites):
            self.assertEqual(favorite.attrib['displayName'], f'favorite_{scene}_label')
            self.assertIn(scene.title(), strings[f'favorite_{scene}_label'])
            self.assertIn('Origami', strings[f'favorite_{scene}_description'])

    def test_woodblock_scene_and_favorite_controls_fit_wff_configuration_limit(self):
        configurations = FACE.find('./UserConfigurations')
        self.assertEqual(len(configurations), 20)

        scene = configurations.find('ListConfiguration[@id="woodblock_scene"]')
        self.assertEqual(scene.attrib['defaultValue'], '0')
        self.assertEqual([option.attrib['id'] for option in scene], [str(i) for i in range(7)])
        self.assertEqual([option.attrib['displayName'] for option in scene],
                         [f'woodblock_scene_{name}' for name in WOODBLOCK_SCENES])
        self.assertEqual([option.attrib['icon'] for option in scene],
                         [f'icon_scene_woodblock_{name}' for name in WOODBLOCK_SCENES])
        for option in scene:
            icon_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{option.attrib['icon']}.png"
            self.assertEqual(struct.unpack('>II', icon_path.read_bytes()[16:24]), (160, 160),
                             option.attrib['icon'])

        wood_favorites = [config for config in configurations.findall('BooleanConfiguration')
                          if config.attrib['id'].startswith('favorite_woodblock_')]
        expected_ids = [f'favorite_woodblock_{name}' for name in WOODBLOCK_SCENES
                        if name not in {'sailboat', 'moon_rabbit'}]
        self.assertEqual([favorite.attrib['id'] for favorite in wood_favorites], expected_ids)
        self.assertTrue(all(favorite.attrib['defaultValue'] == 'TRUE' for favorite in wood_favorites))

        lunar = configurations.find('ListConfiguration[@id="woodblock_lunar_favorites"]')
        self.assertEqual(lunar.attrib['defaultValue'], 'BOTH')
        self.assertEqual([option.attrib['id'] for option in lunar],
                         ['BOTH', 'SAILBOAT', 'MOON_RABBIT', 'NONE'])

        strings = {string.attrib['name']: string.text
                   for string in ET.parse(ROOT / 'watchface/src/main/res/values/strings.xml').getroot()}
        for scene in WOODBLOCK_SCENES:
            self.assertIn('Woodblock', strings[f'woodblock_scene_{scene}'])
            if scene not in {'sailboat', 'moon_rabbit'}:
                favorite = configurations.find(f'BooleanConfiguration[@id="favorite_woodblock_{scene}"]')
                self.assertEqual(favorite.attrib['displayName'], f'favorite_woodblock_{scene}_label')
                self.assertEqual(favorite.attrib['screenReaderText'],
                                 f'favorite_woodblock_{scene}_description')
                self.assertIn('Woodblock', strings[f'favorite_woodblock_{scene}_label'])
                self.assertIn('Woodblock', strings[f'favorite_woodblock_{scene}_description'])
        self.assertIn('Woodblock', strings['woodblock_lunar_favorites_title'])
        self.assertIn('Woodblock', strings['woodblock_lunar_favorites_description'])
        self.assertEqual([strings[option.attrib['displayName']] for option in lunar],
                         ['Both', 'Sailboat', 'Moon Rabbit', 'Neither'])
        self.assertNotIn('koi', '\n'.join(f'{key}:{value}' for key, value in strings.items()).lower())
        self.assertNotIn('koi', (ROOT / 'watchface/src/main/res/raw/watchface.xml')
                         .read_text().lower())
        self.assertNotIn('orrery', (ROOT / 'watchface/src/main/res/raw/watchface.xml')
                         .read_text().lower())
        self.assertNotIn('orrery', '\n'.join(strings.values()).lower())

    def test_woodblock_rotation_uses_each_favorite_subset_and_selected_fallback(self):
        now = datetime(2026, 10, 25, 16, 0)
        for mask in range(1 << len(WOODBLOCK_SCENES)):
            favorites = {scene for i, scene in enumerate(WOODBLOCK_SCENES) if mask & (1 << i)}
            for selected in range(len(WOODBLOCK_SCENES)):
                values = config_values(now, 60, selected, style='woodblock',
                                       woodblock_favorites=favorites)
                actual = [i for i, expression in enumerate(EXPRESSIONS)
                          if evaluate_expression(expression, values)]
                expected = expected_scene_for_config(now, 60, selected, 'woodblock', SCENES,
                                                     favorites)
                self.assertEqual(actual, [SCENES.index(WOODBLOCK_SHOW_IDS[expected])],
                                 (mask, selected, favorites))

    def test_woodblock_fixed_and_empty_favorites_keep_selected_slot(self):
        now = datetime(2026, 10, 25, 16, 0)
        for selected in range(len(WOODBLOCK_SCENES)):
            for period, favorites in (('FIXED', WOODBLOCK_SCENES), (60, ())):
                values = config_values(now, period, selected, style='woodblock',
                                       woodblock_favorites=favorites)
                actual = [i for i, expression in enumerate(EXPRESSIONS)
                          if evaluate_expression(expression, values)]
                self.assertEqual(actual, [SCENES.index(WOODBLOCK_SHOW_IDS[selected])],
                                 (period, selected, favorites))

    def test_woodblock_scene_fade_requires_multiple_rotating_favorites_and_motion(self):
        now = datetime(2026, 10, 25, 16, 0)
        group = FACE.find('./Scene/Condition/Compare[@expression="show_bicycle"]'
                          '/Condition/Compare[@expression="style_woodblock"]/Group')
        fade = group.find('Transform[@target="alpha"]').attrib['value']
        for second, expected in ((0, 0), (.4, 127.5), (1, 255)):
            values = config_values(now, 60, 0, style='woodblock', second=second)
            self.assertAlmostEqual(evaluate_expression(fade, values), expected)
        for values in (
            config_values(now, 'FIXED', 0, style='woodblock', second=.2),
            config_values(now, 60, 0, style='woodblock', woodblock_favorites=(), second=.2),
            config_values(now, 60, 0, style='woodblock', woodblock_favorites={'bicycle'}, second=.2),
            {**config_values(now, 60, 0, style='woodblock', second=.2),
             'CONFIGURATION.motion_enabled': 'FALSE'},
        ):
            self.assertEqual(group.find('Variant[@target="alpha"][@mode="AMBIENT"]')
                             .attrib['value'], '0')
            self.assertAlmostEqual(evaluate_expression(fade, values), 255)

    def test_scene_rotation_selects_one_scene_then_only_one_style_pack(self):
        scene_compares = [compare for compare in FACE.findall('./Scene/Condition/Compare')
                          if compare.attrib.get('expression', '').startswith('show_')]
        self.assertEqual(len(scene_compares), len(SCENES))
        dates = (datetime(2024, 2, 29, 23, 59), datetime(2026, 10, 25, 16, 0))

        for selected_style in STYLES:
            for period in ('FIXED', 15, 60, 1440):
                for date in dates:
                    scene_count = (len(WOODBLOCK_SCENES) if selected_style == 'woodblock' else
                                   len(PIXEL_SCENES) if selected_style == 'pixel_art' else len(SCENES))
                    for selected_scene in range(scene_count):
                        now = date + timedelta(minutes=period if period != 'FIXED' else 0)
                        pixel_scene = PIXEL_SCENES[selected_scene] if selected_style == 'pixel_art' else 'velodrome'
                        values = config_values(now, period, selected_scene, selected_style,
                                               pixel_scene=pixel_scene)
                        active_scenes = [i for i, expression in enumerate(EXPRESSIONS)
                                         if evaluate_expression(expression, values)]
                        selected_for_expectation = pixel_scene if selected_style == 'pixel_art' else selected_scene
                        expected = expected_scene_for_config(now, period, selected_for_expectation,
                                                             selected_style, SCENES, WOODBLOCK_SCENES)
                        if selected_style == 'woodblock':
                            expected_slot = WOODBLOCK_SHOW_IDS[expected]
                            expected_active_index = SCENES.index(expected_slot)
                            scene_id = WOODBLOCK_SCENES[expected]
                        elif selected_style == 'pixel_art':
                            expected_slot = PIXEL_SHOW_IDS[expected]
                            expected_active_index = expected
                            scene_id = PIXEL_SCENES[expected]
                        else:
                            expected_slot = SCENES[expected]
                            expected_active_index = expected
                            scene_id = SCENES[expected]
                        self.assertEqual(active_scenes, [expected_active_index])

                        scene = scene_compares[expected_active_index]
                        self.assertEqual(scene.attrib['expression'], f'show_{expected_slot}')
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
                        if selected_style == 'origami':
                            self.assertIn(f'scene_{scene_id}', resources)
                            self.assertIn(f'glass_{scene_id}', resources)
                            self.assertIn('origami_ambient', resources)
                        else:
                            if selected_style == 'woodblock':
                                resources.remove('woodblock_ambient')
                                expected_resources = [f'{kind}_woodblock_{scene_id}'
                                                      for kind in ('scene', 'motion', 'drift', 'glass')]
                            elif selected_style == 'pixel_art':
                                expected_resources = ([f'scene_pixel_art_{scene_id}',
                                                      'flipper_pixel_art_pinball_left',
                                                      'flipper_pixel_art_pinball_right',
                                                      'drift_pixel_art_pinball',
                                                      'motion_pixel_art_pinball',
                                                      'glass_pixel_art_pinball']
                                                     if scene_id == 'pinball' else
                                                     [f'{kind}_pixel_art_{scene_id}'
                                                      for kind in ('scene', 'motion', 'drift', 'glass')])
                                self.assertEqual(set(resources), set(expected_resources))
                                self.assertEqual(resources[0], expected_resources[0])
                                self.assertEqual(resources[-1], expected_resources[-1])
                                continue
                            else:
                                origami = scene.find('./Condition/Compare[@expression="style_origami"]')
                                overlay_order = [part.find('Image').attrib['resource'].split('_', 1)[0]
                                                for part in origami.findall('.//PartImage')
                                                if part.find('Image').attrib['resource'].startswith(('motion_', 'drift_'))]
                                expected_resources = [f'scene_{selected_style}_{scene_id}']
                                expected_resources.extend(f'{kind}_{selected_style}_{scene_id}'
                                                          for kind in overlay_order)
                                expected_resources.append(f'glass_{selected_style}_{scene_id}')
                            self.assertEqual(resources, expected_resources)

    def test_new_packs_have_animated_ambient_safe_layers(self):
        assets = ROOT / 'watchface/src/main/res/drawable-nodpi'
        packs = [('bioluminescent', SCENES, SCENES), ('pixel_art', PIXEL_SCENES, PIXEL_SHOW_IDS)]
        for style, scene_ids, show_ids in packs:
            for scene_id, show_id in zip(scene_ids, show_ids):
                branch = FACE.find(f'./Scene/Condition/Compare[@expression="show_{show_id}"]'
                                   f'/Condition/Compare[@expression="style_{style}"]')
                self.assertIsNotNone(branch, (style, scene_id))
                parts = {p.find('Image').attrib['resource']: p for p in branch.findall('.//PartImage')}
                background = parts[f'scene_{style}_{scene_id}']
                self.assertEqual([background.attrib[k] for k in ('x', 'y', 'width', 'height')],
                                 ['0', '0', '450', '450'])
                self.assertFalse(background.findall('Transform'))
                for layer in ('scene', 'motion', 'drift', 'glass'):
                    name = f'{layer}_{style}_{scene_id}'
                    self.assertIn(name, parts)
                    self.assertTrue((assets / f'{name}.png').is_file(), name)
                    self.assertIsNotNone(parts[name].find('Variant[@mode="AMBIENT"]'), name)
                for layer in ('motion', 'drift'):
                    part = parts[f'{layer}_{style}_{scene_id}']
                    if style == 'pixel_art' and scene_id in {'ramen', 'vinyl'} and layer == 'motion':
                        self.assertFalse(part.findall('Transform'), (style, scene_id, layer))
                        continue
                    self.assertTrue(part.findall('Transform'), (style, scene_id, layer))
                    self.assertTrue(all('motion_enabled' in t.attrib['value'] for t in part.findall('Transform')))
                self.assertTrue((assets / f'icon_scene_{style}_{scene_id}.png').is_file())

        for show_id in set(SCENES) - set(PIXEL_SHOW_IDS):
            self.assertIsNone(FACE.find(f'./Scene/Condition/Compare[@expression="show_{show_id}"]'
                                        '/Condition/Compare[@expression="style_pixel_art"]'))

    def test_new_style_art_pans_as_one_ambient_safe_canvas(self):
        for scene_id in SCENES:
            scene = FACE.find(f'./Scene/Condition/Compare[@expression="show_{scene_id}"]')
            branch = scene.find('./Condition/Compare[@expression="style_risograph"]')
            parts = {part.find('Image').attrib['resource']: part
                     for part in branch.findall('.//PartImage')}
            self.assertEqual(set(parts), {f'{kind}_risograph_{scene_id}'
                                         for kind in ('scene', 'motion', 'drift', 'glass')})
            self.assertEqual((parts[f'scene_risograph_{scene_id}'].attrib['x'],
                              parts[f'scene_risograph_{scene_id}'].attrib['y'],
                              parts[f'scene_risograph_{scene_id}'].attrib['width'],
                              parts[f'scene_risograph_{scene_id}'].attrib['height']),
                             ('-25', '-25', '500', '500'))
            for kind in ('motion', 'drift', 'glass'):
                self.assertEqual(parts[f'{kind}_risograph_{scene_id}']
                                 .find('Variant[@target="alpha"][@mode="AMBIENT"]')
                                 .attrib['value'], '0')
            original = scene.find('./Condition/Compare[@expression="style_origami"]')
            original_parts = {part.find('Image').attrib['resource']: part
                              for part in original.findall('.//PartImage')}
            for kind in ('motion', 'drift'):
                part = parts[f'{kind}_risograph_{scene_id}']
                transforms = {item.attrib['target']: item.attrib['value']
                              for item in part.findall('Transform')}
                original_transforms = {item.attrib['target']: item.attrib['value']
                                       for item in original_parts[f'{kind}_{scene_id}'].findall('Transform')}
                if scene_id == 'bicycle':
                    self.assertEqual(transforms, original_transforms)
                self.assertEqual((part.attrib['x'], part.attrib['y'],
                                  part.attrib['width'], part.attrib['height']),
                                 ('0', '0', '450', '450'))
                for axis, expression in transforms.items():
                    if axis not in ('x', 'y'):
                        continue
                    self.assertIn('[CONFIGURATION.motion_enabled] == "TRUE"', expression)
                    moving, frozen = expression.split('?', 1)[1].split(':', 1)
                    self.assertEqual(float(frozen), 0)
                    positions = [evaluate_expression(expression, {
                        'CONFIGURATION.motion_enabled': 'TRUE',
                        'SECOND_MILLISECOND': sample / 10,
                    }) for sample in range(200)]
                    self.assertGreaterEqual(max(positions) - min(positions), 12,
                                            ('risograph', scene_id, kind, axis))
            background = parts[f'scene_risograph_{scene_id}']
            if scene_id == 'bicycle':
                self.assertEqual(background.findall('Transform'), [])
            else:
                for axis in ('x', 'y'):
                    transform = background.find(f'Transform[@target="{axis}"]')
                    self.assertEqual(transform.attrib['mode'], 'TO')
                    self.assertIn('[CONFIGURATION.motion_enabled] == "TRUE"', transform.attrib['value'])
                    values = [evaluate_expression(transform.attrib['value'], {
                        'CONFIGURATION.motion_enabled': 'TRUE',
                        'SECOND_MILLISECOND': sample / 10,
                    }) for sample in range(180)]
                    self.assertGreaterEqual(max(values) - min(values), 23.9,
                                            ('risograph', scene_id, axis))
            self.assertEqual(parts[f'glass_risograph_{scene_id}']
                             .find('Variant[@target="alpha"][@mode="AMBIENT"]')
                             .attrib['value'], '0')

        for slot, scene_id in enumerate(WOODBLOCK_SCENES):
            scene = FACE.find(f'./Scene/Condition/Compare[@expression="show_{WOODBLOCK_SHOW_IDS[slot]}"]')
            branch = scene.find('./Condition/Compare[@expression="style_woodblock"]')
            group = branch.find('Group')
            self.assertEqual(group.attrib['name'], f'woodblock_{scene_id}')
            self.assertIsNotNone(group.find('Transform[@target="alpha"]'))
            self.assertIsNotNone(branch.find('PartImage/Image[@resource="woodblock_ambient"]'))
            parts = {part.find('Image').attrib['resource']: part
                     for part in group.findall('PartImage')}
            self.assertEqual(set(parts), {f'{kind}_woodblock_{scene_id}'
                                         for kind in ('scene', 'motion', 'drift', 'glass')})
            for resource, part in parts.items():
                kind = resource.split('_', 1)[0]
                if scene_id in {'bicycle', 'kitten'}:
                    continue
                expected_position = ('150', '0') if scene_id == 'sailboat' and kind == 'motion' else ('0', '0')
                self.assertEqual((part.attrib['x'], part.attrib['y'],
                                  part.attrib['width'], part.attrib['height']),
                                 (*expected_position, '450', '450'))
                self.assertEqual(part.find('Variant[@target="alpha"][@mode="AMBIENT"]')
                                 .attrib['value'], '0')
                if kind in ('motion', 'drift'):
                    transforms = part.findall('Transform')
                    self.assertTrue(transforms, scene_id)
                    movement = []
                    for transform in transforms:
                        self.assertEqual(transform.attrib['mode'], 'TO')
                        self.assertIn('[CONFIGURATION.motion_enabled] == "TRUE"', transform.attrib['value'])
                        if transform.attrib['target'] in ('x', 'y'):
                            moving, frozen = transform.attrib['value'].split('?', 1)[1].split(':', 1)
                            self.assertEqual(float(frozen), float(part.attrib[transform.attrib['target']]))
                            positions = [evaluate_expression(transform.attrib['value'], {
                                'CONFIGURATION.motion_enabled': 'TRUE',
                                'SECOND_MILLISECOND': sample / 10,
                            }) for sample in range(120)]
                            movement.append(max(positions) - min(positions))
                    self.assertGreaterEqual(max(movement), 20, (scene_id, kind))
                    if scene_id == 'lanterns' and kind == 'drift':
                        alpha = part.find('Transform[@target="alpha"]').attrib['value']
                        values = [evaluate_expression(alpha, {
                            'CONFIGURATION.motion_enabled': 'TRUE',
                            'SECOND_MILLISECOND': seconds,
                        }) for seconds in (0, .5, 1, 1.5, 2)]
                        for actual, expected in zip(values, (152.5, 255, 152.5, 50, 152.5)):
                            self.assertAlmostEqual(actual, expected)
                        self.assertEqual(evaluate_expression(alpha, {
                            'CONFIGURATION.motion_enabled': 'FALSE',
                            'SECOND_MILLISECOND': 1.5,
                        }), 255)

    def test_new_style_assets_use_expected_texture_resolutions(self):
        resources = [('risograph', scene) for scene in SCENES]
        resources += [('woodblock', scene) for scene in WOODBLOCK_SCENES]
        resources += [('pixel_art', scene) for scene in PIXEL_SCENES]
        for style, scene_id in resources:
            for kind in ('scene', 'motion', 'drift', 'glass'):
                resource = f'{kind}_{style}_{scene_id}'
                image_path = ROOT / 'watchface/src/main/res/drawable-nodpi' / f'{resource}.png'
                data = image_path.read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n', resource)
                width, height = struct.unpack('>II', data[16:24])
                if style == 'pixel_art':
                    size = 112 if kind == 'glass' else 225
                else:
                    size = 225 if kind in ('drift', 'glass') else 450
                self.assertEqual((width, height), (size, size), resource)

        ambient = ROOT / 'watchface/src/main/res/drawable-nodpi/woodblock_ambient.png'
        self.assertEqual(struct.unpack('>II', ambient.read_bytes()[16:24]), (450, 450))

    def test_pixel_art_sprites_keep_solid_edges(self):
        from PIL import Image
        folder = ROOT / 'watchface/src/main/res/drawable-nodpi'
        for scene in PIXEL_SCENES:
            for kind in ('motion', 'drift'):
                with Image.open(folder / f'{kind}_pixel_art_{scene}.png') as image:
                    alpha = image.convert('RGBA').getchannel('A')
                    self.assertLessEqual({value for _, value in alpha.getcolors()}, {0, 255})
                    self.assertIsNotNone(alpha.getbbox(), (scene, kind))

    def test_woodblock_clock_keeps_base_glyph_geometry_and_alpha(self):
        from PIL import Image, ImageChops

        fonts = {font.attrib['name']: font for font in FACE.findall('./BitmapFonts/BitmapFont')}
        base = {character.attrib['name']: character for character in fonts['fold_time']}
        woodblock = {character.attrib['name']: character for character in fonts['fold_time_woodblock']}
        self.assertEqual(set(woodblock), set(base))
        for character, native in woodblock.items():
            base_resource = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{base[character].attrib['resource']}.png"
            wood_resource = ROOT / 'watchface/src/main/res/drawable-nodpi' / f"{native.attrib['resource']}.png"
            self.assertEqual(native.attrib['width'], base[character].attrib['width'], character)
            self.assertEqual(native.attrib['height'], base[character].attrib['height'], character)
            base_alpha = Image.open(base_resource).convert('RGBA').getchannel('A')
            wood_alpha = Image.open(wood_resource).convert('RGBA').getchannel('A')
            self.assertEqual(wood_alpha.size, base_alpha.size, character)
            self.assertIsNone(ImageChops.difference(base_alpha, wood_alpha).getbbox(), character)

        clock_condition = next(condition for condition in FACE.findall('./Scene/Condition')
                               if condition.find('./Expressions/Expression[@name="clock_style_origami"]') is not None)
        woodblock_clock = clock_condition.find('Compare[@expression="clock_style_woodblock"]')
        self.assertEqual(woodblock_clock.find('.//BitmapFont').attrib['family'], 'fold_time_woodblock')

    def test_sailboat_traverse_enters_and_exits_beyond_the_dial_edges(self):
        from PIL import Image

        scene = FACE.find('./Scene/Condition/Compare[@expression="show_ocean"]'
                          '/Condition/Compare[@expression="style_woodblock"]/Group')
        actor = next(part for part in scene.findall('PartImage')
                     if part.find('Image').attrib['resource'] == 'motion_woodblock_sailboat')
        x = actor.find('Transform[@target="x"]').attrib['value']
        self.assertEqual(actor.attrib['x'], '150')
        sprite_path = ROOT / 'watchface/src/main/res/drawable-nodpi/motion_woodblock_sailboat.png'
        sprite_bounds = Image.open(sprite_path).convert('RGBA').getchannel('A').getbbox()
        self.assertIsNotNone(sprite_bounds)
        left, _, right, _ = sprite_bounds
        self.assertLessEqual(left, 5)
        self.assertLessEqual(right, 200)

        def position(seconds):
            return evaluate_expression(x, {
                'CONFIGURATION.motion_enabled': 'TRUE',
                'SECOND_MILLISECOND': seconds,
            })

        self.assertAlmostEqual(position(0), -180)
        self.assertAlmostEqual(position(7), 135.5)
        self.assertAlmostEqual(position(13.9), -180 + 631 * 13.9 / 14)
        self.assertEqual(evaluate_expression(x, {
            'CONFIGURATION.motion_enabled': 'FALSE',
            'SECOND_MILLISECOND': 7,
        }), 150)
        # At the wrap both the departing and entering sprite are off-screen.
        self.assertLessEqual(right + position(0), 0)
        self.assertGreaterEqual(left + position(13.99), 450)
        self.assertEqual(position(14), -180)

    def test_road_camera_and_bicycle_layer_stay_attached(self):
        for style in STYLES[1:]:
            branch = FACE.find('./Scene/Condition/Compare[@expression="show_bicycle"]'
                               f'/Condition/Compare[@expression="style_{style}"]')
            group = branch.find('Group')
            parts = group.findall('PartImage') if group is not None else branch.findall('PartImage')
            background, actor = parts[:2]
            self.assertEqual(background.findall('Transform'), [])
            self.assertIsNone(actor.find('Transform[@target="y"]'))
            self.assertIsNotNone(actor.find('Transform[@target="x"]'))

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
            plate = _complication_plate(complication)
            def attribute(element, name, value):
                transform = element.find(f'Transform[@target="{name}"]')
                if transform is None:
                    return float(element.attrib[name])
                expression = transform.attrib['value'].replace('[COMPLICATION.TEXT]', repr(value))
                return eval(expression, {'__builtins__': {}, 'textLength': len,
                                        'clamp': lambda x, lo, hi: max(lo, min(x, hi))})
            previous_width = 0
            slot = FACE.find(f'.//ComplicationSlot[@slotId="{slot_id}"]')
            slot_center = float(slot.attrib['width']) / 2
            for value in ('', '8', '80', '67°', '100%', '6,248', '12,345', '1234567890'):
                ix, tx = attribute(icon, 'x', value), attribute(text, 'x', value)
                tw, px, pw = (attribute(text, 'width', value),
                              attribute(plate, 'x', value), attribute(plate, 'width', value))
                self.assertAlmostEqual(tx - ix - float(icon.attrib['width']), 8)
                self.assertAlmostEqual((ix + tx + tw) / 2, slot_center)
                self.assertAlmostEqual(ix - px, 8)
                self.assertAlmostEqual(px + pw - tx - tw, 8)
                self.assertLessEqual(pw, 161)
                if value == '12,345':
                    self.assertEqual(tw, 111)
                    self.assertEqual(pw, 161)
                self.assertGreaterEqual(pw, previous_width)
                previous_width = pw

    def test_complication_and_date_text_are_larger_for_readability(self):
        for font in FACE.findall('.//Complication//Font'):
            self.assertEqual(font.attrib['size'], '32')
        self.assertEqual({font.attrib['size'] for font in FACE.findall('.//ComplicationSlot[@slotId="0"]//Font')},
                         {'32'})


    def test_origami_complication_glass_uses_warm_borderless_palette(self):
        complications = FACE.findall('.//ComplicationSlot/Complication')
        self.assertEqual(len(complications), 4)
        for complication in complications:
            condition = complication.find('Condition')
            expressions = {expression.attrib['name']: expression.text.strip()
                           for expression in condition.findall('Expressions/Expression')}
            self.assertEqual(expressions['origami_glass_style'], '[CONFIGURATION.art_style] == "origami"')
            self.assertEqual(expressions['woodblock_glass_style'], '[CONFIGURATION.art_style] == "woodblock"')
            origami = _complication_plate(complication, 'Compare[@expression="origami_glass_style"]')
            woodblock = _complication_plate(complication, 'Compare[@expression="woodblock_glass_style"]')
            other_styles = _complication_plate(complication)
            new_styles = _complication_plate(complication, 'Compare[@expression="new_glass_style"]')
            self.assertIsNotNone(origami)
            self.assertIsNotNone(woodblock)
            self.assertIsNotNone(other_styles)
            self.assertIsNotNone(new_styles)
            for plate, fill_color, gradient_colors in (
                    (origami, '#FFFFFFFF', '#38FFE9BF #24E8BC95'),
                    (woodblock, '#FFFFFFFF', '#38E9DFC0 #24A3BCBE'),
                    (new_styles, '#FFFFFFFF', '#B8071022 #99071022'),
                    (other_styles, '#30DFEBF7', '#38DFEBF7 #24B8CCE4')):
                self.assertIsNone(plate.find('Stroke'))
                fill = plate.find('Fill')
                self.assertEqual(fill.attrib['color'], fill_color)
                gradient = fill.find('LinearGradient')
                self.assertEqual(gradient.attrib['colors'], gradient_colors)
            self.assertEqual(origami.attrib, woodblock.attrib)
            self.assertEqual(origami.attrib, other_styles.attrib)
            self.assertEqual(origami.attrib, new_styles.attrib)
            transforms = [(node.attrib['target'], node.attrib['value'])
                          for node in origami.findall('Transform')]
            self.assertEqual(transforms, [(node.attrib['target'], node.attrib['value'])
                                          for node in woodblock.findall('Transform')])
            self.assertEqual(transforms, [(node.attrib['target'], node.attrib['value'])
                                          for node in other_styles.findall('Transform')])
            self.assertEqual(transforms, [(node.attrib['target'], node.attrib['value'])
                                          for node in new_styles.findall('Transform')])

    def test_date_glass_stays_centered_and_caps_long_provider_text(self):
        for kind in ('SHORT_TEXT', 'LONG_TEXT'):
            complication = FACE.find(f'.//ComplicationSlot[@slotId="0"]/Complication[@type="{kind}"]')
            plate = _complication_plate(complication)
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
