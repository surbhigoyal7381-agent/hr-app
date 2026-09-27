#!/usr/bin/env python3
"""Make the three brand images the product actually serves, from one master file.

    python scripts/make_brand_assets.py

That is the whole swap. Drop new artwork at

    alvoraa_portal/brand/alvoraa-logo-master.<jpg|png|webp>

run the line above, and the three files under
`alvoraa_portal/alvoraa_portal/public/images/` are rewritten. No code, no path and
no template changes - `brand.py` names the files, and the names do not change.

WHY THREE FILES AND NOT ONE
---------------------------
The master is a 1600x1600, 84 KB JPEG. That is about 80 KB too much for a 32-pixel
mark in a sidebar and a 32-pixel favicon, and an employee on a factory-floor phone
pays for every byte (nfr-budget.md section 2: 3G p95 of 2.5 s). So:

  alvoraa-mark.png     the monogram alone, square. The rail draws it at 32 px, so
                       128 px covers a 4x screen and nothing more.
  alvoraa-logo.png     the full lockup - monogram plus wordmark - for the sign-in
                       page, the desk splash and the website banner, where there
                       is room to read it.
  alvoraa-favicon.png  32x32, flattened onto white. Browser tab chrome is not
                       reliably light or dark and a transparent favicon can
                       disappear into it, so this one keeps its ground.

WHY PNG AND NOT THE JPEG
------------------------
A JPEG cannot hold transparency, so it carries its white box everywhere it goes.
The portal has a dark theme (design_system.html line 15) and a white box in the
dark rail looks like a sticker somebody left on the screen. The artwork is flat
colour on flat white, so keying the white out is safe.

The keying is deliberately dull. `alpha = distance from white, in the darkest
channel, scaled so anything past EDGE is fully opaque`. Solid artwork - even pale
lilac at (173,153,188) - is 102 away from white and comes out completely opaque.
Only genuine anti-aliased edge pixels land in between, and those get
un-premultiplied so the outline does not turn grey against a dark background.

HOW THE PARTS ARE FOUND
-----------------------
By ink, not by hard-coded pixel numbers, so a replacement master with different
margins still works. The whole inked area is the lockup. Inside it, the monogram
is the part above the first blank row that separates the two - found by scanning
the row-ink profile for the gap. If no gap is found (a one-piece logo), the mark
falls back to the whole lockup, squared. That is a design decision, not a bug:
a one-piece logo has nothing to split.
"""

import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - a developer's machine, not a server
    sys.exit("This needs Pillow:  python -m pip install Pillow")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_DIR = os.path.join(HERE, "alvoraa_portal", "brand")
OUT_DIR = os.path.join(HERE, "alvoraa_portal", "alvoraa_portal", "public", "images")

MASTER_STEM = "alvoraa-logo-master"
MASTER_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# A pixel this far from white, in its darkest channel, is treated as solid ink.
# 40 of 255 is well below any real brand colour and well above JPEG ringing.
EDGE = 40

# Anything at or above this in every channel is background, never ink.
WHITE = 246

MARK_PX = 128      # the rail draws 32 px; 4x for a retina screen
LOGO_W = 320       # the website banner and the desk splash
FAVICON_PX = 32

# Palette size for the two transparent PNGs. Measured on this artwork, at 320 px
# wide: full-colour PNG 56,872 bytes, 64-colour palette 8,170, WebP at quality 88
# 25,726. A smooth two-colour gradient is the worst case for full-colour PNG and
# about the best case for a palette, and lossy WebP spends its bytes on the alpha
# channel. 64 colours keeps 53 distinct alpha levels, so the anti-aliased edge
# stays smooth - checked by compositing the saved file onto the dark theme's
# background and looking at it, not by trusting the number.
PALETTE = 64


def find_master():
    for ext in MASTER_EXTS:
        p = os.path.join(MASTER_DIR, MASTER_STEM + ext)
        if os.path.isfile(p):
            return p
    sys.exit(
        f"No master artwork found.\nExpected one of:\n  "
        + "\n  ".join(os.path.join(MASTER_DIR, MASTER_STEM + e) for e in MASTER_EXTS)
    )


