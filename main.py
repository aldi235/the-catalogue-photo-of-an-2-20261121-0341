#!/usr/bin/env python3
"""The Catalogue Photo of an Impossible Gadget: a solar-powered torch.

A studio product photograph, drawn entirely in code: a sleek aluminium
torch with a solar panel on its body, charged by a small desk lamp pointed
at the panel -- a torch that needs light to make light.

Pure stdlib Python (no PIL): own RGB pixel buffer, drawing engine,
5x7 bitmap font, and a zlib/struct PNG encoder. Writes /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png), 1024x1024, under 1 MiB.
"""
import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- pixel buffer
BUF = bytearray(W * H * 3)


def px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        BUF[i] = r
        BUF[i + 1] = g
        BUF[i + 2] = b


def blend(x, y, r, g, b, a):
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        if a >= 1.0:
            BUF[i] = r
            BUF[i + 1] = g
            BUF[i + 2] = b
        else:
            BUF[i] = int(BUF[i] * (1.0 - a) + r * a)
            BUF[i + 1] = int(BUF[i + 1] * (1.0 - a) + g * a)
            BUF[i + 2] = int(BUF[i + 2] * (1.0 - a) + b * a)


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def grad_stops(stops, t):
    """Interpolate a colour through sorted (pos, colour) stops."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            f = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            return mix(c0, c1, f)
    return stops[-1][1]


# ---------------------------------------------------------------- shapes
def _rr_range(x, y, w, h, r, yy):
    """x-range (exclusive end) of row yy inside a rounded rect, or None."""
    if yy < y or yy >= y + h:
        return None
    x0, x1 = float(x), float(x + w)
    if yy < y + r:
        dy = (y + r) - (yy + 0.5)
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        x0 = max(x0, x + r - dx)
        x1 = min(x1, x + w - r + dx)
    elif yy >= y + h - r:
        dy = (yy + 0.5) - (y + h - r)
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        x0 = max(x0, x + r - dx)
        x1 = min(x1, x + w - r + dx)
    return (int(x0), int(x1))


def rrect(x, y, w, h, r, color):
    for yy in range(max(0, y), min(H, y + h)):
        rng = _rr_range(x, y, w, h, r, yy)
        if rng:
            for xx in range(max(0, rng[0]), min(W, rng[1])):
                px(xx, yy, *color)


def rrect_hgrad(x, y, w, h, r, stops):
    for yy in range(max(0, y), min(H, y + h)):
        rng = _rr_range(x, y, w, h, r, yy)
        if rng:
            for xx in range(max(0, rng[0]), min(W, rng[1])):
                t = (xx - x) / max(1, w - 1)
                px(xx, yy, *grad_stops(stops, t))


def rrect_vgrad(x, y, w, h, r, c_top, c_bot):
    for yy in range(max(0, y), min(H, y + h)):
        rng = _rr_range(x, y, w, h, r, yy)
        if rng:
            t = (yy - y) / max(1, h - 1)
            c = mix(c_top, c_bot, t)
            for xx in range(max(0, rng[0]), min(W, rng[1])):
                px(xx, yy, *c)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    for yy in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
        dy = (yy + 0.5 - cy) / ry
        if abs(dy) >= 1.0:
            continue
        dx = rx * math.sqrt(1.0 - dy * dy)
        for xx in range(max(0, int(cx - dx)), min(W, int(cx + dx))):
            if alpha >= 1.0:
                px(xx, yy, *color)
            else:
                blend(xx, yy, *color, alpha)


def polygon(points, color, alpha=1.0):
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys)) + 1
    n = len(points)
    for yy in range(max(0, y0), min(H, y1)):
        yc = yy + 0.5
        xs = []
        for i in range(n):
            x0, yp0 = points[i]
            x1, yp1 = points[(i + 1) % n]
            if (yp0 <= yc < yp1) or (yp1 <= yc < yp0):
                t = (yc - yp0) / (yp1 - yp0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for xx in range(max(0, int(xs[i])), min(W, int(xs[i + 1]))):
                if alpha >= 1.0:
                    px(xx, yy, *color)
                else:
                    blend(xx, yy, *color, alpha)


def thick_line(x0, y0, x1, y1, width, color):
    length = max(1, int(math.hypot(x1 - x0, y1 - y0)))
    r = width / 2.0
    for i in range(length + 1):
        t = i / length
        ellipse(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, r, color)


def soft_ellipse(cx, cy, rx, ry, color, peak=0.28, layers=7):
    """A soft-edged shadow/glow: stacked ellipses, fading outward."""
    for k in range(layers, 0, -1):
        f = k / layers
        ellipse(cx, cy, rx * (2.0 - f) * 0.75 + rx * 0.25,
                ry * (2.0 - f) * 0.75 + ry * 0.25,
                color, peak * f / layers * 2.2)


# ---------------------------------------------------------------- bitmap font
FONT = {
    'A': [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'L': ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    'O': [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    'R': ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    'S': [".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."],
    'U': ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    'X': ["#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"],
}


def draw_text(x, y, s, scale, color):
    cx = x
    for ch in s:
        g = FONT.get(ch)
        if g is None:
            cx += 6 * scale
            continue
        for row in range(7):
            for col in range(5):
                if g[row][col] == '#':
                    for dy in range(scale):
                        for dx in range(scale):
                            px(cx + col * scale + dx, y + row * scale + dy, *color)
        cx += 6 * scale
    return cx - x - scale


# ---------------------------------------------------------------- PNG encoder
def _chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, buf):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- scene
METAL = [(0.00, (88, 93, 99)), (0.16, (214, 218, 222)), (0.38, (158, 163, 169)),
         (0.62, (126, 131, 137)), (0.84, (96, 101, 107)), (1.00, (66, 70, 76))]
HEAD_METAL = [(0.00, (70, 74, 80)), (0.20, (190, 194, 199)), (0.45, (140, 145, 151)),
              (0.70, (112, 117, 123)), (1.00, (58, 62, 68))]


def draw_scene():
    # --- studio backdrop: vertical gradient + soft radial light + floor
    for y in range(H):
        t = y / (H - 1)
        base = mix((246, 247, 249), (208, 212, 217), t)
        if y > 760:  # floor darkens gently below the horizon
            f = min(1.0, (y - 760) / 160.0)
            base = mix(base, (196, 200, 205), f * 0.6)
        for x in range(W):
            d = math.sqrt((x - 500) ** 2 + (y - 360) ** 2) / 950.0
            a = max(0.0, 0.22 * (1.0 - d))
            px(x, y, *mix(base, (255, 255, 255), a))

    # --- soft contact shadows
    soft_ellipse(420, 792, 185, 26, (60, 64, 70), peak=0.30)
    soft_ellipse(772, 792, 115, 18, (60, 64, 70), peak=0.26)

    # ============================== TORCH (hero, centre-left) ==============
    # tail cap
    rrect_hgrad(348, 748, 144, 36, 12, HEAD_METAL)
    # body: brushed aluminium, horizontal gradient
    rrect_hgrad(345, 252, 150, 500, 18, METAL)
    # brushed-metal micro texture: faint vertical streaks
    for xx in range(348, 492, 3):
        a = 0.05 if (xx // 3) % 2 == 0 else 0.035
        c = (255, 255, 255) if (xx // 3) % 2 == 0 else (40, 44, 48)
        for yy in range(258, 746, 2):
            blend(xx, yy, *c, a)
    # left-edge highlight stripe
    for yy in range(258, 746):
        blend(352, yy, 255, 255, 255, 0.35)
        blend(353, yy, 255, 255, 255, 0.18)
    # head / bezel
    rrect_hgrad(330, 192, 180, 66, 14, HEAD_METAL)
    # bezel grooves
    for gy in (216, 232):
        for xx in range(334, 506):
            blend(xx, gy, 40, 43, 47, 0.55)
            blend(xx, gy + 1, 40, 43, 47, 0.35)
    # lens on top (thin ellipse: we see the torch from the side)
    ellipse(420, 192, 88, 15, (38, 41, 46))
    ellipse(420, 191, 66, 11, (24, 34, 52))
    ellipse(420, 191, 46, 8, (58, 92, 140))
    ellipse(402, 189, 16, 4, (200, 225, 255), alpha=0.85)
    ellipse(436, 192, 8, 2, (200, 225, 255), alpha=0.5)

    # --- solar panel (the joke): silver frame + dark cells + gloss
    rrect(360, 296, 120, 288, 10, (168, 173, 179))
    rrect(365, 301, 110, 278, 7, (22, 30, 56))
    # cells: 5 columns x 10 rows, subtly varied blues
    for ci in range(5):
        for ri in range(10):
            cx0 = 365 + ci * 22
            cy0 = 301 + ri * 28
            shade = (26 + ((ci + ri) % 3) * 5, 38 + ((ci * 2 + ri) % 3) * 6,
                     74 + ((ci + ri * 2) % 3) * 8)
            for yy in range(cy0 + 1, cy0 + 27):
                for xx in range(cx0 + 1, cx0 + 21):
                    px(xx, yy, *shade)
    # cell grid lines
    for ci in range(6):
        xx = 365 + ci * 22
        for yy in range(301, 579):
            blend(xx, yy, 96, 140, 200, 0.55)
    for ri in range(11):
        yy = 301 + ri * 28
        for xx in range(365, 475):
            blend(xx, yy, 96, 140, 200, 0.55)
    # glossy diagonal highlight across the panel
    polygon([(368, 560), (400, 302), (436, 302), (392, 578)],
            (255, 255, 255), alpha=0.10)
    polygon([(408, 302), (424, 302), (380, 578), (372, 578)],
            (255, 255, 255), alpha=0.08)

    # --- power button + symbol
    rrect(404, 616, 32, 48, 12, (44, 47, 51))
    rrect(407, 619, 26, 42, 9, (58, 62, 67))
    ellipse(420, 636, 9, 9, (220, 224, 228))
    ellipse(420, 636, 6, 6, (58, 62, 67))
    for yy in range(624, 634):
        blend(419, yy, 220, 224, 228, 0.9)
        blend(420, yy, 220, 224, 228, 0.9)
        blend(421, yy, 220, 224, 228, 0.9)

    # --- brand label
    w = draw_text(373, 686, "SOLARLUX", 2, (52, 56, 61))

    # ============================== DESK LAMP (the one accessory) ==========
    # base
    ellipse(772, 782, 72, 16, (52, 55, 60))
    ellipse(772, 778, 58, 13, (74, 78, 84))
    ellipse(772, 776, 40, 9, (92, 96, 102))
    # stem leaning toward the torch
    thick_line(772, 774, 706, 468, 11, (48, 51, 56))
    thick_line(768, 772, 702, 470, 4, (120, 124, 130))
    # hinge
    ellipse(706, 466, 13, 13, (40, 43, 47))
    ellipse(706, 466, 7, 7, (150, 154, 160))
    # shade: cone pointing down-left at the solar panel
    polygon([(708, 448), (620, 414), (612, 498), (702, 484)],
            (44, 47, 52))
    polygon([(708, 448), (620, 414), (626, 424), (706, 456)],
            (120, 124, 130), alpha=0.7)
    # bulb glow at the shade opening
    for k in range(9, 0, -1):
        ellipse(618, 456, 30 * k / 9.0 + 6, 26 * k / 9.0 + 5,
                (255, 214, 130), alpha=0.10 + 0.05 * (9 - k) / 9.0)
    ellipse(618, 456, 20, 17, (255, 232, 170))
    ellipse(614, 452, 9, 7, (255, 246, 220))
    # light cone: warm beam from the lamp onto the solar panel
    polygon([(622, 442), (622, 470), (472, 528), (472, 352)],
            (255, 205, 110), alpha=0.10)
    polygon([(622, 448), (622, 464), (472, 500), (472, 380)],
            (255, 215, 130), alpha=0.08)
    # warm kiss of light on the panel's right edge
    soft_ellipse(468, 440, 26, 110, (255, 210, 120), peak=0.16, layers=5)


def main():
    draw_scene()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    n = write_png(path, BUF)
    print("wrote %s %dx%d %d bytes" % (path, W, H, n))


if __name__ == "__main__":
    main()
