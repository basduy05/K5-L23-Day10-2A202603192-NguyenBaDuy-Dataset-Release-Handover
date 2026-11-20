#!/usr/bin/env python3
"""Validator kiểm tra chất lượng dữ liệu của nhóm.

Sử dụng hoàn toàn thư viện chuẩn của Python 3.10+ kết hợp pngutil.py.
Không đọc _private/, không đọc data_source/, không dùng mạng.

Giao diện dòng lệnh chuẩn:
    python validator/validate.py <thư_mục_delivery> --out <errors.json> [--candidates <candidates.json>]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

# Thêm đường dẫn scripts để import pngutil
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import pngutil  # noqa: E402


def sha256_file(path: Path) -> str:
    """Tính mã băm sha256 của file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def bbox_iou(box1: list[float], box2: list[float]) -> float:
    """Tính IoU giữa 2 bounding box dạng [x, y, w, h] (pixel)."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    ax1, ay1, ax2, ay2 = x1, y1, x1 + w1, y1 + h1
    bx1, by1, bx2, by2 = x2, y2, x2 + w2, y2 + h2

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter_area = inter_w * inter_h

    union_area = (w1 * h1) + (w2 * h2) - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


class DeliveryValidator:
    def __init__(self, delivery_dir: Path):
        self.delivery_dir = delivery_dir
        self.manifest_file = delivery_dir / "manifest.json"
        self.metadata_file = delivery_dir / "metadata.json"
        self.jobs_file = delivery_dir / "jobs.csv"
        self.classes_file = delivery_dir / "classes.txt"
        self.panoptic_file = delivery_dir / "panoptic.json"

        # Tải các metadata
        self.manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))["items"]
        self.metadata = {m["image"]: m for m in json.loads(self.metadata_file.read_text(encoding="utf-8"))["items"]}
        
        with self.jobs_file.open(encoding="utf-8", newline="") as f:
            self.jobs = {row["job_id"]: row for row in csv.DictReader(f)}

        self.class_names = [line.split(" ", 1)[1].strip() for line in self.classes_file.read_text(encoding="utf-8").splitlines() if line.strip()]

        self.panoptic_doc = json.loads(self.panoptic_file.read_text(encoding="utf-8"))
        self.categories = {c["id"]: c for c in self.panoptic_doc["categories"]}
        self.things_cat_ids = {c["id"] for c in self.panoptic_doc["categories"] if c.get("isthing")}
        
        self.pan_images = {im["id"]: im for im in self.panoptic_doc["images"]}
        self.pan_annotations = {a["image_id"]: a for a in self.panoptic_doc["annotations"]}

    def validate_rules(self) -> list[dict]:
        """Bắt 9 loại lỗi luật (Rule-detectable faults)."""
        errors = []
        scenes: dict[str, set[str]] = {}

        # 1. Kiểm tra từng ảnh trong manifest
        for name, item in self.manifest.items():
            meta = self.metadata.get(name, {})
            scene_id = meta.get("scene_id")
            split = meta.get("split")
            if scene_id and split:
                scenes.setdefault(scene_id, set()).add(split)

            img_path = self.delivery_dir / item["image"]
            label_path = self.delivery_dir / item["label"]
            mask_path = self.delivery_dir / item["mask"]

            # Luật 1: missing_image
            if not img_path.is_file():
                errors.append({"type": "missing_image", "target": name})
                continue

            # Luật 2: wrong_hash
            real_img_hash = sha256_file(img_path)
            if real_img_hash != item["image_sha256"]:
                errors.append({"type": "wrong_hash", "target": name})

            # Luật 7: guideline_mismatch (so sánh với job trong jobs.csv)
            job_id = meta.get("job_id")
            if job_id in self.jobs:
                expected_guideline = self.jobs[job_id]["guideline"]
                if meta.get("guideline_version") != expected_guideline:
                    errors.append({"type": "guideline_mismatch", "target": name})

            # Kiểm tra nhãn Detection (labels)
            if label_path.is_file():
                label_text = label_path.read_text(encoding="utf-8")
                boxes = []
                for line in label_text.splitlines():
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    boxes.append(parts)

                # Luật 3: invalid_class & Luật 4: bbox_out_of_bounds
                has_invalid_class = False
                has_oob = False
                for b in boxes:
                    try:
                        c = int(float(b[0]))
                        x, y, w, h = float(b[1]), float(b[2]), float(b[3]), float(b[4])
                    except ValueError:
                        has_invalid_class = True
                        break

                    if not (0 <= c < 80):
                        has_invalid_class = True
                        break

                    # Out of bounds check: tràn ngoài mép [0, 1]
                    if x - w / 2 < -0.01 or y - h / 2 < -0.01 or x + w / 2 > 1.01 or y + h / 2 > 1.01:
                        has_oob = True
                        break

                if has_invalid_class:
                    errors.append({"type": "invalid_class", "target": name})
                if has_oob:
                    errors.append({"type": "bbox_out_of_bounds", "target": name})

                # Luật 5: duplicate_box
                # Cùng class, cùng kích thước, chỉ lệch 1-2 pixel
                is_duplicate = False
                n_boxes = len(boxes)
                for i in range(n_boxes):
                    if is_duplicate:
                        break
                    c1, x1, y1, w1, h1 = int(float(boxes[i][0])), float(boxes[i][1]), float(boxes[i][2]), float(boxes[i][3]), float(boxes[i][4])
                    for j in range(i + 1, n_boxes):
                        c2, x2, y2, w2, h2 = int(float(boxes[j][0])), float(boxes[j][1]), float(boxes[j][2]), float(boxes[j][3]), float(boxes[j][4])
                        if c1 == c2:
                            # Cùng kích thước (chênh lệch kích thước rất nhỏ <= 1e-4)
                            if abs(w1 - w2) < 1e-4 and abs(h1 - h2) < 1e-4:
                                # Tâm lệch rất nhỏ (khoảng cách tâm <= 0.01)
                                if abs(x1 - x2) < 0.01 and abs(y1 - y2) < 0.01:
                                    is_duplicate = True
                                    break
                if is_duplicate:
                    errors.append({"type": "duplicate_box", "target": name})

            # Kiểm tra Panoptic mask & annotations
            # Tìm image_id tương ứng
            image_id = None
            for iid, im_info in self.pan_images.items():
                if Path(im_info["file_name"]).stem == name or im_info["file_name"] == f"{name}.jpg":
                    image_id = iid
                    break
            if image_id is None:
                # Tìm theo số nếu có
                for iid in self.pan_images:
                    if str(iid) == name or f"{iid:012d}" == name:
                        image_id = iid
                        break

            if image_id is not None and image_id in self.pan_annotations:
                ann = self.pan_annotations[image_id]
                segments = ann.get("segments_info", [])

                # Luật 8: invalid_category_id
                has_invalid_cat = any(s["category_id"] not in self.categories for s in segments)
                if has_invalid_cat:
                    errors.append({"type": "invalid_category_id", "target": name})

                # Luật 9: thing_overlap (area > số pixel thực tế trong mask PNG)
                if mask_path.is_file():
                    try:
                        width, height, raw_pixels = pngutil.read_rgb(mask_path)
                        # Đếm số pixel cho từng segment id
                        pixel_counts = {}
                        for i in range(0, len(raw_pixels), 3):
                            sid = pngutil.segment_id(raw_pixels, i)
                            if sid:
                                pixel_counts[sid] = pixel_counts.get(sid, 0) + 1

                        has_thing_overlap = False
                        for s in segments:
                            # Chỉ xét các thing segments có khai báo area
                            if s["category_id"] in self.things_cat_ids and not s.get("iscrowd"):
                                declared_area = s.get("area", 0)
                                actual_px = pixel_counts.get(s["id"], 0)
                                # Lỗi thing_overlap gài lấy mất 15-30% diện tích (ít nhất vài chục px)
                                if declared_area - actual_px >= 10:
                                    has_thing_overlap = True
                                    break
                        if has_thing_overlap:
                            errors.append({"type": "thing_overlap", "target": name})
                    except Exception as e:
                        # Không đọc được PNG hoặc lỗi định dạng
                        pass

        # Luật 6: scene_leak (target là scene_id)
        for sc_id, split_set in scenes.items():
            if len(split_set) > 1:
                errors.append({"type": "scene_leak", "target": sc_id})

        return errors

    def find_candidates(self) -> list[dict]:
        """Đối chiếu Detection ↔ Panoptic để tìm ứng viên lỗi ngữ nghĩa (Semantic candidates)."""
        candidates = []

        for name, item in self.manifest.items():
            img_path = self.delivery_dir / item["image"]
            label_path = self.delivery_dir / item["label"]
            mask_path = self.delivery_dir / item["mask"]

            if not img_path.is_file() or not label_path.is_file() or not mask_path.is_file():
                continue

            # Tìm panoptic image_id
            image_id = None
            im_w, im_h = 640, 480
            for iid, im_info in self.pan_images.items():
                if Path(im_info["file_name"]).stem == name or im_info["file_name"] == f"{name}.jpg":
                    image_id = iid
                    im_w, im_h = im_info["width"], im_info["height"]
                    break

            if image_id is None or image_id not in self.pan_annotations:
                continue

            ann = self.pan_annotations[image_id]
            segments = [s for s in ann.get("segments_info", []) if s["category_id"] in self.things_cat_ids and not s.get("iscrowd")]

            # Đọc boxes detection
            boxes = []
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        c = int(float(parts[0]))
                        if 0 <= c < len(self.class_names):
                            x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                            boxes.append({
                                "class_id": c,
                                "class_name": self.class_names[c],
                                "px_box": [(x - w / 2) * im_w, (y - h / 2) * im_h, w * im_w, h * im_h],
                                "norm_box": [x, y, w, h],
                                "area": w * h
                            })
                    except ValueError:
                        pass

            # 1. Tìm instance_merge: 1 segment bao phủ 2 box cùng class
            for s in segments:
                s_box = s["bbox"]
                s_name = self.categories[s["category_id"]]["name"]
                same_class_boxes = [b for b in boxes if b["class_name"] == s_name]
                enclosed = []
                for b in same_class_boxes:
                    bx, by, bw, bh = b["px_box"]
                    # Kiểm tra tâm box nằm trong segment bbox
                    cx, cy = bx + bw / 2, by + bh / 2
                    if s_box[0] <= cx <= s_box[0] + s_box[2] and s_box[1] <= cy <= s_box[1] + s_box[3]:
                        enclosed.append(b)
                if len(enclosed) >= 2 and s.get("area", 0) >= 500:
                    candidates.append({
                        "image": name,
                        "type": "instance_merge",
                        "suspect_class": s_name,
                        "note": f"segment panoptic {s_name} phu {len(enclosed)} box cung lop"
                    })

            # 2. Ghép từng box với segment
            matched_segments = set()
            for b in boxes:
                best_iou = 0.0
                best_seg = None
                for s in segments:
                    iou = bbox_iou(b["px_box"], s["bbox"])
                    if iou > best_iou:
                        best_iou = iou
                        best_seg = s

                if best_seg:
                    seg_name = self.categories[best_seg["category_id"]]["name"]
                    # Kiểm tra class_swap hoặc category_swap: trùng vị trí cao nhưng khác lớp
                    if best_iou > 0.4 and b["class_name"] != seg_name:
                        candidates.append({
                            "image": name,
                            "type": "class_swap",  # hoặc category_swap (cần xem ảnh quyết định)
                            "det_class": b["class_name"],
                            "pan_class": seg_name,
                            "iou": round(best_iou, 3),
                            "note": f"bat dong lop: detection ghi {b['class_name']}, panoptic ghi {seg_name} (IoU={best_iou:.2f})"
                        })
                    # Kiểm tra bbox_drift: cùng lớp nhưng IoU chỉ đạt mức thấp (0.15 - 0.45) với box lớn
                    elif b["class_name"] == seg_name and b["area"] >= 0.005:
                        if 0.15 <= best_iou < 0.50:
                            candidates.append({
                                "image": name,
                                "type": "bbox_drift",
                                "det_class": b["class_name"],
                                "iou": round(best_iou, 3),
                                "note": f"box {b['class_name']} bi lech khoi segment (IoU={best_iou:.2f})"
                            })
                    if best_iou > 0.3:
                        matched_segments.add(best_seg["id"])

            # 3. Tìm missing_box: segment thing lớn không có box nào ghép được
            for s in segments:
                if s["id"] not in matched_segments and s.get("area", 0) >= 1200:
                    s_name = self.categories[s["category_id"]]["name"]
                    # Kiểm tra xem có box nào cùng lớp không
                    has_box = any(b["class_name"] == s_name and bbox_iou(b["px_box"], s["bbox"]) > 0.1 for b in boxes)
                    if not has_box:
                        candidates.append({
                            "image": name,
                            "type": "missing_box",
                            "pan_class": s_name,
                            "area": s["area"],
                            "note": f"segment {s_name} dien tich lon ({s['area']} px) nhung thieu box detection"
                        })

        return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Validator kiểm định chất lượng bộ dữ liệu")
    parser.add_argument("delivery", help="Đường dẫn thư mục delivery cần kiểm tra")
    parser.add_argument("--out", required=True, help="Đường dẫn file errors.json xuất ra")
    parser.add_argument("--candidates", help="Đường dẫn file candidates.json xuất danh sách ứng viên (tùy chọn)")
    args = parser.parse_args()

    delivery_dir = Path(args.delivery).resolve()
    if not delivery_dir.is_dir():
        raise SystemExit(f"Lỗi: Thư mục {delivery_dir} không tồn tại!")

    validator = DeliveryValidator(delivery_dir)

    # 1. Phát hiện lỗi luật
    rule_errors = validator.validate_rules()
    print(f"Phát hiện {len(rule_errors)} lỗi luật.")

    # 2. Tìm ứng viên lỗi ngữ nghĩa (nếu yêu cầu)
    candidates = []
    if args.candidates:
        candidates = validator.find_candidates()
        cand_file = Path(args.candidates)
        cand_file.parent.mkdir(parents=True, exist_ok=True)
        cand_file.write_text(json.dumps({"candidates": candidates}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Đã xuất {len(candidates)} ứng viên vào {cand_file}")

    # Xuất file kết quả
    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({"errors": rule_errors}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Đã lưu danh sách lỗi vào {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
