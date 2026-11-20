import base64
import json
from pathlib import Path

REPO_ROOT = Path(r"c:\Users\phamm\OneDrive\Documents\lab10\K5-L23-Day10-2A202603192-NguyenBaDuy-Dataset-Release-Handover")
DELIVERY = REPO_ROOT / "delivery"

classes_file = DELIVERY / "classes.txt"
classes80 = [ln.strip().split(" ", 1)[1] for ln in classes_file.read_text(encoding="utf-8").splitlines()]

panoptic_data = json.loads((DELIVERY / "panoptic.json").read_text(encoding="utf-8"))
pan_cats = {c["id"]: c["name"] for c in panoptic_data["categories"]}

candidates_info = [
    {"name": "img_0115", "assignee": "Phạm Mạnh Hùng", "conflict": "Det 'cup' vs Pan 'bowl'", "focus": "Xem cốc hay bát ở giữa bàn ăn"},
    {"name": "img_0117", "assignee": "Phạm Mạnh Hùng", "conflict": "Box 'elephant' IoU 0.48", "focus": "Xem box voi có lệch khỏi thân voi không hay do cành cây che"},
    {"name": "img_0120", "assignee": "Phạm Mạnh Hùng", "conflict": "Det 'backpack' vs Pan 'handbag'", "focus": "Xem vật thể trên bãi cát là ba lô hay túi xách"},
    {"name": "img_0131", "assignee": "Phạm Mạnh Hùng", "conflict": "Det 'truck' vs Pan 'car'", "focus": "Xem xe ở góc phải làn đường là xe con hay xe tải"},
    {"name": "img_0006", "assignee": "Nguyễn Bá Duy", "conflict": "Det 'bus' vs Pan 'truck'", "focus": "Xe buýt hay xe tải?"},
    {"name": "img_0028", "assignee": "Nguyễn Bá Duy", "conflict": "Det 'bicycle' vs Pan 'motorcycle'", "focus": "Xe đạp hay mô tô?"},
    {"name": "img_0036", "assignee": "Nguyễn Bá Duy", "conflict": "Det 'bed' vs Pan 'couch'", "focus": "Giường hay sofa?"},
    {"name": "img_0045", "assignee": "Nguyễn Bá Duy", "conflict": "Det 'handbag' vs Pan 'backpack'", "focus": "Túi xách hay ba lô?"},
    {"name": "img_0061", "assignee": "Hoàng Nhật Anh", "conflict": "Det 'cake' vs Pan 'donut'", "focus": "Bánh ngọt hay donut?"},
    {"name": "img_0062", "assignee": "Hoàng Nhật Anh", "conflict": "Det 'truck' vs Pan 'car'", "focus": "Xe tải hay xe con?"},
    {"name": "img_0079", "assignee": "Hoàng Nhật Anh", "conflict": "Thiếu box 'cat'", "focus": "Có con mèo to không có box?"},
    {"name": "img_0086", "assignee": "Hoàng Nhật Anh", "conflict": "Det 'chair' vs Pan 'dining table'", "focus": "Ghế hay bàn ăn?"},
    {"name": "img_0145", "assignee": "Đỗ Huy Kiên", "conflict": "Det 'couch' vs Pan 'chair'", "focus": "Sofa hay ghế tựa?"},
    {"name": "img_0146", "assignee": "Đỗ Huy Kiên", "conflict": "Det 'truck' vs Pan 'car'", "focus": "Xe tải hay xe con?"},
    {"name": "img_0169", "assignee": "Đỗ Huy Kiên", "conflict": "Det 'bus' vs Pan 'truck'", "focus": "Xe buýt hay xe tải?"},
    {"name": "img_0171", "assignee": "Đỗ Huy Kiên", "conflict": "Thiếu box 'backpack'", "focus": "Ba lô bị sót box?"},
    {"name": "img_0226", "assignee": "Nguyễn Đức Cường", "conflict": "Det 'backpack' vs Pan 'suitcase'", "focus": "Ba lô hay vali?"},
    {"name": "img_0238", "assignee": "Nguyễn Đức Cường", "conflict": "Det 'bench' vs Pan 'chair'", "focus": "Ghế dài hay ghế đơn?"},
    {"name": "img_0245", "assignee": "Nguyễn Đức Cường", "conflict": "Thiếu box 'toilet'", "focus": "Bồn cầu có box không?"},
]

cards_data = []

