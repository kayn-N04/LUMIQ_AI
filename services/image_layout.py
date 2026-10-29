"""Image validation and one placement guide shared with browser geometry."""
from pathlib import Path
from PIL import Image, ImageOps

def load_image(path: str | Path) -> Image.Image:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh đầu vào: {path}")
    with Image.open(path) as source:
        if source.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Chỉ hỗ trợ PNG, JPEG hoặc WebP.")
        if source.width * source.height > 25_000_000:
            raise ValueError("Ảnh tối đa 25 megapixel.")
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.info = source.info.copy()
        return image


def build_layout(shirt, artwork, output, x, y, width, rotation=0):
    # Reuse the validated shirt without decoding it a second time.
    garment = shirt.copy() if isinstance(shirt, Image.Image) else load_image(shirt)
    art = rotate_artwork(load_image(artwork), rotation)
    left, top, aw, ah = placement_box(garment.size, art.size, x, y, width)
    garment.alpha_composite(art.resize((aw, ah), Image.Resampling.LANCZOS), (left, top))
    garment.save(output, "PNG", compress_level=1)
    return (100 * left / garment.width, 100 * top / garment.height, 100 * (left + aw) / garment.width, 100 * (top + ah) / garment.height)


def rotate_artwork(artwork, rotation):
    """Rotate clockwise and expand the canvas without clipping transparent edges."""
    if rotation == 0:
        return artwork
    return artwork.rotate(-rotation, Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))


def placement_box(garment_size, artwork_size, x, y, width):
    """Shared integer geometry for AI guide and protected final rendering."""
    w, h = garment_size
    art_width, art_height = artwork_size
    scale = min(w * width / 100 / art_width, h / art_height)
    aw, ah = max(1, int(art_width * scale + .5)), max(1, int(art_height * scale + .5))
    left = max(0, min(w - aw, int(w * x / 100 - aw / 2 + .5)))
    top = max(0, min(h - ah, int(h * y / 100 - ah / 2 + .5)))
    return left, top, aw, ah
