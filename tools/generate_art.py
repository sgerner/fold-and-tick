#!/usr/bin/env python3
"""Render Fold & Tick's full-dial cut-paper scenes and previews.

Run from any directory with: tools/.venv/bin/python tools/generate_art.py
All scene art is deterministic Pillow geometry. Each scene is exported as a
full-bleed still plus independently transformable actor and drift layers.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "watchface/src/main/res/drawable-nodpi"
PREVIEW = ROOT / "preview/contact-sheet.png"
MOTION_PREVIEW = ROOT / "preview/scene-motion.gif"
CHASE_PREVIEW = ROOT / "preview/chase-motion.gif"
KITTEN_PREVIEW = ROOT / "preview/kitten-motion.gif"
ROCKET_PREVIEW = ROOT / "preview/rocket-motion.gif"
SIZE = 450
SCALE = 3
HI = SIZE * SCALE


def xy(points):
    return [(round(x * SCALE), round(y * SCALE)) for x, y in points]


class Canvas:
    """Small coordinate wrapper for crisp 3x Pillow vector geometry."""

    def __init__(self, draw: ImageDraw.ImageDraw):
        self.d = draw

    def poly(self, points, fill=None, outline=None, width=1):
        self.d.polygon(xy(points), fill=fill)
        if outline:
            self.d.line(xy(points + [points[0]]), fill=outline,
                        width=max(1, round(width * SCALE)), joint="curve")

    def line(self, points, fill, width=1, joint="curve"):
        self.d.line(xy(points), fill=fill,
                    width=max(1, round(width * SCALE)), joint=joint)

    def ellipse(self, box, fill=None, outline=None, width=1):
        b = tuple(round(v * SCALE) for v in box)
        self.d.ellipse(b, fill=fill, outline=outline,
                       width=max(1, round(width * SCALE)))

    def rect(self, box, fill=None, outline=None, width=1):
        b = tuple(round(v * SCALE) for v in box)
        self.d.rectangle(b, fill=fill, outline=outline,
                         width=max(1, round(width * SCALE)))

    def rounded(self, box, radius, fill=None, outline=None, width=1):
        b = tuple(round(v * SCALE) for v in box)
        self.d.rounded_rectangle(b, radius=round(radius * SCALE), fill=fill,
                                 outline=outline,
                                 width=max(1, round(width * SCALE)))


def regular_polygon(cx, cy, radius, sides=12, phase=-math.pi / 2):
    return [
        (cx + math.cos(phase + i * math.tau / sides) * radius,
         cy + math.sin(phase + i * math.tau / sides) * radius)
        for i in range(sides)
    ]


def hexrgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def gradient(stops):
    """Create a vertical, smoothly blended 450px paper-sky background."""
    im = Image.new("RGB", (HI, HI))
    d = ImageDraw.Draw(im)
    for py in range(HI):
        t = py / max(1, HI - 1)
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                q = (t - p0) / max(0.0001, p1 - p0)
                c0, c1 = hexrgb(c0), hexrgb(c1)
                col = tuple(round(c0[k] + (c1[k] - c0[k]) * q) for k in range(3))
                break
        d.line((0, py, HI, py), fill=col)
    return im.convert("RGBA")


def art_layer(painter, blur=4.0, offset=(0, 4), shadow_alpha=82):
    art = Image.new("RGBA", (HI, HI), (0, 0, 0, 0))
    painter(Canvas(ImageDraw.Draw(art)))
    mask = art.getchannel("A").transform(
        art.size, Image.Transform.AFFINE, (1, 0, 0, 0, 1, -round(offset[1] * SCALE)),
        resample=Image.Resampling.BICUBIC, fillcolor=0,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(blur * SCALE))
    mask = mask.point(lambda a: round(a * shadow_alpha / 255))
    shadow = Image.new("RGBA", art.size, (8, 12, 34, 0))
    shadow.putalpha(mask)
    return Image.alpha_composite(shadow, art)


def composite_art(base, painter, blur=4.0, offset=(0, 4), shadow_alpha=82):
    return Image.alpha_composite(base, art_layer(painter, blur, offset, shadow_alpha))


# ── Bicycle: valley sunrise, layered bridge, turquoise river ────────────────

def bicycle_environment(c: Canvas):
    # Wide faceted sun behind the valley ridges.
    sun = regular_polygon(215, 163, 108, 20)
    c.poly(sun, "#ffb95f")
    for i, color in enumerate(["#ffd978", "#ff9a68", "#ffe394", "#f58482",
                               "#ffc269", "#ffda82", "#ed7b88", "#ffb85f"]):
        a = -math.pi / 2 + i * math.tau / 8
        b = a + math.tau / 8
        c.poly([(215, 163),
                (215 + math.cos(a) * 106, 163 + math.sin(a) * 106),
                (215 + math.cos((a + b) / 2) * 95, 163 + math.sin((a + b) / 2) * 95),
                (215 + math.cos(b) * 106, 163 + math.sin(b) * 106)], color)

    # Mountain planes layer from violet distance to hot pink foothills.
    c.poly([(0, 212), (58, 153), (110, 191), (175, 122), (237, 186),
            (298, 141), (364, 198), (421, 154), (450, 179), (450, 306), (0, 306)], "#754bba")
    c.poly([(0, 214), (58, 153), (110, 191), (81, 185), (58, 169), (23, 221)], "#b26ccc")
    c.poly([(110, 191), (175, 122), (237, 186), (204, 171), (175, 139), (148, 203)], "#a45dc0")
    c.poly([(237, 186), (298, 141), (364, 198), (331, 180), (299, 155), (274, 201)], "#cf648f")
    c.poly([(364, 198), (421, 154), (450, 179), (450, 225), (421, 177), (397, 212)], "#ad5bae")
    c.poly([(0, 239), (84, 191), (139, 219), (219, 176), (286, 226),
            (365, 188), (450, 229), (450, 325), (0, 325)], "#e45f8d")
    c.poly([(0, 239), (84, 191), (139, 219), (96, 213), (84, 200), (42, 256)], "#f1889b")
    c.poly([(139, 219), (219, 176), (286, 226), (250, 212), (219, 186), (191, 240)], "#bc5f9d")
    c.poly([(286, 226), (365, 188), (450, 229), (407, 215), (366, 199), (335, 241)], "#f17c91")

    # River bends through the full lower valley, with bright folded reflections.
    c.poly([(0, 269), (52, 284), (116, 272), (190, 291), (253, 279),
            (333, 296), (393, 277), (450, 292), (450, 450), (0, 450)], "#2097aa")
    c.poly([(0, 290), (63, 301), (117, 288), (195, 309), (258, 296),
            (330, 315), (402, 293), (450, 306), (450, 341), (0, 333)], "#48c4bd")
    c.poly([(0, 333), (78, 340), (152, 326), (226, 346), (303, 329),
            (386, 348), (450, 332), (450, 375), (370, 386), (300, 363),
            (222, 380), (151, 359), (74, 378), (0, 365)], "#278ca9")
    c.poly([(0, 392), (100, 375), (193, 395), (286, 377), (374, 398), (450, 383),
            (450, 450), (0, 450)], "#176f91")
    for pts in [[(23, 317), (84, 307), (132, 312)], [(290, 340), (342, 349), (408, 334)],
                [(52, 397), (117, 385), (177, 390)], [(280, 420), (353, 409), (427, 417)]]:
        c.line(pts, "#91e2d0", 2)

    # A single broad folded bridge crosses the river in the middle distance.
    c.poly([(0, 260), (450, 260), (450, 286), (368, 292), (286, 301),
            (220, 310), (151, 297), (76, 290), (0, 286)], "#493a83")
    c.poly([(0, 260), (450, 260), (450, 273), (367, 278), (286, 286),
            (220, 294), (151, 282), (76, 275), (0, 273)], "#f19b72")
    c.poly([(0, 260), (450, 260), (450, 268), (0, 268)], "#ffe092")
    # The bridge's tapered supports and arch face give it paper depth.
    c.poly([(54, 287), (83, 287), (106, 327), (79, 337)], "#7750a8")
    c.poly([(83, 287), (106, 327), (94, 332), (77, 295)], "#b360a2")
    c.poly([(345, 293), (373, 291), (388, 326), (361, 333)], "#684995")
    c.poly([(373, 291), (388, 326), (377, 329), (362, 296)], "#a353a1")
    c.poly([(0, 286), (75, 290), (152, 298), (220, 310), (286, 301),
            (370, 292), (450, 286), (450, 303), (371, 309), (288, 319),
            (219, 328), (151, 314), (74, 307), (0, 304)], "#3c397e")
    c.poly([(0, 286), (74, 290), (151, 298), (220, 310), (286, 301),
            (370, 292), (450, 286), (450, 293), (371, 300), (287, 309),
            (220, 317), (152, 305), (74, 297), (0, 294)], "#7350a8")
    # Foreground riverside road keeps the cyclist grounded without hiding the river.
    c.poly([(0, 380), (93, 371), (174, 383), (272, 370), (365, 385), (450, 373),
            (450, 408), (366, 418), (272, 404), (174, 419), (92, 407), (0, 416)], "#eaa36d")
    c.poly([(0, 380), (93, 371), (174, 383), (272, 370), (365, 385), (450, 373),
            (450, 385), (366, 397), (272, 383), (174, 396), (92, 384), (0, 393)], "#ffd07b")
    c.line([(14, 397), (97, 390), (171, 400), (270, 387)], "#fff0ae", 1.5)


def bicycle_actor(c: Canvas):
    # Wheels and spoke facets.
    for cx in (111, 198):
        c.ellipse((cx - 27, 339, cx + 27, 393), fill="#32365f", outline="#ffe1a0", width=3)
        c.ellipse((cx - 21, 345, cx + 21, 387), outline="#89d9db", width=1.4)
        for a in range(0, 360, 45):
            r = math.radians(a)
            c.line([(cx, 366), (cx + math.cos(r) * 20, 366 + math.sin(r) * 20)], "#a4d8db", 0.9)
        c.ellipse((cx - 3.5, 362.5, cx + 3.5, 369.5), fill="#ffd66e")

    # Angular frame, handlebar and folded fork.
    rear, crank, seat, head, front = (111, 366), (151, 366), (136, 340), (174, 342), (198, 366)
    tubes = [(rear, seat, "#f35b78"), (seat, head, "#ffc25d"),
             (head, front, "#52d4cf"), (front, crank, "#50c9ce"),
             (crank, seat, "#f27f69"), (crank, rear, "#62d6ba")]
    for a, b, color in tubes:
        c.line([a, b], color, 5.2)
        c.line([a, b], "#fff0bd", 1.05)
    c.line([(132, 338), (143, 338)], "#fff0c8", 3.5)
    c.line([(137, 339), (133, 334)], "#fff0c8", 2.4)
    c.line([(173, 341), (183, 333), (190, 334)], "#fff0c8", 3)
    c.line([(173, 341), (171, 334)], "#fff0c8", 2.3)
    c.ellipse((147, 362, 155, 370), fill="#ffcf61")
    c.line([(151, 366), (164, 375)], "#fff0c8", 1.5)

    # A bright folded rider: helmet, jacket, bent arms and legs.
    c.line([(144, 332), (155, 344), (172, 343), (181, 340)], "#ef6281", 7)
    c.line([(146, 333), (164, 330), (174, 337)], "#ffd276", 4.5)
    c.poly([(141, 323), (154, 320), (165, 332), (154, 340), (142, 336)], "#ec5d78")
    c.poly([(141, 323), (154, 320), (154, 340), (142, 336)], "#ff966f")
    c.line([(149, 333), (135, 352), (151, 366)], "#ffcc70", 5.2)
    c.line([(149, 333), (161, 348), (151, 366)], "#f07772", 4.5)
    c.ellipse((139, 298, 160, 320), fill="#f8c296")
    c.poly([(137, 306), (140, 296), (153, 292), (164, 300), (159, 307), (143, 305)], "#54d3cc")
    c.poly([(140, 297), (153, 292), (156, 301), (141, 303)], "#9ce9d3")
    c.line([(149, 310), (155, 311)], "#583e63", 1.2)


def bicycle_drift(c: Canvas):
    # Two tiny paper leaves sit in the foreground air, separate from the cyclist.
    c.poly([(46, 293), (56, 278), (69, 287), (61, 300)], "#ffcf60")
    c.poly([(56, 278), (69, 287), (61, 300)], "#f47b75")
    c.line([(48, 295), (62, 286)], "#fff0af", 1)
    c.poly([(386, 326), (396, 311), (409, 319), (399, 332)], "#5bd7ca")
    c.poly([(396, 311), (409, 319), (399, 332)], "#ffd477")


# ── Forest: emerald canopy, jewel pond, friendly frog and fireflies ─────────

def forest_environment(c: Canvas):
    # Enchanted emerald woodland: layered canopy, trunks, pond and a lily pad.
    c.poly([(0, 0), (450, 0), (450, 450), (0, 450)], "#0d513e")
    c.poly([(0, 0), (450, 0), (450, 215), (370, 195), (295, 215),
            (219, 188), (145, 215), (68, 194), (0, 220)], "#176849")
    # Broad overlapping canopy leaves frame a soft glade down the center.
    c.poly([(0, 0), (141, 0), (174, 48), (138, 92), (92, 81), (56, 129), (0, 111)], "#228450")
    c.poly([(0, 0), (78, 0), (115, 39), (81, 74), (38, 57), (0, 89)], "#61bd67")
    c.poly([(112, 0), (237, 0), (250, 46), (215, 84), (166, 60), (141, 29)], "#2f9b58")
    c.poly([(214, 0), (334, 0), (360, 42), (323, 81), (277, 59), (251, 38)], "#62bd62")
    c.poly([(326, 0), (450, 0), (450, 122), (402, 101), (363, 127), (337, 74), (368, 35)], "#237e4a")
    c.poly([(369, 0), (450, 0), (450, 76), (414, 58), (389, 88), (358, 54)], "#83ce69")
    # Soft shafts of mint light pass through the canopy behind the frog.
    c.poly([(185, 30), (219, 22), (249, 190), (214, 203)], "#26794d")
    c.poly([(250, 16), (273, 25), (291, 183), (269, 190)], "#388b4f")
    # Trunks stay at the dial edges; layered roots point toward the water.
    c.poly([(9, 88), (47, 86), (61, 319), (32, 361), (0, 336)], "#644c3d")
    c.poly([(12, 97), (32, 93), (39, 330), (17, 344), (0, 317)], "#92714a")
    c.poly([(402, 112), (438, 98), (450, 330), (419, 364), (391, 329)], "#5e4939")
    c.poly([(421, 108), (438, 101), (450, 318), (433, 343), (412, 319)], "#96754a")
    # Jewel-green water and a folded lily pad fill the lower dial.
    c.poly([(0, 267), (71, 250), (146, 269), (223, 247), (300, 270),
            (376, 249), (450, 269), (450, 450), (0, 450)], "#168273")
    c.poly([(0, 309), (71, 291), (148, 312), (226, 291), (304, 313),
            (382, 290), (450, 310), (450, 374), (373, 391), (297, 370),
            (222, 391), (148, 369), (72, 389), (0, 372)], "#43b790")
    c.poly([(0, 383), (80, 365), (157, 389), (235, 368), (313, 391),
            (391, 368), (450, 387), (450, 450), (0, 450)], "#187b72")
    c.ellipse((79, 377, 373, 452), fill="#145e50", outline="#85d879", width=2)
    c.poly([(94, 409), (141, 385), (223, 393), (301, 379), (357, 401),
            (323, 431), (159, 435)], "#54bd73")
    c.poly([(94, 409), (141, 385), (223, 393), (201, 414), (159, 435)], "#9ce17e")
    c.line([(223, 393), (223, 430)], "#d2f4a3", 2)
    # Fern fans at the lower corners echo the canopy without crowding the frog.
    for x, y, side in [(37, 303, 1), (405, 303, -1)]:
        c.line([(x, y + 76), (x, y)], "#53a85b", 3)
        for k in range(4):
            yy = y + 18 + k * 13
            c.poly([(x, yy), (x + side*25, yy - 18), (x + side*36, yy - 14),
                    (x + side*20, yy + 2)], "#50a85d")
            c.poly([(x, yy), (x + side*25, yy - 18), (x + side*19, yy - 4)], "#9cda69")


def forest_actor(c: Canvas):
    # A friendly folded frog sits low on the lily pad, with round golden eyes.
    c.poly([(169, 362), (144, 378), (126, 405), (146, 418), (179, 397)], "#217952")
    c.poly([(281, 362), (306, 378), (326, 405), (307, 418), (273, 397)], "#217952")
    c.poly([(167, 354), (185, 337), (216, 342), (242, 339), (273, 356),
            (296, 389), (281, 416), (168, 416), (153, 389)], "#23985e")
    c.poly([(167, 354), (185, 337), (216, 342), (225, 383), (196, 411), (168, 416), (153, 389)], "#54c36d")
    c.poly([(225, 383), (216, 342), (242, 339), (273, 356), (296, 389),
            (281, 416), (225, 416)], "#258957")
    c.poly([(188, 379), (225, 367), (262, 380), (250, 407), (201, 407)], "#a2df78")
    # Front feet curl over the pad with rounded toes.
    c.poly([(178, 393), (196, 400), (188, 418), (167, 426), (156, 418)], "#68cb71")
    c.poly([(252, 396), (270, 392), (294, 410), (288, 423), (265, 419)], "#59c46b")
    for x in (161, 175, 189, 277, 291, 305):
        c.ellipse((x-4, 411, x+5, 421), fill="#d5ef9c")
    # Cheeky head, broad smile and friendly eye stalks.
    c.poly([(151, 344), (155, 325), (176, 316), (197, 326),
            (224, 331), (251, 321), (274, 316), (294, 329),
            (298, 350), (280, 372), (253, 383), (193, 381), (164, 369)], "#3eb566")
    c.poly([(158, 349), (166, 330), (184, 324), (207, 340), (203, 363), (179, 371)], "#82d66e")
    c.poly([(207, 340), (224, 331), (251, 321), (274, 316), (292, 332),
            (290, 352), (269, 368), (239, 376), (203, 363)], "#49bc63")
    c.ellipse((168, 303, 214, 349), fill="#41b85f", outline="#267a51", width=2)
    c.ellipse((237, 303, 283, 349), fill="#41b85f", outline="#267a51", width=2)
    c.ellipse((174, 309, 209, 344), fill="#ffd86d")
    c.ellipse((243, 309, 278, 344), fill="#ffd86d")
    c.ellipse((184, 316, 201, 338), fill="#26394a")
    c.ellipse((253, 316, 270, 338), fill="#26394a")
    c.ellipse((187, 318, 193, 325), fill="#fff8d9")
    c.ellipse((256, 318, 262, 325), fill="#fff8d9")
    c.ellipse((202, 357, 208, 363), fill="#1b7652")
    c.ellipse((244, 357, 250, 363), fill="#1b7652")
    c.line([(205, 369), (223, 374), (243, 368)], "#1b7652", 1.7)


def forest_drift(c: Canvas):
    # Tiny golden and mint fireflies glow around the canopy and pond.
    for x, y, color, r in [(71, 148, "#ffe78a", 5), (122, 221, "#cbf48b", 4),
                           (350, 172, "#fff0a0", 5), (392, 253, "#b9ef9c", 4),
                           (52, 278, "#ffdf7b", 4), (320, 91, "#ffe897", 3),
                           (194, 205, "#f8f49a", 4), (273, 245, "#bdf3a5", 3),
                           (369, 325, "#ffe186", 4)]:
        c.ellipse((x-r, y-r, x+r, y+r), fill=(255, 237, 153, 80))
        c.ellipse((x-r/2, y-r/2, x+r/2, y+r/2), fill=color)
        c.line([(x-r-2, y), (x+r+2, y)], "#e9f8b3", 0.8)
        c.line([(x, y-r-2), (x, y+r+2)], "#e9f8b3", 0.8)


# ── Coding: luminous terminal glass, saturated desk, code on the right edge ──

def coding_environment(c: Canvas):
    # Oversized monitor shell and its folded luminous screen planes.
    c.poly([(31, 24), (414, 24), (396, 244), (50, 244)], "#252654")
    c.poly([(40, 31), (405, 31), (388, 229), (60, 229)], "#256e9a")
    c.poly([(40, 31), (200, 31), (207, 229), (60, 229)], "#3854a6")
    c.poly([(200, 31), (405, 31), (388, 229), (207, 229)], "#6f4aa5")
    c.poly([(40, 31), (405, 31), (405, 88), (40, 113)], "#303872")
    c.poly([(40, 113), (200, 102), (207, 229), (60, 229)], "#176b88")
    c.poly([(200, 102), (405, 88), (388, 229), (207, 229)], "#443d80")
    # Overlapping translucent-looking facets become paper reflections.
    c.poly([(49, 42), (172, 40), (198, 79), (62, 90)], "#527ac1")
    c.poly([(246, 41), (394, 38), (385, 83), (226, 91)], "#9a57a0")
    c.poly([(66, 134), (208, 119), (208, 218), (71, 222)], "#286e92")
    c.poly([(214, 115), (383, 101), (375, 215), (218, 218)], "#613f88")
    c.poly([(220, 118), (298, 111), (292, 169), (220, 176)], "#d74f9b")
    c.poly([(299, 111), (379, 104), (375, 155), (296, 164)], "#f07a7c")
    c.poly([(65, 143), (198, 131), (198, 143), (65, 155)], "#53d6d1")
    c.poly([(65, 168), (177, 157), (177, 168), (65, 179)], "#f5ca69")
    c.poly([(79, 194), (193, 185), (193, 196), (79, 205)], "#c57bd0")
    c.poly([(225, 188), (341, 178), (340, 187), (224, 198)], "#ffd06a")
    c.poly([(246, 204), (366, 194), (365, 202), (246, 213)], "#5addc7")
    # A small faceted status rail under the screen.
    c.poly([(60, 231), (388, 231), (385, 242), (60, 242)], "#91d9d6")
    c.poly([(60, 231), (220, 231), (220, 238), (60, 238)], "#e36a9a")

    # Angular stand, broad glowing desktop, and shallow keyboard plane.
    c.poly([(192, 243), (255, 243), (275, 297), (172, 297)], "#313b78")
    c.poly([(193, 243), (222, 243), (220, 291), (172, 297)], "#5462a5")
    c.poly([(26, 294), (418, 279), (450, 316), (0, 341)], "#cb5b8c")
    c.poly([(0, 310), (418, 279), (450, 294), (0, 337)], "#f18b80")
    c.poly([(0, 337), (450, 294), (450, 450), (0, 450)], "#342d69")
    c.poly([(0, 337), (450, 294), (450, 331), (0, 378)], "#5c3d8a")
    c.poly([(25, 354), (308, 328), (359, 351), (70, 385)], "#29305e")
    c.poly([(25, 354), (308, 328), (342, 343), (59, 375)], "#90c6d1")
    # Repeating paper keycaps add scale without turning the desk into visual noise.
    for row in range(3):
        for col in range(10 - row):
            x = 45 + col * 25 + row * 9
            y = 361 + row * 9
            color = ["#354375", "#3b4a80", "#345f83", "#59477f"][(col + row) % 4]
            c.poly([(x, y), (x + 18, y - 2), (x + 20, y + 3), (x + 2, y + 6)], color)
            if (row + col) % 4 == 0:
                c.poly([(x + 2, y), (x + 18, y - 2), (x + 17, y + 1), (x + 2, y + 3)], "#6fe0d0")
    c.poly([(315, 365), (422, 353), (440, 384), (329, 398)], "#e46698")
    c.poly([(315, 365), (422, 353), (430, 365), (322, 377)], "#ffc96a")
    c.poly([(324, 380), (430, 369), (439, 383), (330, 396)], "#7553a3")


def coding_actor(c: Canvas):
    # Folded code brackets and a floating syntax ribbon live at the screen edge.
    c.poly([(370, 183), (357, 198), (371, 212), (377, 207), (367, 198), (377, 188)], "#ff7e9c")
    c.poly([(397, 183), (410, 198), (397, 212), (391, 207), (401, 198), (391, 188)], "#69e1d1")
    c.poly([(386, 181), (379, 214), (386, 216), (393, 183)], "#ffd267")
    c.poly([(358, 222), (397, 218), (397, 223), (358, 227)], "#99d8e4")
    c.poly([(365, 231), (406, 226), (406, 231), (365, 236)], "#d68bd7")


def coding_cursor(c: Canvas):
    c.poly([(409, 219), (420, 218), (420, 235), (409, 236)], "#ffe071")
    c.poly([(409, 219), (420, 218), (416, 224), (409, 225)], "#fff4b9")


def coding_drift(c: Canvas):
    # Tiny angular chips drift over the lower desk as a distinct foreground plane.
    for x, y, color in [(374, 407, "#61dbce"), (402, 416, "#ff789d"), (341, 423, "#ffd36f")]:
        c.poly([(x, y), (x + 11, y - 4), (x + 17, y + 4), (x + 6, y + 8)], color)
        c.poly([(x + 6, y + 8), (x + 17, y + 4), (x + 14, y + 12), (x + 3, y + 15)], "#3e3b72")


# ── Kitten: colorful yarn world, plush cat and an independent mouse ─────────

def kitten_environment(c: Canvas):
    # A full-dial yarn world of large soft wool balls and looping ribbon.
    c.poly([(0, 0), (450, 0), (450, 450), (0, 450)], "#563a68")
    c.poly([(0, 0), (450, 0), (450, 231), (377, 214), (300, 232),
            (223, 210), (146, 236), (73, 213), (0, 236)], "#7b4b76")
    c.poly([(0, 237), (89, 218), (169, 239), (252, 219), (333, 240),
            (413, 218), (450, 228), (450, 450), (0, 450)], "#4a416c")
    # Faceted yarn balls anchor the corners with pink, cream and mint wool.
    c.poly(regular_polygon(80, 350, 94, 14), "#bc6e96")
    c.poly([(0, 315), (48, 261), (116, 273), (166, 329), (155, 398),
            (104, 448), (19, 428), (0, 398)], "#d987a1")
    c.poly([(0, 315), (48, 261), (82, 341), (19, 428), (0, 398)], "#f1adad")
    c.poly([(82, 341), (48, 261), (116, 273), (166, 329), (128, 366)], "#e99ab3")
    c.poly([(82, 341), (128, 366), (155, 398), (104, 448), (19, 428)], "#a65d8a")
    c.poly(regular_polygon(384, 95, 74, 14), "#86cda7")
    c.poly([(326, 42), (367, 21), (423, 41), (450, 94), (431, 143),
            (380, 167), (334, 142), (309, 94)], "#9fe0b0")
    c.poly([(326, 42), (367, 21), (384, 93), (334, 142), (309, 94)], "#c9edbb")
    c.poly([(384, 93), (367, 21), (423, 41), (450, 94), (431, 143)], "#72b994")
    c.poly([(325, 42), (367, 21), (384, 93), (352, 73)], "#ebd7c0")
    c.poly(regular_polygon(53, 139, 57, 12), "#927ab0")
    c.poly([(13, 100), (50, 77), (91, 104), (107, 147), (78, 191),
            (32, 187), (0, 156)], "#a991c5")
    c.poly([(13, 100), (50, 77), (57, 137), (32, 187), (0, 156)], "#d4bad4")
    c.poly([(57, 137), (50, 77), (91, 104), (107, 147), (78, 191)], "#786a9c")
    # Thick looping wool threads sweep through the whole composition.
    c.line([(0, 242), (46, 221), (88, 230), (113, 251), (95, 267), (66, 257),
            (56, 241), (79, 231), (109, 245), (137, 265), (172, 263)], "#f4c4c8", 7)
    c.line([(0, 246), (46, 225), (88, 234), (111, 252)], "#ffe8cf", 2)
    c.line([(282, 190), (317, 174), (357, 185), (377, 205), (361, 222),
            (331, 210), (322, 194), (346, 181), (380, 193), (415, 219), (450, 214)], "#e5a5c1", 7)
    c.line([(282, 186), (317, 170), (357, 181), (377, 201)], "#ffe1cb", 2)
    c.line([(25, 57), (88, 30), (147, 49), (168, 83), (149, 103)], "#de9fc2", 5)
    c.line([(28, 53), (88, 26), (147, 45)], "#f7d2d3", 1.8)
    c.poly([(0, 429), (93, 404), (181, 420), (262, 400), (350, 421), (450, 402),
            (450, 450), (0, 450)], "#413c62")


def kitten_actor(c: Canvas):
    # Plush full-body kitten with a round head, huge eyes and little pink paws.
    c.line([(151, 302), (125, 331), (105, 360), (119, 385), (149, 379)], "#d88b83", 24)
    c.line([(148, 304), (124, 333), (108, 360)], "#f2b5a7", 6)
    # Soft body silhouette and overlapping warm facets.
    c.ellipse((112, 151, 340, 430), fill="#c97778", outline="#8c5272", width=2)
    c.poly([(124, 212), (159, 170), (204, 185), (219, 272), (188, 369),
            (126, 388), (109, 331)], "#e99b83")
    c.poly([(219, 272), (204, 185), (257, 168), (306, 198), (340, 300),
            (322, 385), (251, 408), (188, 369)], "#d4847c")
    c.ellipse((155, 263, 302, 413), fill="#f0ba9b")
    c.poly([(165, 309), (220, 278), (278, 310), (265, 391), (217, 415), (164, 390)], "#ffe0bd")
    c.poly([(220, 278), (278, 310), (302, 359), (265, 391), (247, 334)], "#f6c9a7")
    # Rounded cheeks and ears frame the face, with gentle paper folds.
    c.poly([(123, 93), (126, 59), (147, 36), (190, 48), (219, 57),
            (251, 47), (294, 39), (323, 67), (323, 111), (312, 148),
            (288, 172), (252, 184), (188, 181), (151, 164), (128, 135)], "#d58a7d")
    c.poly([(130, 77), (135, 37), (178, 54), (177, 93)], "#ecaa91")
    c.poly([(267, 54), (306, 36), (318, 78), (283, 95)], "#e9a28d")
    c.poly([(139, 77), (143, 47), (170, 59), (166, 89)], "#f5afc1")
    c.poly([(278, 59), (302, 46), (310, 77), (287, 91)], "#f2b0bf")
    c.ellipse((134, 72, 214, 158), fill="#e9a082")
    c.ellipse((234, 71, 314, 158), fill="#d98479")
    c.poly([(145, 115), (168, 80), (217, 63), (232, 108), (212, 142), (175, 151)], "#f1b691")
    c.poly([(232, 108), (217, 63), (253, 53), (292, 72), (309, 114), (279, 150), (246, 144)], "#e89b83")
    c.poly([(145, 121), (178, 146), (218, 128), (232, 156), (210, 177), (169, 165), (138, 143)], "#f7c8a4")
    c.poly([(232, 156), (218, 128), (246, 144), (279, 150), (309, 120),
            (307, 146), (282, 171), (250, 182)], "#cd7c76")
    # Huge round jewel eyes sit well above the date strip.
    for box, iris in [((157, 65, 205, 111), "#60a89a"), ((245, 65, 293, 111), "#6fae9d")]:
        c.ellipse(box, fill="#fff1d4", outline="#a66072", width=2)
        x0, y0, x1, y1 = box
        c.ellipse((x0+7, y0+5, x1-5, y1-3), fill=iris)
        c.ellipse((x0+15, y0+7, x1-12, y1-3), fill="#263a4e")
        c.ellipse((x0+17, y0+9, x0+25, y0+17), fill="#fffdf0")
        c.ellipse((x1-17, y1-14, x1-12, y1-9), fill="#d7f7ec")
    # Tiny heart-shaped pink nose, smile and soft whiskers.
    c.poly([(207, 104), (216, 99), (224, 104), (232, 99), (241, 105),
            (235, 114), (224, 118), (213, 114)], "#e97591")
    c.ellipse((212, 102, 219, 108), fill="#ffb2c0")
    c.line([(224, 116), (224, 126), (216, 132)], "#8b5967", 1.7)
    c.line([(224, 126), (233, 132)], "#8b5967", 1.7)
    c.ellipse((160, 127, 188, 146), fill="#ef9b9e")
    c.ellipse((262, 127, 290, 146), fill="#ef9b9e")
    for pts in [[(211, 119), (181, 121), (159, 115)], [(211, 126), (181, 136), (158, 138)],
                [(237, 119), (267, 121), (291, 115)], [(237, 126), (267, 136), (292, 138)]]:
        c.line(pts, "#ffe8d2", 1.3)
    # Small cream paws peek out beneath the plush belly.
    c.ellipse((139, 389, 208, 438), fill="#ffe0bf", outline="#bd767e", width=1.4)
    c.ellipse((244, 389, 313, 438), fill="#ffe0bf", outline="#bd767e", width=1.4)
    for x in (161, 179, 266, 284):
        c.line([(x, 420), (x+2, 428)], "#de98a0", 1.2)


def kitten_drift(c: Canvas):
    # A side-on mouse faces right and runs independently along the lower dial.
    c.line([(292, 324), (278, 333), (270, 345), (277, 351)], "#8f6275", 2.6)
    c.ellipse((285, 301, 337, 342), fill="#a68796", outline="#6b536d", width=1.5)
    c.poly([(312, 306), (332, 298), (350, 313), (344, 331), (329, 340), (309, 332)], "#b79aa1")
    c.ellipse((314, 297, 328, 314), fill="#d99cae")
    c.ellipse((331, 302, 343, 317), fill="#d99cae")
    c.ellipse((333, 313, 339, 319), fill="#293746")
    c.poly([(346, 318), (356, 322), (347, 328), (340, 324)], "#ed8da2")
    c.ellipse((293, 333, 304, 339), fill="#f2c7c7")
    c.ellipse((322, 335, 333, 341), fill="#f2c7c7")


# ── Landscape: saturated mountain bowl, faceted sunset and reflective lake ──

def landscape_environment(c: Canvas):
    # Distant peaks and folded ridgelines in rainbow sunset light.
    c.poly([(0, 184), (47, 146), (91, 178), (151, 110), (216, 176),
            (271, 129), (333, 185), (391, 145), (450, 178), (450, 306), (0, 306)], "#7043a4")
    c.poly([(0, 184), (47, 146), (91, 178), (60, 166), (47, 153), (22, 198)], "#bc5cb1")
    c.poly([(91, 178), (151, 110), (216, 176), (183, 156), (151, 126), (126, 192)], "#e264a0")
    c.poly([(216, 176), (271, 129), (333, 185), (300, 164), (271, 143), (246, 197)], "#9c4b9b")
    c.poly([(333, 185), (391, 145), (450, 178), (450, 225), (411, 166), (381, 197)], "#dc648e")
    c.poly([(0, 221), (76, 181), (134, 212), (211, 171), (271, 214),
            (343, 180), (450, 222), (450, 316), (0, 316)], "#e27686")
    c.poly([(0, 221), (76, 181), (134, 212), (102, 200), (76, 189), (44, 237)], "#f5a078")
    c.poly([(134, 212), (211, 171), (271, 214), (238, 196), (211, 184), (180, 231)], "#c15c93")
    c.poly([(271, 214), (343, 180), (450, 222), (406, 207), (343, 191), (314, 231)], "#fa9b78")
    # Lower slopes fan outward like folded paper into the lake.
    c.poly([(0, 264), (84, 225), (157, 258), (223, 222), (299, 265),
            (365, 231), (450, 265), (450, 338), (0, 338)], "#a44e97")
    c.poly([(0, 264), (84, 225), (157, 258), (124, 248), (84, 235), (49, 281)], "#e77491")
    c.poly([(157, 258), (223, 222), (299, 265), (264, 251), (223, 236), (195, 279)], "#f6a45f")
    c.poly([(299, 265), (365, 231), (450, 265), (418, 257), (365, 243), (336, 286)], "#dc6a92")

    # The lake is a wide jewel-blue plane, broken by horizontal reflections.
    c.poly([(0, 272), (69, 285), (145, 269), (220, 287), (304, 270),
            (377, 288), (450, 273), (450, 450), (0, 450)], "#286f9f")
    c.poly([(0, 297), (68, 305), (143, 291), (218, 307), (303, 291),
            (378, 308), (450, 293), (450, 345), (379, 359), (303, 342),
            (218, 359), (143, 341), (68, 358), (0, 346)], "#49b4b7")
    c.poly([(0, 346), (72, 359), (147, 344), (223, 364), (303, 346),
            (379, 365), (450, 348), (450, 393), (375, 407), (302, 388),
            (222, 408), (147, 388), (72, 405), (0, 392)], "#287eaa")
    c.poly([(0, 407), (79, 395), (157, 412), (228, 399), (306, 417),
            (378, 398), (450, 414), (450, 450), (0, 450)], "#235b8f")
    for pts, color in [([(34, 320), (94, 316), (129, 321)], "#f7b67b"),
                       ([(239, 324), (284, 320), (341, 327)], "#ffe08a"),
                       ([(80, 373), (143, 369), (177, 375)], "#9ce0d2"),
                       ([(310, 377), (376, 370), (425, 375)], "#f1a1a1"),
                       ([(177, 431), (225, 425), (267, 432)], "#78cbd0")]:
        c.line(pts, color, 2.2)
    # Near shore folds along the bottom edge.
    c.poly([(0, 425), (118, 407), (210, 431), (314, 411), (450, 433),
            (450, 450), (0, 450)], "#493875")
    c.poly([(0, 425), (118, 407), (210, 431), (314, 411), (450, 433),
            (450, 442), (314, 423), (210, 443), (118, 419), (0, 438)], "#d86688")


def landscape_actor(c: Canvas):
    # Large, softly faceted paper sun, intentionally behind the time glass.
    cx, cy, r = 364, 222, 42
    c.poly(regular_polygon(cx, cy, r, 16), "#ffd56b")
    c.poly([(cx, cy), (cx + 42, cy), (cx + 30, cy + 30), (cx + 1, cy + 41)], "#f28b6c")
    c.poly([(cx, cy), (cx - 30, cy + 29), (cx - 42, cy), (cx - 27, cy - 30)], "#fff0a2")
    c.poly([(cx, cy), (cx - 27, cy - 30), (cx, cy - 42), (cx + 24, cy - 31)], "#ffbc62")


def landscape_drift(c: Canvas):
    # A distant folded cloud passes through the upper left sky.
    c.poly([(65, 82), (80, 70), (96, 74), (106, 63), (123, 68),
            (135, 83), (124, 91), (75, 92)], "#f0a6b2")
    c.poly([(65, 82), (80, 70), (95, 76), (78, 87)], "#ffd294")
    c.poly([(96, 76), (106, 63), (123, 68), (135, 83), (111, 82)], "#ffe6ac")
    c.poly([(325, 110), (337, 103), (350, 106), (358, 115), (346, 121), (329, 118)], "#e88d9c")


# ── Cosmos: open deep space, one ringed planet and a paper rocket ────────────

def cosmos_environment(c: Canvas):
    # Open deep-space gradient, one large ringed planet, and a few tiny stars.
    # The gradient beneath this layer supplies the navy-to-teal color field.
    c.ellipse((266, 39, 441, 149), outline="#b77e85", width=9)
    c.ellipse((269, 37, 438, 147), outline="#f3d19a", width=2)
    c.poly(regular_polygon(352, 91, 53, 18), "#3e8294")
    c.poly([(301, 91), (312, 58), (339, 40), (369, 42), (392, 62),
            (404, 92), (389, 121), (361, 143), (329, 136), (307, 116)], "#4e9b9c")
    c.poly([(301, 91), (312, 58), (339, 40), (352, 91), (329, 136), (307, 116)], "#79d4c3")
    c.poly([(352, 91), (339, 40), (369, 42), (392, 62), (404, 92),
            (389, 121), (361, 143)], "#3e688f")
    c.poly([(312, 58), (339, 40), (352, 91), (329, 78)], "#b8e6ce")
    lower_ring = [(353 + 86*math.cos(math.radians(a)), 94 + 49*math.sin(math.radians(a)))
                  for a in range(12, 170, 8)]
    c.line(lower_ring, "#d9a875", 9)
    c.line(lower_ring, "#ffedbf", 1.8)
    for x, y, r, col in [(61, 64, 4, "#fff0a8"), (183, 165, 3, "#73e4d1"),
                         (72, 272, 4, "#eca1c5"), (412, 215, 3, "#ffe08a"),
                         (45, 386, 3, "#7be4d2"), (402, 354, 4, "#efa5d0"),
                         (211, 421, 3, "#ffe18c")]:
        c.poly([(x, y-r), (x+1, y-1), (x+r, y), (x+1, y+1),
                (x, y+r), (x-1, y+1), (x-r, y), (x-1, y-1)], col)


def cosmos_actor(c: Canvas):
    # Draw an anatomical retro rocket horizontally, then rotate its full
    # capsule, fins, nose, porthole and plume 45 degrees toward the northeast.
    local = Image.new("RGBA", (HI, HI), (0, 0, 0, 0))
    r = Canvas(ImageDraw.Draw(local))
    # Long rounded silver capsule body.
    r.rounded((157, 291, 259, 329), 18, fill="#dce5eb", outline="#71869e", width=2)
    r.poly([(164, 294), (235, 294), (235, 308), (164, 308)], "#f8f8ed")
    r.poly([(164, 310), (235, 310), (251, 325), (164, 325)], "#9eafc2")
    # Distinct red pointed nose cone.
    r.poly([(247, 291), (272, 310), (247, 329)], "#e4475f", outline="#a82e4d", width=1.5)
    r.poly([(247, 291), (272, 310), (252, 306)], "#ff8a79")
    # Two red tail fins and a bright orange/yellow engine plume.
    r.poly([(168, 294), (151, 277), (148, 302), (168, 311)], "#e4475f")
    r.poly([(168, 326), (151, 344), (148, 319), (168, 309)], "#d8405c")
    r.poly([(158, 300), (135, 288), (140, 310), (135, 332), (159, 320)], "#ff714f")
    r.poly([(158, 303), (143, 297), (147, 310), (143, 323), (159, 317)], "#ffcf5e")
    r.poly([(157, 307), (147, 304), (151, 311), (148, 318), (159, 314)], "#fff0ad")
    # Circular cyan porthole with a polished light rim.
    r.ellipse((200, 298, 226, 322), fill="#263a5b", outline="#fff2d0", width=3)
    r.ellipse((204, 302, 221, 318), fill="#62d4d5")
    r.poly([(205, 304), (215, 302), (221, 308), (211, 311)], "#b8f2df")
    r.poly([(211, 311), (221, 308), (220, 316), (208, 317)], "#3d87a1")
    r.line([(178, 293), (232, 293)], "#fffef1", 1.5)
    # Rotate around the center so the nose points northeast and exhaust southwest.
    angled = local.rotate(45, resample=Image.Resampling.BICUBIC,
                          center=(210 * SCALE, 310 * SCALE), fillcolor=(0, 0, 0, 0))
    c.d._image.alpha_composite(angled)


def cosmos_drift(c: Canvas):
    # Small bright sparks cluster southwest of the rocket's engine exhaust.
    for x, y, r, color in [(124, 365, 5, "#ffe16d"), (139, 386, 4, "#7de4d2"),
                           (157, 374, 4, "#ff8b79"), (111, 381, 3, "#e999c0"),
                           (171, 362, 3, "#fff0b2"), (130, 405, 3, "#ffcc6e")]:
        c.poly([(x, y-r), (x+2, y-1), (x+r, y), (x+1, y+2),
                (x, y+r), (x-2, y+1), (x-r, y), (x-1, y-2)], color)
        c.poly([(x, y-r), (x+2, y-1), (x, y)], "#fff8d9")


def ocean_environment(c: Canvas):
    # Layered sea bands fill the dial with turquoise water and folded foam.
    c.poly([(0, 46), (70, 29), (143, 43), (222, 28), (300, 45),
            (374, 29), (450, 44), (450, 450), (0, 450)], "#167d9a")
    c.poly([(0, 90), (58, 77), (123, 93), (195, 75), (268, 92),
            (340, 76), (411, 91), (450, 82), (450, 153), (365, 166),
            (288, 148), (212, 166), (131, 147), (52, 166), (0, 153)], "#39b9b4")
    c.poly([(0, 173), (77, 157), (152, 176), (227, 155), (304, 177),
            (379, 157), (450, 174), (450, 260), (368, 279), (291, 257),
            (216, 278), (137, 257), (61, 280), (0, 260)], "#207d9e")
    c.poly([(0, 258), (81, 239), (161, 261), (239, 242), (319, 263),
            (398, 240), (450, 255), (450, 350), (367, 370), (287, 350),
            (207, 373), (124, 351), (48, 373), (0, 361)], "#1a668d")
    c.poly([(0, 354), (72, 336), (152, 357), (232, 338), (313, 359),
            (393, 338), (450, 356), (450, 450), (0, 450)], "#154c78")
    for pts, col, w in [([(0, 112), (55, 102), (111, 113), (145, 108)], "#a4f0d8", 3),
                        ([(294, 125), (343, 111), (392, 123), (450, 111)], "#d2f4d6", 2),
                        ([(0, 211), (47, 202), (94, 211)], "#78ddd0", 2),
                        ([(339, 218), (387, 204), (450, 214)], "#9ae9d3", 2),
                        ([(29, 317), (82, 306), (121, 315)], "#78ced0", 2),
                        ([(318, 321), (371, 307), (419, 315)], "#83dbd0", 2)]:
        c.line(pts, col, w)
    # Folded foam edges and a pale diagonal surface current.
    c.poly([(0, 0), (450, 0), (450, 37), (376, 51), (296, 34),
            (214, 50), (135, 31), (57, 48), (0, 38)], "#47beb6")
    c.poly([(0, 38), (57, 48), (135, 31), (214, 50), (296, 34),
            (376, 51), (450, 37), (450, 50), (376, 63), (296, 48),
            (214, 64), (135, 46), (57, 63), (0, 52)], "#b0f0dc")


def ocean_actor(c: Canvas):
    # A broad blue-green paper whale glides right through the sea.
    c.poly([(119, 274), (100, 254), (99, 232), (121, 246), (143, 252),
            (154, 269)], "#247d9b")
    c.poly([(120, 274), (99, 232), (137, 248), (155, 267)], "#71d9cf")
    c.poly([(137, 257), (164, 231), (203, 218), (255, 222), (302, 238),
            (342, 257), (357, 279), (338, 304), (301, 323), (254, 336),
            (204, 330), (164, 312), (135, 291)], "#247d9b")
    c.poly([(137, 257), (164, 231), (203, 218), (230, 252), (203, 297), (164, 312), (135, 291)], "#52c4be")
    c.poly([(230, 252), (203, 218), (255, 222), (302, 238), (342, 257), (300, 277)], "#58d2c7")
    c.poly([(203, 297), (230, 252), (300, 277), (338, 304), (301, 323), (254, 336), (204, 330)], "#1d6d91")
    c.poly([(164, 312), (203, 297), (254, 336), (204, 330)], "#a6e5d1")
    c.poly([(189, 269), (216, 280), (241, 301), (225, 308), (197, 292)], "#328eaa")
    # Curved forehead, smiling mouth, tiny eye and a water spout.
    c.ellipse((321, 254, 329, 262), fill="#193956")
    c.ellipse((323, 255, 326, 258), fill="#f7f0d5")
    c.line([(325, 279), (346, 282), (353, 277)], "#e2f4d8", 1.8)
    c.poly([(275, 225), (286, 209), (297, 216), (290, 236)], "#41c4bc")
    c.line([(286, 214), (276, 199), (282, 188)], "#a8efdc", 2)
    c.line([(290, 215), (294, 197), (302, 190)], "#dbf6d9", 2)


def ocean_drift(c: Canvas):
    # Bubbles float just ahead of and above the whale.
    for x, y, r in [(350, 208, 8), (380, 241, 6), (321, 179, 5),
                    (91, 193, 7), (61, 222, 4), (294, 194, 4), (398, 293, 5)]:
        c.ellipse((x-r, y-r, x+r, y+r), fill=(164, 239, 225, 58), outline="#b7f5e1", width=1.5)
        c.ellipse((x-r+3, y-r+2, x-r+6, y-r+5), fill="#f1ffe2")


def aurora_environment(c: Canvas):
    # Amber and scarlet aurora over a burgundy polar night and cream snow.
    c.poly([(0, 0), (450, 0), (450, 245), (375, 224), (300, 242),
            (224, 219), (149, 243), (73, 220), (0, 243)], "#3d1e39")
    c.poly([(0, 236), (76, 213), (151, 236), (226, 214), (301, 238),
            (376, 215), (450, 237), (450, 302), (374, 320), (298, 298),
            (224, 321), (149, 298), (74, 319), (0, 300)], "#6a3045")
    # Folded snow shelves glow in warm apricot and honey tones.
    c.poly([(0, 257), (62, 226), (119, 255), (184, 232), (248, 264),
            (313, 237), (377, 265), (420, 236), (450, 255), (450, 450), (0, 450)], "#9f5960")
    c.poly([(0, 290), (70, 261), (137, 288), (204, 264), (274, 295),
            (342, 266), (414, 294), (450, 279), (450, 450), (0, 450)], "#e3a77b")
    c.poly([(0, 330), (75, 302), (153, 327), (229, 301), (306, 331),
            (382, 303), (450, 326), (450, 450), (0, 450)], "#f3d6a4")
    c.poly([(0, 385), (83, 359), (164, 382), (246, 356), (330, 385),
            (411, 358), (450, 369), (450, 450), (0, 450)], "#fff0cf")
    c.poly([(0, 421), (111, 393), (220, 419), (333, 390), (450, 420),
            (450, 450), (0, 450)], "#d9ac8d")
    c.poly([(0, 278), (62, 226), (119, 255), (83, 252), (62, 240), (28, 292)], "#b36b69")
    c.poly([(343, 261), (420, 236), (450, 255), (450, 295), (413, 251), (380, 283)], "#bd776b")
    for x, y, r in [(47, 160, 4), (148, 183, 3), (307, 167, 4), (407, 143, 3)]:
        c.poly([(x, y-r), (x+2, y-1), (x+r, y), (x, y+r), (x-r, y)], "#ffe8c1")


def aurora_actor(c: Canvas):
    # A golden-red paper fox stands against the snow.
    c.line([(162, 376), (134, 366), (118, 346), (126, 328), (151, 340)], "#aa503e", 19)
    c.line([(159, 375), (134, 365), (121, 349)], "#ffd17b", 5)
    c.poly([(165, 324), (181, 294), (211, 281), (240, 290), (270, 286),
            (299, 309), (318, 356), (311, 421), (145, 421), (136, 359)], "#a94b3e")
    c.poly([(165, 324), (181, 294), (211, 281), (224, 324), (190, 372), (145, 393), (136, 359)], "#f0a052")
    c.poly([(224, 324), (211, 281), (240, 290), (270, 286), (299, 309),
            (318, 356), (270, 374), (231, 361)], "#cf633e")
    c.poly([(190, 372), (224, 324), (231, 361), (270, 374), (249, 421), (163, 421)], "#ffd48d")
    c.poly([(231, 361), (270, 374), (318, 356), (311, 421), (249, 421)], "#983e3c")
    c.poly([(163, 403), (205, 392), (224, 407), (218, 423), (157, 423)], "#fff0d4")
    c.poly([(239, 402), (273, 390), (301, 407), (304, 423), (238, 423)], "#fff0d4")
    # Pointed fox ears and a warm cream muzzle.
    c.poly([(163, 326), (169, 276), (208, 303), (225, 287), (244, 300),
            (285, 273), (295, 329), (280, 362), (249, 383), (188, 371)], "#ad4e3d")
    c.poly([(170, 321), (176, 286), (205, 310), (190, 337)], "#ffd080")
    c.poly([(250, 306), (282, 283), (290, 328), (269, 339)], "#ffc676")
    c.poly([(190, 329), (211, 312), (228, 326), (218, 349), (195, 351)], "#ffdc9a")
    c.poly([(228, 326), (249, 312), (270, 333), (254, 352), (234, 349)], "#e99558")
    c.poly([(209, 348), (228, 341), (247, 350), (227, 368), (207, 360)], "#fff2d5")
    c.ellipse((199, 329, 206, 336), fill="#473342")
    c.ellipse((251, 329, 258, 336), fill="#473342")
    c.ellipse((201, 329, 204, 332), fill="#fff7de")
    c.ellipse((253, 329, 256, 332), fill="#fff7de")
    c.poly([(219, 348), (229, 344), (237, 350), (228, 356)], "#573a40")


def aurora_drift(c: Canvas):
    # Independent amber, coral and scarlet light curtains flow down the sky.
    c.poly([(35, 0), (80, 0), (102, 49), (96, 99), (126, 164),
            (114, 220), (88, 202), (75, 145), (81, 93), (59, 47)], (251, 166, 87, 190))
    c.poly([(35, 0), (60, 0), (84, 47), (78, 103), (101, 165), (92, 207),
            (75, 143), (80, 92), (59, 47)], (255, 220, 146, 207))
    c.poly([(151, 0), (204, 0), (222, 54), (207, 110), (229, 171),
            (211, 225), (189, 199), (181, 143), (193, 93), (174, 48)], (226, 75, 83, 184))
    c.poly([(151, 0), (179, 0), (199, 48), (188, 103), (208, 161),
            (195, 209), (181, 143), (193, 93), (174, 48)], (255, 150, 101, 202))
    c.poly([(291, 0), (343, 0), (365, 44), (354, 104), (385, 165),
            (369, 221), (345, 199), (336, 143), (347, 88), (322, 42)], (246, 126, 79, 185))
    c.poly([(291, 0), (319, 0), (340, 42), (331, 96), (354, 155),
            (345, 207), (336, 143), (347, 88), (322, 42)], (255, 206, 127, 204))


SCENES = {
    "bicycle": {
        "stops": [(0, "#5b327e"), (0.35, "#e45e8c"), (0.65, "#ffb867"), (1, "#2a7193")],
        "background": bicycle_environment, "motion": bicycle_actor, "drift": bicycle_drift,
    },
    "forest": {
        "stops": [(0, "#15583e"), (0.34, "#238a51"), (0.68, "#146d70"), (1, "#124e60")],
        "background": forest_environment, "motion": forest_actor, "drift": forest_drift,
    },
    "coding": {
        "stops": [(0, "#201e59"), (0.48, "#3b326f"), (1, "#613869")],
        "background": coding_environment, "motion": coding_actor, "drift": coding_drift,
    },
    "kitten": {
        "stops": [(0, "#91516f"), (0.42, "#bc6d8d"), (0.72, "#68517d"), (1, "#393b68")],
        "background": kitten_environment, "motion": kitten_actor, "drift": kitten_drift,
        "motion_offset": (0, -18),
    },
    "landscape": {
        "stops": [(0, "#652e83"), (0.3, "#d54c9a"), (0.58, "#ff956f"), (1, "#246c9c")],
        "background": landscape_environment, "motion": landscape_actor, "drift": landscape_drift,
    },
    "cosmos": {
        "stops": [(0, "#111e3f"), (0.4, "#1b3454"), (0.75, "#142f4e"), (1, "#111b3a")],
        "background": cosmos_environment, "motion": cosmos_actor, "drift": cosmos_drift,
        "drift_below_actor": True,
    },
    "ocean": {
        "stops": [(0, "#42c0b2"), (0.22, "#167d9a"), (0.62, "#1a668d"), (1, "#123c68")],
        "background": ocean_environment, "motion": ocean_actor, "drift": ocean_drift,
        "motion_offset": (0, 100),
    },
    "aurora": {
        "stops": [(0, "#321b35"), (0.38, "#692d47"), (0.68, "#b25353"), (1, "#f0bd8f")],
        "background": aurora_environment, "motion": aurora_actor, "drift": aurora_drift,
        "drift_below_actor": True,
    },
}


def render_static(name):
    spec = SCENES[name]
    bg = gradient(spec["stops"])
    env = art_layer(spec["background"], blur=3.2, offset=(0, 3), shadow_alpha=62)
    return Image.alpha_composite(bg, env).convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def render_transparent(painter, scale=1.0, center=(225, 225)):
    layer = art_layer(painter, blur=3.2, offset=(0, 3), shadow_alpha=88)
    layer = layer.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    if isinstance(scale, (tuple, list)):
        sx, sy = scale
    else:
        sx = sy = scale
    if sx != 1.0 or sy != 1.0:
        cx, cy = center
        layer = layer.transform(
            (SIZE, SIZE), Image.Transform.AFFINE,
            (1 / sx, 0, cx - cx / sx, 0, 1 / sy, cy - cy / sy),
            resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0),
        )
    return layer


def translate(layer, dx=0, dy=0):
    return layer.transform((SIZE, SIZE), Image.Transform.AFFINE,
                           (1, 0, -dx, 0, 1, -dy), resample=Image.Resampling.BICUBIC)


def assemble(scene, motion, drift, motion_offset=(0, 0), drift_offset=(0, 0), drift_below=False):
    out = scene.convert("RGBA")
    if drift_below:
        out.alpha_composite(translate(drift, *drift_offset))
        out.alpha_composite(translate(motion, *motion_offset))
    else:
        out.alpha_composite(translate(motion, *motion_offset))
        out.alpha_composite(translate(drift, *drift_offset))
    return out


def feathered_glass(scene):
    """Scene-aware translucent blur plates with feathered edges and no borders."""
    blurred = scene.convert("RGB").filter(ImageFilter.GaussianBlur(6))
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # Date and time dissolve beyond their text bounds; small lower plates stay
    # lightly tinted so the scene color remains visible around their icons.
    plates = [((35, 117, 415, 149), 18, 110, 0.40, 13.0),
              ((50, 145, 400, 267), 42, 154, 0.48, 19.0),
              ((50, 273, 195, 315), 14, 112, 0.30, 4.0),
              ((255, 273, 400, 315), 14, 112, 0.30, 4.0)]
    for box, radius, alpha, tint, feather in plates:
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
        patch = blurred.copy()
        navy = Image.new("RGB", patch.size, (13, 20, 43))
        patch = Image.blend(patch, navy, tint).convert("RGBA")
        patch.putalpha(mask.point(lambda a: round(a * alpha / 255)))
        layer = Image.alpha_composite(layer, patch)
    return layer


def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def native_clock():
    paths = [OUT / f"clock_{digit}.png" for digit in "1008"]
    paths.insert(2, OUT / "clock_colon.png")
    if not all(path.exists() for path in paths):
        return None
    glyphs = [Image.open(path).convert("RGBA") for path in paths]
    clock = Image.new("RGBA", (sum(glyph.width for glyph in glyphs), 96), (0, 0, 0, 0))
    cursor = 0
    for glyph in glyphs:
        clock.alpha_composite(glyph, (cursor, 0))
        cursor += glyph.width
    return clock


def draw_complications(draw):
    # Native-sized 24px battery and walking-person icons, with values only.
    draw.rounded_rectangle((52, 286, 69, 302), radius=3,
                           outline=(255, 225, 162, 255), width=2)
    draw.rectangle((57, 283, 64, 286), fill=(255, 225, 162, 255))
    draw.rounded_rectangle((55, 289, 66, 299), radius=2,
                           fill=(255, 211, 105, 255))
    # Person silhouette: head, body, one arm and a walking stride.
    draw.ellipse((267, 282, 273, 288), fill=(119, 236, 222, 255))
    draw.line([(270, 289), (268, 297), (263, 302)], fill=(119, 236, 222, 255), width=3)
    draw.line([(269, 292), (276, 297), (281, 297)], fill=(119, 236, 222, 255), width=3)
    draw.line([(269, 296), (275, 302), (275, 307)], fill=(119, 236, 222, 255), width=3)
    draw.line([(268, 297), (264, 304), (260, 306)], fill=(119, 236, 222, 255), width=3)
    draw.text((136.5, 294), "82%", font=font(28, True),
              fill=(255, 232, 173, 255), anchor="mm")
    draw.text((341.5, 294), "6,248", font=font(28, True),
              fill=(166, 236, 230, 255), anchor="mm")


def add_watch_content(face, glass, clock):
    overlay = glass.copy()
    d = ImageDraw.Draw(overlay)
    d.text((225, 133), "SUN  ·  OCT 25", font=font(28, True),
           fill=(239, 243, 255, 255), anchor="mm")
    if clock is not None:
        overlay.alpha_composite(clock, (95, 158))
    else:
        d.text((225, 206), "10:08", font=font(68, True), fill=(255, 240, 221, 255), anchor="mm")
    draw_complications(d)
    out = face.convert("RGBA")
    out.alpha_composite(overlay)
    return out


def circular_crop(face):
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, face.width - 1, face.height - 1), fill=255)
    result = face.convert("RGBA")
    result.putalpha(ImageChops.multiply(result.getchannel("A"), mask))
    return result


def picker_preview(face, glass, clock):
    return circular_crop(add_watch_content(face, glass, clock))


def add_mockup(face, glass, clock):
    window = circular_crop(face.resize((408, 408), Image.Resampling.LANCZOS))
    rim = Image.new("RGBA", (422, 422), (0, 0, 0, 0))
    d = ImageDraw.Draw(rim)
    d.ellipse((1, 1, 420, 420), fill=(49, 55, 83, 255), outline=(139, 152, 190, 210), width=2)
    rim.alpha_composite(window, (7, 7))
    framed_content = add_watch_content(face, glass, clock).resize((408, 408), Image.Resampling.LANCZOS)
    rim.alpha_composite(circular_crop(framed_content), (7, 7))
    ImageDraw.Draw(rim).ellipse((8, 8, 413, 413), outline=(218, 222, 243, 82), width=1)
    return rim


def contact_sheet(faces, glasses, clock):
    names = list(SCENES)
    cell_w, cell_h, gap = 478, 492, 20
    columns = 4
    rows = math.ceil(len(names) / columns)
    sheet = Image.new("RGB", (gap + columns * (cell_w + gap), gap + rows * (cell_h + gap)), "#11172c")
    d = ImageDraw.Draw(sheet)
    for idx, name in enumerate(names):
        col, row = idx % columns, idx // columns
        x, y = gap + col * (cell_w + gap), gap + row * (cell_h + gap)
        d.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=28,
                            fill="#1a2340", outline="#394765", width=2)
        d.text((x + 22, y + 23), name.upper(), font=font(17, True), fill="#e7edff")
        d.text((x + cell_w - 22, y + 23), "FOLD & TICK", font=font(10, True), fill="#a3aec8", anchor="ra")
        dial = add_mockup(faces[name], glasses[name], clock)
        sheet.paste(dial, (x + (cell_w - dial.width) // 2, y + 58), dial)
    return sheet


def alpha_layer(layer, opacity):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda a: round(a * opacity)))
    return out


def make_motion_gif(path, scene, motion, drift, glass, clock, route, drift_below=False):
    frames = []
    # Every proof is a 10-second native-matched route with both actors offscreen
    # at the loop seam. GIF delays are exact 100ms increments.
    frame_count = 100
    for i in range(frame_count):
        t = i / (frame_count - 1)
        if route == "bicycle":
            offset = (round(-300 + 720 * t), 0)
            drift_offset = (round(math.sin(i * math.tau / frame_count) * 12),
                            round(math.cos(i * math.tau / frame_count) * 8))
            actor, floater = motion, drift
        elif route == "kitten":
            # The plush cat plays in place while the mouse runs independently
            # across the lower dial, matching the two native animation tracks.
            offset = (round(math.sin(t * math.tau) * 18),
                      round(math.sin(t * math.tau * 2) * 9))
            drift_offset = (round(-320 + 770 * t), round(math.sin(t * math.tau) * 4))
            actor, floater = motion, drift
        elif route == "rocket":
            offset = (round(-320 + 740 * t), round(320 - 740 * t))
            drift_offset = offset
            actor = motion
            opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(i * math.tau / 18))
            floater = alpha_layer(drift, opacity)
        else:
            raise ValueError(f"Unknown motion route: {route}")
        face = assemble(scene, actor, floater, offset, drift_offset, drift_below)
        frame = picker_preview(face, glass, clock).convert("RGB")
        frames.append(frame)
    palette = frames[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=True, disposal=2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    # Remove retired scene assets so resource folders match the current scene list.
    for stale in ("scene_garden.png", "icon_scene_garden.png", "motion_garden.png",
                  "drift_garden.png", "glass_garden.png", "scene_baking.png",
                  "icon_scene_baking.png", "motion_baking.png", "drift_baking.png",
                  "glass_baking.png"):
        (OUT / stale).unlink(missing_ok=True)
    (CHASE_PREVIEW).unlink(missing_ok=True)

    stills, motions, drifts, assembled, glasses = {}, {}, {}, {}, {}
    for name, spec in SCENES.items():
        stills[name] = render_static(name)
        motions[name] = render_transparent(spec["motion"], spec.get("motion_scale", 1.0),
                                           spec.get("motion_center", (225, 225)))
        if spec.get("motion_offset", (0, 0)) != (0, 0):
            motions[name] = translate(motions[name], *spec["motion_offset"])
        drifts[name] = render_transparent(spec["drift"])
        stills[name].save(OUT / f"scene_{name}.png", optimize=True)
        motions[name].save(OUT / f"motion_{name}.png", optimize=True)
        drifts[name].save(OUT / f"drift_{name}.png", optimize=True)
        assembled[name] = assemble(stills[name], motions[name], drifts[name],
                                    drift_below=spec.get("drift_below_actor", False))
        # Keep scene-aware glass independent of moving actors so native motion
        # never leaves a blurred duplicate at the actor's default position.
        glasses[name] = feathered_glass(stills[name])
        glasses[name].save(OUT / f"glass_{name}.png", optimize=True)
        assembled[name].resize((160, 160), Image.Resampling.LANCZOS).save(
            OUT / f"icon_scene_{name}.png", optimize=True
        )

    cursor_layer = render_transparent(coding_cursor)
    cursor_layer.save(OUT / "blink_coding.png", optimize=True)
    clock = native_clock()
    contact_faces = dict(assembled)
    # Keep the poster cat centered with its mouse visible below the readouts.
    contact_faces["kitten"] = assemble(stills["kitten"], motions["kitten"], drifts["kitten"],
                                       (0, 0), (20, 44))
    contact_sheet(contact_faces, glasses, clock).save(PREVIEW, optimize=True)
    picker_preview(assembled["bicycle"], glasses["bicycle"], clock).save(
        OUT / "watchface_preview.png", optimize=True
    )
    make_motion_gif(MOTION_PREVIEW, stills["bicycle"], motions["bicycle"],
                    drifts["bicycle"], glasses["bicycle"], clock, "bicycle")
    make_motion_gif(KITTEN_PREVIEW, stills["kitten"], motions["kitten"],
                    drifts["kitten"], glasses["kitten"], clock, "kitten")
    make_motion_gif(ROCKET_PREVIEW, stills["cosmos"], motions["cosmos"],
                    drifts["cosmos"], glasses["cosmos"], clock, "rocket",
                    drift_below=SCENES["cosmos"].get("drift_below_actor", False))
    print(f"Wrote {len(stills)} full-bleed 450x450 scenes and actor/drift/glass layers to {OUT}")
    print(f"Wrote watch mockup contact sheet to {PREVIEW}")
    print(f"Wrote animated bicycle proof to {MOTION_PREVIEW}")
    print(f"Wrote animated kitten-and-mouse proof to {KITTEN_PREVIEW}")
    print(f"Wrote animated rocket proof to {ROCKET_PREVIEW}")


if __name__ == "__main__":
    main()
