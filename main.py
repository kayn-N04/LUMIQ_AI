"""Chạy LUMIQ AI từ dòng lệnh, không cần mở giao diện web."""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from services.generation import generate_design
from services.prompt_builder import COLORS


PROJECT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    """Đọc hai đường dẫn ảnh và tên file kết quả tùy chọn."""
    parser = argparse.ArgumentParser(
        description="Tach nen hoa tiet va tao anh ao bang Cloudflare AI."
    )
    parser.add_argument("--shirt", required=True, help="Duong dan den anh ao goc")
    parser.add_argument("--pattern", required=True, help="Duong dan den anh hoa tiet")
    parser.add_argument("--output", help="Duong dan anh ket qua (PNG)")
    parser.add_argument("--x", type=float, default=50, help="Tam ngang theo phan tram")
    parser.add_argument("--y", type=float, default=45, help="Tam doc theo phan tram")
    parser.add_argument("--width", type=float, default=25, help="Chieu rong hoa tiet theo phan tram anh")
    parser.add_argument("--color", default="Giữ nguyên", choices=list(COLORS), help="Mau vai ao co san")
    return parser.parse_args()


def main() -> int:
    """Tạo ảnh áo bằng cùng luồng AI với giao diện web."""
    load_dotenv(PROJECT_DIR / ".env")
    args = parse_args()
    output_dir = PROJECT_DIR / "output"
    result_path = Path(args.output) if args.output else output_dir / f"ao-{uuid4().hex[:12]}.png"

    try:
        generate_design(args.shirt, args.pattern, result_path, args.x, args.y, args.width, args.color)
        print(f"Hoan thanh: {result_path}")
        return 0
    except Exception as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
