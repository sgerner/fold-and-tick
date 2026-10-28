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
OCEAN_PREVIEW = ROOT / "preview/ocean-motion.gif"
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
    # A small paper sun rests in the upper-left sky, clear of the clock glass.
    sun = regular_polygon(64, 60, 58, 20)
    c.poly(sun, "#ffb95f")
    for i, color in enumerate(["#ffd978", "#ff9a68", "#ffe394", "#f58482",
                               "#ffc269", "#ffda82", "#ed7b88", "#ffb85f"]):
        a = -math.pi / 2 + i * math.tau / 8
        b = a + math.tau / 8
        c.poly([(64, 60),
                (64 + math.cos(a) * 56, 60 + math.sin(a) * 56),
                (64 + math.cos((a + b) / 2) * 50, 60 + math.sin((a + b) / 2) * 50),
                (64 + math.cos(b) * 56, 60 + math.sin(b) * 56)], color)

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
    # A broad lower road gives the moving bicycle a clear lane beneath readouts.
    c.poly([(0, 387), (93, 378), (174, 390), (272, 377), (365, 392), (450, 380),
            (450, 431), (366, 442), (272, 426), (174, 443), (92, 428), (0, 437)], "#eaa36d")
    c.poly([(0, 387), (93, 378), (174, 390), (272, 377), (365, 392), (450, 380),
            (450, 399), (366, 410), (272, 394), (174, 411), (92, 396), (0, 405)], "#ffd07b")
    c.line([(14, 414), (97, 407), (171, 417), (270, 404), (351, 416)], "#fff0ae", 1.5)


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


# ── Coding: a bright folded laptop rests below the watch readouts ────────────

def coding_environment(c: Canvas):
    # Keep the broad center calm. The laptop is large enough to read in the
    # lower band without competing with the central clock.
    c.poly([(0, 0), (450, 0), (450, 450), (0, 450)], "#282b62")
    c.poly([(0, 0), (450, 0), (450, 250), (0, 250)], "#303b79")
    c.poly([(0, 250), (450, 250), (450, 450), (0, 450)], "#382e68")
    c.poly([(0, 334), (450, 311), (450, 450), (0, 450)], "#514080")
    # Two dim paper planes frame the device and leave the readout area open.
    c.poly([(0, 300), (81, 287), (136, 305), (91, 316), (0, 318)], "#604982")
    c.poly([(450, 284), (388, 295), (350, 311), (405, 321), (450, 316)], "#61417a")
    # Laptop screen: distinct bezel, cool glass and broad syntax rows.
    c.poly([(68, 317), (382, 317), (372, 389), (78, 389)], "#202443")
    c.poly([(78, 325), (372, 325), (364, 381), (86, 381)], "#153d62")
    c.poly([(86, 329), (218, 327), (220, 381), (86, 381)], "#185273")
    c.poly([(220, 327), (372, 325), (364, 381), (220, 381)], "#263b70")
    # A folded code window gives the screen a readable, familiar story.
    c.poly([(101, 338), (168, 337), (168, 343), (101, 345)], "#68ded4")
    c.poly([(111, 350), (230, 347), (230, 354), (111, 356)], "#f5c86c")
    c.poly([(101, 362), (205, 360), (205, 366), (101, 368)], "#e98dc4")
    c.poly([(234, 340), (302, 339), (301, 345), (234, 347)], "#ff8d93")
    c.poly([(244, 354), (342, 351), (341, 357), (244, 359)], "#74ddd0")
    c.poly([(269, 366), (333, 364), (332, 370), (269, 371)], "#ffc96a")
    c.line([(76, 389), (374, 389)], "#a5e5dd", 2)
    # Perspective keyboard deck and a simple visible trackpad.
    c.poly([(51, 392), (398, 392), (433, 420), (18, 420)], "#d56b98")
    c.poly([(51, 392), (398, 392), (420, 408), (32, 408)], "#f2a17f")
    for row in range(2):
        for col in range(11):
            x = 72 + col * 25 + row * 5
            y = 398 + row * 8
            color = ["#3d477c", "#43518b", "#356487", "#614982"][(col + row) % 4]
            c.poly([(x, y), (x + 18, y), (x + 20, y + 5), (x + 2, y + 5)], color)
    c.poly([(188, 414), (267, 414), (277, 419), (178, 419)], "#c9c5dc")
    c.poly([(18, 420), (433, 420), (400, 434), (48, 434)], "#25284d")


