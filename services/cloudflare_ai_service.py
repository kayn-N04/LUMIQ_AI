"""Chuẩn bị hai ảnh tham chiếu, gọi Cloudflare AI và lưu ảnh sản phẩm."""

import atexit
import threading
import base64
import io
import os
from pathlib import Path

import httpx
from PIL import Image
from services.image_layout import load_image


DEFAULT_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
# Ảnh đầu vào giới hạn 1024 px để giảm dữ liệu gửi; không phóng ảnh nhỏ lên.
MAX_INPUT_EDGE = 1024
# Giữ đầu ra 512 px: mức thử nghiệm gọn, không giảm thêm làm hình/chữ quá khó nhìn.
DEFAULT_OUTPUT_EDGE = 512


_client = None
_client_lock = threading.Lock()


def get_http_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(trust_env=False, timeout=httpx.Timeout(180, connect=15, pool=15),
                                   limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))
            atexit.register(_client.close)
        return _client


class CloudflareAPIError(RuntimeError):
    """Lỗi nhà cung cấp với HTTP status phù hợp cho giao diện."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def prepare_reference_image(path: str | Path, preserve_alpha: bool = False) -> bytes:
    """Xoay và thu nhỏ ảnh; giữ alpha PNG cho họa tiết, dùng JPEG cho ảnh áo."""
    rgba = load_image(path)
    rgba.thumbnail((MAX_INPUT_EDGE, MAX_INPUT_EDGE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    if preserve_alpha:
        rgba.save(buffer, "PNG", optimize=True)
    else:
        image = Image.new("RGB", rgba.size, "white")
        image.paste(rgba, mask=rgba.getchannel("A"))
        image.save(buffer, "JPEG", quality=90, optimize=True)
    return buffer.getvalue()


def decode_cloudflare_image(payload: dict) -> Image.Image:
    """Giải mã ảnh base64 mà Cloudflare trả về thành ảnh Pillow."""
    if not isinstance(payload, dict):
        raise CloudflareAPIError("Cloudflare trả về dữ liệu không hợp lệ.")
    result = payload.get("result", payload)
    encoded = result.get("image") if isinstance(result, dict) else result
    if not encoded or not isinstance(encoded, str):
        errors = payload.get("errors") or payload.get("messages") or payload
        raise CloudflareAPIError(f"Cloudflare không trả về ảnh: {errors}")
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        raw = base64.b64decode(encoded, validate=True)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise CloudflareAPIError("Không thể giải mã ảnh do Cloudflare trả về.") from exc


class CloudflareAIService:
    """Giữ cấu hình Cloudflare và thực hiện một lần tạo ảnh cho mỗi yêu cầu."""

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
    ) -> None:
        """Đọc tài khoản, token, model và kích thước từ môi trường/.env."""
        self.account_id = account_id or os.getenv("CF_ACCOUNT_ID")
        self.api_token = api_token or os.getenv("CF_API_TOKEN")
        if not self.account_id or not self.api_token or self.account_id.startswith("your_") or self.api_token.startswith("your_"):
            raise RuntimeError(
                "Chưa cấu hình Cloudflare. Hãy điền CF_ACCOUNT_ID và "
                "CF_API_TOKEN trong file .env."
            )

        self.model = os.getenv("CF_MODEL", DEFAULT_MODEL)
        self.output_width = int(os.getenv("CF_OUTPUT_WIDTH", str(DEFAULT_OUTPUT_EDGE)))
        self.output_height = int(os.getenv("CF_OUTPUT_HEIGHT", str(DEFAULT_OUTPUT_EDGE)))
        if not 256 <= self.output_width <= 1920 or not 256 <= self.output_height <= 1920:
            raise ValueError("Kích thước Cloudflare phải nằm trong khoảng 256–1920 px.")

    @property
    def endpoint(self) -> str:
        """Địa chỉ API của model trong tài khoản Cloudflare hiện tại."""
        return (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )

    def generate(
        self,
        garment_image: str | Path,
        graphic_image: str | Path,
        prompt: str,
        output_path: str | Path,
    ) -> Path:
        """Gửi hai ảnh và prompt, nhận một ảnh rồi lưu PNG không mất chi tiết."""
        garment_bytes = prepare_reference_image(garment_image)
        graphic_bytes = prepare_reference_image(graphic_image, preserve_alpha=True)
        files = {
            "input_image_0": ("garment.jpg", garment_bytes, "image/jpeg"),
            "input_image_1": ("graphic.png", graphic_bytes, "image/png"),
        }
        data = {
            "prompt": prompt,
            "width": str(self.output_width),
            "height": str(self.output_height),
        }
        headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            # Không dùng proxy hệ thống vì proxy cục bộ có thể không hoạt động.
            response = get_http_client().post(
                self.endpoint, headers=headers, data=data, files=files,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("errors", exc.response.text)
            except (ValueError, AttributeError):
                detail = exc.response.text
            if "flagged" in str(detail).lower() or "nsfw" in str(detail).lower():
                raise CloudflareAPIError(
                    "Cloudflare đã chặn yêu cầu theo bộ lọc nội dung. "
                    "Vui lòng kiểm tra ảnh áo và họa tiết; hệ thống có thể nhận diện nhầm.",
                    422,
                ) from exc
            raise CloudflareAPIError(
                f"Cloudflare API lỗi {exc.response.status_code}: {detail}",
                503 if exc.response.status_code == 429 else 502,
            ) from exc
        except httpx.TimeoutException as exc:
            raise CloudflareAPIError("Cloudflare phản hồi quá lâu. Vui lòng thử lại sau.", 504) from exc
        except httpx.HTTPError as exc:
            raise CloudflareAPIError("Không kết nối được Cloudflare. Vui lòng thử lại sau.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise CloudflareAPIError("Cloudflare trả về phản hồi không phải JSON.") from exc
        image = decode_cloudflare_image(payload)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Nén PNG chỉ giảm dung lượng file, không làm giảm chất lượng hình.
        image.save(output_path, "PNG", optimize=True)
        return output_path
