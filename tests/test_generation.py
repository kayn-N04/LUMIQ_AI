import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from PIL import Image

import app
from services.cloudflare_ai_service import (
    CloudflareAIService, CloudflareAPIError, prepare_reference_image,
)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parent / ".runtime"
        runtime.mkdir(exist_ok=True)
        temp_patch = patch.object(tempfile, "tempdir", str(runtime))
        temp_patch.start()
        self.addCleanup(temp_patch.stop)
        self.root = runtime / uuid4().hex
        self.root.mkdir()
        self.addCleanup(self.cleanup_files)
        self.input = self.root / "input.png"
        Image.new("RGBA", (800, 400), (0, 0, 0, 0)).save(self.input)

    def cleanup_files(self):
        for path in self.root.iterdir():
            path.unlink()
        self.root.rmdir()

    def test_transparent_background_becomes_white_and_size_is_limited(self):
        Image.new("RGBA", (1600, 800), (0, 0, 0, 0)).save(self.input)
        image = Image.open(io.BytesIO(prepare_reference_image(self.input)))
        self.assertEqual(image.size, (1024, 512))
        self.assertEqual(image.getpixel((100, 100)), (255, 255, 255))

    def service(self):
        return CloudflareAIService(account_id="test", api_token="test")

    def test_moderation_is_not_retried_or_saved(self):
        response = httpx.Response(400, request=httpx.Request("POST", "https://example.com"),
                                 json={"errors": [{"code": 3030, "message": "Your output has been flagged"}]})
        with patch("httpx.Client.post", return_value=response) as post:
            with self.assertRaises(CloudflareAPIError) as caught:
                self.service().generate(self.input, self.input, "test", self.root / "out.png")
        self.assertEqual(caught.exception.status_code, 422)
        post.assert_called_once()
        self.assertFalse((self.root / "out.png").exists())

    def test_success_saves_image(self):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), "red").save(buffer, "PNG")
        response = httpx.Response(200, request=httpx.Request("POST", "https://example.com"),
                                 json={"result": {"image": base64.b64encode(buffer.getvalue()).decode()}})
        with patch("httpx.Client.post", return_value=response):
            output = self.service().generate(self.input, self.input, "test", self.root / "out.png")
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))

    def test_invalid_provider_response(self):
        response = httpx.Response(200, request=httpx.Request("POST", "https://example.com"), text="not json")
        with patch("httpx.Client.post", return_value=response):
            with self.assertRaises(CloudflareAPIError) as caught:
                self.service().generate(self.input, self.input, "test", self.root / "out.png")
        self.assertEqual(caught.exception.status_code, 502)

    def test_route_preserves_error_status_and_removes_temporary_files(self):
        paths = []

        def fail(shirt, pattern, output, *placement):
            paths.extend([shirt, pattern])
            self.assertTrue(all(path.exists() for path in paths))
            raise ValueError("invalid image")

        with patch.object(app, "OUTPUT_DIR", self.root), patch.object(app, "generate_ai_design", side_effect=fail):
            with TestClient(app.app) as client:
                response = client.post("/api/generate", files={
                    "shirt": ("shirt.png", b"image"), "pattern": ("pattern.png", b"image"),
                })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid image")
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths))

    def test_oversized_upload_never_calls_provider(self):
        with patch.object(app, "OUTPUT_DIR", self.root), patch.object(app, "MAX_UPLOAD_BYTES", 4), \
                patch.object(app, "generate_ai_design") as service:
            with TestClient(app.app) as client:
                response = client.post("/api/generate", files={
                    "shirt": ("shirt.png", b"12345"), "pattern": ("pattern.png", b"123"),
                })
        self.assertEqual(response.status_code, 413)
        service.assert_not_called()


    def test_route_calls_ai_and_returns_provider_output(self):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), "red").save(buffer, "PNG")
        provider = httpx.Response(200, request=httpx.Request("POST", "https://example.com"),
            json={"result": {"image": base64.b64encode(buffer.getvalue()).decode()}})
        art = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        art.putpixel((5, 5), (255, 255, 255, 255))
        pattern = io.BytesIO()
        art.save(pattern, "PNG")
        with patch.object(app, "OUTPUT_DIR", self.root), patch.dict("os.environ", {"CF_ACCOUNT_ID": "test", "CF_API_TOKEN": "test"}), patch("httpx.Client.post", return_value=provider) as post:
            with TestClient(app.app) as client:
                response = client.request("POST", "/api/generate", data={"garment_color": "Xanh navy"}, files={
                    "shirt": ("shirt.png", self.input.read_bytes()), "pattern": ("pattern.png", pattern.getvalue())})
                self.assertEqual(response.status_code, 200, response.text)
                with Image.open(io.BytesIO(client.get(response.json()["image_url"]).content)) as result:
                    self.assertEqual(result.size, (32, 32))
                    self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))
            post.assert_called_once()
            self.assertIn("#14213D", post.call_args.kwargs["data"]["prompt"])
            self.assertEqual(post.call_args.kwargs["files"]["input_image_1"][2], "image/png")


    def test_artwork_transparency_and_canvas(self):
        from services.background import remove_artwork_background
        art = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        art.putpixel((5, 5), (255, 255, 255, 128))
        art.save(self.input)
        result = remove_artwork_background(self.input, self.root / "cut.png")
        with Image.open(result) as image:
            self.assertEqual(image.size, (10, 10))
            self.assertEqual(image.getpixel((5, 5)), (255, 255, 255, 128))
        encoded = prepare_reference_image(result, preserve_alpha=True)
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((5, 5))[3], 128)

    def test_invalid_controls_never_call_ai(self):
        from services.generation import generate_design
        for color, x in [("red", 50), ("#123456", float("nan")), ("Giữ nguyên", 101)]:
            with patch("services.generation.CloudflareAIService") as service, self.assertRaises(ValueError):
                generate_design(self.input, self.input, self.root / "out.png", x, 45, 25, color)
            service.assert_not_called()

    def test_provider_error_reaches_browser(self):
        with patch.object(app, "OUTPUT_DIR", self.root), patch.object(app, "generate_ai_design", side_effect=CloudflareAPIError("busy", 503)), TestClient(app.app) as client:
            response = client.post("/api/generate", files={"shirt": ("a.png", b"test"), "pattern": ("b.png", b"test")})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"], "busy")


if __name__ == "__main__":
    unittest.main()