def coding_actor(c: Canvas):
    # A bright folded terminal mark lives inside the visible laptop screen.
    c.poly([(321, 340), (308, 350), (321, 359), (326, 355), (318, 350), (326, 344)], "#ff8ca4")
    c.poly([(341, 340), (354, 350), (341, 359), (336, 355), (344, 350), (336, 344)], "#69e1d1")
    c.poly([(332, 339), (325, 362), (331, 363), (338, 340)], "#ffd267")
    c.poly([(291, 370), (349, 369), (349, 373), (291, 374)], "#99d8e4")


def coding_cursor(c: Canvas):
    c.poly([(356, 365), (366, 365), (366, 378), (356, 378)], "#ffe071")
    c.poly([(356, 365), (366, 365), (362, 371), (356, 372)], "#fff4b9")


def coding_drift(c: Canvas):
    # A few restrained paper flecks sit on the desktop corners.
    for x, y, color in [(24, 362, "#61dbce"), (411, 367, "#ff789d"), (406, 431, "#ffd36f")]:
        c.poly([(x, y), (x + 11, y - 4), (x + 17, y + 4), (x + 6, y + 8)], color)
        c.poly([(x + 6, y + 8), (x + 17, y + 4), (x + 14, y + 12), (x + 3, y + 15)], "#3e3b72")


# ── Kitten: colorful yarn world, plush cat and an independent mouse ─────────

def kitten_environment(c: Canvas):
    # A calm felt-paper playroom keeps its yarn accents at the dial edges.
    c.poly([(0, 0), (450, 0), (450, 450), (0, 450)], "#60446f")
    c.poly([(0, 0), (450, 0), (450, 150), (0, 150)], "#795276")
    c.poly([(0, 150), (450, 150), (450, 327), (0, 327)], "#59456f")
    c.poly([(0, 327), (450, 327), (450, 450), (0, 450)], "#474269")
    # Small faceted yarn balls frame the face instead of crowding the clock.
    c.poly(regular_polygon(43, 66, 49, 12), "#be7399")
    c.poly([(0, 34), (26, 18), (63, 27), (87, 57), (73, 93), (35, 111), (0, 95)], "#e29baa")
    c.poly([(0, 34), (26, 18), (43, 68), (35, 111), (0, 95)], "#f3b8b1")
    c.poly([(43, 68), (26, 18), (63, 27), (87, 57), (73, 93)], "#ba6f95")
    c.poly(regular_polygon(407, 77, 48, 12), "#74ad91")
    c.poly([(368, 35), (399, 22), (431, 38), (450, 68), (436, 103),
            (401, 121), (369, 102), (351, 68)], "#9ed5a9")
    c.poly([(368, 35), (399, 22), (401, 71), (369, 102), (351, 68)], "#c2e5b7")
    c.poly([(401, 71), (399, 22), (431, 38), (450, 68), (436, 103)], "#78b18f")
    # One loose thread curls around the bottom corners like a toy waiting to play.
    c.line([(0, 359), (39, 345), (72, 358), (81, 379), (66, 394),
            (45, 389), (42, 371), (61, 358), (92, 368)], "#f1c4cb", 5)
    c.line([(0, 354), (39, 340), (72, 353), (79, 372)], "#ffe8cf", 1.8)
    c.line([(450, 369), (414, 354), (385, 366), (377, 387), (394, 402),
            (416, 394), (417, 377), (398, 366), (370, 376)], "#e8a9c3", 5)
    c.line([(450, 364), (414, 349), (385, 361), (379, 379)], "#ffe4cf", 1.8)
    c.poly([(0, 425), (96, 410), (181, 424), (268, 409), (353, 426), (450, 411),
            (450, 450), (0, 450)], "#3e3b60")


