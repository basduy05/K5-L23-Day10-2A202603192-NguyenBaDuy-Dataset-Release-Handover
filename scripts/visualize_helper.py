#!/usr/bin/env python3
"""Script nâng cao hỗ trợ Visualize Bounding Box YOLO và Mask Panoptic phục vụ Human Review.

Được thiết kế chuyên biệt cho công cụ thẩm định chất lượng dữ liệu nhóm (Pha 2 & Pha 6b).
Sử dụng thư viện Pillow để vẽ trực quan nhãn Detection (xanh lá) và Panoptic Thing (đỏ/cam),
tự động gắn cờ các đối tượng bất đồng từ candidates.json, hỗ trợ zoom/crop và sinh HTML gallery.

Cách dùng cơ bản:
    # 1. Xem 1 ảnh cụ thể trên seed luyện tập:
    py scripts/visualize_helper.py --run runs/r5007 --image 000000000139 --open

    # 2. Xem ảnh trên Đề Ẩn (delivery trực tiếp):
    py scripts/visualize_helper.py --delivery delivery --image img_0115 --open

    # 3. Xem nhiều ảnh cùng lúc:
    py scripts/visualize_helper.py --delivery delivery --image img_0115,img_0117,img_0120,img_0131

    # 4. Tự động vẽ tất cả ảnh ứng viên nghi vấn và tạo thư viện HTML xem trên web:
    py scripts/visualize_helper.py --run runs/r5007 --all-candidates --html
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Thư mục gốc repo
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pngutil  # noqa: E402


def get_font(size: int = 14) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Tải font TrueType hệ thống nếu có, fallback về font mặc định nếu không có font ngoài."""
    font_candidates = [
        "arial.ttf",
        "segoeui.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
        "Helvetica.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_rounded_badge(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    text_color: tuple[int, int, int, int],
    bg_color: tuple[int, int, int, int],
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    padding: int = 4,
) -> None:
    """Vẽ nhãn chữ kèm nền đen/màu bo góc tương phản cao, chống chìm màu trên ảnh."""
    bbox = font.getbbox(text) if hasattr(font, "getbbox") else (0, 0, len(text) * 8, 14)
    w = bbox[2] - bbox[0] + padding * 2
    h = bbox[3] - bbox[1] + padding * 2
    draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=text_color, width=1)
    draw.text((x + padding, y + padding - (bbox[1] if hasattr(font, "getbbox") else 0)), text, fill=text_color, font=font)


