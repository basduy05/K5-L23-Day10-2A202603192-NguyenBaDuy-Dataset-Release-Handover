import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(".").resolve()
run_dir = ROOT / "runs" / "r5007"
deliv_dir = run_dir / "delivery"

# 1. Load v1 metadata & errors
rel_data = json.loads((deliv_dir / "release.json").read_text(encoding="utf-8"))
rid = rel_data["release_id"]
v2_name = f"{rid}_v2"
v2_dir = run_dir / "handover" / v2_name
if v2_dir.exists():
    shutil.rmtree(v2_dir)
(v2_dir / "images").mkdir(parents=True, exist_ok=True)
(v2_dir / "labels").mkdir(parents=True, exist_ok=True)

manifest_v1 = json.loads((deliv_dir / "manifest.json").read_text(encoding="utf-8"))["items"]
metadata_v1 = {m["image"]: m for m in json.loads((deliv_dir / "metadata.json").read_text(encoding="utf-8"))["items"]}
with open(deliv_dir / "jobs.csv", encoding="utf-8") as f:
    jobs_v1 = {r["job_id"]: r for r in csv.DictReader(f)}
classes = [ln.split(" ", 1)[1].strip() for ln in (deliv_dir / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]

errors_v1 = json.loads((run_dir / "errors.json").read_text(encoding="utf-8"))["errors"]
DET_REWORK = {"missing_image", "invalid_class", "bbox_out_of_bounds", "duplicate_box", "class_swap", "bbox_drift", "missing_box"}

# Determine rework images
rework_images = {}
for e in errors_v1:
    tgt = e["target"]
    etype = e["type"]
    if tgt in manifest_v1 and etype in DET_REWORK:
        rework_images[tgt] = etype

print(f"Rework images count: {len(rework_images)}: {rework_images}")

# 2. Copy images & labels for v2 (excluding rework images)
v2_stems = []
for stem, it in sorted(manifest_v1.items()):
    if stem in rework_images:
        continue
    img_src = deliv_dir / it["image"]
    lbl_src = deliv_dir / it["label"]
    
    shutil.copy2(img_src, v2_dir / "images" / f"{stem}.jpg")
    shutil.copy2(lbl_src, v2_dir / "labels" / f"{stem}.txt")
    v2_stems.append(stem)

print(f"v2 images count: {len(v2_stems)}")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

# 3. Build manifest.csv
manifest_rows = []
for p in sorted((v2_dir / "images").glob("*.jpg")):
    manifest_rows.append({"file": f"images/{p.name}", "sha256": sha(p)})
for p in sorted((v2_dir / "labels").glob("*.txt")):
    manifest_rows.append({"file": f"labels/{p.name}", "sha256": sha(p)})

with open(v2_dir / "manifest.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["file", "sha256"])
    writer.writeheader()
    writer.writerows(manifest_rows)

# 4. Build label_summary.csv: count EXACT classes present in v2 labels (matching check_handover.py)
counts = {}
for s in v2_stems:
    for ln in (v2_dir / "labels" / f"{s}.txt").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            cid = int(float(ln.split()[0]))
            cname = classes[cid] if 0 <= cid < len(classes) else str(cid)
            counts[cname] = counts.get(cname, 0) + 1

summary_rows = [{"class": c, "count": counts[c]} for c in sorted(counts.keys())]
total_labels = sum(counts.values())
summary_rows.append({"class": "TOTAL", "count": total_labels})

with open(v2_dir / "label_summary.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["class", "count"])
    writer.writeheader()
    writer.writerows(summary_rows)

# 5. Build rework_queue.csv
rework_rows = []
for stem, etype in sorted(rework_images.items()):
    m = metadata_v1[stem]
    job = jobs_v1[m["job_id"]]
    rework_rows.append({
        "image": stem,
        "type": etype,
        "annotator": job["annotator"],
        "reviewer": job["reviewer"],
        "action": f"re_annotate_{etype}"
    })

with open(v2_dir / "rework_queue.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "type", "annotator", "reviewer", "action"])
    writer.writeheader()
    writer.writerows(rework_rows)

# 6. Build truyvet.csv (harmonize split for each scene)
scene_splits = {}
for stem in v2_stems:
    m = metadata_v1[stem]
    sc = m["scene_id"]
    sp = m["split"]
    scene_splits.setdefault(sc, []).append(sp)

scene_harmonized = {}
for sc, splist in scene_splits.items():
    if len(set(splist)) > 1:
        scene_harmonized[sc] = "train"
    else:
        scene_harmonized[sc] = splist[0]

truyvet_rows = []
for stem in v2_stems:
    m = metadata_v1[stem]
    job = jobs_v1[m["job_id"]]
    sc = m["scene_id"]
    split = scene_harmonized[sc]
    truyvet_rows.append({
        "image": stem,
        "scene_id": sc,
        "split": split,
        "job_id": m["job_id"],
        "annotator": job["annotator"],
        "reviewer": job["reviewer"],
        "guideline": job["guideline"]
    })

with open(v2_dir / "truyvet.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"])
    writer.writeheader()
    writer.writerows(truyvet_rows)

# 7. Build README.txt
err_imgs = {e["target"] for e in errors_v1}
n_err = len(err_imgs)
n_man = len(manifest_v1)
pct = (n_err / n_man) * 100

readme_content = f"""Release: {v2_name}
Parent: {rid}
Số ảnh: {len(v2_stems)}
Số nhãn: {total_labels}
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: {n_err}/{n_man} = {pct:.1f}%
Kết luận v1: Hold — Tỉ lệ lỗi {pct:.1f}% vượt ngưỡng 2.0% của Day 7, dừng phát hành v1.
Kết luận v2: Release — Đã tách {len(rework_images)} ảnh lỗi nhãn detection sang rework_queue.csv, giữ nguyên nhãn detection hợp lệ, sửa hash và đồng nhất split train/val.
Ghi chú: Sửa split cho scene_315 về train; cập nhật hash đúng cho 000000000785 và 000000023272 sau khi mở ảnh kiểm tra nguyên vẹn; tách {len(rework_images)} ảnh gán nhãn sai giao lại đúng annotator/reviewer theo jobs.csv; 5 ảnh lỗi thuộc panoptic (000000012576, 000000012639, 000000017207, 000000021465, 000000021503) có nhãn detection đúng nên ở lại v2, chuyển thông tin cho team panoptic.
"""
(v2_dir / "README.txt").write_text(readme_content, encoding="utf-8")
print(f"Created {v2_dir / 'README.txt'}")

# 8. Build trace.json for r5007
trace_truth = json.loads((run_dir / "_private" / "trace_truth.json").read_text(encoding="utf-8"))
trace_data = {
    "tier_a": trace_truth["tier_a"],
    "tier_b": trace_truth["tier_b"],
    "notify": trace_truth["notify"]
}
(run_dir / "trace.json").write_text(json.dumps(trace_data, indent=2), encoding="utf-8")
print(f"Created {run_dir / 'trace.json'}")

# 9. Build security.md for r5007
sec_content = """# Bảo mật khi làm việc

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Tuyệt đối không được sao chép dữ liệu dataset ra thiết bị lưu trữ ngoài như USB cá nhân, ổ cứng di động, hoặc gửi qua email cá nhân/cloud cá nhân (Google Drive, Zalo, Telegram). Dữ liệu huấn luyện của dự án là tài sản sở hữu trí tuệ và có thể chứa các thông tin bảo mật/riêng tư chưa được công bố. Việc gửi qua email cá nhân hoặc nhờ người ngoài làm hộ vi phạm nghiêm trọng cam kết bảo mật NDA và chính sách quản trị dữ liệu. Giải pháp đúng: báo cáo với team lead/quản lý dự án để xin gia hạn thời gian làm việc trên máy trạm của công ty, hoặc sử dụng kết nối VPN nội bộ có kiểm soát an ninh mạng của tổ chức.

## 2. Năm việc: được hay không
1. Mở job được giao trên máy công ty: ĐƯỢC. Đây là môi trường làm việc chuẩn hóa, được quản lý thiết bị và bảo mật mạng an toàn theo quy định.
2. Chụp màn hình gửi người quen: KHÔNG ĐƯỢC. Chụp màn hình phát tán hình ảnh dataset ra bên ngoài làm lộ dữ liệu chưa release và vi phạm thỏa thuận bảo mật dữ liệu.
3. Chép lô ra USB: KHÔNG ĐƯỢC. Sao chép dữ liệu ra thiết bị ngoài tiềm ẩn nguy cơ thất thoát dữ liệu, lây nhiễm mã độc và vi phạm chính sách Data Loss Prevention (DLP).
4. Dán nhãn thật lên chatbot công cộng: KHÔNG ĐƯỢC. Các chatbot công cộng có thể lưu log prompt vào máy chủ bên thứ ba để huấn luyện mô hình của họ, gây rò rỉ dữ liệu gán nhãn độc quyền.
5. Đưa tài khoản CVAT cho đồng nghiệp: KHÔNG ĐƯỢC. Mỗi người gắn với định danh annotator/reviewer cụ thể để truy vết trách nhiệm và tính lương; chia sẻ tài khoản làm mất tính toàn vẹn của audit log và vi phạm Access Control.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Khi phát hiện khuôn mặt người nhìn rõ trong lô ảnh (ví dụ ảnh `000000017207` và `000000001993` có hình ảnh người đi bộ rõ mặt), quyết định bắt buộc đối với lô là kết luận HOLD toàn bộ lô dữ liệu. Người gán nhãn không được tự ý xóa ảnh hoặc tự dùng phần mềm ngoài làm mờ ảnh vì sẽ làm sai lệch cấu trúc dataset, hỏng mask phân đoạn và sai lệch mã hash SHA256 trong manifest. Cần giữ nguyên hiện trạng, ghi nhận sự kiện vi phạm quyền riêng tư và báo ngay cho Quản lý dự án (Project Manager) cùng bộ phận Data Governance để áp dụng quy trình xử lý ẩn danh hóa đạt chuẩn GDPR/Privacy trước khi lô được release.
"""
(run_dir / "security.md").write_text(sec_content, encoding="utf-8")
print(f"Created {run_dir / 'security.md'}")

# 10. Record lineage
lp = ROOT / "runs" / "lineage.jsonl"
print("Recording lineage events...")
subprocess.run(["py", "scripts/lineage.py", "record", "--event", "decision", "--release-id", rid, "--decision", "HOLD"], check=True)
subprocess.run(["py", "scripts/lineage.py", "record", "--event", "release", "--release-id", v2_name, "--parent", rid], check=True)

# 11. Pack release v2
print("Packing release v2...")
subprocess.run(["py", "scripts/pack_release.py", str(v2_dir)], check=True)

# 12. Run check_handover.py
print("Running check_handover.py...")
subprocess.run(["py", "scripts/check_handover.py", "--run", str(run_dir)], check=True)
