"""Build step for Swift Learning Lab.

source/content.json is the only manually edited content source. This script:
  1. embeds content.json into index.html (const DATA = ...),
  2. regenerates source/<track-id>.txt for every track from the same data.

Generation is idempotent: running it twice produces no further diff.
Files without a matching track id (e.g. source/references.txt) are left alone.
"""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
tracks = json.loads((root / "source/content.json").read_text(encoding="utf-8"))

INTRO = "このファイルは人が読みやすい教材原本です。構造化データは content.json、完成版は index.html です."
LETTERS = "ABCD"


def render_track(track):
    """Human-readable rendering of one track. The single source of TXT format."""
    out = ["# %s\n" % track["name"], "%s\n" % track["description"], "%s\n" % INTRO]
    for i, lesson in enumerate(track["lessons"], 1):
        out.append("## %02d. %s [%s]\n" % (i, lesson["title"], lesson["level"]))
        out.append("概要: %s" % lesson["summary"])
        out.append("考え方: %s\n" % lesson["mental"])
        out.append("重要ポイント:")
        out.extend("- %s" % p for p in lesson["points"])
        out.append("")
        out.append("コード:")
        out.append("```swift")
        out.append(lesson["code"])
        out.append("```\n")
        out.append("なぜ重要か: %s" % lesson["why"])
        out.append("注意: %s\n" % lesson["pitfall"])
        out.append("確認問題:")
        for n, q in enumerate(lesson["questions"], 1):
            out.append("Q%d. %s [%s]" % (n, q["prompt"], q["difficulty"]))
            out.append("```swift")
            out.append(q["code"])
            out.append("```")
            out.extend("%s. %s" % (LETTERS[j], c) for j, c in enumerate(q["choices"]))
            out.append("正解: %s" % LETTERS[q["answer"]])
            out.append("解説: %s\n" % q["explanation"])
            out.extend(render_detail(q.get("detail")))
        out.append("---\n")
    return "\n".join(out)


def render_detail(detail):
    """Optional rich explanation. Every field is optional; skip what is absent."""
    if not detail:
        return []
    out = ["詳しい解説:"]
    if detail.get("concept"):
        out.append("- 用語・考え方: %s" % detail["concept"])
    for step in detail.get("steps") or []:
        out.append("- コードの流れ: %s" % step)
    if detail.get("whyCorrect"):
        out.append("- 正解になる理由: %s" % detail["whyCorrect"])
    for other in detail.get("otherChoices") or []:
        out.append("- 他の選択肢 %s: %s" % (other.get("choice", ""), other.get("reason", "")))
    example = detail.get("example") or {}
    if example.get("code"):
        out.append("- 関連例:")
        out.append("```swift")
        out.append(example["code"])
        out.append("```")
    if example.get("output"):
        out.append("- 関連例の出力: %s" % example["output"])
    if example.get("explanation"):
        out.append("- 関連例の説明: %s" % example["explanation"])
    if detail.get("takeaway"):
        out.append("- 覚えておくこと: %s" % detail["takeaway"])
    out.append("")
    return out


def write_if_changed(path, text):
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


index_path = root / "index.html"
html = index_path.read_text(encoding="utf-8")
payload = "const DATA = " + json.dumps(tracks, ensure_ascii=False) + ";\n\nconst state"
html = re.sub(r"const DATA = .*?;\n\nconst state", lambda _: payload, html, flags=re.S)
embedded = write_if_changed(index_path, html)

written = []
for track in tracks:
    path = root / ("source/%s.txt" % track["id"])
    if write_if_changed(path, render_track(track)):
        written.append(path.name)

print("Embedded source/content.json into index.html" + ("" if embedded else " (unchanged)"))
print("Regenerated %d track file(s): %s" % (len(written), ", ".join(written) if written else "none (all up to date)"))
