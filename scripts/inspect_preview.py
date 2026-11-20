import re
from pathlib import Path

html_path = Path(r"C:\Users\basduy05\Downloads\preview.html")
content = html_path.read_text(encoding="utf-8")

planned = re.findall(r'<article data-image="([^"]+)" data-owner="([^"]+)" data-group="planned">', content)
print(f"Planned count: {len(planned)}")
for img, owner in planned:
    print(f"  {img}: {owner}")
