"""Local AI background removal; keep existing meaningful transparency."""
import os
import hashlib
import io
from collections import OrderedDict
import logging
import threading
from pathlib import Path
from services.image_layout import load_image

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_session = None
_cache = OrderedDict()
_cache_bytes = 0
CACHE_LIMIT_BYTES = 32 * 1024 * 1024
CACHE_LIMIT_ITEMS = 8


def _remember(key, value):
    global _cache_bytes
    if len(value) > CACHE_LIMIT_BYTES:
        return
    previous = _cache.pop(key, None)
    if previous is not None:
        _cache_bytes -= len(previous)
    _cache[key] = value
    _cache_bytes += len(value)
    while len(_cache) > CACHE_LIMIT_ITEMS or _cache_bytes > CACHE_LIMIT_BYTES:
        _, evicted = _cache.popitem(last=False)
        _cache_bytes -= len(evicted)



def remove_artwork_background(source, output):
    # Hash file contents, not temporary upload names; never cache failed work.
    with open(source, "rb") as handle:
        key = hashlib.file_digest(handle, "sha256").digest()
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
    if cached is not None:
        Path(output).write_bytes(cached)
        return Path(output)
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
                logger.exception("Artwork background removal failed (model=u2netp, image_size=%s)", image.size)
                raise RuntimeError("Không thể tách nền họa tiết. Xem lỗi chi tiết trong terminal máy chủ (Artwork background removal failed).") from exc
    bounds = image.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if bounds is None:
        raise ValueError("Không tìm thấy họa tiết sau khi tách nền. Hãy dùng PNG đã tách nền.")
    buffer = io.BytesIO()
    image.save(buffer, "PNG", compress_level=1)
    encoded = buffer.getvalue()
    Path(output).write_bytes(encoded)
    with _lock:
        _remember(key, encoded)
    return Path(output)
