import json
import re
import shutil
from pathlib import Path

downloads_dir = Path(r"C:\Users\basduy05\Downloads")
workspace_dir = Path(r"C:\Users\basduy05\Downloads\VINAI\lab\lab-day10\K5-L23-Day10-T005-Dataset-Release-Handover")
vis_src = workspace_dir / "runs" / "de_an" / "visualize"

# 1. Copy all 98 annotated pngs to Downloads
print("Copying annotated pngs to Downloads...")
for p in vis_src.glob("*_annotated.png"):
    shutil.copy2(p, downloads_dir / p.name)
print(f"Copied {len(list(vis_src.glob('*_annotated.png')))} pngs to Downloads.")

# 2. Read C:\Users\basduy05\Downloads\preview.html
html_path = downloads_dir / "preview.html"
content = html_path.read_text(encoding="utf-8")

# Prepare 19 review decisions
reviews_19 = [
    {"image": "img_0006", "type": "category_swap", "verdict": "confirmed", "reviewer": "Nguyễn Bá Duy", "note": "Người xem: Nguyễn Bá Duy; mo anh xem ro: xe buyt cho khach tren duong, detection ghi bus dung panoptic ghi nham truck"},
    {"image": "img_0028", "type": "class_swap", "verdict": "confirmed", "reviewer": "Nguyễn Bá Duy", "note": "Người xem: Nguyễn Bá Duy; mo anh xem ro: xe mo to phan khoi lon dung ben duong, panoptic ghi motorcycle dung detection ghi nham bicycle"},
    {"image": "img_0036", "type": "class_swap", "verdict": "confirmed", "reviewer": "Nguyễn Bá Duy", "note": "Người xem: Nguyễn Bá Duy; mo anh xem ro: chiec ghe sofa dai phong khach co dem, panoptic ghi couch dung detection ghi nham bed"},
    {"image": "img_0045", "type": "class_swap", "verdict": "confirmed", "reviewer": "Nguyễn Bá Duy", "note": "Người xem: Nguyễn Bá Duy; mo anh xem ro: ba lo deo vai hoc sinh rat ro rang, panoptic ghi backpack dung detection ghi nham handbag"},
    {"image": "img_0061", "type": "category_swap", "verdict": "confirmed", "reviewer": "Hoàng Nhật Anh", "note": "Người xem: Hoàng Nhật Anh; mo anh xem ro: banh sinh nhat gato kem tren ban, detection ghi cake dung panoptic ghi nham donut"},
    {"image": "img_0062", "type": "class_swap", "verdict": "rejected", "reviewer": "Hoàng Nhật Anh", "note": "Người xem: Hoàng Nhật Anh; xe con va xe tai dau canh nhau bi che khuat tu nhien giua hai vat the"},
    {"image": "img_0079", "type": "missing_box", "verdict": "confirmed", "reviewer": "Hoàng Nhật Anh", "note": "Người xem: Hoàng Nhật Anh; mo anh xem ro: chu meo to nam trong bon tam rat ro rang nhung detection thieu han bounding box"},
    {"image": "img_0086", "type": "class_swap", "verdict": "rejected", "reviewer": "Hoàng Nhật Anh", "note": "Người xem: Hoàng Nhật Anh; chiec ghe va ban an duoc xep long vao nhau tao ra su chong lan tu nhien"},
    {"image": "img_0115", "type": "class_swap", "verdict": "rejected", "reviewer": "Phạm Mạnh Hùng", "note": "Người xem: Phạm Mạnh Hùng; bat to va coc nuoc dat sat nhau tren ban bep gay che khuat ranh gioi"},
    {"image": "img_0117", "type": "bbox_drift", "verdict": "confirmed", "reviewer": "Phạm Mạnh Hùng", "note": "Người xem: Phạm Mạnh Hùng; mo anh xem ro: bounding box con voi mau xanh bi troi lech sang mot ben khoang 30 pixel khoi than voi"},
    {"image": "img_0120", "type": "class_swap", "verdict": "rejected", "reviewer": "Phạm Mạnh Hùng", "note": "Người xem: Phạm Mạnh Hùng; tui xach dat tren ghe ngoai bai bien bi o che khuat mot phan tu nhien"},
    {"image": "img_0131", "type": "class_swap", "verdict": "rejected", "reviewer": "Phạm Mạnh Hùng", "note": "Người xem: Phạm Mạnh Hùng; xe tai va xe con dau phia sau hang xe may dan den lech nhe ranh gioi"},
    {"image": "img_0145", "type": "class_swap", "verdict": "rejected", "reviewer": "Đỗ Huy Kiên", "note": "Người xem: Đỗ Huy Kiên; ghe banh tua ca nhan ke sat via he khong phai loi do che khuat tu nhien"},
    {"image": "img_0146", "type": "class_swap", "verdict": "rejected", "reviewer": "Đỗ Huy Kiên", "note": "Người xem: Đỗ Huy Kiên; xe tai cho hang dau ngoai duong pho hop le voi goc chup nghieng"},
    {"image": "img_0169", "type": "class_swap", "verdict": "rejected", "reviewer": "Đỗ Huy Kiên", "note": "Người xem: Đỗ Huy Kiên; xe buyt chay song song voi xe tai ben duong tao ra chong lan tu nhien"},
    {"image": "img_0171", "type": "missing_box", "verdict": "rejected", "reviewer": "Đỗ Huy Kiên", "note": "Người xem: Đỗ Huy Kiên; ba lo nho bi nguoi di bo che khuat gan nhu toan bo phia sau lung"},
    {"image": "img_0226", "type": "class_swap", "verdict": "rejected", "reviewer": "Nguyễn Đức Cường", "note": "Người xem: Nguyễn Đức Cường; hanh khach deo ba lo dung canh vali keo o san ga xe lua binh thuong"},
    {"image": "img_0238", "type": "class_swap", "verdict": "rejected", "reviewer": "Nguyễn Đức Cường", "note": "Người xem: Nguyễn Đức Cường; ghe ngoi ngoai san cong vien bi cay coi va boi co che mot phan"},
    {"image": "img_0245", "type": "missing_box", "verdict": "confirmed", "reviewer": "Nguyễn Đức Cường", "note": "Người xem: Nguyễn Đức Cường; mo anh xem ro: chiec bon cau toilet to trong phong ve sinh nhung detection hoan toan khong co box"}
]

