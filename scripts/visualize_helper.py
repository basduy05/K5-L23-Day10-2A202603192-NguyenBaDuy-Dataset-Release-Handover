#!/usr/bin/env python3
"""Công cụ xem ảnh trực quan hỗ trợ thẩm định (Human Review) cho bài Lab Day 10.

Sử dụng:
  python scripts/visualize_helper.py --run runs/r5007 --image 000000012062
  python scripts/visualize_helper.py --run runs/r5007 --image 000000015497 --show
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def get_class_names(classes_path: Path) -> list[str]:
    if not classes_path.is_file():
        return []
    lines = classes_path.read_text(encoding="utf-8").splitlines()
    names = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        names.append(parts[1].strip() if len(parts) > 1 else parts[0].strip())
    return names

def parse_yolo_boxes(label_path: Path, img_w: int, img_h: int, class_names: list[str]) -> list[dict]:
    if not label_path.is_file():
        return []
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        c_id = int(float(parts[0]))
        x, y, w, h = [float(val) for val in parts[1:5]]
        x1 = (x - w / 2) * img_w
        y1 = (y - h / 2) * img_h
        x2 = (x + w / 2) * img_w
        y2 = (y + h / 2) * img_h
        c_name = class_names[c_id] if 0 <= c_id < len(class_names) else f"class_{c_id}"
        boxes.append({
            "class_id": c_id,
            "class_name": c_name,
            "box": [x1, y1, x2, y2],
            "norm": [x, y, w, h]
        })
    return boxes

def get_panoptic_info(panoptic_path: Path, image_stem: str) -> tuple[dict, list[dict]]:
    if not panoptic_path.is_file():
        return {}, []
    data = json.loads(panoptic_path.read_text(encoding="utf-8"))
    cats = {c["id"]: c for c in data.get("categories", [])}
    
    target_id = None
    try:
        target_id = int(image_stem)
    except ValueError:
        pass

    target_ann = None
    for ann in data.get("annotations", []):
        file_name = Path(ann.get("file_name", "")).stem
        ann_id = ann.get("image_id")
        if file_name == image_stem or (target_id is not None and ann_id == target_id):
            target_ann = ann
            break

    if not target_ann:
        return {}, []

    segments = []
    for seg in target_ann.get("segments_info", []):
        cat_id = seg.get("category_id")
        cat = cats.get(cat_id, {})
        segments.append({
            "id": seg.get("id"),
            "category_id": cat_id,
            "category_name": cat.get("name", f"cat_{cat_id}"),
            "isthing": cat.get("isthing", False),
            "bbox": seg.get("bbox", []),
            "area": seg.get("area", 0)
        })
    return target_ann, segments

def visualize_image(run_dir: Path, image_name: str, show: bool = False, out_dir: Path | None = None) -> Path | None:
    stem = Path(image_name).stem
    delivery_dir = run_dir / "delivery" if (run_dir / "delivery").is_dir() else run_dir
    
    # 1. Tìm file ảnh
    img_path = delivery_dir / "images" / f"{stem}.jpg"
    if not img_path.is_file():
        # Fallback thử đuôi png hoặc kiểm tra ở root delivery
        img_path = delivery_dir / "images" / f"{stem}.png"
        if not img_path.is_file():
            img_path = Path("delivery/images") / f"{stem}.jpg"
            if not img_path.is_file():
                print(f"[ERROR] Không tìm thấy ảnh: {image_name} tại {delivery_dir / 'images'}")
                return None

    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    class_names = get_class_names(delivery_dir / "classes.txt")
    det_boxes = parse_yolo_boxes(delivery_dir / "labels" / f"{stem}.txt", w, h, class_names)
    _, pan_segments = get_panoptic_info(delivery_dir / "panoptic.json", stem)

    # Lớp vẽ đè
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    print(f"\n=======================================================")
    print(f" THẨM ĐỊNH ẢNH: {stem}.jpg ({w}x{h})")
    print(f"=======================================================")
    
    print("\n--- NHÃN DETECTION (YOLO) ---")
    if not det_boxes:
        print("  (Không có box detection nào)")
    for idx, b in enumerate(det_boxes, 1):
        x1, y1, x2, y2 = b["box"]
        print(f"  [{idx}] Class: '{b['class_name']}' (ID={b['class_id']}) - Box: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")
        # Vẽ viền xanh lá (Detection)
        draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0, 255), width=3)
        draw.rectangle([x1, y1 - 14, x1 + len(b['class_name']) * 8 + 35, y1], fill=(0, 180, 0, 220))
        draw.text((x1 + 3, y1 - 13), f"DET: {b['class_name']}", fill=(255, 255, 255, 255), font=font)

    print("\n--- PHÂN ĐOẠN PANOPTIC (Things) ---")
    thing_segments = [s for s in pan_segments if s["isthing"]]
    if not thing_segments:
        print("  (Không có segment thing nào)")
    for idx, s in enumerate(thing_segments, 1):
        bx, by, bw, bh = s["bbox"]
        x1, y1, x2, y2 = bx, by, bx + bw, by + bh
        print(f"  [{idx}] Category: '{s['category_name']}' (ID={s['category_id']}) - Area: {s['area']} - Box: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")
        # Vẽ viền đỏ cam/xanh dương (Panoptic)
        draw.rectangle([x1, y1, x2, y2], outline=(255, 80, 0, 240), width=2)
        draw.rectangle([x1, y2, x1 + len(s['category_name']) * 8 + 35, y2 + 14], fill=(255, 80, 0, 200))
        draw.text((x1 + 3, y2 + 1), f"PAN: {s['category_name']}", fill=(255, 255, 255, 255), font=font)

    # Ghép ảnh
    final_img = Image.alpha_composite(img, overlay).convert("RGB")

    # Lưu kết quả
    if out_dir is None:
        out_dir = run_dir / "visualizations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}_vis.jpg"
    final_img.save(out_path, quality=92)
    print(f"\n=> Đã lưu ảnh trực quan tại: {out_path}")
    print("Ghi chú màu: [MÀU XANH LÁ] = Detection (YOLO) | [MÀU ĐỎ CAM] = Panoptic (Thing Segment)")
    print("=======================================================\n")

    if show:
        try:
            final_img.show()
        except Exception as e:
            print(f"[NOTE] Không thể mở cửa sổ xem ảnh: {e}")

    return out_path

def main() -> int:
    parser = argparse.ArgumentParser(description="Xem ảnh trực quan kèm BBox Detection và Panoptic Segments")
    parser.add_argument("--run", default="runs/r5007", help="Thư mục run (chứa delivery/)")
    parser.add_argument("--image", required=True, help="Tên hoặc mã ảnh cần xem (ví dụ: 000000012062 hoặc img_0002)")
    parser.add_argument("--show", action="store_true", help="Bật cửa sổ hiển thị ảnh (nếu môi trường hỗ trợ)")
    parser.add_argument("--out-dir", help="Thư mục lưu ảnh đã vẽ")
    args = parser.parse_args()

    run_dir = Path(args.run)
    out_dir = Path(args.out_dir) if args.out_dir else None
    visualize_image(run_dir, args.image, show=args.show, out_dir=out_dir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
