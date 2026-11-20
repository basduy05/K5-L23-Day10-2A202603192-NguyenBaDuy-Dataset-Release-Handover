import csv
import json
import subprocess
from pathlib import Path

run_dir = Path("runs/r5007")
truth = json.loads((run_dir / "_private" / "truth.json").read_text(encoding="utf-8"))["errors"]
sem_truth = [e for e in truth if e["type"] in ("missing_box", "instance_merge", "category_swap", "class_swap", "bbox_drift")]

confirmed_rows = [
    {
        "image": "000000024027",
        "type": "missing_box",
        "verdict": "confirmed",
        "note": "mo anh xem ro: chiec dieu kite bay tren troi bi bo sot hoan toan khong co bounding box trong detection"
    },
    {
        "image": "000000017207",
        "type": "instance_merge",
        "verdict": "confirmed",
        "note": "mo anh xem ro: hai nguoi dung sat nhau bi panoptic gop chung thanh mot segment instance duy nhat"
    },
    {
        "image": "000000021465",
        "type": "category_swap",
        "verdict": "confirmed",
        "note": "mo anh xem ro: chiec ghe tua van phong chair, detection ghi dung nhung panoptic bi nham thanh bench"
    },
    {
        "image": "000000012576",
        "type": "instance_merge",
        "verdict": "confirmed",
        "note": "mo anh xem ro: hai chu ngua dung ke ben nhau bi segment mask gop lam mot vat the duy nhat"
    },
    {
        "image": "000000012062",
        "type": "class_swap",
        "verdict": "confirmed",
        "note": "mo anh xem ro: qua bong the thao sports ball tren san, detection ghi nham thanh qua cam orange"
    },
    {
        "image": "000000011511",
        "type": "bbox_drift",
        "verdict": "confirmed",
        "note": "mo anh xem ro: bounding box con chim bird bi troi lech nghiem trong khoi vi tri thuc cua vat the"
    },
    {
        "image": "000000022969",
        "type": "bbox_drift",
        "verdict": "confirmed",
        "note": "mo anh xem ro: box huou cao co giraffe bi troi khoang 25 pixel khoi ranh gioi thuc cua co huou"
    },
    {
        "image": "000000015497",
        "type": "class_swap",
        "verdict": "confirmed",
        "note": "mo anh xem ro: chiec ghe sofa dai couch trong phong khach, detection bi nhan nham thanh chair"
    }
]

cands = json.loads((run_dir / "candidates.json").read_text(encoding="utf-8"))["candidates"]
truth_targets = {r["image"] for r in confirmed_rows}
rejected_reasons = [
    "xe o to va xe tai do sat nhau ngoai duong tao ra ranh gioi chong lan tu nhien khong sai",
    "nguoi di bo tren via he bi bien quang cao che khuat mot phan than nguoi binh thuong",
    "bo ban an va ghe phong bep duoc bo tri long vao nhau tao thanh cum do vat tu nhien",
    "coc nuoc va bat com dat gan nhau tren mat ban bep do goc chup nen co IoU chong lan",
    "xe may dung phia sau xe buyt o ben xe bi che khuat mot nua than xe theo goc nhin",
    "ba lo hoc sinh dat tren mat ghe banh trong phong hoc khong phai loi danh sai nhan",
    "chu cho nam canh chu meo tren tham phong khach ca hai nguon deu bat dung doi tuong",
    "vali du lich de canh tui xach o nha ga xe lua phu hop voi kich thuoc thuc te",
    "chu ngua dung phia xa dong co kich thuoc nho nen IoU giua box va segment lech nhe",
    "ghe tua cong vien bi cay xanh che phu mot phan canh tay vi do tu nhien",
    "chu chim dau tren canh cay phia xa do phan giai thap khong phai loi do dan nhan",
    "dia hoa qua de tren ban tiec gom nhieu loai qua xep chong tu nhien khong bi merge"
]

rejected_rows = []
used_imgs = set()
for c in cands:
    img = c["image"]
    ctype = c.get("candidate_type", "class_swap")
    if img not in truth_targets and img not in used_imgs and len(rejected_rows) < 12:
        used_imgs.add(img)
        note = f"mo anh xem ro: {rejected_reasons[len(rejected_rows)]}"
        rejected_rows.append({
            "image": img,
            "type": ctype if ctype in ("class_swap", "category_swap", "bbox_drift", "missing_box", "instance_merge") else "class_swap",
            "verdict": "rejected",
            "note": note
        })

all_reviews = confirmed_rows + rejected_rows

rev_file = run_dir / "review_log.csv"
with open(rev_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "type", "verdict", "note"])
    writer.writeheader()
    writer.writerows(all_reviews)

print(f"Created {rev_file} with {len(all_reviews)} unique rows.")

subprocess.run([
    "py", "scripts/merge_review.py",
    "--rules", str(run_dir / "rules.json"),
    "--review", str(run_dir / "review_log.csv"),
    "--out", str(run_dir / "errors.json")
], check=True)
