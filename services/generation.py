"""Shared AI pipeline for web and CLI."""
import tempfile
from pathlib import Path
from services.background import remove_artwork_background
from services.cloudflare_ai_service import CloudflareAIService
from services.prompt_builder import build_design_prompt, validate_design_options
from services.image_layout import build_layout, load_image
from services.preserve_garment import finish_preserving_garment


def generate_design(shirt, pattern, output, center_x=50, center_y=45, print_width=25, garment_color="Giữ nguyên", rotation=0):
    validate_design_options(garment_color, center_x, center_y, print_width, rotation)
    service = CloudflareAIService()
    garment = load_image(shirt)  # Validate once before segmentation; reuse for layout.
    with tempfile.TemporaryDirectory(prefix="lumiq-") as directory:
        cutout = remove_artwork_background(pattern, Path(directory) / "artwork.png")
        layout = Path(directory) / "layout.png"
        bounds = build_layout(garment, cutout, layout, center_x, center_y, print_width, rotation)
        prompt = build_design_prompt(garment_color, center_x, center_y, print_width, bounds)
        if garment_color == "Giữ nguyên":
            ai_result = Path(directory) / "ai-result.png"
            service.generate(layout, cutout, prompt, ai_result)
            return finish_preserving_garment(garment, cutout, ai_result, output,
                                            center_x, center_y, print_width, rotation)
        return service.generate(layout, cutout, prompt, output)
