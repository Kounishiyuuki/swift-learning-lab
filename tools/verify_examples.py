"""source/practice.json の detail.example を実際にコンパイル・実行し、記載した output と一致するか確認する。

    python3 tools/verify_examples.py                 # 全300問
    python3 tools/verify_examples.py practice-uikit  # ID前方一致で絞り込み

swift コマンドが必要（標準ライブラリのみ利用、パッケージ導入なし）。
UIKit / SwiftUI を import する例は macOS上で実行できないため対象外として数える。
そのため、UIKit の挙動そのものをコンパイルで検証しているわけではない。"""
import json, subprocess, sys, tempfile, os
from pathlib import Path
root = Path(__file__).resolve().parents[1]
data = json.loads((root/"source/practice.json").read_text(encoding="utf-8"))
targets = set(sys.argv[1:]) if len(sys.argv) > 1 else None
UIKIT = ("import UIKit", "import SwiftUI")
ok = fail = skipped = noexample = 0
work = Path(tempfile.mkdtemp())
for c in data["challenges"]:
    if targets and not any(c["id"].startswith(t) for t in targets):
        continue
    ex = (c.get("detail") or {}).get("example") or {}
    code, expected = ex.get("code"), ex.get("output")
    if not code:
        noexample += 1
        continue
    if any(k in code for k in UIKIT):
        skipped += 1
        print("SKIP(UI) %s" % c["id"])
        continue
    f = work/("%s.swift" % c["id"].replace("-", "_"))
    f.write_text(code, encoding="utf-8")
    r = subprocess.run(["swift", str(f)], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        fail += 1
        print("COMPILE/RUN FAIL %s\n%s" % (c["id"], (r.stderr or "").strip()[:400]))
        continue
    got = r.stdout.rstrip("\n")
    if expected is None:
        ok += 1
        continue
    if got != expected.rstrip("\n"):
        fail += 1
        print("OUTPUT MISMATCH %s\n  expected: %r\n  got     : %r" % (c["id"], expected, got))
    else:
        ok += 1
print("\nok=%d fail=%d skipped_ui=%d no_example=%d" % (ok, fail, skipped, noexample))
sys.exit(1 if fail else 0)
