import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
from collections import OrderedDict
import app
from services import background

class PerformanceTests(unittest.TestCase):
    def test_repeated_artwork_reuses_cache_and_preserves_pixels(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(background, "_cache", OrderedDict()), patch.object(background, "_cache_bytes", 0):
            root = Path(directory)
            art = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
            art.putpixel((8, 8), (255, 12, 34, 128))
            art.save(root / "a.png")
            background.remove_artwork_background(root / "a.png", root / "first.png")
            (root / "renamed.png").write_bytes((root / "a.png").read_bytes())
            with patch.object(background, "load_image", side_effect=AssertionError("Cache miss")):
                background.remove_artwork_background(root / "renamed.png", root / "second.png")
            self.assertEqual((root / "first.png").read_bytes(), (root / "second.png").read_bytes())
            with Image.open(root / "second.png") as result:
                self.assertEqual(result.tobytes(), art.tobytes())

    def test_cache_has_memory_limit(self):
        with patch.object(background, "_cache", OrderedDict()), patch.object(background, "_cache_bytes", 0), patch.object(background, "CACHE_LIMIT_BYTES", 10):
            background._remember(b"one", b"123456")
            background._remember(b"two", b"abcdef")
            self.assertNotIn(b"one", background._cache)
            self.assertEqual(background._cache_bytes, 6)
            background._remember(b"large", b"x" * 11)
            self.assertNotIn(b"large", background._cache)

    def test_busy_api_rejects_without_calling_provider(self):
        app._generation_slots.acquire()
        app._generation_slots.acquire()
        try:
            with patch.object(app, "generate_ai_design") as provider, TestClient(app.app) as client:
                response = client.post("/api/generate", files={"shirt": ("a.png", b"test"), "pattern": ("b.png", b"test")})
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response.headers["Retry-After"], "5")
                provider.assert_not_called()
        finally:
            app._generation_slots.release()
            app._generation_slots.release()