for item in candidates_info:
    name = item["name"]
    img_path = DELIVERY / "images" / f"{name}.jpg"
    if not img_path.is_file():
        continue
    img_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    
    # Read YOLO labels
    lbl_path = DELIVERY / "labels" / f"{name}.txt"
    det_boxes = []
    if lbl_path.is_file():
        for ln in lbl_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                c, x, y, w, h = ln.split()[:5]
                det_boxes.append({
                    "class_id": int(c),
                    "class_name": classes80[int(c)],
                    "cx": float(x),
                    "cy": float(y),
                    "w": float(w),
                    "h": float(h)
                })
    
    # Read Panoptic annotations
    pan_boxes = []
    im_obj = next((im for im in panoptic_data["images"] if Path(im["file_name"]).stem == name), None)
    if im_obj:
        ann = next((a for a in panoptic_data["annotations"] if a["image_id"] == im_obj["id"]), None)
        if ann:
            for s in ann["segments_info"]:
                cat_name = pan_cats.get(s["category_id"], "unknown")
                bx, by, bw, bh = s["bbox"]
                pan_boxes.append({
                    "cat_id": s["category_id"],
                    "cat_name": cat_name,
                    "area": s["area"],
                    "bbox": [bx, by, bw, bh],
                    "iscrowd": s.get("iscrowd", 0)
                })
    
    cards_data.append({
        "name": name,
        "assignee": item["assignee"],
        "conflict": item["conflict"],
        "focus": item["focus"],
        "img_b64": f"data:image/jpeg;base64,{img_b64}",
        "width": im_obj["width"] if im_obj else 640,
        "height": im_obj["height"] if im_obj else 480,
        "det_boxes": det_boxes,
        "pan_boxes": pan_boxes
    })

