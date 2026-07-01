"""Generate HA/HACS brand images for the Amazing Irrigation integration.

Produces (into custom_components/amazing_irrigation/brand/):
  icon.png       256x256   square avatar icon
  icon@2x.png    512x512   hDPI icon
  logo.png       landscape wordmark (light background)
  logo@2x.png    hDPI logo
  dark_logo.png / dark_logo@2x.png   wordmark for dark backgrounds

Design: rounded-square water gradient with a white droplet holding a green
leaf. No Home Assistant branding is used. Rendered at 4x supersampling for
crisp anti-aliasing, then downscaled with LANCZOS.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 4  # supersampling factor

# Palette (generic irrigation: water blue -> fresh teal, with a green leaf)
TOP = (33, 199, 168)      # teal-green
BOTTOM = (45, 119, 224)   # water blue
DROP = (255, 255, 255)
LEAF = (46, 158, 79)      # fresh green
LEAF_DARK = (33, 122, 60)
INK = (30, 41, 59)        # slate ink for light-bg wordmark
INK_LIGHT = (241, 245, 249)


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def _gradient(size: int) -> Image.Image:
    g = Image.new("RGB", (size, size))
    px = g.load()
    for y in range(size):
        t = y / (size - 1)
        r = _lerp(TOP[0], BOTTOM[0], t)
        gg = _lerp(TOP[1], BOTTOM[1], t)
        b = _lerp(TOP[2], BOTTOM[2], t)
        for x in range(size):
            px[x, y] = (r, gg, b)
    return g


def _droplet_polygon(cx: float, cy: float, R: float, tip_y: float):
    """Return (circle_bbox, triangle_points) forming a teardrop."""
    d = cy - tip_y
    phi = math.acos(max(-1.0, min(1.0, R / d)))
    base = -math.pi / 2  # direction from center up to the tip
    a1 = base + phi
    a2 = base - phi
    t1 = (cx + R * math.cos(a1), cy + R * math.sin(a1))
    t2 = (cx + R * math.cos(a2), cy + R * math.sin(a2))
    circle_bbox = (cx - R, cy - R, cx + R, cy + R)
    triangle = [(cx, tip_y), t1, t2]
    return circle_bbox, triangle


def _leaf_layer(box: int) -> Image.Image:
    """Pointed-oval (vesica) leaf with a central vein, on transparent bg."""
    m1 = Image.new("L", (box, box), 0)
    m2 = Image.new("L", (box, box), 0)
    Rl = box * 0.62
    off = box * 0.40
    cyl = box / 2
    ImageDraw.Draw(m1).ellipse(
        (box / 2 - off - Rl, cyl - Rl, box / 2 - off + Rl, cyl + Rl), fill=255
    )
    ImageDraw.Draw(m2).ellipse(
        (box / 2 + off - Rl, cyl - Rl, box / 2 + off + Rl, cyl + Rl), fill=255
    )
    inter = Image.new("L", (box, box), 0)
    ip = inter.load()
    p1, p2 = m1.load(), m2.load()
    for y in range(box):
        for x in range(box):
            if p1[x, y] and p2[x, y]:
                ip[x, y] = 255

    leaf = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    leaf.paste(Image.new("RGBA", (box, box), LEAF + (255,)), (0, 0), inter)

    vd = ImageDraw.Draw(leaf)
    vw = max(2, box // 40)
    vd.line((box * 0.14, cyl, box * 0.86, cyl), fill=LEAF_DARK + (255,), width=vw)
    for fx in (0.34, 0.50, 0.66):
        vd.line((box * fx, cyl, box * (fx + 0.10), cyl - box * 0.12),
                fill=LEAF_DARK + (255,), width=max(1, vw - 1))
        vd.line((box * fx, cyl, box * (fx + 0.10), cyl + box * 0.12),
                fill=LEAF_DARK + (255,), width=max(1, vw - 1))
    return leaf


def render_icon(px: int) -> Image.Image:
    size = px * SS
    radius = round(size * 0.235)

    base = _gradient(size)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(base, (0, 0), _rounded_mask(size, radius))

    drop = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dd = ImageDraw.Draw(drop)
    cx = size / 2
    cy = size * 0.605
    R = size * 0.255
    tip_y = size * 0.175
    bbox, tri = _droplet_polygon(cx, cy, R, tip_y)
    dd.ellipse(bbox, fill=DROP + (255,))
    dd.polygon(tri, fill=DROP + (255,))
    icon.alpha_composite(drop)

    lbox = round(R * 2.05)
    leaf = _leaf_layer(lbox).rotate(-38, resample=Image.BICUBIC, expand=True)
    lx = round(cx - leaf.width / 2)
    ly = round(cy - leaf.height / 2)
    icon.alpha_composite(leaf, (lx, ly))

    return icon.resize((px, px), Image.LANCZOS)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf"):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def render_logo(short_side: int, dark: bool) -> Image.Image:
    icon_px = short_side
    ss = SS
    pad = round(icon_px * 0.10)
    icon = render_icon(icon_px)

    ink = INK_LIGHT if dark else INK
    accent = (90, 200, 250) if dark else (45, 119, 224)

    title_f = _font(round(icon_px * 0.46) * ss)
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    t1 = "Amazing"
    t2 = "Irrigation"
    b1 = td.textbbox((0, 0), t1, font=title_f)
    b2 = td.textbbox((0, 0), t2, font=title_f)
    tw = max(b1[2] - b1[0], b2[2] - b2[0])
    line_h = (b1[3] - b1[1])

    gap = round(icon_px * 0.06) * ss
    text_w = tw
    text_h = line_h * 2 + gap
    canvas_w = icon_px + pad * 2 + round(text_w / ss)
    canvas_h = icon_px

    logo = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    logo.alpha_composite(icon, (0, 0))

    tlayer = Image.new("RGBA", (text_w + 8 * ss, text_h + 8 * ss), (0, 0, 0, 0))
    tl = ImageDraw.Draw(tlayer)
    y0 = -b1[1]
    tl.text((0, y0), t1, font=title_f, fill=ink + (255,))
    tl.text((0, y0 + line_h + gap), t2, font=title_f, fill=accent + (255,))
    tlayer = tlayer.resize(
        (round(tlayer.width / ss), round(tlayer.height / ss)), Image.LANCZOS
    )
    ty = round((canvas_h - tlayer.height) / 2)
    logo.alpha_composite(tlayer, (icon_px + pad, ty))

    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    return logo


def main() -> None:
    out = Path(__file__).resolve().parents[1] / (
        "custom_components/amazing_irrigation/brand"
    )
    out.mkdir(parents=True, exist_ok=True)

    render_icon(256).save(out / "icon.png", optimize=True)
    render_icon(512).save(out / "icon@2x.png", optimize=True)

    render_logo(128, dark=False).save(out / "logo.png", optimize=True)
    render_logo(256, dark=False).save(out / "logo@2x.png", optimize=True)
    render_logo(128, dark=True).save(out / "dark_logo.png", optimize=True)
    render_logo(256, dark=True).save(out / "dark_logo@2x.png", optimize=True)

    for f in sorted(out.glob("*.png")):
        with Image.open(f) as im:
            print(f"{f.name:20s} {im.size[0]}x{im.size[1]}  {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
