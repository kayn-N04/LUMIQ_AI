"""Keep original fabric pixels; transfer only bounded AI shading to new artwork."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from services.image_layout import load_image, placement_box, rotate_artwork


def finish_preserving_garment(garment, artwork_path, ai_path, output, x, y, width, rotation=0):
    art = rotate_artwork(load_image(artwork_path), rotation)
    left, top, aw, ah = placement_box(garment.size, art.size, x, y, width)
    art = art.resize((aw, ah), Image.Resampling.LANCZOS)
    # AI can redraw the shirt or invent details. Never copy its RGB pixels onto
    # the garment. Use only a small, smoothed luminance adjustment on artwork.
    box = (left, top, left + aw, top + ah)
    radius = max(2, min(aw, ah) / 32)
    # Rebuild only the print patch; avoid decoding another full-resolution guide.
    reference_patch = Image.alpha_composite(garment.crop(box), art)
    original_light = np.asarray(ImageOps.grayscale(reference_patch).filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)
    generated = load_image(ai_path)
    # Upscale a single luminance channel rather than a full RGBA image.
    generated_light = ImageOps.grayscale(generated).resize(garment.size, Image.Resampling.LANCZOS)
    ai_light = np.asarray(generated_light.crop(box).filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)
    del generated_light, generated, reference_patch
    adjustment = np.clip(ai_light - original_light, -12, 12) * 0.25
    pixels = np.array(art)
    # Bound float scratch arrays even for very large print areas.
    for start in range(0, ah, 128):
        stop = min(start + 128, ah)
        rgb = pixels[start:stop, :, :3].astype(np.float32)
        rgb += adjustment[start:stop, :, None]
        pixels[start:stop, :, :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    shaded = Image.fromarray(pixels)
    result = garment.copy()
    patch = result.crop(box)
    blended = Image.alpha_composite(patch, shaded)
    # Also preserve hidden RGB of fully transparent original pixels outside ink.
    coverage = shaded.getchannel("A").point(lambda a: 255 if a else 0)
    result.paste(blended, (left, top), coverage)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "PNG", icc_profile=garment.info.get("icc_profile"))
    return output