def kitten_actor(c: Canvas):
    # A compact kitten crouches and looks toward the mouse on its lower lane.
    c.line([(165, 386), (139, 376), (121, 384), (117, 400), (131, 406)], "#d88b83", 17)
    c.line([(160, 386), (139, 380), (124, 387)], "#f2b5a7", 4)
    c.ellipse((143, 366, 296, 447), fill="#c97778", outline="#8c5272", width=2)
    c.poly([(148, 385), (165, 371), (211, 380), (219, 425), (194, 444),
            (151, 426)], "#e99b83")
    c.poly([(211, 380), (245, 369), (281, 383), (296, 418), (276, 444),
            (219, 425)], "#d4847c")
    c.poly([(173, 402), (218, 388), (267, 404), (267, 434), (225, 444), (177, 431)], "#ffe0bd")
    # Ear tips start below the complication band; the broad face stays readable.
    c.poly([(150, 351), (157, 327), (181, 342), (197, 354)], "#d58a7d")
    c.poly([(253, 354), (276, 328), (289, 357), (276, 375)], "#d58a7d")
    c.poly([(160, 347), (165, 335), (180, 348)], "#f5afc1")
    c.poly([(264, 350), (276, 337), (281, 353)], "#f2b0bf")
    c.poly([(149, 354), (171, 337), (207, 331), (232, 337), (265, 331),
            (288, 347), (295, 369), (284, 391), (258, 404), (215, 409),
            (177, 399), (153, 382)], "#d58a7d")
    c.poly([(154, 359), (176, 343), (207, 338), (224, 356), (218, 391),
            (181, 399), (155, 381)], "#f1b691")
    c.poly([(224, 356), (242, 338), (267, 340), (286, 352), (292, 371),
            (278, 391), (249, 400), (220, 391)], "#e89b83")
    # Oversized eyes and right-looking pupils give the cat a playful focus.
    for box, iris in [((177, 348, 211, 382), "#69b4a1"), ((235, 348, 269, 382), "#69b4a1")]:
        c.ellipse(box, fill="#fff1d4", outline="#a66072", width=1.6)
        x0, y0, x1, y1 = box
        c.ellipse((x0 + 8, y0 + 5, x1 - 3, y1 - 3), fill=iris)
        c.ellipse((x0 + 14, y0 + 7, x1 - 4, y1 - 3), fill="#263a4e")
        c.ellipse((x0 + 16, y0 + 9, x0 + 22, y0 + 15), fill="#fffdf0")
    c.poly([(209, 382), (218, 378), (227, 383), (220, 390), (213, 389)], "#e97591")
    c.line([(218, 389), (218, 395), (211, 399)], "#8b5967", 1.4)
    c.line([(218, 395), (225, 400)], "#8b5967", 1.4)
    for pts in [[(209, 387), (181, 386), (165, 381)], [(209, 392), (182, 397), (167, 399)],
                [(228, 387), (257, 385), (277, 379)], [(228, 393), (255, 399), (276, 402)]]:
        c.line(pts, "#ffe8d2", 1.2)
    # One raised paw reaches toward the mouse; the other anchors the crouch.
    c.poly([(264, 408), (288, 401), (303, 391), (312, 396), (308, 409), (291, 420)], "#f0ba9b")
    c.ellipse((157, 419, 204, 446), fill="#ffe0bf", outline="#bd767e", width=1.2)
    c.ellipse((227, 420, 273, 446), fill="#ffe0bf", outline="#bd767e", width=1.2)
    for x in (170, 185, 240, 255):
        c.line([(x, 434), (x + 1, 440)], "#de98a0", 1.1)


def kitten_drift(c: Canvas):
    # A separate mouse runs on a low path under the kitten's reaching paw.
    c.line([(292, 394), (278, 403), (270, 415), (277, 421)], "#8f6275", 2.6)
    c.ellipse((285, 371, 337, 412), fill="#a68796", outline="#6b536d", width=1.5)
    c.poly([(312, 376), (332, 368), (350, 383), (344, 401), (329, 410), (309, 402)], "#b79aa1")
    c.ellipse((314, 367, 328, 384), fill="#d99cae")
    c.ellipse((331, 372, 343, 387), fill="#d99cae")
    c.ellipse((333, 383, 339, 389), fill="#293746")
    c.poly([(346, 388), (356, 392), (347, 398), (340, 394)], "#ed8da2")
    c.ellipse((293, 403, 304, 409), fill="#f2c7c7")
    c.ellipse((322, 405, 333, 411), fill="#f2c7c7")


