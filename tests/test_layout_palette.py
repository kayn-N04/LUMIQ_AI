import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from services.image_layout import build_layout
from services.prompt_builder import COLORS, build_design_prompt
from services.generation import generate_design
import app

class LayoutPaletteTests(unittest.TestCase):
    def test_placement_and_single_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new("RGBA", (200, 100), "white").save(root / "shirt.png")
            Image.new("RGBA", (20, 20), "red").save(root / "art.png")
            bounds = build_layout(root / "shirt.png", root / "art.png", root / "layout.png", 75, 50, 10)
            self.assertEqual(bounds, (70, 40, 80, 60))
            with Image.open(root / "layout.png") as image:
                reds = [(x, y) for y in range(100) for x in range(200) if image.getpixel((x, y)) == (255, 0, 0, 255)]
                self.assertEqual(len(reds), 400)
                self.assertEqual(min(x for x, y in reds), 140)
                self.assertEqual(max(x for x, y in reds), 159)

    def test_all_palette_options_reach_prompt_and_page(self):
        page = app.home().body.decode()
        self.assertEqual(len(COLORS), 6)
        for name, (code, description) in COLORS.items():
            prompt = build_design_prompt(name)
            self.assertIn(description if code else "unchanged", prompt)
            if code:
                self.assertIn(code, prompt)
            self.assertIn(f'value="{name}"', page)
        self.assertNotIn('recolorEnabled', page)
        self.assertNotIn('recolor.js', page)

    def test_pipeline_sends_placed_guide_not_plain_shirt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new("RGBA", (200, 100), "white").save(root / "shirt.png")
            art = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
            art.paste("red", (5, 5, 15, 15))
            art.save(root / "art.png")
            def check(guide, artwork, prompt, output):
                with Image.open(guide) as image:
                    self.assertEqual(image.getpixel((150, 50)), (255, 0, 0, 255))
                    self.assertEqual(image.getpixel((100, 50)), (255, 255, 255, 255))
                self.assertIn("exactly ONE", prompt)
                self.assertIn("#A8DCC8", prompt)
                self.assertIn("left 70.000%", prompt)
                return output
            with patch("services.generation.CloudflareAIService") as service:
                service.return_value.generate.side_effect = check
                generate_design(root / "shirt.png", root / "art.png", root / "out.png", 75, 50, 10, "Xanh mint")
                service.return_value.generate.assert_called_once()
