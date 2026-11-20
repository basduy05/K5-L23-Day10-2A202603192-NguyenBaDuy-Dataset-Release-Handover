"""trace_query.py - Pha 5: truy vết ticket của team AI -> trace.json

Dùng:  py trace_query.py <thư_mục_delivery> --out <trace.json>

Chỉ đọc thư mục delivery, chỉ thư viện chuẩn, không mạng.
Tiêu chí (GUIDE Pha 5):
  - ảnh thuộc job có guideline CŨ (lấy theo jobs.csv, KHÔNG theo guideline ghi ở ảnh)
  - labels/<ảnh>.txt có ít nhất 1 box thuộc lớp bị đổi quy tắc
  - tier_a: ảnh đó nằm trong cảnh ticket nêu; tier_b: phần còn lại
  - notify: annotator + reviewer của các job chứa ảnh tier_a/tier_b
"""
import argparse
import csv
import json
import re
from pathlib import Path


def version_key(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def load_classes(d: Path) -> dict[str, int]:
    """tên lớp -> class_id, từ classes.txt (mỗi dòng 'id tên', tên có thể có dấu cách)."""
    out = {}
    for line in (d / "classes.txt").read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            out[parts[1]] = int(parts[0])
    return out


def find_rule_change(d: Path, classes: dict[str, int]) -> tuple[str, str]:
    """Đọc changelog: tìm lớp bị đổi quy tắc và phiên bản bắt đầu áp dụng quy tắc mới."""
    text = (d / "guideline" / "changelog.md").read_text(encoding="utf-8")
    # tách theo mục '## vX.Y'
    for m in re.finditer(r"^##\s*(v[\d.]+)\s*$(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S):
        version, body = m.group(1), m.group(2)
        names = [n for n in re.findall(r"`([^`]+)`", body) if n in classes]
        if names:
            return names[0], version
    raise SystemExit("Không tìm thấy lớp bị đổi quy tắc trong changelog.md")


def find_reported_scenes(d: Path, all_scenes: set[str]) -> set[str]:
    """Cảnh team AI nêu trong ticket: mọi scene_id có thật trong metadata xuất hiện trong ticket."""
    text = (d / "incoming" / "ticket.md").read_text(encoding="utf-8")
    tokens = set(re.findall(r"[A-Za-z0-9_\-]+", text))
    return tokens & all_scenes


def has_class(label_file: Path, class_id: int) -> bool:
    if not label_file.is_file():
        return False
    for line in label_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts and parts[0].lstrip("-").isdigit() and int(parts[0]) == class_id:
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("delivery")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    d = Path(args.delivery)

    classes = load_classes(d)
    rule_class, new_version = find_rule_change(d, classes)
    class_id = classes[rule_class]

    with (d / "jobs.csv").open(encoding="utf-8", newline="") as f:
        jobs = {row["job_id"]: row for row in csv.DictReader(f)}
    old_jobs = {j for j, row in jobs.items() if version_key(row["guideline"]) < version_key(new_version)}

    items = json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]
    reported = find_reported_scenes(d, {it["scene_id"] for it in items})

    tier_a, tier_b, hit_jobs = [], [], set()
    for it in items:
        if it["job_id"] not in old_jobs:          # guideline theo JOB
            continue
        if not has_class(d / "labels" / f"{it['image']}.txt", class_id):
            continue
        (tier_a if it["scene_id"] in reported else tier_b).append(it["image"])
        hit_jobs.add(it["job_id"])

    notify = sorted({jobs[j]["annotator"] for j in hit_jobs} | {jobs[j]["reviewer"] for j in hit_jobs})
    result = {"tier_a": sorted(tier_a), "tier_b": sorted(tier_b), "notify": notify}
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"rule_class={rule_class} (id {class_id}), quy tắc mới từ {new_version}")
    print(f"job guideline cũ: {sorted(old_jobs)}")
    print(f"cảnh ticket nêu: {sorted(reported)}")
    print(f"tier_a={len(tier_a)} tier_b={len(tier_b)} notify={notify}")


if __name__ == "__main__":
    main()
