"""Shared AI pipeline for web and CLI."""
import tempfile
from pathlib import Path
from services.background import remove_artwork_background
from services.cloudflare_ai_service import CloudflareAIService
from services.prompt_builder import build_design_prompt, validate_design_options
from services.image_layout import build_layout, load_image


def generate_design(shirt, pattern, output, center_x=50, center_y=45, print_width=25, garment_color="Giữ nguyên"):
    validate_design_options(garment_color, center_x, center_y, print_width)
    service = CloudflareAIService()
    garment = load_image(shirt)  # Validate once before segmentation; reuse for layout.
    with tempfile.TemporaryDirectory(prefix="lumiq-") as directory:
        cutout = remove_artwork_background(pattern, Path(directory) / "artwork.png")
        layout = Path(directory) / "layout.png"
        bounds = build_layout(garment, cutout, layout, center_x, center_y, print_width)
        prompt = build_design_prompt(garment_color, center_x, center_y, print_width, bounds)
        return service.generate(layout, cutout, prompt, output)
