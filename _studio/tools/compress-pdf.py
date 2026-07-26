# Recompress the raster plates inside a generated PDF.
#
# Printing the illustrated edition on paper embeds one full colour plate per
# canto, which took that book from 1.8 MB to 12 MB. That is too heavy for a
# download link on a phone. Re-encoding the images at quality 72 brings it to
# about 2 MB with no visible loss at reading size, and the text layer is
# untouched, so extraction and search still match byte for byte.
#
#   python tools/compress-pdf.py in.pdf out.pdf

import sys
from pypdf import PdfReader, PdfWriter

src, dst = sys.argv[1], sys.argv[2]
reader = PdfReader(src)
writer = PdfWriter(clone_from=reader)

replaced = 0
for page in writer.pages:
    for img in page.images:
        try:
            img.replace(img.image, quality=72, optimize=True)
            replaced += 1
        except Exception:
            pass  # not every XObject is a re-encodable raster

writer.compress_identical_objects()
for page in writer.pages:
    page.compress_content_streams()
writer.write(dst)

before = len(open(src, 'rb').read())
after = len(open(dst, 'rb').read())
print(f'{src}: {replaced} images, {before // 1024} KB -> {after // 1024} KB')
