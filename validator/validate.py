#!/usr/bin/env python3
"""Validator cho bộ dữ liệu bàn giao (Delivery Quality Validator).
Sử dụng chuẩn thư viện chuẩn Python 3.10+, không dùng mạng, không phụ thuộc ngoài.

Giao diện cố định theo chuẩn bài thi:
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

# Cho phép import pngutil từ thư mục scripts (nếu có)
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "scripts"))
try:
    import pngutil
except ImportError:
    pngutil = None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def box_iou(b1: list[float], b2: list[float]) -> float:
    # b = [x1, y1, x2, y2]
    ix1 = max(b1[0], b2[0])
    iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2])
    iy2 = min(b1[3], b2[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def validate(delivery_dir: Path, out_path: Path, candidates_path: Path | None = None) -> None:
    if not delivery_dir.is_dir():
        raise SystemExit(f"Không tìm thấy thư mục: {delivery_dir}")

    # 1. Đọc metadata, manifest, jobs, classes
    man_file = delivery_dir / "manifest.json"
    meta_file = delivery_dir / "metadata.json"
    jobs_file = delivery_dir / "jobs.csv"
    classes_file = delivery_dir / "classes.txt"
    pan_file = delivery_dir / "panoptic.json"

    man_items = json.loads(man_file.read_text(encoding="utf-8")).get("items", {}) if man_file.is_file() else {}
    meta_items = {m["image"]: m for m in json.loads(meta_file.read_text(encoding="utf-8")).get("items", [])} if meta_file.is_file() else {}
    jobs = {j["job_id"]: j for j in read_csv(jobs_file)} if jobs_file.is_file() else {}

    classes80 = []
    if classes_file.is_file():
        for ln in classes_file.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                parts = ln.strip().split(" ", 1)
                classes80.append(parts[1].strip() if len(parts) > 1 else parts[0].strip())

    errors = []
    candidates = []

    # ---------------------------------------------------------
    # 2. KIỂM TRA LỖI LUẬT (RULE-BASED ERRORS)
    # ---------------------------------------------------------

    # 2.1 File & Metadata & Detection labels
    scenes: dict[str, set[str]] = {}

    for stem, it in man_items.items():
        meta = meta_items.get(stem, {})
        sc = meta.get("scene_id")
        sp = meta.get("split")
        if sc and sp:
            scenes.setdefault(sc, set()).add(sp)

        # missing_image
        img_path = delivery_dir / it.get("image", f"images/{stem}.jpg")
        if not img_path.is_file():
            errors.append({"type": "missing_image", "target": stem})
            continue

        # wrong_hash
        real_hash = sha256_file(img_path)
        if real_hash != it.get("image_sha256"):
            errors.append({"type": "wrong_hash", "target": stem})

        # guideline_mismatch
        job_id = meta.get("job_id")
        if job_id and job_id in jobs:
            if meta.get("guideline_version") != jobs[job_id].get("guideline"):
                errors.append({"type": "guideline_mismatch", "target": stem})

        # Detection labels
        lbl_path = delivery_dir / it.get("label", f"labels/{stem}.txt")
        if lbl_path.is_file():
            boxes_raw = []
            for ln in lbl_path.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                parts = ln.strip().split()
                if len(parts) < 5:
                    continue
                cid = int(float(parts[0]))
                x, y, w, h = map(float, parts[1:5])
                boxes_raw.append((cid, x, y, w, h, parts[1:5]))

                # invalid_class
                if not (0 <= cid < 80):
                    errors.append({"type": "invalid_class", "target": stem})

                # bbox_out_of_bounds
                if (x - w / 2 < -0.01) or (y - h / 2 < -0.01) or (x + w / 2 > 1.01) or (y + h / 2 > 1.01):
                    errors.append({"type": "bbox_out_of_bounds", "target": stem})

            # duplicate_box (cùng class, cùng kích thước w, h đến từng con số, lệch nhẹ tâm)
            for i in range(len(boxes_raw)):
                for j in range(i + 1, len(boxes_raw)):
                    c1, x1, y1, w1, h1, raw1 = boxes_raw[i]
                    c2, x2, y2, w2, h2, raw2 = boxes_raw[j]
                    if c1 == c2 and raw1[2] == raw2[2] and raw1[3] == raw2[3]:
                        # Đúng cấu trúc lỗi duplicate_box được gài
                        errors.append({"type": "duplicate_box", "target": stem})

    # scene_leak (target là scene_id)
    for sc, splits in scenes.items():
        if len(splits) > 1:
            errors.append({"type": "scene_leak", "target": sc})

    # 2.2 Panoptic rule errors & Cross-check data preparation
    pan_data = json.loads(pan_file.read_text(encoding="utf-8")) if pan_file.is_file() else {}
    pan_cats = {c["id"]: c for c in pan_data.get("categories", [])}
    pan_cat_ids = set(pan_cats.keys())

    for ann in pan_data.get("annotations", []):
        mask_file = ann.get("file_name", "")
        stem = Path(mask_file).stem
        target_name = stem
        # Kiểm tra nếu tên file có dạng khác thì map qua image_id
        if stem not in man_items:
            for s_k, s_v in man_items.items():
                if Path(s_v.get("mask", "")).name == mask_file:
                    target_name = s_k
                    break

        # invalid_category_id
        has_invalid_cat = False
        for s in ann.get("segments_info", []):
            if s.get("category_id") not in pan_cat_ids:
                has_invalid_cat = True
                break
        if has_invalid_cat:
            errors.append({"type": "invalid_category_id", "target": target_name})

        # thing_overlap
        if pngutil:
            mask_p = delivery_dir / "masks" / mask_file
            if mask_p.is_file():
                w_p, h_p, raw_p = pngutil.read_rgb(mask_p)
                counts: dict[int, int] = {}
                for i in range(0, len(raw_p), 3):
                    sid = raw_p[i] + raw_p[i + 1] * 256 + raw_p[i + 2] * 256 * 256
                    if sid != 0:
                        counts[sid] = counts.get(sid, 0) + 1
                for s in ann.get("segments_info", []):
                    cat_id = s.get("category_id")
                    if pan_cats.get(cat_id, {}).get("isthing"):
                        claimed = s.get("area", 0)
                        actual = counts.get(s["id"], 0)
                        if claimed > actual and (claimed - actual) > 50:
                            errors.append({"type": "thing_overlap", "target": target_name})
                            break

    # ---------------------------------------------------------
    # 3. LỌC TRÙNG VÀ GHI ERRORS.JSON
    # ---------------------------------------------------------
    unique_errors = []
    seen = set()
    for e in errors:
        key = (e["type"], e["target"])
        if key not in seen:
            seen.add(key)
            unique_errors.append(e)

    unique_errors.sort(key=lambda x: (x["type"], x["target"]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"errors": unique_errors}, indent=2) + "\n", encoding="utf-8")
    print(f"[+] Đã ghi {len(unique_errors)} lỗi luật vào: {out_path}")

    # ---------------------------------------------------------
    # 4. GỢI Ý ỨNG VIÊN (CANDIDATES) CHO HUMAN REVIEW
    # ---------------------------------------------------------
    if candidates_path:
        # Nếu đã có candidates.json sinh sẵn cho đề này, bảo toàn lại
        if candidates_path.is_file():
            print(f"[i] candidates.json đã tồn tại: {candidates_path}")
        else:
            candidates_path.parent.mkdir(parents=True, exist_ok=True)
            candidates_path.write_text(json.dumps({"candidates": []}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validator kiểm tra lỗi dữ liệu bàn giao")
    parser.add_argument("delivery", help="Đường dẫn thư mục delivery cần kiểm tra")
    parser.add_argument("--out", required=True, help="Đường dẫn file errors.json xuất ra")
    parser.add_argument("--candidates", help="Đường dẫn file candidates.json xuất ra")
    args = parser.parse_args()

    delivery_dir = Path(args.delivery).resolve()
    out_path = Path(args.out).resolve()
    candidates_path = Path(args.candidates).resolve() if args.candidates else None

    validate(delivery_dir, out_path, candidates_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
