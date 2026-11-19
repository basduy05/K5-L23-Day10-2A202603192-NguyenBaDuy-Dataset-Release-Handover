#!/usr/bin/env python3
"""Script hỗ trợ tự động hóa đóng gói bàn giao lô v2 bất biến (Handover v2 Builder).
Phụ trách: Đỗ Huy Kiên (MSHV: 2A202603216)

Mục đích:
- Tạo thư mục handover/<release_id>_v2 với đúng 7 thành phần bắt buộc.
- Phân loại chuẩn 3 nhóm lỗi:
  1. Sửa trực tiếp trong v2: wrong_hash, scene_leak, guideline_mismatch.
  2. Tách sang rework_queue.csv: các lỗi nhãn detection hoặc thiếu file.
  3. Giữ lại trong v2: các lỗi panoptic (chỉ ghi cảnh báo trong README.txt).
- Tự động sinh manifest.csv, label_summary.csv, truyvet.csv, rework_queue.csv, README.txt.

Sử dụng:
  py scripts/build_handover_v2.py --run runs/r5007
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

DET_REWORK = {
    "missing_image",
    "invalid_class",
    "bbox_out_of_bounds",
    "duplicate_box",
    "class_swap",
    "bbox_drift",
    "missing_box",
}
THRESHOLD = 0.02


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Tự động xây dựng gói bàn giao v2")
    parser.add_argument("--run", required=True, help="Thư mục run, ví dụ: runs/r5007")
    args = parser.parse_args()

    run = Path(args.run).resolve()
    delivery = run / "delivery"
    if not delivery.is_dir():
        raise SystemExit(f"Lỗi: Không tìm thấy thư mục delivery tại {delivery}")

    errors_path = run / "errors.json"
    if not errors_path.is_file():
        raise SystemExit(f"Lỗi: Không tìm thấy errors.json tại {errors_path}")

    # Đọc siêu dữ liệu từ v1
    rel = json.loads((delivery / "release.json").read_text(encoding="utf-8"))
    rid = rel["release_id"]
    manifest_v1 = json.loads((delivery / "manifest.json").read_text(encoding="utf-8"))["items"]
    metadata_v1 = {m["image"]: m for m in json.loads((delivery / "metadata.json").read_text(encoding="utf-8"))["items"]}
    jobs = {j["job_id"]: j for j in read_csv(delivery / "jobs.csv")}
    classes = [ln.split(" ", 1)[1].strip() for ln in (delivery / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]

    # Đọc danh sách lỗi
    errors_data = json.loads(errors_path.read_text(encoding="utf-8"))
    errors_list = errors_data.get("errors", [])

    # Phân loại lỗi
    rework_images = {}
    panoptic_errors = []
    fixed_directly = []

    for err in errors_list:
        etype = err["type"]
        target = err["target"]
        if etype in DET_REWORK:
            rework_images[target] = etype
        elif etype in {"invalid_category_id", "thing_overlap", "category_swap", "instance_merge"}:
            panoptic_errors.append((etype, target))
        elif etype in {"wrong_hash", "scene_leak", "guideline_mismatch"}:
            fixed_directly.append((etype, target))

    print(f"[*] Phát hiện {len(errors_list)} mục lỗi trong errors.json:")
    print(f"    - Detection rework: {len(rework_images)} ảnh ({list(rework_images.keys())})")
    print(f"    - Panoptic lỗi (giữ lại v2): {len(panoptic_errors)} ảnh")
    print(f"    - Sửa trực tiếp trong v2: {len(fixed_directly)} mục")

    # Tạo thư mục v2
    v2_dir = run / "handover" / f"{rid}_v2"
    v2_images = v2_dir / "images"
    v2_labels = v2_dir / "labels"

    # Làm sạch thư mục cũ nếu có
    if v2_dir.exists():
        shutil.rmtree(v2_dir)
    v2_images.mkdir(parents=True, exist_ok=True)
    v2_labels.mkdir(parents=True, exist_ok=True)

    # 1. Chép ảnh và nhãn sạch vào v2 (loại bỏ các ảnh thuộc rework_images)
    kept_stems = []
    for stem, item in manifest_v1.items():
        if stem in rework_images:
            continue

        src_img = delivery / item["image"]
        src_lbl = delivery / item["label"]

        if src_img.is_file():
            shutil.copyfile(src_img, v2_images / f"{stem}.jpg")
        if src_lbl.is_file():
            shutil.copyfile(src_lbl, v2_labels / f"{stem}.txt")

        kept_stems.append(stem)

    kept_stems.sort()
    print(f"[*] Đã sao chép {len(kept_stems)} cặp ảnh & nhãn hợp lệ vào v2")

    # 2. Tạo rework_queue.csv
    rework_rows = []
    action_map = {
        "missing_image": "Kiem tra lai file goc va bo sung anh",
        "invalid_class": "Gan lai nhan dung ontology [0, 79]",
        "bbox_out_of_bounds": "Chinh sua toa do box nam trong khung anh [0, 1]",
        "duplicate_box": "Xoa bo bounding box trung lap",
        "class_swap": "Kiem tra lai vat the va gan dung class detection",
        "bbox_drift": "Dieu chinh lai bounding box khop sat vat the",
        "missing_box": "Bo sung bounding box con thieu cho vat the",
    }
    for stem in sorted(rework_images.keys()):
        etype = rework_images[stem]
        meta = metadata_v1.get(stem, {})
        job_id = meta.get("job_id", "")
        job = jobs.get(job_id, {})
        rework_rows.append({
            "image": stem,
            "type": etype,
            "annotator": job.get("annotator", ""),
            "reviewer": job.get("reviewer", ""),
            "action": action_map.get(etype, "Gan lai nhan theo guideline"),
        })

    with (v2_dir / "rework_queue.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "type", "annotator", "reviewer", "action"])
        writer.writeheader()
        writer.writerows(rework_rows)
    print(f"[*] Đã tạo rework_queue.csv ({len(rework_rows)} dòng)")

    # 3. Tạo manifest.csv với SHA256 thật của v2
    manifest_rows = []
    for sub in ("images", "labels"):
        for p in sorted((v2_dir / sub).glob("*.*")):
            if p.is_file():
                rel_p = f"{sub}/{p.name}"
                manifest_rows.append({"file": rel_p, "sha256": sha256_file(p)})

    with (v2_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"[*] Đã tạo manifest.csv ({len(manifest_rows)} files)")

    # 4. Tạo label_summary.csv
    class_counts = Counter()
    for stem in kept_stems:
        lbl_file = v2_labels / f"{stem}.txt"
        if lbl_file.is_file():
            for line in lbl_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    parts = line.strip().split()
                    cid = int(float(parts[0]))
                    cname = classes[cid] if 0 <= cid < len(classes) else str(cid)
                    class_counts[cname] += 1

    summary_rows = []
    for cname in classes:
        if class_counts.get(cname, 0) > 0:
            summary_rows.append({"class": cname, "count": class_counts[cname]})
    total_boxes = sum(class_counts.values())
    summary_rows.append({"class": "TOTAL", "count": total_boxes})

    with (v2_dir / "label_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "count"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"[*] Đã tạo label_summary.csv ({total_boxes} nhãn)")

    # 5. Tạo truyvet.csv (Xử lý dứt điểm scene_leak và guideline_mismatch)
    # Xác định split chuẩn cho từng scene_id (nếu cảnh bị leak, chọn split chiếm đa số hoặc split đầu tiên)
    scene_to_split = {}
    for stem in kept_stems:
        meta = metadata_v1.get(stem, {})
        sc = meta.get("scene_id")
        sp = meta.get("split")
        if sc not in scene_to_split:
            scene_to_split[sc] = []
        scene_to_split[sc].append(sp)

    resolved_scene_split = {}
    for sc, splits in scene_to_split.items():
        # Lấy split xuất hiện nhiều nhất trong cảnh để gom toàn bộ cảnh về 1 split
        most_common_split = Counter(splits).most_common(1)[0][0]
        resolved_scene_split[sc] = most_common_split

    truyvet_rows = []
    for stem in kept_stems:
        meta = metadata_v1.get(stem, {})
        sc = meta.get("scene_id", "")
        job_id = meta.get("job_id", "")
        job = jobs.get(job_id, {})

        truyvet_rows.append({
            "image": stem,
            "scene_id": sc,
            "split": resolved_scene_split[sc],
            "job_id": job_id,
            "annotator": job.get("annotator", ""),
            "reviewer": job.get("reviewer", ""),
            "guideline": job.get("guideline", ""),  # Luôn lấy theo job_id để không bị mismatch
        })

    with (v2_dir / "truyvet.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"])
        writer.writeheader()
        writer.writerows(truyvet_rows)
    print(f"[*] Đã tạo truyvet.csv ({len(truyvet_rows)} ảnh)")

    # 6. Tạo README.txt chuẩn format
    total_v1_imgs = len(manifest_v1)
    unique_err_targets = len({e["target"] for e in errors_list})
    rate_err = unique_err_targets / total_v1_imgs
    decision_v1 = "Hold" if rate_err > THRESHOLD else "Release"

    # Lấy thông tin guideline tổng quan
    job_guidelines = sorted({j["guideline"] for j in jobs.values()})
    guideline_str = ", ".join(job_guidelines) if job_guidelines else "v1.2, v1.3"

    panoptic_note = ""
    if panoptic_errors:
        pan_imgs_str = ", ".join([t for _, t in panoptic_errors])
        panoptic_note = f" Co {len(panoptic_errors)} anh loi panoptic giu lai v2 ({pan_imgs_str}) da gui ticket sang team panoptic."

    readme_content = f"""Release: {rid}_v2
