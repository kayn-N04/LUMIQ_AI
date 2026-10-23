"""Local AI background removal; keep existing meaningful transparency."""
import os
import threading
from pathlib import Path
from services.image_layout import load_image

_lock = threading.Lock()
_session = None


def remove_artwork_background(source, output):
    image = load_image(source)
    alpha = image.getchannel("A")
    if alpha.getbbox() is None:
        raise ValueError("Họa tiết hoàn toàn trong suốt.")
    if alpha.getextrema()[0] >= 250:
        # Bound inference memory; a single cached model serves concurrent requests safely.
        image.thumbnail((2048, 2048))
        global _session
        with _lock:
            try:
                os.environ.setdefault("U2NET_HOME", str(Path(__file__).resolve().parents[1] / ".models"))
                from rembg import new_session, remove
                if _session is None:
                    _session = new_session("u2netp", providers=["CPUExecutionProvider"])
                image = remove(image, session=_session).convert("RGBA")
            except Exception as exc:
                raise RuntimeError("Không thể tách nền. Kiểm tra cài đặt rembg và model u2netp (lần đầu cần Internet).") from exc
    bounds = image.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if bounds is None:
        raise ValueError("Không tìm thấy họa tiết sau khi tách nền. Hãy dùng PNG đã tách nền.")
    image.save(output, "PNG")  # Preserve canvas geometry used by the placement preview.
    return Path(output)