html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Preview Đề Ẩn Lab 10 - Nhóm 05</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
  header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 25px; }}
  h1 {{ margin: 0; font-size: 24px; color: #38bdf8; }}
  .badge {{ background: #0284c7; padding: 4px 10px; border-radius: 9999px; font-size: 13px; font-weight: bold; }}
  .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; }}
  .tab {{ padding: 8px 16px; border-radius: 8px; background: #1e293b; color: #94a3b8; border: 1px solid #334155; cursor: pointer; font-weight: 500; transition: all 0.2s; }}
  .tab.active, .tab:hover {{ background: #38bdf8; color: #0f172a; font-weight: bold; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(550px, 1fr)); gap: 24px; }}
  .card {{ background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }}
  .card-header {{ padding: 12px 16px; background: #0f172a; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }}
  .card-title {{ font-size: 18px; font-weight: bold; color: #f1f5f9; display: flex; gap: 10px; align-items: center; }}
  .tag {{ font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
  .tag-hung {{ background: #10b981; color: #0f172a; }}
  .tag-other {{ background: #64748b; color: #fff; }}
  .canvas-wrapper {{ position: relative; background: #000; display: flex; justify-content: center; align-items: center; min-height: 380px; }}
  canvas {{ max-width: 100%; height: auto; }}
  .card-body {{ padding: 16px; }}
  .conflict-box {{ background: #334155; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; border-left: 4px solid #f59e0b; }}
  .legend {{ display: flex; gap: 16px; font-size: 13px; margin-bottom: 12px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .color-box {{ width: 14px; height: 14px; border-radius: 3px; }}
  .controls {{ display: flex; gap: 8px; margin-top: 10px; }}
  .btn {{ padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; cursor: pointer; border: none; background: #334155; color: #f8fafc; }}
  .btn:hover {{ background: #475569; }}
  .notes-box {{ background: #090d16; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-family: monospace; font-size: 12px; color: #38bdf8; margin-top: 10px; }}
</style>
</head>
<body>

<header>
  <div>
    <h1>Preview Đề Ẩn Lab 10 — Nhóm 05</h1>
    <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Release ID: <b>lab250_62d7641abb98</b> | Bộ công cụ trực quan hóa của Phạm Mạnh Hùng</div>
  </div>
  <span class="badge">19 Ứng Viên Nghi Vấn</span>
</header>

<div class="tabs">
  <div class="tab active" onclick="filterCards('all')">Tất cả (19)</div>
  <div class="tab" onclick="filterCards('Phạm Mạnh Hùng')" style="border-color: #10b981; color: #10b981;">Ảnh của Phạm Mạnh Hùng (4)</div>
  <div class="tab" onclick="filterCards('Nguyễn Bá Duy')">Nguyễn Bá Duy (4)</div>
  <div class="tab" onclick="filterCards('Hoàng Nhật Anh')">Hoàng Nhật Anh (4)</div>
  <div class="tab" onclick="filterCards('Đỗ Huy Kiên')">Đỗ Huy Kiên (4)</div>
  <div class="tab" onclick="filterCards('Nguyễn Đức Cường')">Nguyễn Đức Cường (3)</div>
</div>

<div class="grid" id="grid"></div>

<script>
const data = {json.dumps(cards_data)};

function render() {{
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  
  data.forEach((item, idx) => {{
    const card = document.createElement("div");
    card.className = "card";
    card.setAttribute("data-assignee", item.assignee);
    const isHung = item.assignee === "Phạm Mạnh Hùng";
    
    card.innerHTML = `
      <div class="card-header">
        <div class="card-title">
          <span>${{item.name}}</span>
          <span class="tag ${{isHung ? 'tag-hung' : 'tag-other'}}">${{item.assignee}}</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8;">${{item.width}}x${{item.height}}</div>
      </div>
      <div class="canvas-wrapper">
        <canvas id="cv_${{idx}}"></canvas>
      </div>
      <div class="card-body">
        <div class="conflict-box">
          <b>Bất đồng:</b> ${{item.conflict}}<br>
          <span style="color: #cbd5e1; font-size: 13px;">👉 <b>Cần xem:</b> ${{item.focus}}</span>
        </div>
        <div class="legend">
          <div class="legend-item"><div class="color-box" style="background: #00ff66;"></div> <b>Detection (YOLO)</b></div>
          <div class="legend-item"><div class="color-box" style="background: #ff0055;"></div> <b>Panoptic</b></div>
        </div>
        <div class="notes-box">
          <b>Gợi ý ghi chú cho Duy:</b><br>
          <span id="note_${{idx}}">${{item.name}},confirmed,"mo anh ${{item.name}}: ${{item.focus}}"</span>
        </div>
      </div>
    `;
    grid.appendChild(card);
    
    // Draw canvas
    const img = new Image();
    img.src = item.img_b64;
    img.onload = () => {{
      const cv = document.getElementById(`cv_${{idx}}`);
      cv.width = item.width;
      cv.height = item.height;
      const ctx = cv.getContext("2d");
      ctx.drawImage(img, 0, 0);
      
      // Draw Detection Boxes (Green/Cyan)
      ctx.lineWidth = 3;
      item.det_boxes.forEach(b => {{
        const x = (b.cx - b.w / 2) * item.width;
        const y = (b.cy - b.h / 2) * item.height;
        const w = b.w * item.width;
        const h = b.h * item.height;
        ctx.strokeStyle = "#00ff66";
        ctx.strokeRect(x, y, w, h);
        
        ctx.fillStyle = "rgba(0, 255, 102, 0.85)";
        ctx.font = "bold 14px sans-serif";
        const text = `Det: ${{b.class_name}}`;
        const tw = ctx.measureText(text).width;
        ctx.fillRect(x, Math.max(0, y - 20), tw + 8, 20);
        ctx.fillStyle = "#000";
        ctx.fillText(text, x + 4, Math.max(15, y - 5));
      }});
      
      // Draw Panoptic Boxes (Pink/Red)
      item.pan_boxes.forEach(b => {{
        const [x, y, w, h] = b.bbox;
        ctx.strokeStyle = "#ff0055";
        ctx.setLineDash([6, 6]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
        
        ctx.fillStyle = "rgba(255, 0, 85, 0.85)";
        ctx.font = "bold 13px sans-serif";
        const text = `Pan: ${{b.cat_name}}`;
        const tw = ctx.measureText(text).width;
        ctx.fillRect(x + w - tw - 8, y + h, tw + 8, 18);
        ctx.fillStyle = "#fff";
        ctx.fillText(text, x + w - tw - 4, y + h + 14);
      }});
    }};
  }});
}}

function filterCards(name) {{
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  const cards = document.querySelectorAll(".card");
  cards.forEach(c => {{
    if (name === "all" || c.getAttribute("data-assignee") === name) {{
      c.style.display = "block";
    }} else {{
      c.style.display = "none";
    }}
  }});
}}

render();
</script>
</body>
</html>
"""

out_file = REPO_ROOT / "preview.html"
out_file.write_text(html_content, encoding="utf-8")
print(f"DONE: {out_file}")
