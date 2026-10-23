"""Máy chủ LUMIQ AI: tách nền họa tiết và tạo ảnh áo bằng AI."""

import os
import logging
import tempfile
import threading
import webbrowser
from pathlib import Path
from uuid import uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from services.generation import generate_design as generate_ai_design
from services.cloudflare_ai_service import CloudflareAPIError
from services.prompt_builder import COLORS


PROJECT_DIR = Path(__file__).resolve().parent
# Các thư mục giao diện và ảnh; đường dẫn lấy theo vị trí file để chạy ở đâu cũng được.
OUTPUT_DIR = PROJECT_DIR / "output"
STATIC_DIR = PROJECT_DIR / "static"
PAGE_PATH = PROJECT_DIR / "templates" / "index.html"
load_dotenv(PROJECT_DIR / ".env")

app = FastAPI(title="LUMIQ AI")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _safe_file(directory: Path, name: str) -> Path:
    """Chỉ cho phép đọc file có trong đúng thư mục ảnh được chỉ định."""
    path = (directory / Path(name).name).resolve()
    if path.parent != directory.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return path


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Trả giao diện LUMIQ AI và danh sách màu áo."""
    # URL thay đổi khi CSS/JS đổi, tránh trình duyệt dùng script cũ với HTML mới.
    static_version = max(
        (STATIC_DIR / "styles.css").stat().st_mtime_ns,
        (STATIC_DIR / "app.js").stat().st_mtime_ns,
    )
    page = PAGE_PATH.read_text(encoding="utf-8")
    options = "".join(f'<option value="{name}">{name}</option>' for name in COLORS)
    page = page.replace("{{COLOR_OPTIONS}}", options)
    page = page.replace("{{STATIC_VERSION}}", str(static_version))
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})


@app.get("/outputs/{name}")
def output_image(name: str):
    """Phục vụ ảnh sản phẩm đã tạo trong thư mục output."""
    return FileResponse(_safe_file(OUTPUT_DIR, name))


@app.post("/api/generate")
async def generate_design(
    shirt: UploadFile = File(...),
    pattern: UploadFile = File(...),
    garment_color: str = Form("Giữ nguyên"),
    center_x: float = Form(50),
    center_y: float = Form(45),
    print_width: float = Form(25),
):
    """Nhận ảnh và lựa chọn thiết kế, tạo một ảnh sản phẩm bằng AI."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Tên ngắn và ngẫu nhiên để các lượt tạo ảnh không ghi đè lên nhau.
    output_path = OUTPUT_DIR / f"ao-{uuid4().hex[:12]}.png"
    while output_path.exists():
        output_path = OUTPUT_DIR / f"ao-{uuid4().hex[:12]}.png"

    temp_paths: list[Path] = []
    try:
        # Luồng AI đọc ảnh qua đường dẫn, nên lưu tạm rồi xóa sau khi xử lý.
        for upload in (shirt, pattern):
            suffix = Path(upload.filename or ".png").suffix or ".png"
            content = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(content) > MAX_UPLOAD_BYTES:
                return JSONResponse({"error": "Mỗi ảnh chỉ được tối đa 10 MB."}, status_code=413)
            if not content:
                raise ValueError("Vui lòng chọn đủ ảnh áo và ảnh họa tiết.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(content)
                temp_paths.append(Path(handle.name))
        await run_in_threadpool(
            generate_ai_design,
            temp_paths[0], temp_paths[1], output_path, center_x, center_y, print_width,
            garment_color,
        )
    except CloudflareAPIError as exc:
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except (UnidentifiedImageError, Image.DecompressionBombError):
        return JSONResponse({"error": "Ảnh không hợp lệ hoặc có kích thước quá lớn."}, status_code=400)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception:
        logger.exception("Image generation failed unexpectedly")
        return JSONResponse({"error": "Không thể xử lý ảnh. Kiểm tra cấu hình và nhật ký máy chủ."}, status_code=500)
    finally:
        for path in temp_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Không thể xóa file tạm %s", path)
        await shirt.close()
        await pattern.close()

    return {
        "image_url": f"/outputs/{output_path.name}",
        "status": "Hoàn tất",
    }


if __name__ == "__main__":
    if os.getenv("SUNEA_OPEN_BROWSER", "1") == "1":
        threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:7860")).start()
    uvicorn.run(app, host="127.0.0.1", port=7860)
