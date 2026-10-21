from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import math

# Canvas
W, H = 1700, 1000
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

# Plate geometry (isometric-ish, matching original layout)
# Top-left, top-right, bottom-right, bottom-left
tl = (430, 260)
tr = (1420, 210)
br = (1490, 730)
bl = (500, 780)

# --- Create metal plate with checker pattern on a separate layer ---
plate_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pdraw = ImageDraw.Draw(plate_layer)

# Base fill (light silver gradient simulated with multiple polygons)
pdraw.polygon([tl, tr, br, bl], fill=(210, 212, 215, 255))

# Add a subtle highlight blob in the middle (like a reflection)
cx = (tl[0] + tr[0] + br[0] + bl[0]) // 4
cy = (tl[1] + tr[1] + br[1] + bl[1]) // 4

# Checker/diamond plate pattern — rows of small raised diamonds
# We draw them in plate-local coordinates, then skew toward the perspective
def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

rows = 28
cols = 55
for r in range(rows):
    for c in range(cols):
        u = (c + 0.5) / cols
        v = (r + 0.5) / rows
        top = lerp(tl, tr, u)
        bot = lerp(bl, br, u)
        p = lerp(top, bot, v)
        if r % 2 == 1:
            p = (p[0] + 9, p[1])
        x, y = p
        # Short raised line (3-bar checker style)
        for k in (-4, 0, 4):
            pdraw.line(
                [(x - 7 + k, y + 3), (x + 7 + k, y - 3)],
                fill=(155, 158, 162, 220),
                width=2,
            )
            pdraw.line(
                [(x - 7 + k, y + 2), (x + 7 + k, y - 4)],
                fill=(235, 237, 240, 160),
                width=1,
            )

# Add a soft highlight overlay
hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hd = ImageDraw.Draw(hl)
for r in range(220, 0, -6):
    alpha = int(55 * (1 - r / 220))
    hd.ellipse(
        [cx - r * 1.4, cy - r * 0.5, cx + r * 1.4, cy + r * 0.5],
        fill=(255, 255, 255, alpha),
    )
hl = hl.filter(ImageFilter.GaussianBlur(radius=25))

# Slight blur to soften the pattern
plate_layer = plate_layer.filter(ImageFilter.GaussianBlur(radius=0.6))
plate_layer = Image.alpha_composite(plate_layer, hl)

# Paste plate onto canvas
img.paste(plate_layer, (0, 0), plate_layer)
draw = ImageDraw.Draw(img)

# Thickness edge (front face of the plate)
edge_front = [
    bl,
    br,
    (br[0] + 5, br[1] + 25),
    (bl[0] + 5, bl[1] + 25),
]
draw.polygon(edge_front, fill=(175, 177, 180))
edge_right = [
    tr,
    br,
    (br[0] + 5, br[1] + 25),
    (tr[0] + 5, tr[1] + 25),
]
draw.polygon(edge_right, fill=(155, 157, 160))

# Outline
draw.polygon([tl, tr, br, bl], outline=(120, 122, 125), width=2)

# --- Dimension arrows and labels ---
BLUE = (0, 85, 170)

def load_font(size):
    for name in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()

font = load_font(58)

def draw_arrow(p1, p2, color, width=4, head=18):
    draw.line([p1, p2], fill=color, width=width)
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for end, a in [(p2, angle), (p1, angle + math.pi)]:
        ex, ey = end
        left = (ex - head * math.cos(a - 0.45), ey - head * math.sin(a - 0.45))
        right = (ex - head * math.cos(a + 0.45), ey - head * math.sin(a + 0.45))
        draw.polygon([end, left, right], fill=color)

# Top arrow: 1500 mm (along the top edge, above the plate)
offset_top = (0, -120)
a1 = (tl[0] + offset_top[0], tl[1] + offset_top[1])
a2 = (tr[0] + offset_top[0], tr[1] + offset_top[1])
draw_arrow(a1, a2, BLUE, width=5, head=22)

label_top = "1500 mm"
bbox = draw.textbbox((0, 0), label_top, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
mid_x = (a1[0] + a2[0]) / 2
mid_y = (a1[1] + a2[1]) / 2
draw.text((mid_x - tw / 2, mid_y - th - 15), label_top, fill=BLUE, font=font)

# Left arrow: 1300 mm (along the left edge, to the left of the plate)
offset_left = (-120, 0)
b1 = (tl[0] + offset_left[0], tl[1] + offset_left[1])
b2 = (bl[0] + offset_left[0], bl[1] + offset_left[1])
draw_arrow(b1, b2, BLUE, width=5, head=22)

label_left = "1300 mm"
bbox = draw.textbbox((0, 0), label_left, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
mid_x = (b1[0] + b2[0]) / 2
mid_y = (b1[1] + b2[1]) / 2
draw.text((mid_x - tw - 20, mid_y - th / 2), label_left, fill=BLUE, font=font)

out_path = r"C:\Users\JonatanÅman\Desktop\chatbot-app\plat_1500x1300_mm.png"
img.save(out_path, "PNG")
print(f"Saved: {out_path}")
print(f"Size: {img.size}")
