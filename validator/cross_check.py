"""Detection/panoptic candidates from delivered files, using only stdlib.

Candidates are observations for human review. This module does not decide which
source has the correct class and never writes confirmed/rejected verdicts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pngutil


@dataclass(frozen=True)
class Thresholds:
    class_iou: float = 0.45
    class_containment: float = 0.80
    drift_containment: float = 0.85
    min_match_iou: float = 0.15
    min_drift_box_fraction: float = 0.005
    min_segment_pixels: int = 256
    min_segment_fraction: float = 0.002
    merge_union_containment: float = 0.80
    merge_exclusive_fraction: float = 0.15
    merge_max_box_iou: float = 0.45


DEFAULT_THRESHOLDS = Thresholds()


def bbox_iou(a, b):
    """IoU for pixel boxes [left, top, width, height]."""
    intersection = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(
        0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    union = a[2] * a[3] + b[2] * b[3] - intersection
    return intersection / union if union > 0 else 0.0


def delivery_file(root: Path, relative: str) -> Path:
    """Reject manifest paths and symlinks escaping the given delivery."""
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes delivery: {relative}")
    return path


class MaskPixels:
    """Horizontal pixel runs, so containment queries avoid rescanning RGB PNGs."""
    def __init__(self, width, height, pixels, segment_ids):
        if len(pixels) != width * height * 3:
            raise ValueError("Mask dimensions do not match RGB buffer")
        self.width, self.height = width, height
        self.runs = {sid: [] for sid in segment_ids if sid != 0}
        self.counts = {sid: 0 for sid in self.runs}
        for y in range(height):
            start = 0
            row_offset = y * width * 3
            previous = pngutil.segment_id(pixels, row_offset)
            for x in range(1, width):
                sid = pngutil.segment_id(pixels, row_offset + x * 3)
                if sid != previous:
                    self._add(previous, y, start, x)
                    previous, start = sid, x
            self._add(previous, y, start, width)

    def _add(self, sid, y, start, end):
        if sid in self.runs:
            self.runs[sid].append((y, start, end))
            self.counts[sid] += end - start

    def count_inside(self, sid, box):
        """Count pixel centers in a half-open floating-point box, clipped to mask."""
        x, y, w, h = box
        if w <= 0 or h <= 0:
            return 0
        left = max(0, math.ceil(x - 0.5))
        top = max(0, math.ceil(y - 0.5))
        right = min(self.width, math.ceil(x + w - 0.5))
        bottom = min(self.height, math.ceil(y + h - 0.5))
        if right <= left or bottom <= top:
            return 0
        return sum(max(0, min(end, right) - max(start, left))
                   for row, start, end in self.runs.get(sid, ()) if top <= row < bottom)

    def containment(self, sid, box):
        total = self.counts.get(sid, 0)
        return self.count_inside(sid, box) / total if total else 0.0


def read_boxes(path, class_names, width, height):
    boxes = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            c, x, y, w, h = map(float, parts)
        except ValueError:
            continue
        if not all(math.isfinite(v) for v in (c, x, y, w, h)):
            continue
        if not c.is_integer() or not 0 <= c < len(class_names) or w <= 0 or h <= 0:
            continue
        # Rule errors have their own output; do not turn malformed boxes into
        # semantic candidates through a failed match.
        if x - w / 2 < -0.01 or y - h / 2 < -0.01 or x + w / 2 > 1.01 or y + h / 2 > 1.01:
            continue
        boxes.append({"line": line_number, "class_name": class_names[int(c)],
                      "px_box": [(x - w / 2) * width, (y - h / 2) * height, w * width, h * height],
                      "area_fraction": w * h})
    return boxes


def _intersection_box(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    return [x, y, max(0.0, min(a[0] + a[2], b[0] + b[2]) - x),
            max(0.0, min(a[1] + a[3], b[1] + b[3]) - y)]


def image_candidates(name, boxes, segments, categories, mask, config=DEFAULT_THRESHOLDS):
    """Evaluate one image, keeping region identities and measured evidence."""
    segments = [s for s in segments if s["id"] != 0 and not s.get("iscrowd")
                and categories.get(s["category_id"], {}).get("isthing")
                and mask.counts.get(s["id"], 0)]
    if not segments:
        return []
    minimum_area = max(config.min_segment_pixels,
                       mask.width * mask.height * config.min_segment_fraction)
    metrics = {}
    for s in segments:
        for i, b in enumerate(boxes):
            inside = mask.count_inside(s["id"], b["px_box"])
            metrics[s["id"], i] = {
                "iou": bbox_iou(b["px_box"], s["bbox"]),
                "inside": inside,
                "containment": inside / mask.counts[s["id"]],
            }
    candidates, merged = [], set()
    # A segment must have actual pixels in two spatially distinct boxes. Its
    # rectangular bbox enclosing two centers is not sufficient evidence.
    for s in segments:
        sid = s["id"]
        total = mask.counts[sid]
        if total < minimum_area:
            continue
        cat_name = categories[s["category_id"]]["name"]
        related = [i for i, b in enumerate(boxes) if b["class_name"] == cat_name
                   and metrics[sid, i]["containment"] >= config.merge_exclusive_fraction]
        for i, j in combinations(related, 2):
            a, b = boxes[i]["px_box"], boxes[j]["px_box"]
            if bbox_iou(a, b) > config.merge_max_box_iou:
                continue
            intersection = mask.count_inside(sid, _intersection_box(a, b))
            ca, cb = metrics[sid, i]["inside"], metrics[sid, j]["inside"]
            exclusive = min(ca - intersection, cb - intersection) / total
            union = (ca + cb - intersection) / total
            if exclusive < config.merge_exclusive_fraction or union < config.merge_union_containment:
                continue
            candidates.append({"image": name, "type": "instance_merge", "segment_id": sid,
                               "suspect_class": cat_name, "box_lines": [boxes[i]["line"], boxes[j]["line"]],
                               "mask_union_containment": round(union, 4),
                               "min_exclusive_fraction": round(exclusive, 4),
                               "note": f"One {cat_name} segment has distinct pixels in two detection boxes; inspect instances."})
            merged.add(sid)
            break

    for i, b in enumerate(boxes):
        best = max(segments, key=lambda s: (metrics[s["id"], i]["iou"], metrics[s["id"], i]["containment"]))
        sid = best["id"]
        m = metrics[sid, i]
        seg_name = categories[best["category_id"]]["name"]
        evidence = {"image": name, "segment_id": sid, "box_line": b["line"],
                    "det_class": b["class_name"], "pan_class": seg_name,
                    "iou": round(m["iou"], 4), "containment": round(m["containment"], 4)}
        if b["class_name"] != seg_name:
            if m["iou"] >= config.class_iou and m["containment"] >= config.class_containment:
                candidates.append({**evidence, "type": "class_swap",
                                   "possible_types": ["class_swap", "category_swap"],
                                   "note": "Classes disagree at the same location; inspect the image to decide which source is wrong."})
        elif (sid not in merged and b["area_fraction"] >= config.min_drift_box_fraction
              and mask.counts[sid] >= minimum_area and m["iou"] >= config.min_match_iou
              and m["containment"] < config.drift_containment):
            candidates.append({**evidence, "type": "bbox_drift",
                               "note": "Detection box excludes a substantial part of the matched segment's pixels; inspect occlusion and matching."})

    for s in segments:
        sid = s["id"]
        if sid in merged or mask.counts[sid] < minimum_area:
            continue
        seg_name = categories[s["category_id"]]["name"]
        # A large unrelated box may enclose an object. Require geometric overlap
        # or a plausible same-class box rather than containment alone.
        plausible = any(metrics[sid, i]["iou"] >= config.min_match_iou
                        or (b["class_name"] == seg_name and metrics[sid, i]["iou"] >= 0.02
                            and metrics[sid, i]["containment"] >= 0.50)
                        for i, b in enumerate(boxes))
        if not plausible:
            candidates.append({"image": name, "type": "missing_box", "segment_id": sid,
                               "pan_class": seg_name, "area": mask.counts[sid],
                               "best_iou": round(max((metrics[sid, i]["iou"] for i in range(len(boxes))), default=0.0), 4),
                               "note": "A substantial thing segment has no plausible detection box; inspect natural annotation differences."})
    return candidates


def profile_candidates(delivery_dir, manifest, class_names, panoptic_doc, profiles):
    """Decode each mask once, evaluating several documented threshold profiles."""
    categories = {c["id"]: c for c in panoptic_doc["categories"]}
    image_by_name = {Path(im["file_name"]).stem: im for im in panoptic_doc["images"]}
    annotations = {a["image_id"]: a for a in panoptic_doc["annotations"]}
    results = {name: [] for name in profiles}
    for name, item in sorted(manifest.items()):
        image = delivery_file(delivery_dir, item["image"])
        label = delivery_file(delivery_dir, item["label"])
        mask_path = delivery_file(delivery_dir, item["mask"])
        if not image.is_file() or not label.is_file() or not mask_path.is_file():
            continue
        im = image_by_name.get(Path(item["image"]).stem)
        if im is None or im["id"] not in annotations:
            raise ValueError(f"Missing panoptic image/annotation mapping for {name}")
        segments = annotations[im["id"]].get("segments_info", [])
        width, height, pixels = pngutil.read_rgb(mask_path)
        if (width, height) != (im["width"], im["height"]):
            raise ValueError(f"Mask/image dimensions differ for {name}")
        wanted = {s["id"] for s in segments if not s.get("iscrowd")
                  and categories.get(s["category_id"], {}).get("isthing")}
        mask = MaskPixels(width, height, pixels, wanted)
        boxes = read_boxes(label, class_names, width, height)
        for profile, config in profiles.items():
            results[profile].extend(image_candidates(name, boxes, segments, categories, mask, config))
    return results


def find_candidates(delivery_dir, manifest, class_names, panoptic_doc, config=DEFAULT_THRESHOLDS):
    return profile_candidates(delivery_dir, manifest, class_names, panoptic_doc, {"default": config})["default"]


def threshold_dict(config=DEFAULT_THRESHOLDS):
    return asdict(config)