def to_rgba_keyed(im):
    """Return the image with its white background turned into transparency."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            d = 255 - min(r, g, b)          # how far from white
            if d >= EDGE:
                continue                     # solid ink, leave it exactly as it is
            if d == 0:
                px[x, y] = (255, 255, 255, 0)
                continue
            na = int(round(d * 255 / EDGE))
            # Un-premultiply from the white ground, so the edge keeps its colour
            # instead of fading to grey over a dark background.
            f = 255 / na
            px[x, y] = (
                max(0, min(255, int(round(255 - (255 - r) * f)))),
                max(0, min(255, int(round(255 - (255 - g) * f)))),
                max(0, min(255, int(round(255 - (255 - b) * f)))),
                na,
            )
    return im


def ink_rows(im):
    """Per-row ink counts, used to find the bounding box and the split."""
    g = im.convert("L")
    px = g.load()
    w, h = im.size
    return [sum(1 for x in range(w) if px[x, y] < WHITE) for y in range(h)]


def ink_cols(im, top, bottom):
    g = im.convert("L")
    px = g.load()
    w, _ = im.size
    return [sum(1 for y in range(top, bottom) if px[x, y] < WHITE) for x in range(w)]


def bbox_of(rows, cols):
    ys = [i for i, v in enumerate(rows) if v]
    xs = [i for i, v in enumerate(cols) if v]
    if not ys or not xs:
        sys.exit("The master looks blank - no ink found. Is it the right file?")
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


def split_monogram(im, box):
    """The monogram's own box: everything above the first blank band inside the lockup.

    Returns None when there is no blank band, i.e. a one-piece logo.
    """
    x0, y0, x1, y1 = box
    g = im.convert("L")
    px = g.load()
    rows = [sum(1 for x in range(x0, x1) if px[x, y] < WHITE) for y in range(y0, y1)]

    # Walk down from the top through ink, then find the first run of blank rows.
    i = 0
    while i < len(rows) and rows[i]:
        i += 1
    gap_start = i
    while i < len(rows) and not rows[i]:
        i += 1
    gap_end = i
    if gap_start == 0 or gap_end >= len(rows) or gap_end == gap_start:
        return None                      # no band, or nothing after it

    top = y0
    bottom = y0 + gap_start
    cols = ink_cols(im, top, bottom)
    xs = [j for j, v in enumerate(cols) if v]
    return xs[0], top, xs[-1] + 1, bottom


def square(im, size, pad_ratio=0.06):
    """Fit `im` inside a transparent square, centred, with a little breathing room."""
    inner = int(size * (1 - 2 * pad_ratio))
    c = im.copy()
    c.thumbnail((inner, inner), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.paste(c, ((size - c.width) // 2, (size - c.height) // 2), c)
    return out


def main():
    master = find_master()
    im = Image.open(master)
    print(f"master   {os.path.relpath(master, HERE)}  {im.size[0]}x{im.size[1]} {im.format}")

    keyed = to_rgba_keyed(im)
    box = bbox_of(ink_rows(im), ink_cols(im, 0, im.size[1]))
    lockup = keyed.crop(box)
    print(f"lockup   {lockup.width}x{lockup.height} (cropped to ink)")

    mono_box = split_monogram(im, box)
    if mono_box:
        mono = keyed.crop(mono_box)
        print(f"monogram {mono.width}x{mono.height} (split at the blank band)")
    else:
        mono = lockup
        print("monogram no blank band found - using the whole lockup for the mark")

    os.makedirs(OUT_DIR, exist_ok=True)

    def palette(img):
        return img.quantize(colors=PALETTE, method=Image.FASTOCTREE)

    # 1. the mark
    palette(square(mono, MARK_PX)).save(
        os.path.join(OUT_DIR, "alvoraa-mark.png"), optimize=True)

    # 2. the full lockup
    logo = lockup.copy()
    logo.thumbnail((LOGO_W, LOGO_W), Image.LANCZOS)
    palette(logo).save(os.path.join(OUT_DIR, "alvoraa-logo.png"), optimize=True)

    # 3. the favicon, on white - tab chrome is not reliably light or dark
    fav = square(mono, FAVICON_PX, pad_ratio=0.03)
    ground = Image.new("RGBA", fav.size, (255, 255, 255, 255))
    ground.alpha_composite(fav)
    ground.convert("RGB").save(os.path.join(OUT_DIR, "alvoraa-favicon.png"), optimize=True)

    total = 0
    print()
    for name in ("alvoraa-mark.png", "alvoraa-logo.png", "alvoraa-favicon.png"):
        p = os.path.join(OUT_DIR, name)
        n = os.path.getsize(p)
        total += n
        with Image.open(p) as chk:
            print(f"  {name:22} {chk.size[0]:>4}x{chk.size[1]:<4} {n:>7,} bytes  {chk.mode}")
    print(f"  {'total':22} {'':>9} {total:>7,} bytes")


if __name__ == "__main__":
    main()
