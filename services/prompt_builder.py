"""Fixed garment palette and unambiguous AI reference roles."""
import math

COLORS = {
    "Giữ nguyên": (None, "original fabric color"),
    "Đen": ("#171717", "deep neutral black"),
    "Đỏ": ("#C62828", "rich red"),
    "Xanh navy": ("#14213D", "dark navy blue"),
    "Xanh mint": ("#A8DCC8", "light pastel mint green"),
    "Be nhạt": ("#E8DCC6", "light warm beige"),
}


def validate_design_options(garment_color, center_x, center_y, print_width):
    if garment_color not in COLORS:
        raise ValueError("Hãy chọn một màu áo trong danh sách có sẵn.")
    if not all(math.isfinite(v) for v in (center_x, center_y, print_width)) or not (0 <= center_x <= 100 and 0 <= center_y <= 100 and 1 <= print_width <= 100):
        raise ValueError("Vị trí phải từ 0–100%, độ rộng từ 1–100%.")


def build_design_prompt(garment_color="Giữ nguyên", center_x=50, center_y=45, print_width=25, bounds=None):
    validate_design_options(garment_color, center_x, center_y, print_width)
    code, name = COLORS[garment_color]
    color = "Keep the original shirt fabric color unchanged." if code is None else f"REQUIRED FABRIC COLOR: recolor all shirt fabric, including sleeves and collar, to {name} (sRGB {code}). Replace the old fabric hue; do not retain it. Preserve natural highlights, shadows and fabric texture. Do not tint the artwork, skin, buttons or accessories. The background must remain pure white."
    region = "Follow the exact existing artwork placement in image 1."
    if bounds is not None:
        left, top, right, bottom = bounds
        region += f" Artwork canvas bounds in image 1: left {left:.3f}%, top {top:.3f}%, right {right:.3f}%, bottom {bottom:.3f}%. These are constraints, not another print request."
    return f"""Finish the shirt mockup in IMAGE 1. It ALREADY contains the requested artwork at its final position and size.
IMAGE 2 is an isolated detail reference of that SAME artwork, not a second graphic to insert.
Keep exactly ONE instance of the requested artwork. Do not add, duplicate, repeat, tile, echo or overlay another copy. Do not move, center, enlarge or shrink the existing print.
{region}
{color}
Integrate only the existing print into the fabric with subtle texture and fold shading. Preserve its lettering, colors, identity and silhouette. Do not add borders, panels or drop shadows.
REQUIRED BACKGROUND: replace the original scene background with a uniform pure white background (sRGB #FFFFFF). No gradient, scenery, texture, halo or cast shadow beneath or around the shirt. Preserve subtle shading only on the fabric.
REQUIRED GARMENT GEOMETRY: preserve the exact shirt silhouette and proportions from IMAGE 1, including collar/neckline, shoulder width, sleeve shape and length, cuffs, torso width and length, hem, seams, buttons and existing folds. Keep its pose, orientation, camera angle, scale and position within the frame. Do not redesign, reshape, stretch, slim, widen, crop or invent missing garment parts. Changing the background must not change the shirt outline. Preserve any visible person and their pose.
Only the scene background, selected fabric color and existing print finish may change. No extra logos, objects, text or reference panels. Return one finished photograph."""
