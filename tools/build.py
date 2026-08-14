"""Build step for Swift Learning Lab.

source/content.json (knowledge) and source/practice.json (implementation
challenges) are the only manually edited content sources. This script:
  1. validates source/practice.json structurally,
  2. embeds both files into index.html (const DATA / const PRACTICE),
  3. regenerates source/<track-id>.txt for every track,
  4. regenerates source/practice.txt as a readable view of the challenge bank.

Generation is idempotent: running it twice produces no further diff.
Files without a matching track id (e.g. source/references.txt) are left alone.
"""
from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "tools"))
import validate_practice  # noqa: E402  (same directory, dependency-free)

tracks = json.loads((root / "source/content.json").read_text(encoding="utf-8"))
practice = json.loads((root / "source/practice.json").read_text(encoding="utf-8"))

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


TYPE_LABELS = {
    "reorder": "並べ替え", "fillBlank": "穴埋め", "chooseBlocks": "ブロック選択",
    "bugHunt": "バグ発見", "repair": "修正", "trace": "実行追跡", "matching": "対応づけ",
    "buildFunction": "関数組み立て", "shortCode": "記述", "testReasoning": "テスト読解",
}
LEVEL_LABELS = {1: "Lv1 ガイド", 2: "Lv2 基本", 3: "Lv3 実装", 4: "Lv4 応用"}


def render_answer(c):
    """One readable answer line per challenge type."""
    content, sol = c.get("content") or {}, c.get("solution") or {}
    blocks = {b["id"]: b["code"] for b in content.get("blocks") or []}
    t = c["type"]
    if t in ("reorder", "buildFunction") or (t == "trace" and content.get("mode") == "sequence"):
        return ["正解の並び:", "```swift", "\n".join(blocks.get(i, i) for i in sol.get("order") or []), "```"]
    if t == "chooseBlocks":
        picked = sol.get("order") or sol.get("selected") or []
        return ["使うブロック:"] + ["- %s" % blocks.get(i, i) for i in picked]
    if t == "fillBlank":
        filled = content.get("template", "")
        for k, v in (sol.get("answers") or {}).items():
            filled = filled.replace("{{%s}}" % k, v)
        return ["埋めたあと:", "```swift", filled, "```"]
    if t == "matching":
        right = {r["id"]: r["label"] for r in content.get("right") or []}
        left = {l["id"]: l["label"] for l in content.get("left") or []}
        return ["対応:"] + ["- %s → %s" % (left.get(k, k), right.get(v, v)) for k, v in (sol.get("pairs") or {}).items()]
    if t == "shortCode":
        return ["想定する書き方: %s" % (sol.get("accepted") or [""])[0]]
    if t == "bugHunt":
        line = next((l for l in content.get("lines") or [] if l["id"] == sol.get("optionId")), {})
        return ["問題のある行: %s" % line.get("code", "")]
    option = next((o for o in content.get("options") or [] if o["id"] == sol.get("optionId")), {})
    return ["正解: %s" % (option.get("code") or option.get("label") or "")]


def render_practice(data):
    """Human-readable rendering of the whole practice bank."""
    challenges = data.get("challenges") or []
    out = ["# 実装練習 (practice)\n",
           "実装練習 %d問。編集元は source/practice.json です。このTXTは生成物です.\n" % len(challenges)]
    by_track = {}
    for c in challenges:
        by_track.setdefault(c["track"], []).append(c)
    for track in tracks:
        items = by_track.get(track["id"]) or []
        if not items:
            continue
        out.append("## %s（%d問）\n" % (track["name"], len(items)))
        for c in items:
            out.append("### %s %s [%s / %s]" % (c["id"], c["title"], TYPE_LABELS.get(c["type"], c["type"]),
                                                LEVEL_LABELS.get(c["difficulty"], c["difficulty"])))
            out.append("対象レッスン: %s" % c["lessonId"])
            if c.get("seriesId"):
                out.append("シリーズ: %s (%s段階目)" % (c["seriesId"], c.get("seriesStep")))
            out.append("スキル: %s" % ", ".join(c.get("skills") or []))
            out.append("問題: %s" % c["prompt"])
            out.extend(render_answer(c))
            for i, h in enumerate(c.get("hints") or [], 1):
                out.append("ヒント%d: %s" % (i, h))
            out.append("解説: %s" % c["explanation"])
            d = c.get("detail") or {}
            if d.get("concept"):
                out.append("- 使っている考え方: %s" % d["concept"])
            for s in d.get("steps") or []:
                out.append("- 手順: %s" % s)
            if d.get("whyCorrect"):
                out.append("- 動く理由: %s" % d["whyCorrect"])
            for s in d.get("commonMistakes") or []:
                out.append("- よくある間違い: %s" % s)
            example = d.get("example") or {}
            if example.get("code"):
                out.append("- 関連例:")
                out.append("```swift")
                out.append(example["code"])
                out.append("```")
                if example.get("output"):
                    out.append("- 関連例の出力: %s" % example["output"])
                if example.get("explanation"):
                    out.append("- 関連例の説明: %s" % example["explanation"])
            if d.get("takeaway"):
                out.append("- 覚えておくこと: %s" % d["takeaway"])
            out.append("")
        out.append("---\n")
    return "\n".join(out)


report, _ = validate_practice.validate(practice, strict=True)
if report.errors:
    for e in report.errors[:40]:
        print("ERROR %s" % e)
    raise SystemExit("source/practice.json is invalid: %d error(s). Build aborted." % len(report.errors))

index_path = root / "index.html"
html = index_path.read_text(encoding="utf-8")
payload = ("const DATA = " + json.dumps(tracks, ensure_ascii=False) + ";\n\n"
           "const PRACTICE = " + json.dumps(practice, ensure_ascii=False) + ";\n\nconst state")
html = re.sub(r"const DATA = .*?;\n\nconst state", lambda _: payload, html, flags=re.S)
embedded = write_if_changed(index_path, html)

written = []
for track in tracks:
    path = root / ("source/%s.txt" % track["id"])
    if write_if_changed(path, render_track(track)):
        written.append(path.name)
if write_if_changed(root / "source/practice.txt", render_practice(practice)):
    written.append("practice.txt")

print("Validated source/practice.json: %d challenge(s)" %
      len(practice.get("challenges") or []))
print("Embedded content.json + practice.json into index.html" + ("" if embedded else " (unchanged)"))
print("Regenerated %d file(s): %s" % (len(written), ", ".join(written) if written else "none (all up to date)"))