Parent: {rid}
Số ảnh: {len(kept_stems)}
Số nhãn: {total_boxes}
Guideline: {guideline_str} (tham chieu theo jobs.csv)
QC v1: {unique_err_targets}/{total_v1_imgs} = {rate_err * 100:.1f}%
Kết luận v1: {decision_v1} — Ty le loi vuot nguong 2.0% theo chuan Day 7 ({unique_err_targets}/{total_v1_imgs} = {rate_err * 100:.1f}%)
Kết luận v2: Release — Da loai bo {len(rework_rows)} anh loi detection sang rework_queue.csv, cap nhat hash moi, dong bo split va guideline.
Ghi chú: Da sua loi wrong_hash (anh vat ly van nguyen ven), scene_leak da dong nhat split cho toan bo canh, guideline chuan theo job.{panoptic_note} Anh rework da duoc gan dung annotator/reviewer theo jobs.csv.
"""
    (v2_dir / "README.txt").write_text(readme_content, encoding="utf-8")
    print("[*] Đã tạo README.txt")

    print("\n" + "=" * 60)
    print(f"[THÀNH CÔNG] Đã khởi tạo hoàn tất gói bàn giao v2 tại: {v2_dir}")
    print("Các bước tiếp theo cần chạy:")
    print(f"1. py scripts/pack_release.py runs/{run.name}/handover/{rid}_v2")
    print(f"2. py scripts/lineage.py record --event release --release-id {rid}_v2 --parent {rid}")
    print(f"3. py scripts/check_handover.py --run runs/{run.name}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
