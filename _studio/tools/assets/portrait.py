"""Alternative portrait crops img/tushar-pandey-b.webp (640) and
img/tushar-pandey-b-320.webp from the original photo, with a mild grade that
cools and desaturates the background while leaving the face untouched.
Writes no metadata (the source carries GPS EXIF).

    python _studio/tools/assets/portrait.py [path/to/source.jpg]
"""
import pathlib, sys
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / 'Pandey_Tushar_pic.jpg')

im = ImageOps.exif_transpose(Image.open(SRC)).convert('RGB')
W, H = im.size

# square crop, as loose as the frame allows while keeping the face near the centre
FACE = (0.452 * W, 0.40 * H)          # centre of the face in the source, by eye
side = int(min(W, H, FACE[0] / 0.475))
left = max(0, min(W - side, int(FACE[0] - 0.475 * side)))
top = max(0, min(H - side, int(FACE[1] - 0.44 * side)))
im = im.crop((left, top, left + side, top + side))

# background grade: less saturation, slightly cooler and a touch darker
bg = ImageEnhance.Color(im).enhance(0.5)
r, g, b = bg.split()
r = r.point(lambda v: v * 0.95)
b = b.point(lambda v: min(255, v * 1.04 + 3))
bg = ImageEnhance.Brightness(Image.merge('RGB', (r, g, b))).enhance(0.95)

# keep mask: head, neck and sweater, feathered so no edge is visible
mask = Image.new('L', im.size, 0)
d = ImageDraw.Draw(mask)
s = side / 1000
fx, fy = (FACE[0] - left) / side * 1000, (FACE[1] - top) / side * 1000
d.ellipse([(fx - 150) * s, (fy - 270) * s, (fx + 150) * s, (fy + 190) * s], fill=255)   # head and hair
d.rectangle([(fx - 75) * s, (fy + 80) * s, (fx + 110) * s, (fy + 330) * s], fill=255)   # neck
d.ellipse([(fx - 400) * s, (fy + 250) * s, (fx + 520) * s, (fy + 900) * s], fill=255)   # shoulders
mask = mask.filter(ImageFilter.GaussianBlur(45 * s))

out = Image.composite(im, bg, mask)

for size, name in ((640, 'tushar-pandey-b.webp'), (320, 'tushar-pandey-b-320.webp')):
    path = ROOT / 'img' / name
    out.resize((size, size), Image.LANCZOS).save(path, 'WEBP', quality=84, method=6)
    check = Image.open(path)
    assert not check.info.get('exif') and not check.getexif(), f'{name} carries EXIF'
    print(f'{name}: {path.stat().st_size} bytes, no EXIF')