def visualize_image(
    delivery_dir: Path,
    image_name: str,
    out_dir: Path,
    candidates_map: dict[str, list[dict[str, Any]]] | None = None,
    crop_mode: bool = False,
) -> tuple[Path | None, Path | None]:
    """Vẽ nhãn Detection và Panoptic lên ảnh và lưu file annotated."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Chuẩn hóa tên ảnh
    image_stem = Path(image_name).stem
    img_path = delivery_dir / "images" / f"{image_stem}.jpg"
    label_path = delivery_dir / "labels" / f"{image_stem}.txt"
    mask_path = delivery_dir / "masks" / f"{image_stem}.png"

    if not img_path.is_file():
        print(f"⚠️ [Cảnh báo] Không tìm thấy file ảnh: {img_path}")
        return None, None

    base_img = Image.open(img_path).convert("RGBA")
    W, H = base_img.size

    # Tạo 2 lớp: 1 lớp phủ màu bán trong suốt (overlay) và 1 lớp vẽ nét đè lên (draw)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    annotated = base_img.copy()
    draw = ImageDraw.Draw(annotated)

    # Đọc danh mục 80 lớp Detection từ classes.txt
    classes_file = delivery_dir / "classes.txt"
    class_names: list[str] = []
    if classes_file.is_file():
        class_names = [line.split(" ", 1)[1].strip() for line in classes_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    font_label = get_font(13)
    font_title = get_font(15)

    all_bounding_boxes: list[tuple[float, float, float, float]] = []

    # 1. Xử lý Panoptic Segments (Thing)
    panoptic_file = delivery_dir / "panoptic.json"
    pan_count = 0
    if panoptic_file.is_file():
        pan_doc = json.loads(panoptic_file.read_text(encoding="utf-8"))
        categories = {c["id"]: c for c in pan_doc.get("categories", [])}
        
        ann = next((a for a in pan_doc.get("annotations", []) if Path(a["file_name"]).stem == image_stem), None)
        if ann:
            for s in ann.get("segments_info", []):
                cat = categories.get(s["category_id"], {})
                cat_name = cat.get("name", f"cat_{s['category_id']}")
                is_thing = cat.get("isthing", False)

                if is_thing:
                    pan_count += 1
                    bx, by, bw, bh = s["bbox"]
                    x1, y1, x2, y2 = bx, by, bx + bw, by + bh
                    all_bounding_boxes.append((x1, y1, x2, y2))

                    # Phủ nền đỏ mờ (alpha = 40)
                    overlay_draw.rectangle([x1, y1, x2, y2], fill=(255, 61, 0, 40))
                    # Vẽ khung nét đứt màu đỏ cam
                    draw.rectangle([x1, y1, x2, y2], outline=(255, 61, 0, 255), width=2)
                    
                    # Badge góc dưới phải của Panoptic box
                    pan_text = f"Pan: {cat_name} ({s.get('area', 0)}px)"
                    draw_rounded_badge(
                        draw=draw,
                        x=max(0, x2 - len(pan_text) * 8 - 12),
                        y=min(H - 22, y2),
                        text=pan_text,
                        text_color=(255, 204, 188, 255),
                        bg_color=(183, 28, 28, 220),
                        font=font_label,
                    )

    # 2. Xử lý YOLO Detection Bounding Boxes
    det_count = 0
    if label_path.is_file():
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                try:
                    c = int(float(parts[0]))
                    x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    c_name = class_names[c] if 0 <= c < len(class_names) else str(c)
                    det_count += 1

                    bx1 = max(0.0, (x - w / 2) * W)
                    by1 = max(0.0, (y - h / 2) * H)
                    bx2 = min(float(W), (x + w / 2) * W)
                    by2 = min(float(H), (y + h / 2) * H)
                    all_bounding_boxes.append((bx1, by1, bx2, by2))

                    # Phủ nền xanh lá mờ (alpha = 40)
                    overlay_draw.rectangle([bx1, by1, bx2, by2], fill=(0, 230, 118, 35))
                    # Vẽ viền xanh dạ quang dày 3px
                    draw.rectangle([bx1, by1, bx2, by2], outline=(0, 230, 118, 255), width=3)

                    # Badge góc trên bên trái của Detection box
                    det_text = f"Det: {c_name} (cls {c})"
                    badge_y = by1 - 22 if by1 > 24 else by1 + 2
                    draw_rounded_badge(
                        draw=draw,
                        x=bx1,
                        y=badge_y,
                        text=det_text,
                        text_color=(0, 230, 118, 255),
                        bg_color=(10, 25, 18, 230),
                        font=font_label,
                    )
                except ValueError:
                    continue

    # Ghép lớp phủ bán trong suốt vào ảnh chính
    annotated = Image.alpha_composite(annotated, overlay)
    final_draw = ImageDraw.Draw(annotated)

    # 3. Vẽ Top Header Banner chuyên nghiệp
    banner_h = 36
    # Thanh header đen mờ ở đỉnh ảnh
    final_draw.rectangle([0, 0, W, banner_h], fill=(15, 23, 42, 235))
    final_draw.line([(0, banner_h), (W, banner_h)], fill=(51, 65, 85, 255), width=1)

    # Tiêu đề ảnh & thống kê
    title_text = f"📷 {image_stem}.jpg  ({W}x{H})  |  🟢 Det: {det_count}  |  🔴 Pan Thing: {pan_count}"
    final_draw.text((10, 8), title_text, fill=(248, 250, 252, 255), font=font_title)

    # Nếu có cảnh báo nghi vấn từ candidates.json
    cands_for_img = (candidates_map or {}).get(image_stem, [])
    if cands_for_img:
        first_cand = cands_for_img[0]
        cand_type = first_cand.get("type", "candidate")
        cand_note = first_cand.get("note", first_cand.get("reason", "Bất đồng đối chiếu"))
        warning_text = f"⚠️ [{cand_type.upper()}] {cand_note[:45]}"
        w_len = len(warning_text) * 8
        final_draw.text((max(W - w_len - 15, 300), 9), warning_text, fill=(251, 191, 36, 255), font=font_label)

    # Lưu ảnh chính
    out_annotated = out_dir / f"{image_stem}_annotated.png"
    annotated.convert("RGB").save(out_annotated, quality=95)

    # 4. Tùy chọn Zoom/Crop vùng nghi vấn
    out_crop = None
    if crop_mode and all_bounding_boxes:
        # Tìm bounding box bao quanh các đối tượng
        min_x = max(0, min(b[0] for b in all_bounding_boxes) - 30)
        min_y = max(0, min(b[1] for b in all_bounding_boxes) - 30)
        max_x = min(W, max(b[2] for b in all_bounding_boxes) + 30)
        max_y = min(H, max(b[3] for b in all_bounding_boxes) + 30)
        
        if (max_x - min_x) > 20 and (max_y - min_y) > 20:
            crop_img = annotated.crop((min_x, min_y, max_x, max_y))
            out_crop = out_dir / f"{image_stem}_crop.png"
            crop_img.convert("RGB").save(out_crop, quality=95)

    return out_annotated, out_crop


def generate_html_gallery(out_dir: Path, processed_images: list[dict[str, Any]]) -> Path:
    """Tạo trang web gallery HTML để người kiểm duyệt mở lướt xem hàng loạt nhanh chóng."""
    gallery_path = out_dir / "index.html"
    
    cards_html = []
    for item in processed_images:
        name = item["name"]
        annotated_rel = Path(item["annotated"]).name
        crop_rel = Path(item["crop"]).name if item.get("crop") else None
        
        cands = item.get("candidates", [])
        cand_badges = "".join([f'<span class="badge">{c.get("type", "candidate")}</span>' for c in cands])
        cand_notes = "<br>".join([f"• <b>{c.get('type')}:</b> {c.get('note', c.get('reason', ''))}" for c in cands]) or "Không có ghi chú"

        crop_html = f'<div class="crop-box"><img src="{crop_rel}" alt="crop" title="Zoom Crop"></div>' if crop_rel else ""

        cards_html.append(f"""
        <div class="card" id="card_{name}">
          <div class="card-header">
            <h3>{name}.jpg</h3>
            <div>{cand_badges}</div>
          </div>
          <div class="img-container">
            <a href="{annotated_rel}" target="_blank">
              <img src="{annotated_rel}" alt="{name}" loading="lazy">
            </a>
          </div>
          {crop_html}
          <div class="card-body">
            <div class="info-text">{cand_notes}</div>
            <div class="actions">
              <button class="btn btn-conf" onclick="copyNote('{name}', 'confirmed')">Copy Confirmed Note</button>
              <button class="btn btn-rej" onclick="copyNote('{name}', 'rejected')">Copy Rejected Note</button>
            </div>
          </div>
        </div>
        """)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Human Review Visualizer Gallery - Day 10 Lab</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b1120; color: #e2e8f0; margin: 0; padding: 20px; }}
  header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; margin-bottom: 25px; }}
  h1 {{ margin: 0; font-size: 24px; color: #38bdf8; }}
  .legend {{ display: flex; gap: 20px; font-size: 14px; }}
  .legend span {{ display: flex; align-items: center; gap: 6px; }}
  .box-green {{ width: 14px; height: 14px; background: #00e676; border-radius: 3px; }}
  .box-red {{ width: 14px; height: 14px; background: #ff3d00; border-radius: 3px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 24px; }}
  .card {{ background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow: hidden; display: flex; flex-direction: column; }}
  .card-header {{ padding: 12px 16px; background: #0f172a; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }}
  .card-header h3 {{ margin: 0; font-size: 16px; color: #f8fafc; }}
  .badge {{ background: #f59e0b; color: #000; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 9999px; margin-left: 6px; text-transform: uppercase; }}
  .img-container {{ background: #000; display: flex; justify-content: center; align-items: center; min-height: 320px; }}
  .img-container img {{ max-width: 100%; height: auto; display: block; }}
  .crop-box {{ background: #090d16; padding: 8px; border-top: 1px solid #334155; display: flex; justify-content: center; }}
  .crop-box img {{ max-height: 160px; border: 1px solid #475569; border-radius: 4px; }}
  .card-body {{ padding: 14px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }}
  .info-text {{ font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 12px; }}
  .actions {{ display: flex; gap: 10px; }}
  .btn {{ flex: 1; padding: 8px; border-radius: 6px; border: none; font-size: 12px; font-weight: bold; cursor: pointer; transition: opacity 0.2s; }}
  .btn:hover {{ opacity: 0.85; }}
  .btn-conf {{ background: #10b981; color: #fff; }}
  .btn-rej {{ background: #64748b; color: #fff; }}
  #toast {{ position: fixed; bottom: 20px; right: 20px; background: #38bdf8; color: #0f172a; padding: 10px 20px; border-radius: 8px; font-weight: bold; display: none; }}
</style>
</head>
<body>

<header>
  <div>
    <h1>Human Review Visualizer Gallery</h1>
    <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Tổng cộng: {len(processed_images)} ảnh đã visualize</div>
  </div>
  <div class="legend">
    <span><div class="box-green"></div> <b>Detection (YOLO)</b></span>
    <span><div class="box-red"></div> <b>Panoptic (Thing)</b></span>
  </div>
</header>

<div class="grid">
  {''.join(cards_html)}
</div>

<div id="toast">Đã copy ghi chú vào clipboard!</div>

<script>
function copyNote(name, verdict) {{
  const note = verdict === 'confirmed' 
    ? `${{name}},confirmed,"mo anh xem ro: phat hien bat dong gán nhan giua detection va panoptic"`
    : `${{name}},rejected,"che khuat tu nhien giua cac vat the trong anh khong phai loi"`;
  navigator.clipboard.writeText(note);
  const toast = document.getElementById("toast");
  toast.innerText = `Đã copy: ${{note}}`;
  toast.style.display = "block";
  setTimeout(() => toast.style.display = "none", 2500);
}}
</script>

</body>
</html>
"""
    gallery_path.write_text(html, encoding="utf-8")
    return gallery_path