# ── Landscape: saturated mountain bowl, faceted sunset and reflective lake ──

def landscape_environment(c: Canvas):
    # Open sunset sky leaves a quiet field for the time; folded peaks rise from
    # the lower edge into a reflective blue lake.
    c.poly([(0, 0), (450, 0), (450, 298), (0, 298)], "#7543a2")
    c.poly([(0, 0), (450, 0), (450, 133), (0, 171)], "#b956a4")
    c.poly([(0, 171), (123, 142), (229, 168), (345, 138), (450, 157),
            (450, 220), (341, 193), (229, 219), (117, 191), (0, 222)], "#dd708d")
    c.poly([(0, 300), (58, 270), (119, 302), (181, 275), (244, 307),
            (316, 272), (384, 304), (450, 273), (450, 354), (0, 354)], "#9e4e98")
    c.poly([(0, 300), (58, 270), (119, 302), (88, 292), (58, 280), (27, 321)], "#f09084")
    c.poly([(181, 275), (244, 307), (316, 272), (281, 290), (244, 286), (215, 322)], "#e77b88")
    c.poly([(316, 272), (384, 304), (450, 273), (418, 290), (384, 287), (351, 326)], "#f3a06f")
    # The lake carries just a few bright folded reflections at the bottom.
    c.poly([(0, 340), (74, 354), (151, 337), (226, 355), (302, 337),
            (378, 355), (450, 340), (450, 450), (0, 450)], "#286f9f")
    c.poly([(0, 363), (74, 375), (151, 359), (226, 377), (302, 359),
            (378, 377), (450, 362), (450, 403), (378, 416), (302, 399),
            (226, 418), (151, 399), (74, 418), (0, 403)], "#49b4b7")
    c.poly([(0, 409), (79, 395), (157, 412), (228, 399), (306, 417),
            (378, 398), (450, 414), (450, 450), (0, 450)], "#235b8f")
    for pts, color in [([(32, 384), (93, 379), (132, 385)], "#f7b67b"),
                       ([(244, 386), (297, 382), (350, 388)], "#ffe08a"),
                       ([(83, 431), (144, 425), (184, 432)], "#9ce0d2"),
                       ([(317, 434), (376, 427), (427, 433)], "#f1a1a1")]:
        c.line(pts, color, 2.2)

def landscape_actor(c: Canvas):
    # A warm paper sun anchors the upper-left corner, clear of the date.
    cx, cy, r = 76, 73, 43
    c.poly(regular_polygon(cx, cy, r, 16), "#ffd56b")
    c.poly([(cx, cy), (cx + 42, cy), (cx + 30, cy + 30), (cx + 1, cy + 41)], "#f28b6c")
    c.poly([(cx, cy), (cx - 30, cy + 29), (cx - 42, cy), (cx - 27, cy - 30)], "#fff0a2")
    c.poly([(cx, cy), (cx - 27, cy - 30), (cx, cy - 42), (cx + 24, cy - 31)], "#ffbc62")


def landscape_drift(c: Canvas):
    # A distant folded cloud passes through the upper left sky.
    c.poly([(268, 84), (283, 72), (299, 76), (309, 65), (326, 70),
            (338, 85), (327, 93), (278, 94)], "#f0a6b2")
    c.poly([(268, 84), (283, 72), (298, 78), (281, 89)], "#ffd294")
    c.poly([(299, 78), (309, 65), (326, 70), (338, 85), (314, 84)], "#ffe6ac")
    c.poly([(325, 110), (337, 103), (350, 106), (358, 115), (346, 121), (329, 118)], "#e88d9c")


# ── Cosmos: open deep space, one ringed planet and a paper rocket ────────────

