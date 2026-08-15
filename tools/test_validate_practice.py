"""Regression tests for the duplicate-signature comparison in validate_practice.py.

Focused on one property: an unordered candidate pool must not let an identical
exercise hide behind a different presentation order, while structures that are
graded on order must stay order-sensitive.

Usage:
    python3 tools/test_validate_practice.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_practice as vp  # noqa: E402  (same directory, dependency-free)

FAILURES = []


def check(name, ok):
    print("%-4s %s" % ("ok" if ok else "FAIL", name))
    if not ok:
        FAILURES.append(name)


def choose_blocks(cid, blocks, selected, order=None, require_order=False):
    content = {"blocks": [{"id": bid, "code": code} for bid, code in blocks]}
    if require_order:
        content["requireOrder"] = True
    sol = {"selected": list(selected)}
    if order is not None:
        sol["order"] = list(order)
    return {"id": cid, "type": "chooseBlocks", "track": "swift",
            "content": content, "solution": sol}


def reorder(cid, blocks, order):
    return {"id": cid, "type": "reorder", "track": "swift",
            "content": {"blocks": [{"id": bid, "code": code} for bid, code in blocks]},
            "solution": {"order": list(order)}}


def build_function(cid, blocks, order):
    c = reorder(cid, blocks, order)
    c["type"] = "buildFunction"
    return c


LET = ("b1", 'let name = "Yuki"')
PRINT = ("b2", 'print("Hello, " + name)')
AGE = ("b3", "let age = 20")
ASSIGN = ("b4", 'name = "Taro"')


def test_permuted_choose_blocks_is_a_duplicate():
    a = choose_blocks("practice-swift-001", [LET, PRINT, AGE, ASSIGN], ["b1", "b2"])
    # Same exercise, candidates shuffled: ids follow their own code, and the
    # selected ids are listed in the other order too.
    b = choose_blocks("practice-swift-002",
                      [("b1", AGE[1]), ("b2", PRINT[1]), ("b3", LET[1]), ("b4", ASSIGN[1])],
                      ["b2", "b3"])
    check("permuted chooseBlocks candidates share a signature",
          vp.code_signature(a) == vp.code_signature(b))

    rep = vp.Report()
    vp.duplicate_audit([a, b], rep)
    check("permuted chooseBlocks pair is reported as identical material",
          any("identical exercise material" in e for e in rep.errors))


def test_choose_blocks_with_different_answer_is_not_a_duplicate():
    a = choose_blocks("practice-swift-001", [LET, PRINT, AGE, ASSIGN], ["b1", "b2"])
    b = choose_blocks("practice-swift-002", [LET, PRINT, AGE, ASSIGN], ["b1", "b3"])
    check("chooseBlocks with a different selection stays distinct",
          vp.code_signature(a) != vp.code_signature(b))


def test_require_order_stays_order_sensitive():
    a = choose_blocks("practice-swift-001", [LET, PRINT, AGE, ASSIGN],
                      ["b1", "b2"], order=["b1", "b2"], require_order=True)
    b = choose_blocks("practice-swift-002", [LET, PRINT, AGE, ASSIGN],
                      ["b1", "b2"], order=["b2", "b1"], require_order=True)
    check("requireOrder chooseBlocks with a different order stays distinct",
          vp.code_signature(a) != vp.code_signature(b))


def test_reorder_stays_order_sensitive():
    blocks = [LET, PRINT, AGE]
    a = reorder("practice-swift-001", blocks, ["b1", "b3", "b2"])
    b = reorder("practice-swift-002", blocks, ["b3", "b1", "b2"])
    check("reorder with a different solution order stays distinct",
          vp.code_signature(a) != vp.code_signature(b))

    # The presented (deliberately wrong) block order is part of a reorder exercise.
    c = reorder("practice-swift-003", [AGE, LET, PRINT], ["b1", "b3", "b2"])
    check("reorder with a different block presentation stays distinct",
          vp.code_signature(a) != vp.code_signature(c))


def test_build_function_stays_order_sensitive():
    blocks = [LET, PRINT, AGE, ASSIGN]
    a = build_function("practice-swift-001", blocks, ["b1", "b2", "b3"])
    b = build_function("practice-swift-002", blocks, ["b3", "b2", "b1"])
    check("buildFunction with a different assembly order stays distinct",
          vp.code_signature(a) != vp.code_signature(b))


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    if FAILURES:
        print("\nFAILED: %d check(s)" % len(FAILURES))
        return 1
    print("\nOK: duplicate-signature regression checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
