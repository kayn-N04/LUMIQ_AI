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


def validate_design_options(garment_color, center_x, center_y, print_width, rotation=0):
    if garment_color not in COLORS:
        raise ValueError("Hãy chọn một màu áo trong danh sách có sẵn.")
    if not all(math.isfinite(v) for v in (center_x, center_y, print_width, rotation)) or not (0 <= center_x <= 100 and 0 <= center_y <= 100 and 1 <= print_width <= 100 and -180 <= rotation <= 180):
        raise ValueError("Vị trí phải từ 0–100%, độ rộng từ 1–100%, góc xoay từ -180 đến 180 độ.")


def build_design_prompt(garment_color="Giữ nguyên", center_x=50, center_y=45, print_width=25, bounds=None):
    validate_design_options(garment_color, center_x, center_y, print_width)
    code, name = COLORS[garment_color]
    color = "COLOR LOCK: Keep the original shirt fabric color unchanged, including its white balance, saturation and brightness. White fabric must stay white, never cream, beige, yellow or tan. Never borrow a color from IMAGE 2 for the shirt or scene. Do not apply a warm filter or harmonize the shirt color with the artwork." if code is None else f"REQUIRED FABRIC COLOR: recolor all shirt fabric, including sleeves and collar, to {name} (sRGB {code}). Replace the old fabric hue; do not retain it. Preserve natural highlights, shadows and fabric texture. Do not tint the artwork, skin, buttons or accessories. The background must remain pure white."
    region = "Follow the exact existing artwork placement in image 1."
    if bounds is not None:
        left, top, right, bottom = bounds
        region += f" Artwork canvas bounds in image 1: left {left:.3f}%, top {top:.3f}%, right {right:.3f}%, bottom {bottom:.3f}%. These are constraints, not another print request."
    background = ("BACKGROUND LOCK: preserve the original scene background; if already white, keep it white. Do not alter pixels outside the new print region." if code is None else "REQUIRED BACKGROUND: replace the scene background with uniform pure white (sRGB #FFFFFF). No gradient, texture, halo or cast shadow outside the shirt.")
    return f"""Finish the shirt mockup in IMAGE 1. It ALREADY contains the requested artwork at its final position and size.
IMAGE 2 is an isolated detail reference of that SAME artwork, not a second graphic to insert. Any background or empty area in IMAGE 2 is NOT a fabric color reference.
Existing logos and lettering already on the original shirt are separate from the requested new artwork: preserve them; do not copy, relocate or erase them.
Keep exactly ONE instance of the requested artwork. Do not add, duplicate, repeat, tile, echo or overlay another copy. Do not move, center, enlarge or shrink the existing print.
{region}
{color}
Integrate only the existing print into the fabric with subtle texture and fold shading. Preserve its lettering, colors, identity and silhouette. Do not add borders, panels or drop shadows.
{background}
REQUIRED GARMENT GEOMETRY: preserve the exact shirt silhouette and proportions from IMAGE 1, including collar/neckline, shoulder width, sleeve shape and length, cuffs, torso width and length, hem, seams, buttons and existing folds. Keep its pose, orientation, camera angle, scale and position within the frame. Do not redesign, reshape, stretch, slim, widen, crop or invent missing garment parts. Changing the background must not change the shirt outline. Preserve any visible person and their pose.
Follow COLOR LOCK and BACKGROUND LOCK when present. Only an explicitly selected new fabric color permits recoloring. No extra logos, objects, text or reference panels. Return one finished photograph."""