def open_file_in_viewer(file_path: Path) -> None:
    """Mở file trên trình xem ảnh / trình duyệt mặc định của hệ thống."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(file_path))
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", str(file_path)], check=False)
        else:
            subprocess.run(["xdg-open", str(file_path)], check=False)
    except Exception as e:
        print(f"Không thể tự động mở file: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Script hỗ trợ Visualize Bounding Box YOLO và Mask Panoptic phục vụ Human Review",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ví dụ lệnh:
  py scripts/visualize_helper.py --delivery delivery --image img_0115 --open
  py scripts/visualize_helper.py --run runs/r5007 --all-candidates --crop --html
  py scripts/visualize_helper.py --delivery delivery --all-candidates --html --open
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="Thư mục run (ví dụ: runs/r5007 hoặc runs/de_an)")
    group.add_argument("--delivery", help="Thư mục delivery trực tiếp (ví dụ: delivery hoặc runs/r5007/delivery)")

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--image", help="Tên 1 hoặc nhiều ảnh cách nhau bởi dấu phẩy (ví dụ: img_0115 hoặc img_0115,img_0117)")
    target_group.add_argument("--all-candidates", action="store_true", help="Vẽ tất cả ảnh xuất hiện trong candidates.json")
    target_group.add_argument("--all", action="store_true", help="Vẽ toàn bộ ảnh có trong thư mục images/")

    parser.add_argument("--out", help="Thư mục lưu ảnh đã visualize (mặc định: <run>/visualize hoặc <delivery>/../visualize)")
    parser.add_argument("--crop", action="store_true", help="Cắt và phóng to (zoom crop) vùng nghi vấn xuất ra file riêng")
    parser.add_argument("--html", action="store_true", help="Tự động xuất trang web index.html để xem thư viện ảnh")
    parser.add_argument("-o", "--open", action="store_true", help="Tự động mở ảnh/trang HTML đầu tiên sau khi hoàn thành")

    args = parser.parse_args()

    # 1. Xác định đường dẫn delivery và out
    if args.run:
        run_path = Path(args.run).resolve()
        delivery_dir = run_path / "delivery" if (run_path / "delivery").is_dir() else run_path
        default_out = run_path / "visualize"
        candidates_file = run_path / "candidates.json"
    else:
        delivery_dir = Path(args.delivery).resolve()
        default_out = delivery_dir.parent / "visualize"
        candidates_file = delivery_dir.parent / "candidates.json"

    out_dir = Path(args.out).resolve() if args.out else default_out
    out_dir.mkdir(parents=True, exist_ok=True)

    if not delivery_dir.is_dir():
        raise SystemExit(f"❌ [Lỗi] Không tìm thấy thư mục delivery: {delivery_dir}")

    # 2. Đọc candidates.json (nếu có)
    candidates_map: dict[str, list[dict[str, Any]]] = {}
    if candidates_file.is_file():
        try:
            cand_data = json.loads(candidates_file.read_text(encoding="utf-8"))
            for c in cand_data.get("candidates", []):
                im_name = Path(c.get("image", "")).stem
                candidates_map.setdefault(im_name, []).append(c)
        except Exception:
            pass

    # 3. Xác định danh sách ảnh cần xử lý
    images_dir = delivery_dir / "images"
    if not images_dir.is_dir():
        raise SystemExit(f"❌ [Lỗi] Không tìm thấy thư mục images trong delivery: {images_dir}")

    targets: list[str] = []
    if args.image:
        targets = [name.strip() for name in args.image.split(",") if name.strip()]
    elif args.all_candidates:
        if not candidates_map:
            raise SystemExit(f"❌ Không tìm thấy thông tin ứng viên trong: {candidates_file}")
        targets = sorted(candidates_map.keys())
    elif args.all:
        targets = sorted(p.stem for p in images_dir.glob("*.jpg"))

    print(f"🚀 Bắt đầu visualize {len(targets)} ảnh...")
    print(f"📂 Thư mục dữ liệu: {delivery_dir}")
    print(f"📁 Thư mục xuất ảnh: {out_dir}\n")

    first_output: Path | None = None
    processed_records: list[dict[str, Any]] = []

    for idx, name in enumerate(targets, start=1):
        clean_name = Path(name).stem
        out_ann, out_crop = visualize_image(
            delivery_dir=delivery_dir,
            image_name=clean_name,
            out_dir=out_dir,
            candidates_map=candidates_map,
            crop_mode=args.crop,
        )
        if out_ann:
            if not first_output:
                first_output = out_ann
            processed_records.append({
                "name": clean_name,
                "annotated": str(out_ann),
                "crop": str(out_crop) if out_crop else None,
                "candidates": candidates_map.get(clean_name, []),
            })
            print(f"  [{idx:03d}/{len(targets):03d}] Đã xuất: {out_ann.name}")

    print(f"\n✅ Hoàn thành xuất {len(processed_records)} ảnh tại: {out_dir}")

    # 4. Sinh trang HTML Gallery nếu có cờ --html
    gallery_file: Path | None = None
    if args.html:
        gallery_file = generate_html_gallery(out_dir, processed_records)
        print(f"🌐 Đã tạo trang web review: {gallery_file}")

    # 5. Tự động mở file nếu có cờ --open
    if args.open:
        target_to_open = gallery_file if (args.html and gallery_file) else first_output
        if target_to_open and target_to_open.is_file():
            print(f"🔍 Đang mở: {target_to_open.name} ...")
            open_file_in_viewer(target_to_open)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
