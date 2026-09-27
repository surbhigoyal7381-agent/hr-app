#!/usr/bin/env python3
"""The field app's launcher icon and splash screen, from the Alvoraa master logo.

    python mobile/field-app/scripts/make_app_icons.py

(ALV-133, Surbhi's request of 27 Sep 2026: "use alvoraa logo in the design".)

Source: alvoraa_portal/brand/alvoraa-logo-master.jpg, the 1,600 x 1,600 master
that scripts/make_brand_assets.py already cuts the portal's images from. This
script reuses that script's keying and cutting, so the app's mark is the same
monogram, cut the same way, at the size a phone needs:

  mipmap-*/ic_launcher_foreground.png   the adaptive icon's foreground, 108 dp.
                                        The mark fills the middle 60 %, inside
                                        Android's 66 dp safe circle, so no
                                        launcher mask ever clips it.
  values/ic_launcher_background.xml     white (unchanged: #FFFFFF), the ground.
  mipmap-*/ic_launcher.png              the pre-Android-8 icon: the mark on a
                                        white rounded square.
  mipmap-*/ic_launcher_round.png        the same on a white circle.
  drawable*/splash.png                  the mark centred on white, every size
                                        and orientation the app already ships.

The largest icon, 432 px, needs a mark about 260 px across; the master's
monogram is 720 x 432 px, so every size is a reduction, never a blow-up
(the portal's 128 px mark would have been blown up twice over).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RES = os.path.join(HERE, "..", "android", "app", "src", "main", "res")
sys.path.insert(0, os.path.join(REPO, "scripts"))

from PIL import Image, ImageDraw  # noqa: E402

import make_brand_assets as brand  # noqa: E402

DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
WHITE = (255, 255, 255, 255)


def fit(mark, box):
    """The mark scaled to fit a box x box square, centred, transparent around."""
    m = mark.copy()
    m.thumbnail((box, box), Image.LANCZOS)
    out = Image.new("RGBA", (box, box), (255, 255, 255, 0))
    out.paste(m, ((box - m.width) // 2, (box - m.height) // 2), m)
    return out


def on_ground(mark, size, mark_ratio, shape):
    """The mark on a white rounded square or circle, for the older icons."""
    scale = 4  # draw big, then shrink, for a smooth edge
    big = size * scale
    ground = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    draw = ImageDraw.Draw(ground)
    inset = int(big * 0.04)
    if shape == "round":
        draw.ellipse([inset, inset, big - inset, big - inset], fill=WHITE)
    else:
        draw.rounded_rectangle([inset, inset, big - inset, big - inset], radius=int(big * 0.18), fill=WHITE)
    m = fit(mark, int(big * mark_ratio))
    ground.alpha_composite(m, ((big - m.width) // 2, (big - m.height) // 2))
    return ground.resize((size, size), Image.LANCZOS)


def main():
    master_path = brand.find_master()
    master = Image.open(master_path)
    keyed = brand.to_rgba_keyed(master)
    box = brand.bbox_of(brand.ink_rows(master), brand.ink_cols(master, 0, master.size[1]))
    mono_box = brand.split_monogram(master, box) or box
    mark = keyed.crop(mono_box)
    print(f"master {os.path.relpath(master_path, REPO)} {master.size}; monogram {mark.size}")

    for name, k in DENSITIES.items():
        folder = os.path.join(RES, f"mipmap-{name}")
        fg_px = int(round(108 * k))
        foreground = Image.new("RGBA", (fg_px, fg_px), (255, 255, 255, 0))
        m = fit(mark, int(round(fg_px * 0.60)))
        foreground.alpha_composite(m, ((fg_px - m.width) // 2, (fg_px - m.height) // 2))
        foreground.save(os.path.join(folder, "ic_launcher_foreground.png"), optimize=True)

        icon_px = int(round(48 * k))
        on_ground(mark, icon_px, 0.70, "square").save(os.path.join(folder, "ic_launcher.png"), optimize=True)
        on_ground(mark, icon_px, 0.62, "round").save(os.path.join(folder, "ic_launcher_round.png"), optimize=True)
        print(f"  {name:8} foreground {fg_px}px, icon {icon_px}px")

    # Splash: every file the app already has, same size, the mark centred on white.
    for folder in sorted(os.listdir(RES)):
        path = os.path.join(RES, folder, "splash.png")
        if not (folder.startswith("drawable") and os.path.isfile(path)):
            continue
        with Image.open(path) as old:
            w, h = old.size
        splash = Image.new("RGBA", (w, h), WHITE)
        m = fit(mark, int(min(w, h) * 0.34))
        splash.alpha_composite(m, ((w - m.width) // 2, (h - m.height) // 2))
        splash.convert("RGB").save(path, optimize=True)
        print(f"  {folder:22} splash {w}x{h}")


if __name__ == "__main__":
    main()
