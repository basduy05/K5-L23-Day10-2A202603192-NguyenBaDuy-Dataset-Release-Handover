"""Measure candidate workload on a delivered clean/calibration lot, without truth."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path

from cross_check import DEFAULT_THRESHOLDS, profile_candidates, threshold_dict
from validate import DeliveryValidator


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("delivery")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    context = DeliveryValidator(Path(args.delivery).resolve())
    base = DEFAULT_THRESHOLDS
    profiles = {
        "sensitive": replace(base, class_iou=0.40, drift_containment=0.90,
                             merge_union_containment=0.70, merge_exclusive_fraction=0.10),
        "balanced": base,
        "strict": replace(base, class_iou=0.55, drift_containment=0.75,
                          merge_union_containment=0.90, merge_exclusive_fraction=0.20),
    }
    candidates = profile_candidates(context.delivery_dir, context.manifest,
                                    context.class_names, context.panoptic_doc, profiles)
    result = {"delivery": str(Path(args.delivery)), "image_count": len(context.manifest),
              "meaning": "Candidate workload only; this does not measure recall or semantic F1.",
              "profiles": {}}
    for name, rows in candidates.items():
        result["profiles"][name] = {
            "thresholds": threshold_dict(profiles[name]),
            "candidate_records": len(rows), "candidate_images": len({r["image"] for r in rows}),
            "by_type": dict(sorted(Counter(r["type"] for r in rows).items())),
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
