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


def build_layout(shirt, artwork, output, x, y, width):
    # Reuse the validated shirt without decoding it a second time.
    garment = shirt.copy() if isinstance(shirt, Image.Image) else load_image(shirt)
    art = load_image(artwork)
    w, h = garment.size
    scale = min(w * width / 100 / art.width, h / art.height)
    aw, ah = max(1, int(art.width * scale + .5)), max(1, int(art.height * scale + .5))
    left = max(0, min(w - aw, int(w * x / 100 - aw / 2 + .5)))
    top = max(0, min(h - ah, int(h * y / 100 - ah / 2 + .5)))
    garment.alpha_composite(art.resize((aw, ah), Image.Resampling.LANCZOS), (left, top))
    garment.save(output, "PNG")
    return (100 * left / w, 100 * top / h, 100 * (left + aw) / w, 100 * (top + ah) / h)
