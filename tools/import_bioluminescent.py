#!/usr/bin/env python3
"""Build the bioluminescent style resources from saved artwork, offline.

Image generation is kept separate. This importer crops the checked-in source
backgrounds and transparent sprite atlas, then writes WFF-sized textures and a
labeled watch proof plate.

Run from the repository root with:
    tools/.venv/bin/python tools/import_bioluminescent.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from generate_art import (OUT, ROOT, SIZE, assemble, feathered_glass, font,
                          native_clock, picker_preview)


STYLE = "bioluminescent"
LABEL = "Bioluminescent"
SCENES = ("bicycle", "forest", "coding", "kitten", "landscape", "cosmos",
          "ocean", "aurora")
SOURCE = ROOT / "artwork/packs/bioluminescent/sources"
PROOF = ROOT / "preview/styles/bioluminescent.png"

# Full-scene logical placement (450 x 450) keeps transparent actor artwork in
# the correct native transform coordinate space before it is reduced to 225px.
ACTOR_PLACEMENTS = {
    "bicycle": (100, 292, 250, 142),
    "forest": (104, 228, 242, 182),
    "coding": (110, 270, 230, 155),
    "kitten": (99, 276, 240, 162),
    "landscape": (275, 72, 140, 190),
    "cosmos": (178, 166, 132, 132),
    "ocean": (165, 322, 120, 125),
    "aurora": (125, 295, 220, 142),
}

# The atlas uses row-major cells: first eight are scene actors, last eight are
# independent glowing particles, companions, and animated accents.
DRIFT_PLACEMENTS = {
    "bicycle": ((48, 138, 42, 42), (344, 252, 42, 42), (299, 365, 30, 30)),
    "forest": ((54, 182, 48, 48), (348, 205, 48, 48), (77, 377, 36, 36)),
    "coding": ((267, 320, 24, 24), (290, 330, 14, 14)),
    "kitten": ((284, 210, 68, 58), (79, 233, 42, 38)),
    "landscape": ((67, 117, 40, 40), (371, 304, 44, 44), (92, 363, 32, 32)),
    "cosmos": ((71, 139, 42, 42), (351, 224, 42, 42), (285, 373, 35, 35)),
    "ocean": ((58, 105, 38, 38), (357, 201, 38, 38),
              (96, 383, 30, 30), (351, 376, 32, 32)),
    "aurora": ((32, 93, 182, 90), (275, 196, 112, 56)),
}


def fit_scene(name):
    path = SOURCE / f"{name}-background.png"
    with Image.open(path) as source:
        return ImageOps.fit(source.convert("RGB"), (SIZE, SIZE),
                            method=Image.Resampling.LANCZOS).convert("RGBA")


def atlas_sprite(sheet, cell):
    """Crop a row-major 4x4 sprite cell and trim transparent outer pixels."""
    left = round((cell % 4) * sheet.width / 4)
    right = round((cell % 4 + 1) * sheet.width / 4)
    top = round((cell // 4) * sheet.height / 4)
    bottom = round((cell // 4 + 1) * sheet.height / 4)
    tile = sheet.crop((left, top, right, bottom))
    alpha = tile.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= 5 else 0).getbbox()
    if visible is None:
        raise ValueError(f"Sprite atlas cell {cell} is empty")
    return tile.crop(visible)


def place(canvas, art, box):
    left, top, width, height = box
    art = art.copy()
    art.thumbnail((width, height), Image.Resampling.LANCZOS)
    x = left + (width - art.width) // 2
    y = top + (height - art.height) // 2
    canvas.alpha_composite(art, (x, y))


def actor_layer(sheet, name):
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    place(layer, atlas_sprite(sheet, SCENES.index(name)), ACTOR_PLACEMENTS[name])
    return layer


def drift_layer(sheet, name):
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    detail = atlas_sprite(sheet, 8 + SCENES.index(name))
    for box in DRIFT_PLACEMENTS[name]:
        place(layer, detail, box)
    return layer


def save_scaled(image, path, size):
    image.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE / "sprites.png") as source:
        sheet = source.convert("RGBA")
    if sheet.getchannel("A").getextrema() != (0, 255):
        raise ValueError("Sprite atlas must retain genuine alpha transparency")
    clock = native_clock()
    if clock is None:
        raise FileNotFoundError("Origami clock glyphs must exist before import")

    proof = Image.new("RGB", (4 * 330, 2 * 370), "#10182c")
    draw = ImageDraw.Draw(proof)
    for index, name in enumerate(SCENES):
        scene = fit_scene(name)
        actor = actor_layer(sheet, name)
        details = drift_layer(sheet, name)
        # The static proof and icon show the actors at their resting positions.
        composed = assemble(scene, actor, details,
                            drift_below=name in ("cosmos", "aurora"))
        glass = feathered_glass(scene, style=STYLE)

        save_scaled(scene, OUT / f"scene_{STYLE}_{name}.png", 225)
        save_scaled(actor, OUT / f"motion_{STYLE}_{name}.png", 225)
        save_scaled(details, OUT / f"drift_{STYLE}_{name}.png", 112)
        save_scaled(glass, OUT / f"glass_{STYLE}_{name}.png", 112)
        save_scaled(composed, OUT / f"icon_scene_{STYLE}_{name}.png", 160)

        x, y = (index % 4) * 330 + 10, (index // 4) * 370
        draw.text((x + 155, y + 18), f"{LABEL} · {name.title()}",
                  font=font(16, True), fill="#f2e9df", anchor="mt")
        dial = picker_preview(composed, glass, clock, style=STYLE).resize(
            (310, 310), Image.Resampling.LANCZOS)
        proof.paste(dial, (x, y + 47), dial)

    proof.save(PROOF, optimize=True)
    print(f"Wrote eight bioluminescent scene packs to {OUT}")
    print(f"Wrote circular clock/complication proof to {PROOF}")


if __name__ == "__main__":
    build()
