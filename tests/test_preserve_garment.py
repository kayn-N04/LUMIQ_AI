import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from services.generation import generate_design
from services.image_layout import placement_box
from services.prompt_builder import build_design_prompt


class PreserveGarmentTests(unittest.TestCase):
    def test_beige_ai_output_cannot_recolor_white_shirt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shirt = Image.new("RGBA", (120, 160), "white")
            shirt.putpixel((3, 3), (20, 100, 90, 255))  # existing logo
            shirt.putpixel((0, 0), (13, 42, 77, 0))  # hidden RGB must survive
            shirt.save(root / "shirt.png")
            art = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
            art.paste((200, 50, 40, 255), (5, 5, 15, 15))
            art.putpixel((10, 10), (200, 50, 40, 0))  # transparent hole
            art.save(root / "art.png")
            def generate(guide, artwork, prompt, output):
                self.assertIn("COLOR LOCK", prompt)
                Image.new("RGB", (64, 64), (220, 190, 140)).save(output)
                return output
            with patch("services.generation.CloudflareAIService") as service:
                service.return_value.generate.side_effect = generate
                output = generate_design(root / "shirt.png", root / "art.png", root / "out.png", 50, 50, 25)
                service.return_value.generate.assert_called_once()
            left, top, aw, ah = placement_box(shirt.size, art.size, 50, 50, 25)
            coverage = Image.new("L", shirt.size)
            coverage.paste(art.resize((aw, ah), Image.Resampling.LANCZOS).getchannel("A"), (left, top))
            with Image.open(output) as result:
                self.assertEqual(result.size, shirt.size)
                unchanged = np.asarray(coverage) == 0
                np.testing.assert_array_equal(np.asarray(result)[unchanged], np.asarray(shirt)[unchanged])
                ink = np.asarray(coverage) == 255
                self.assertTrue(ink.any())
                resized_art = Image.new("RGBA", shirt.size)
                resized_art.paste(art.resize((aw, ah), Image.Resampling.LANCZOS), (left, top))
                delta = np.abs(np.asarray(result)[:, :, :3][ink].astype(int) - np.asarray(resized_art)[:, :, :3][ink].astype(int))
                self.assertLessEqual(int(delta.max()), 3)

    def test_selected_color_still_uses_generated_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (40, 40), "white").save(root / "shirt.png")
            art = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
            art.putpixel((5, 5), (255, 0, 0, 255))
            art.save(root / "art.png")
            def generate(guide, artwork, prompt, output):
                self.assertIn("#14213D", prompt)
                Image.new("RGB", (32, 32), (20, 33, 61)).save(output)
                return output
            with patch("services.generation.CloudflareAIService") as service:
                service.return_value.generate.side_effect = generate
                output = generate_design(root / "shirt.png", root / "art.png", root / "out.png", garment_color="Xanh navy")
            with Image.open(output) as result:
                self.assertEqual(result.size, (32, 32))
                self.assertEqual(result.getpixel((0, 0)), (20, 33, 61))

    def test_preservation_prompt_has_no_recolor_or_background_replacement(self):
        prompt = build_design_prompt()
        self.assertIn("White fabric must stay white", prompt)
        self.assertIn("preserve the original scene background", prompt)
        self.assertIn("Existing logos", prompt)
        self.assertNotIn("replace the scene background", prompt)
