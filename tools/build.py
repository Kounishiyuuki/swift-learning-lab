from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
tracks = json.loads((root / "source/content.json").read_text(encoding="utf-8"))

index_path = root / "index.html"
html = index_path.read_text(encoding="utf-8")

payload = "const DATA = " + json.dumps(tracks, ensure_ascii=False) + ";\n\nconst state"
html = re.sub(
    r"const DATA = .*?;\n\nconst state",
    lambda _: payload,
    html,
    flags=re.S,
)

index_path.write_text(html, encoding="utf-8")
print("Embedded source/content.json into index.html")
