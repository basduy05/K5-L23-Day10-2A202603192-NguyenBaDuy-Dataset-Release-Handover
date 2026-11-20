#!/usr/bin/env python3
"""Script hỗ trợ visualize bounding box YOLO và mask Panoptic lên ảnh để phục vụ Human Review.

Chỉ dùng cho công cụ xem ảnh của nhóm (được phép dùng Pillow), không dùng trong validator.

Cách dùng:
    py scripts/visualize_helper.py --run runs/r5007 --image 000000000139
    py scripts/visualize_helper.py --run runs/r5007 --all-candidates
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pngutil  # noqa: E402


def visualize_image(delivery_dir: Path, image_name: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = delivery_dir / "images" / f"{image_name}.jpg"
    label_path = delivery_dir / "labels" / f"{image_name}.txt"
    mask_path = delivery_dir / "masks" / f"{image_name}.png"

    if not img_path.is_file():
        print(f"Không tìm thấy ảnh: {img_path}")
        return None

    img = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Đọc classes.txt
    classes_file = delivery_dir / "classes.txt"
    class_names = [line.split(" ", 1)[1].strip() for line in classes_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    # 1. Vẽ Mask Panoptic (bán trong suốt)
    if mask_path.is_file():
        pan_doc = json.loads((delivery_dir / "panoptic.json").read_text(encoding="utf-8"))
        categories = {c["id"]: c for c in pan_doc["categories"]}
        
        # Tìm annotation cho ảnh
        ann = None
        for a in pan_doc["annotations"]:
            if Path(a["file_name"]).stem == image_name:
                ann = a
                break

        if ann:
            for s in ann.get("segments_info", []):
                cat = categories.get(s["category_id"], {})
                cat_name = cat.get("name", "unknown")
                is_thing = cat.get("isthing", False)
                if is_thing:
                    # Vẽ bbox của segment panoptic bằng nét đứt màu đỏ
                    sb = s["bbox"]
                    draw.rectangle([sb[0], sb[1], sb[0] + sb[2], sb[1] + sb[3]], outline=(255, 0, 0, 255), width=2)
                    draw.text((sb[0] + 2, sb[1] + 2), f"Pan: {cat_name}", fill=(255, 0, 0, 255))

    # 2. Vẽ Bounding box YOLO Detection (màu xanh lá cây)
    if label_path.is_file():
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                try:
                    c, x, y, w, h = int(float(parts[0])), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    c_name = class_names[c] if 0 <= c < len(class_names) else str(c)
                    bx1 = (x - w / 2) * W
                    by1 = (y - h / 2) * H
                    bx2 = (x + w / 2) * W
                    by2 = (y + h / 2) * H
                    draw.rectangle([bx1, by1, bx2, by2], outline=(0, 255, 0, 255), width=3)
                    draw.text((bx1 + 2, by1 - 12 if by1 > 15 else by1 + 2), f"Det: {c_name}", fill=(0, 255, 0, 255))
                except ValueError:
                    pass

    out_path = out_dir / f"{image_name}_annotated.png"
    img.save(out_path)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize nhãn và mask lên ảnh")
    parser.add_argument("--run", required=True, help="Thư mục run (ví dụ: runs/r5007)")
    parser.add_argument("--image", help="Tên ảnh cần vẽ (không gồm đuôi .jpg)")
    parser.add_argument("--all-candidates", action="store_true", help="Vẽ tất cả ảnh trong candidates.json")
    args = parser.parse_args()

    run_dir = Path(args.run).resolve()
    delivery_dir = run_dir / "delivery"
    out_dir = run_dir / "visualize"

    if args.image:
        out = visualize_image(delivery_dir, args.image, out_dir)
        if out:
            print(f"Đã xuất ảnh: {out}")
    elif args.all_candidates:
        cand_file = run_dir / "candidates.json"
        if not cand_file.is_file():
            raise SystemExit(f"Không tìm thấy {cand_file}")
        data = json.loads(cand_file.read_text(encoding="utf-8"))
        cands = data.get("candidates", [])
        images = sorted({c["image"] for c in cands})
        print(f"Đang visualize {len(images)} ảnh ứng viên...")
        for img_name in images:
            visualize_image(delivery_dir, img_name, out_dir)
        print(f"Hoàn thành! Toàn bộ ảnh đã được lưu tại: {out_dir}")
    else:
        print("Vui lòng chỉ định --image <tên_ảnh> hoặc --all-candidates")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