def cosmos_environment(c: Canvas):
    # A ringed planet sits in the upper-right pocket of open deep space.
    c.ellipse((281, 26, 452, 111), outline="#b77e85", width=8)
    c.ellipse((284, 24, 449, 109), outline="#f3d19a", width=2)
    c.poly(regular_polygon(368, 67, 40, 18), "#3e8294")
    c.poly([(328, 67), (336, 43), (355, 28), (378, 29), (396, 46),
            (408, 68), (396, 88), (378, 105), (352, 100), (333, 84)], "#4e9b9c")
    c.poly([(328, 67), (336, 43), (355, 28), (368, 67), (352, 100), (333, 84)], "#79d4c3")
    c.poly([(368, 67), (355, 28), (378, 29), (396, 46), (408, 68),
            (396, 88), (378, 105)], "#3e688f")
    c.poly([(336, 43), (355, 28), (368, 67), (352, 58)], "#b8e6ce")
    lower_ring = [(368 + 84 * math.cos(math.radians(a)), 68 + 38 * math.sin(math.radians(a)))
                  for a in range(8, 173, 8)]
    c.line(lower_ring, "#d9a875", 8)
    c.line(lower_ring, "#ffedbf", 1.7)
    # Tiny stars mark the margins; the lower-left cluster becomes the rocket trail.
    for x, y, r, col in [(55, 58, 3, "#fff0a8"), (405, 145, 3, "#ffe08a"),
                         (45, 357, 3, "#7be4d2"), (404, 346, 4, "#efa5d0"),
                         (211, 425, 3, "#ffe18c")]:
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
    c.d._image.alpha_composite(angled, dest=(0, 65 * SCALE))


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
    # A quiet polar night frames two narrow aurora ribbons at the outer edges.
    c.poly([(0, 0), (450, 0), (450, 450), (0, 450)], "#3d1e39")
    c.poly([(0, 0), (56, 0), (88, 52), (74, 103), (92, 157),
            (71, 193), (45, 154), (54, 96), (35, 45)], "#bd6859")
    c.poly([(0, 0), (27, 0), (58, 49), (49, 102), (68, 154),
            (55, 181), (40, 145), (43, 94), (22, 43)], "#f4b56e")
    c.poly([(391, 0), (450, 0), (450, 166), (419, 195), (396, 153),
            (410, 95), (382, 47)], "#a44d58")
    c.poly([(423, 0), (450, 0), (450, 139), (431, 174), (415, 137),
            (428, 87), (408, 42)], "#e89962")
    # Snow shelves start beneath the readouts and give the fox a warm stage.
    c.poly([(0, 318), (75, 294), (153, 320), (229, 296), (306, 323),
            (382, 298), (450, 321), (450, 450), (0, 450)], "#9f5960")
    c.poly([(0, 343), (70, 317), (137, 344), (204, 320), (274, 350),
            (342, 322), (414, 349), (450, 334), (450, 450), (0, 450)], "#e3a77b")
    c.poly([(0, 372), (75, 347), (153, 371), (229, 345), (306, 375),
            (382, 349), (450, 372), (450, 450), (0, 450)], "#f3d6a4")
    c.poly([(0, 410), (83, 387), (164, 409), (246, 384), (330, 412),
            (411, 386), (450, 398), (450, 450), (0, 450)], "#fff0cf")
    c.poly([(0, 430), (111, 407), (220, 431), (333, 403), (450, 429),
            (450, 450), (0, 450)], "#d9ac8d")
    for x, y, r in [(112, 50, 3), (152, 91, 3), (344, 53, 4), (377, 114, 3)]:
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
        "motion_scale": (1.0, 0.9), "motion_center": (225, 360), "motion_offset": (0, 30),
    },
    "forest": {
        "stops": [(0, "#15583e"), (0.34, "#238a51"), (0.68, "#146d70"), (1, "#124e60")],
        "background": forest_environment, "motion": forest_actor, "drift": forest_drift,
        "motion_scale": (1.0, 0.68), "motion_center": (225, 299), "motion_offset": (0, 45),
    },
    "coding": {
        "stops": [(0, "#201e59"), (0.48, "#3b326f"), (1, "#613869")],
        "background": coding_environment, "motion": coding_actor, "drift": coding_drift,
    },
    "kitten": {
        "stops": [(0, "#91516f"), (0.42, "#bc6d8d"), (0.72, "#68517d"), (1, "#393b68")],
        "background": kitten_environment, "motion": kitten_actor, "drift": kitten_drift,
        "motion_scale": (1.08, 0.9), "motion_center": (225, 327),
    },
    "landscape": {
        "stops": [(0, "#652e83"), (0.3, "#d54c9a"), (0.58, "#ff956f"), (1, "#246c9c")],
        "background": landscape_environment, "motion": landscape_actor, "drift": landscape_drift,
    },
    "cosmos": {
        "stops": [(0, "#111e3f"), (0.4, "#1b3454"), (0.75, "#142f4e"), (1, "#111b3a")],
        "background": cosmos_environment, "motion": cosmos_actor, "drift": cosmos_drift,
        "motion_scale": (0.9, 0.9), "motion_center": (210, 375),
        "drift_below_actor": True,
    },
    "ocean": {
        "stops": [(0, "#42c0b2"), (0.22, "#167d9a"), (0.62, "#1a668d"), (1, "#123c68")],
        "background": ocean_environment, "motion": ocean_actor, "drift": ocean_drift,
        "motion_scale": (0.82, 0.72), "motion_center": (225, 225), "motion_offset": (0, 130),
    },
    "aurora": {
        "stops": [(0, "#321b35"), (0.38, "#692d47"), (0.68, "#b25353"), (1, "#f0bd8f")],
        "background": aurora_environment, "motion": aurora_actor, "drift": aurora_drift,
        "motion_scale": (1.0, 0.68), "motion_center": (225, 350), "motion_offset": (0, 34),
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


def feathered_glass(scene, style=None):
    """Scene-aware translucent blur plates with feathered edges and no borders."""
    blurred = scene.convert("RGB").filter(ImageFilter.GaussianBlur(6))
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # Only the broad time backing is preblurred; complication glass is dynamic.
    plates = [((35, 143, 415, 270), 42, 154, 0.48, 19.0)]
    for box, radius, alpha, tint, feather in plates:
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
        patch = blurred.copy()
        tint_color = (62, 39, 47) if style == "origami" else (13, 20, 43)
        navy = Image.new("RGB", patch.size, tint_color)
        patch = Image.blend(patch, navy, tint)
        patch = patch.convert("RGBA")
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


def native_clock(style=None):
    glyph_names = ([f"clock_{style}_{digit}.png" for digit in "1008"] if style else
                   [f"clock_{digit}.png" for digit in "1008"])
    colon_name = f"clock_{style}_colon.png" if style else "clock_colon.png"
    paths = [OUT / name for name in glyph_names]
    paths.insert(2, OUT / colon_name)
    if not all(path.exists() for path in paths):
        return None
    glyphs = [Image.open(path).convert("RGBA") for path in paths]
    clock = Image.new("RGBA", (sum(glyph.width for glyph in glyphs), 96), (0, 0, 0, 0))
    cursor = 0
    for glyph in glyphs:
        clock.alpha_composite(glyph, (cursor, 0))
        cursor += glyph.width
    return clock.resize((round(clock.width * 112 / 96), 112), Image.Resampling.LANCZOS)


def proof_glass_color(style):
    return {
        "origami": (255, 226, 186, 54),
        "woodblock": (213, 214, 191, 48),
        "bioluminescent": (7, 16, 34, 168),
        "pixel_art": (7, 16, 34, 168),
    }.get(style, (223, 235, 247, 48))


def draw_complications(draw, style=None):
    for center, value, icon_color in [(122.5, "82%", (164, 209, 188, 255)),
                                      (327.5, "6,248", (166, 236, 230, 255))]:
        label_font = font(32, True)
        label_width = draw.textbbox((0, 0), value, font=label_font)[2]
        row_width = 26 + 8 + label_width
        left = center - row_width / 2
        plate_width = min(161, 50 + label_width)
        draw.rounded_rectangle((center - plate_width / 2, 273,
                                center + plate_width / 2, 315), radius=14,
                               fill=proof_glass_color(style))
        if value == "82%":
            draw.rounded_rectangle((left+3, 284, left+23, 303), radius=4,
                                   outline=icon_color, width=2)
            draw.rectangle((left+9, 281, left+17, 284), fill=icon_color)
        else:
            draw.ellipse((left+11, 281, left+17, 287), fill=icon_color)
            draw.line([(left+14, 288), (left+12, 297), (left+5, 305)], fill=icon_color, width=3)
            draw.line([(left+13, 293), (left+22, 298)], fill=icon_color, width=3)
            draw.line([(left+12, 297), (left+20, 306)], fill=icon_color, width=3)
        draw.text((left + 34 + label_width / 2, 294), value, font=label_font,
                  fill=(255, 244, 232, 255), anchor="mm")


def add_watch_content(face, glass, clock, style=None):
    overlay = glass.copy()
    d = ImageDraw.Draw(overlay)
    date = "SUN OCT 25"
    date_font = font(32, True)
    date_text_width = d.textbbox((0, 0), date, font=date_font)[2]
    date_width = max(58, min(date_text_width + 24, 380))
    d.rounded_rectangle((225-date_width/2, 112, 225+date_width/2, 154), radius=14,
                        fill=proof_glass_color(style))
    d.text((225, 133), date, font=date_font,
           fill=(239, 243, 255, 255), anchor="mm")
    if clock is not None:
        overlay.alpha_composite(clock, ((450-clock.width)//2, 152))
    else:
        d.text((225, 206), "10:08", font=font(68, True), fill=(255, 240, 221, 255), anchor="mm")
    draw_complications(d, style=style)
    out = face.convert("RGBA")
    out.alpha_composite(overlay)
    return out


def origami_ambient():
    """Sparse, low-light folded marks for the Origami ambient watch face."""
    layer = Image.new("RGBA", (HI, HI), (0, 0, 0, 0))
    c = Canvas(ImageDraw.Draw(layer))
    motifs = [(34, 59, 9), (416, 62, 8), (28, 193, 6), (422, 196, 6),
              (40, 385, 9), (413, 386, 8), (116, 422, 5), (348, 419, 5)]
    for x, y, size in motifs:
        # Two paper facets make each tiny star read as a folded mark, not a dot.
        c.poly([(x, y-size), (x+size*0.42, y-size*0.18), (x, y),
                (x-size*0.42, y-size*0.18)], (220, 185, 124, 42))
        c.poly([(x, y), (x+size*0.42, y-size*0.18), (x+size, y),
                (x+size*0.42, y+size*0.24)], (240, 214, 163, 48))
        c.poly([(x, y), (x+size*0.42, y+size*0.24), (x, y+size),
                (x-size*0.42, y+size*0.24)], (201, 166, 109, 38))
        c.poly([(x, y), (x-size*0.42, y+size*0.24), (x-size, y),
                (x-size*0.42, y-size*0.18)], (226, 193, 134, 36))
        c.line([(x-size, y), (x, y+size), (x+size, y)], (248, 227, 177, 52), 0.8)
    return layer.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def circular_crop(face):
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, face.width - 1, face.height - 1), fill=255)
    result = face.convert("RGBA")
    result.putalpha(ImageChops.multiply(result.getchannel("A"), mask))
    return result


def picker_preview(face, glass, clock, style=None):
    return circular_crop(add_watch_content(face, glass, clock, style=style))


def add_mockup(face, glass, clock, style=None):
    window = circular_crop(face.resize((408, 408), Image.Resampling.LANCZOS))
    rim = Image.new("RGBA", (422, 422), (0, 0, 0, 0))
    d = ImageDraw.Draw(rim)
    d.ellipse((1, 1, 420, 420), fill=(49, 55, 83, 255), outline=(139, 152, 190, 210), width=2)
    rim.alpha_composite(window, (7, 7))
    framed_content = add_watch_content(face, glass, clock, style=style).resize((408, 408), Image.Resampling.LANCZOS)
    rim.alpha_composite(circular_crop(framed_content), (7, 7))
    ImageDraw.Draw(rim).ellipse((8, 8, 413, 413), outline=(218, 222, 243, 82), width=1)
    return rim


def contact_sheet(faces, glasses, clock, style=None):
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
        dial = add_mockup(faces[name], glasses[name], clock, style=style)
        sheet.paste(dial, (x + (cell_w - dial.width) // 2, y + 58), dial)
    return sheet


def alpha_layer(layer, opacity):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda a: round(a * opacity)))
    return out


def make_motion_gif(path, scene, motion, drift, glass, clock, route, drift_below=False, style=None):
    frames = []
    # Match each native route's period. GIF delays are exact 100ms increments.
    frame_count = {"kitten": 80, "ocean": 140}.get(route, 100)
    for i in range(frame_count):
        t = i / frame_count
        if route == "bicycle":
            offset = (round(-300 + 720 * t), 0)
            drift_offset = (round(math.sin(i * math.tau / frame_count) * 12),
                            round(math.cos(i * math.tau / frame_count) * 8))
            actor, floater = motion, drift
        elif route == "kitten":
            # The kitten lunges toward the mouse, which runs independently
            # across the lower dial on its own eight-second pass.
            seconds = i / 10
            lunge_phase = seconds % 3
            if lunge_phase < 0.5:
                lunge = lunge_phase / 0.5
            elif lunge_phase < 1.0:
                lunge = 1.0
            elif lunge_phase < 2.0:
                lunge = 2.0 - lunge_phase
            else:
                lunge = 0.0
            offset = (round(lunge * 10), round(-lunge * 5))
            drift_offset = (round(-350 + 720 * t), round(7 * math.sin(t * math.tau)))
            actor, floater = motion, drift
        elif route == "rocket":
            offset = (round(-320 + 740 * t), round(180 - 740 * t))
            drift_offset = offset
            actor = motion
            opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(i * math.tau / 18))
            floater = alpha_layer(drift, opacity)
        elif route == "ocean":
            offset = (round(-320 + 740 * t), round(8 * math.sin(i * math.tau / frame_count)))
            drift_offset = (0, round(4 * math.sin(i * math.tau / frame_count)))
            actor, floater = motion, drift
        else:
            raise ValueError(f"Unknown motion route: {route}")
        face = assemble(scene, actor, floater, offset, drift_offset, drift_below)
        frame = picker_preview(face, glass, clock, style=style).convert("RGB")
        frames.append(frame)
    palette = frames[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=True, disposal=2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    origami_ambient().save(OUT / "origami_ambient.png", optimize=True)
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
        glasses[name] = feathered_glass(stills[name], style="origami")
        glasses[name].save(OUT / f"glass_{name}.png", optimize=True)
        assembled[name].resize((160, 160), Image.Resampling.LANCZOS).save(
            OUT / f"icon_scene_{name}.png", optimize=True
        )

    cursor_layer = render_transparent(coding_cursor)
    cursor_layer.save(OUT / "blink_coding.png", optimize=True)
    clock = native_clock(style="origami")
    contact_faces = dict(assembled)
    contact_sheet(contact_faces, glasses, clock, style="origami").save(PREVIEW, optimize=True)
    picker_preview(assembled["bicycle"], glasses["bicycle"], clock, style="origami").save(
        OUT / "watchface_preview.png", optimize=True
    )
    make_motion_gif(MOTION_PREVIEW, stills["bicycle"], motions["bicycle"],
                    drifts["bicycle"], glasses["bicycle"], clock, "bicycle", style="origami")
    make_motion_gif(KITTEN_PREVIEW, stills["kitten"], motions["kitten"],
                    drifts["kitten"], glasses["kitten"], clock, "kitten", style="origami")
    make_motion_gif(ROCKET_PREVIEW, stills["cosmos"], motions["cosmos"],
                    drifts["cosmos"], glasses["cosmos"], clock, "rocket",
                    drift_below=SCENES["cosmos"].get("drift_below_actor", False), style="origami")
    make_motion_gif(OCEAN_PREVIEW, stills["ocean"], motions["ocean"],
                    drifts["ocean"], glasses["ocean"], clock, "ocean", style="origami")
    print(f"Wrote {len(stills)} full-bleed 450x450 scenes and actor/drift/glass layers to {OUT}")
    print(f"Wrote watch mockup contact sheet to {PREVIEW}")
    print(f"Wrote animated bicycle proof to {MOTION_PREVIEW}")
    print(f"Wrote animated kitten-and-mouse proof to {KITTEN_PREVIEW}")
    print(f"Wrote animated rocket proof to {ROCKET_PREVIEW}")
    print(f"Wrote animated ocean proof to {OCEAN_PREVIEW}")


if __name__ == "__main__":
    main()