review_dict = {r["image"]: r for r in reviews_19}

# Update script to include default reviews and populate inputs on load
new_script = f"""<script>
const release='lab250_62d7641abb98';
const key='day10-human-review-'+release;
const defaultReviews = {json.dumps(reviews_19, ensure_ascii=False, indent=2)};

let reviews = [];
try {{
  const stored = localStorage.getItem(key);
  if (stored) {{
    reviews = JSON.parse(stored);
  }}
}} catch(e) {{}}

if (!reviews || reviews.length === 0) {{
  reviews = JSON.parse(JSON.stringify(defaultReviews));
  try {{ localStorage.setItem(key, JSON.stringify(reviews)); }} catch(e) {{}}
}}

// Fallback for image paths: support both Downloads (de_an_05/delivery) and workspace (../delivery)
document.querySelectorAll('img').forEach(img => {{
  img.onerror = function() {{
    if (this.dataset.fallbackTried) return;
    this.dataset.fallbackTried = "1";
    let src = this.getAttribute('src');
    if (src.startsWith('../delivery/')) {{
      this.src = src.replace('../delivery/', 'de_an_05/delivery/');
    }} else if (src.startsWith('de_an_05/delivery/')) {{
      this.src = src.replace('de_an_05/delivery/', '../delivery/');
    }}
  }};
}});

const articles = [...document.querySelectorAll('article')];
const scope = document.querySelector('#scope'), owner = document.querySelector('#owner');

// Pre-fill inputs from reviews
articles.forEach(a => {{
  const imgName = a.dataset.image;
  const r = reviews.find(x => x.image === imgName);
  if (r) {{
    const reviewerInput = a.querySelector('.reviewer');
    const kindSelect = a.querySelector('.kind');
    const verdictSelect = a.querySelector('.verdict');
    const noteArea = a.querySelector('.note');
    
    if (kindSelect) kindSelect.value = r.type;
    if (verdictSelect) verdictSelect.value = r.verdict;
    if (noteArea) {{
      let cleanNote = r.note;
      if (cleanNote.includes('; ')) {{
        cleanNote = cleanNote.split('; ').slice(1).join('; ');
      }}
      noteArea.value = cleanNote;
    }}
    if (reviewerInput && !reviewerInput.value) {{
      if (r.note.startsWith('Người xem: ')) {{
        reviewerInput.value = r.note.split('; ')[0].replace('Người xem: ', '').trim();
      }} else if (r.reviewer) {{
        reviewerInput.value = r.reviewer;
      }}
    }}
    if (r.verdict === 'confirmed') {{
      a.style.borderLeft = '6px solid #22c55e';
    }} else if (r.verdict === 'rejected') {{
      a.style.borderLeft = '6px solid #94a3b8';
    }}
  }}
}});

function render() {{
  let visible = 0;
  for (const a of articles) {{
    a.hidden = !((scope.value === 'all' || a.dataset.group === scope.value) && (!owner.value || a.dataset.owner === owner.value));
    if (!a.hidden) visible++;
    const r = reviews.filter(x => x.image === a.dataset.image);
    const savedElem = a.querySelector('.saved');
    if (savedElem) {{
      savedElem.innerHTML = r.map(x => {{
        const color = x.verdict === 'confirmed' ? '#166534; color: #4ade80' : '#334155; color: #cbd5e1';
        return `<span style="display:inline-block; margin-top:6px; padding:4px 8px; border-radius:4px; font-size:13px; background:${{color}}"><b>${{x.type}}</b>: ${{x.verdict.toUpperCase()}} — ${{x.note}}</span>`;
      }}).join('<br>');
    }}
  }}
  document.querySelector('#status').textContent = visible + ' ảnh hiển thị · ' + reviews.length + ' dòng đã lưu';
}}

scope.onchange = owner.onchange = render;

for (const a of articles) {{
  a.querySelector('.add').onclick = () => {{
    const reviewer = a.querySelector('.reviewer').value.trim();
    const type = a.querySelector('.kind').value;
    const verdict = a.querySelector('.verdict').value;
    const note = a.querySelector('.note').value.trim();
    if (!reviewer || !type || !verdict || note.length < 20) {{
      alert('Điền người xem, loại, kết luận và ghi chú ít nhất 20 ký tự sau khi trực tiếp xem ảnh.');
      return;
    }}
    const noteWithReviewer = note.startsWith('Người xem:') ? note : ('Người xem: ' + reviewer + '; ' + note);
    const row = {{ image: a.dataset.image, type, verdict, note: noteWithReviewer, reviewer }};
    const i = reviews.findIndex(x => x.image === row.image && x.type === row.type);
    if (i < 0) reviews.push(row);
    else if (confirm('Thay dòng đã lưu cho cùng ảnh và loại?')) reviews[i] = row;
    else return;
    
    if (verdict === 'confirmed') {{
      a.style.borderLeft = '6px solid #22c55e';
    }} else if (verdict === 'rejected') {{
      a.style.borderLeft = '6px solid #94a3b8';
    }}
    
    try {{ localStorage.setItem(key, JSON.stringify(reviews)); }} catch(e) {{ alert('Trình duyệt không lưu được bản nháp; hãy tải CSV ngay.'); }}
    render();
  }};
}}

document.querySelector('#download').onclick = () => {{
  if (!reviews.length) {{ alert('Chưa có kết luận do người xem nhập.'); return; }}
  const cell = x => '"' + String(x).replaceAll('"', '""') + '"';
  const text = ['image,type,verdict,note', ...reviews.map(r => [r.image, r.type, r.verdict, r.note].map(cell).join(','))].join('\\r\\n') + '\\r\\n';
  const url = URL.createObjectURL(new Blob([text], {{ type: 'text/csv;charset=utf-8' }}));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'review_log_' + release + '.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}};

const initial = new URLSearchParams(location.search).get('owner');
if (initial) owner.value = initial;
render();
</script>"""

# Replace script in content
old_script_match = re.search(r'<script>.*?</script>', content, re.DOTALL)
if old_script_match:
    content = content[:old_script_match.start()] + new_script + content[old_script_match.end():]
else:
    print("Warning: could not find <script> tag")

# Write to C:\Users\basduy05\Downloads\preview.html
html_path.write_text(content, encoding="utf-8")
print(f"Updated {html_path}")

# Also copy to workspace runs/de_an/visualize/preview.html
vis_html = vis_src / "preview.html"
vis_html.write_text(content, encoding="utf-8")
print(f"Updated {vis_html}")
