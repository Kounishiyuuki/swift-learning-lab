"""Structural validation for source/practice.json (実装練習の300問).

The practice bank is large enough that structural mistakes cannot be caught by
reading. This tool is a permanent part of the repository and is also imported by
tools/build.py, so a broken bank can never be embedded into index.html.

Usage:
    python3 tools/validate_practice.py                # strict: expects the full bank
    python3 tools/validate_practice.py --partial      # skip count/balance checks
    python3 tools/validate_practice.py --audit out.json  # write duplicate audit

Dependency-free: standard library only.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

TRACK_COUNTS = {
    "starter": 42, "swift": 84, "foundation": 42, "concurrency": 36,
    "development": 42, "swiftui": 27, "uikit": 27,
}
TOTAL = 300

# The type minimums requested for v0.5.0 add up to exactly 300, so they are the
# exact expected distribution rather than a lower bound.
TYPE_COUNTS = {
    "reorder": 35, "fillBlank": 45, "chooseBlocks": 30, "bugHunt": 35,
    "repair": 35, "trace": 30, "matching": 20, "buildFunction": 30,
    "shortCode": 20, "testReasoning": 20,
}
TYPES = set(TYPE_COUNTS)
SKILLS = {
    "syntax", "controlFlow", "functions", "optional", "collections", "types",
    "protocols", "errors", "debugging", "testing", "foundation", "concurrency",
    "memory", "swiftui", "uikit", "architecture",
}
DIFFICULTIES = {1, 2, 3, 4}
ID_RE = re.compile(r"^practice-([a-z]+)-(\d{3})$")

MIN_EXPLANATION = 60
MIN_HINT = 10
MIN_CONCEPT = 25
MIN_WHY = 30
MIN_TAKEAWAY = 12
# Cross-track exercises this similar are printed for a human to judge, not failed.
CROSS_TRACK_REPORT = 0.42


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, cid, msg):
        self.errors.append("%s: %s" % (cid, msg))

    def warn(self, cid, msg):
        self.warnings.append("%s: %s" % (cid, msg))


def load_lesson_ids():
    tracks = json.loads((ROOT / "source/content.json").read_text(encoding="utf-8"))
    return {t["id"]: {l["id"] for l in t["lessons"]} for t in tracks}


def block_ids(content):
    return [b.get("id") for b in content.get("blocks") or []]


def check_common(c, rep, lesson_ids):
    cid = c.get("id", "<no id>")
    for field in ("id", "track", "lessonId", "type", "difficulty", "title",
                  "prompt", "skills", "content", "solution", "hints",
                  "explanation", "detail"):
        if c.get(field) in (None, "", [], {}):
            rep.error(cid, "missing required field: %s" % field)
    m = ID_RE.match(str(c.get("id", "")))
    if not m:
        rep.error(cid, "id must look like practice-<track>-000")
    elif m.group(1) != c.get("track"):
        rep.error(cid, "id prefix does not match track %r" % c.get("track"))
    if c.get("track") not in TRACK_COUNTS:
        rep.error(cid, "unknown track %r" % c.get("track"))
    elif c.get("lessonId") not in lesson_ids.get(c["track"], set()):
        rep.error(cid, "lessonId %r does not exist in content.json" % c.get("lessonId"))
    if c.get("type") not in TYPES:
        rep.error(cid, "unknown type %r" % c.get("type"))
    if c.get("difficulty") not in DIFFICULTIES:
        rep.error(cid, "difficulty must be 1-4, got %r" % c.get("difficulty"))
    skills = c.get("skills") or []
    if not skills:
        rep.error(cid, "at least one skill tag is required")
    for s in skills:
        if s not in SKILLS:
            rep.error(cid, "unknown skill tag %r" % s)
    if any(skills.count(s) > 1 for s in skills):
        rep.error(cid, "skill tags must be unique")

    hints = c.get("hints") or []
    if len(hints) != 3:
        rep.error(cid, "exactly 3 hints required, got %d" % len(hints))
    for i, h in enumerate(hints, 1):
        if not isinstance(h, str) or len(h.strip()) < MIN_HINT:
            rep.error(cid, "hint %d is too short to be useful" % i)
    if len(set(hints)) != len(hints):
        rep.error(cid, "hints must differ from each other")

    if len((c.get("explanation") or "").strip()) < MIN_EXPLANATION:
        rep.error(cid, "explanation is shorter than %d chars" % MIN_EXPLANATION)

    d = c.get("detail") or {}
    if len((d.get("concept") or "").strip()) < MIN_CONCEPT:
        rep.error(cid, "detail.concept is missing or too short")
    if len(d.get("steps") or []) < 2:
        rep.error(cid, "detail.steps needs at least 2 reasoning steps")
    for s in d.get("steps") or []:
        if len(str(s).strip()) < 10:
            rep.error(cid, "detail.steps entry is too short")
    if len((d.get("whyCorrect") or "").strip()) < MIN_WHY:
        rep.error(cid, "detail.whyCorrect is missing or too short")
    if len(d.get("commonMistakes") or []) < 1:
        rep.error(cid, "detail.commonMistakes needs at least 1 entry")
    for s in d.get("commonMistakes") or []:
        if len(str(s).strip()) < 12:
            rep.error(cid, "detail.commonMistakes entry is too short")
    if len((d.get("takeaway") or "").strip()) < MIN_TAKEAWAY:
        rep.error(cid, "detail.takeaway is missing or too short")
    ex = d.get("example") or {}
    if ex and not (ex.get("code") and ex.get("explanation")):
        rep.error(cid, "detail.example needs both code and explanation")


def check_blocks(c, rep, minimum, distractors_required):
    cid = c["id"]
    content = c.get("content") or {}
    ids = block_ids(content)
    if len(ids) < minimum:
        rep.error(cid, "needs at least %d blocks, got %d" % (minimum, len(ids)))
    if len(set(ids)) != len(ids):
        rep.error(cid, "block ids must be unique")
    for b in content.get("blocks") or []:
        if not str(b.get("code", "")).strip():
            rep.error(cid, "block %r has empty code" % b.get("id"))
    order = (c.get("solution") or {}).get("order") or []
    for bid in order:
        if bid not in ids:
            rep.error(cid, "solution.order references unknown block %r" % bid)
    if len(set(order)) != len(order):
        rep.error(cid, "solution.order repeats a block")
    if distractors_required and len(order) >= len(ids):
        rep.error(cid, "needs at least one distractor block that is not used")
    return ids, order


def check_choice(c, rep, key="options", minimum=3):
    cid = c["id"]
    content = c.get("content") or {}
    options = content.get(key) or []
    ids = [o.get("id") for o in options]
    if len(options) < minimum:
        rep.error(cid, "%s needs at least %d entries" % (key, minimum))
    if len(set(ids)) != len(ids):
        rep.error(cid, "%s ids must be unique" % key)
    for o in options:
        if not (str(o.get("code", "")).strip() or str(o.get("label", "")).strip()):
            rep.error(cid, "option %r has no code and no label" % o.get("id"))
    answer = (c.get("solution") or {}).get("optionId")
    if answer not in ids:
        rep.error(cid, "solution.optionId %r is not one of the %s" % (answer, key))


def check_by_type(c, rep):
    cid = c["id"]
    t = c.get("type")
    content = c.get("content") or {}
    sol = c.get("solution") or {}
    if t == "reorder":
        ids, order = check_blocks(c, rep, 3, False)
        if sorted(order) != sorted(ids):
            rep.error(cid, "solution.order must be a permutation of every block")
        elif order == ids:
            rep.error(cid, "blocks are already presented in the correct order")
    elif t == "buildFunction":
        ids, order = check_blocks(c, rep, 4, True)
        if len(order) < 3:
            rep.error(cid, "buildFunction should assemble at least 3 blocks")
    elif t == "chooseBlocks":
        ids = block_ids(content)
        selected = sol.get("order") if content.get("requireOrder") else (sol.get("selected") or sol.get("order"))
        selected = selected or []
        if len(ids) < 4:
            rep.error(cid, "chooseBlocks needs at least 4 candidate blocks")
        if len(set(ids)) != len(ids):
            rep.error(cid, "block ids must be unique")
        for b in content.get("blocks") or []:
            if not str(b.get("code", "")).strip():
                rep.error(cid, "block %r has empty code" % b.get("id"))
        for bid in selected:
            if bid not in ids:
                rep.error(cid, "solution references unknown block %r" % bid)
        if len(set(selected)) != len(selected):
            rep.error(cid, "solution repeats a selected block")
        if not selected:
            rep.error(cid, "solution needs the selected blocks")
        if len(selected) >= len(ids):
            rep.error(cid, "needs at least one unnecessary block")
        if content.get("requireOrder") and not sol.get("order"):
            rep.error(cid, "requireOrder is set but solution.order is missing")
    elif t == "trace":
        if content.get("mode") == "sequence":
            ids, order = check_blocks(c, rep, 3, False)
            if sorted(order) != sorted(ids):
                rep.error(cid, "solution.order must be a permutation of every state block")
            elif order == ids:
                rep.error(cid, "state blocks are already in the correct order")
        else:
            if not content.get("code"):
                rep.error(cid, "trace needs the code being traced")
            check_choice(c, rep)
    elif t == "fillBlank":
        template = content.get("template") or ""
        blanks = content.get("blanks") or []
        answers = sol.get("answers") or {}
        if not template:
            rep.error(cid, "content.template is required")
        placeholders = re.findall(r"\{\{([^}]+)\}\}", template)
        if not placeholders:
            rep.error(cid, "template has no {{blank}} placeholder")
        if sorted(placeholders) != sorted(b.get("id") for b in blanks):
            rep.error(cid, "template placeholders and content.blanks do not match")
        if sorted(answers) != sorted(b.get("id") for b in blanks):
            rep.error(cid, "solution.answers does not cover exactly the blanks")
        for b in blanks:
            options = b.get("options") or []
            if len(options) < 3:
                rep.error(cid, "blank %r needs at least 3 options" % b.get("id"))
            if len(set(options)) != len(options):
                rep.error(cid, "blank %r has duplicate options" % b.get("id"))
            if answers.get(b.get("id")) not in options:
                rep.error(cid, "answer for blank %r is not among its options" % b.get("id"))
    elif t == "bugHunt":
        lines = content.get("lines") or []
        ids = [l.get("id") for l in lines]
        if len(lines) < 3:
            rep.error(cid, "bugHunt needs at least 3 code lines")
        if len(set(ids)) != len(ids):
            rep.error(cid, "line ids must be unique")
        for line in lines:
            if not str(line.get("code", "")).strip():
                rep.error(cid, "line %r has empty code" % line.get("id"))
        if sol.get("optionId") not in ids:
            rep.error(cid, "solution.optionId is not one of the lines")
        if not sol.get("fixedCode"):
            rep.error(cid, "bugHunt must show the corrected code in solution.fixedCode")
    elif t == "repair":
        if not content.get("code"):
            rep.error(cid, "repair needs the broken code in content.code")
        check_choice(c, rep)
        if not sol.get("fixedCode"):
            rep.error(cid, "repair must show the corrected code in solution.fixedCode")
    elif t == "matching":
        left = content.get("left") or []
        right = content.get("right") or []
        pairs = sol.get("pairs") or {}
        lids = [x.get("id") for x in left]
        rids = [x.get("id") for x in right]
        if len(left) < 3:
            rep.error(cid, "matching needs at least 3 left items")
        if len(right) < len(left):
            rep.error(cid, "matching needs at least as many right items as left items")
        if len(set(lids)) != len(lids) or len(set(rids)) != len(rids):
            rep.error(cid, "matching ids must be unique")
        for side, items in (("left", left), ("right", right)):
            for item in items:
                if not str(item.get("label", "")).strip():
                    rep.error(cid, "matching %s item %r has empty label" %
                              (side, item.get("id")))
        if sorted(pairs) != sorted(lids):
            rep.error(cid, "solution.pairs must cover exactly the left items")
        for k, v in pairs.items():
            if v not in rids:
                rep.error(cid, "pair %r points at unknown right item %r" % (k, v))
        if len(set(pairs.values())) != len(pairs):
            rep.error(cid, "two left items map to the same right item (ambiguous)")
    elif t == "shortCode":
        accepted = sol.get("accepted") or []
        if not accepted:
            rep.error(cid, "shortCode needs solution.accepted")
        norm = [normalize_code(a) for a in accepted]
        if any(not a for a in norm):
            rep.error(cid, "shortCode accepted answer is empty")
        if len(set(norm)) != len(norm):
            rep.error(cid, "accepted answers duplicate after normalization")
        if len(norm) and max(len(a) for a in norm) > 120:
            rep.error(cid, "shortCode answer is too long to check without a compiler")
    elif t == "testReasoning":
        if not content.get("requirement"):
            rep.error(cid, "testReasoning needs content.requirement")
        if len(content.get("tests") or []) < 2:
            rep.error(cid, "testReasoning needs at least 2 visible test cases")
        for i, case in enumerate(content.get("tests") or [], 1):
            if not isinstance(case, dict):
                rep.error(cid, "test case %d must be an object" % i)
                continue
            for field in ("name", "input", "expected", "result"):
                if not isinstance(case.get(field), str) or not case[field].strip():
                    rep.error(cid, "test case %d needs a meaningful %s" % (i, field))
        check_choice(c, rep)


def canonical_answer(c):
    """The literal answer text, used for hint leakage checks."""
    t = c.get("type")
    sol = c.get("solution") or {}
    if t == "fillBlank":
        return [str(v) for v in (sol.get("answers") or {}).values()]
    if t == "shortCode":
        return [str(a) for a in (sol.get("accepted") or [])]
    return []


def check_leakage(c, rep):
    """Hint 1 must point at the idea, not hand over the answer."""
    hints = c.get("hints") or []
    if not hints:
        return
    first = hints[0]
    for answer in canonical_answer(c):
        a = normalize_code(answer)
        if len(a) >= 4 and a in normalize_code(first):
            rep.error(c["id"], "hint 1 already contains the literal answer %r" % answer)


def normalize_code(text):
    lines = [l.strip() for l in str(text).replace("\r\n", "\n").split("\n")]
    return re.sub(r"[ \t]+", " ", "\n".join(l for l in lines if l))


def trigrams(text):
    t = re.sub(r"\s+", " ", text)
    return {t[i:i + 3] for i in range(max(len(t) - 2, 1))}


def code_signature(c):
    """The code a learner actually reasons about, plus the answer.

    Wording can differ while the exercise is the same, so title/prompt similarity
    alone misses duplicated exercises. This signature compares the material itself.
    """
    content = c.get("content") or {}
    parts = [str(content.get("code") or ""), str(content.get("template") or ""),
             str(content.get("context") or ""), str(content.get("requirement") or "")]
    parts += [str(b.get("code", "")) for b in content.get("blocks") or []]
    parts += [str(l.get("code", "")) for l in content.get("lines") or []]
    parts += [str(o.get("code", "") or o.get("label", "")) for o in content.get("options") or []]
    parts += [str(x.get("label", "")) for x in (content.get("left") or []) + (content.get("right") or [])]
    parts.append(json.dumps(c.get("solution") or {}, sort_keys=True, ensure_ascii=False))
    return normalize_code("\n".join(p for p in parts if p.strip()))


def duplicate_audit(challenges, rep):
    """Exact duplicates are errors; high-similarity pairs are reported for review."""
    pairs = []
    seen = {}
    for c in challenges:
        key = normalize_code(c.get("title", "")) + "|" + normalize_code(c.get("prompt", ""))
        if key in seen:
            rep.error(c["id"], "duplicate title+prompt with %s" % seen[key])
        seen[key] = c["id"]

    # Identical exercise material is a defect wherever it appears, including across
    # tracks, where the title/prompt sweep below never compares the two.
    by_code = {}
    for c in challenges:
        sig = code_signature(c)
        if not sig:
            continue
        if sig in by_code:
            rep.error(c["id"], "identical exercise material and solution as %s" % by_code[sig])
        by_code[sig] = c["id"]

    # Cross-track near duplicates are reported, never auto-failed: a shared idea
    # taught at two levels can be legitimate, so a human decides. The threshold is
    # deliberately low (the same-idea pair found in review scored 0.43 after rewording),
    # which costs a handful of pairs to eyeball rather than hiding real repeats.
    code_grams = [(c, trigrams(code_signature(c))) for c in challenges]
    for i in range(len(code_grams)):
        ci, gi = code_grams[i]
        for j in range(i + 1, len(code_grams)):
            cj, gj = code_grams[j]
            if ci.get("track") == cj.get("track"):
                continue
            score = len(gi & gj) / (len(gi | gj) or 1)
            if score >= CROSS_TRACK_REPORT:
                pairs.append({"a": ci["id"], "b": cj["id"], "score": round(score, 3),
                              "track": "%s/%s" % (ci.get("track"), cj.get("track")),
                              "kind": "cross-track-material",
                              "aTitle": ci.get("title"), "bTitle": cj.get("title")})

    grams = [(c, trigrams(str(c.get("title", "")) + " " + str(c.get("prompt", "")))) for c in challenges]
    by_track = {}
    for c, g in grams:
        by_track.setdefault(c.get("track"), []).append((c, g))
    for track, items in by_track.items():
        for i in range(len(items)):
            ci, gi = items[i]
            for j in range(i + 1, len(items)):
                cj, gj = items[j]
                inter = len(gi & gj)
                union = len(gi | gj) or 1
                score = inter / union
                if score >= 0.62:
                    pairs.append({"a": ci["id"], "b": cj["id"], "score": round(score, 3),
                                  "track": track, "aTitle": ci.get("title"), "bTitle": cj.get("title")})
                    if score >= 0.85:
                        rep.error(ci["id"], "near-duplicate of %s (similarity %.2f)" % (cj["id"], score))
    pairs.sort(key=lambda p: -p["score"])
    return pairs


def validate(data, strict=True):
    rep = Report()
    lesson_ids = load_lesson_ids()
    challenges = data.get("challenges") if isinstance(data, dict) else None
    if challenges is None:
        rep.error("<root>", "practice.json must be an object with a challenges array")
        return rep, []
    if data.get("version") != 1:
        rep.error("<root>", "unsupported practice.json version %r" % data.get("version"))

    ids = [c.get("id") for c in challenges]
    for cid, count in {i: ids.count(i) for i in ids}.items():
        if count > 1:
            rep.error(str(cid), "duplicate challenge id (%d times)" % count)

    for c in challenges:
        check_common(c, rep, lesson_ids)
        if c.get("type") in TYPES:
            check_by_type(c, rep)
        check_leakage(c, rep)

    for c in challenges:
        sid = c.get("seriesId")
        step = c.get("seriesStep")
        if sid is not None and (not isinstance(sid, str) or not sid.strip()):
            rep.error(c.get("id", "?"), "seriesId must be a non-empty string")
        if sid and (not isinstance(step, int) or isinstance(step, bool) or step <= 0):
            rep.error(c.get("id", "?"), "seriesId requires a positive integer seriesStep")
        if step is not None and not sid:
            rep.error(c.get("id", "?"), "seriesStep requires a non-empty seriesId")
    series = {}
    for c in challenges:
        if c.get("seriesId"):
            series.setdefault(c["seriesId"], []).append(c)
    for sid, items in series.items():
        steps = [c.get("seriesStep") for c in items]
        if len(items) < 2:
            rep.error(sid, "a series needs at least 2 challenges")
        if len(set(steps)) != len(steps):
            rep.error(sid, "seriesStep values repeat inside the series")
        if all(isinstance(step, int) and not isinstance(step, bool) and step > 0 for step in steps):
            if sorted(steps) != list(range(1, len(steps) + 1)):
                rep.error(sid, "seriesStep values must be contiguous starting at 1")
        tracks = {c.get("track") for c in items}
        if len(tracks) != 1:
            rep.error(sid, "all challenges in a series must use the same track")
        # A series is meant to build on itself. Repeating the same exercise, or the
        # same answer over identical material, adds a step without adding a demand.
        # Note this is a structural guard only: whether the reasoning actually
        # deepens from step to step still needs a human read of the series.
        sigs = {}
        for c in sorted(items, key=lambda x: x.get("seriesStep") or 0):
            sig = code_signature(c)
            if sig and sig in sigs:
                rep.error(sid, "steps %s and %s present the same exercise" % (sigs[sig], c.get("id")))
            sigs[sig] = c.get("id")
        if len(items) >= 3 and len({c.get("type") for c in items}) == 1:
            rep.error(sid, "every step uses the same challenge type %r" % items[0].get("type"))

    pairs = duplicate_audit(challenges, rep)

    if strict:
        if len(challenges) != TOTAL:
            rep.error("<bank>", "expected %d challenges, found %d" % (TOTAL, len(challenges)))
        for track, expected in TRACK_COUNTS.items():
            got = sum(1 for c in challenges if c.get("track") == track)
            if got != expected:
                rep.error("<bank>", "track %s expected %d challenges, found %d" % (track, expected, got))
        for t, expected in TYPE_COUNTS.items():
            got = sum(1 for c in challenges if c.get("type") == t)
            if got < expected:
                rep.error("<bank>", "type %s expected at least %d, found %d" % (t, expected, got))
        for track in TRACK_COUNTS:
            used = {c.get("type") for c in challenges if c.get("track") == track}
            if len(used) < 5:
                rep.error("<bank>", "track %s uses only %d challenge types" % (track, len(used)))
            if not used & {"bugHunt", "repair"}:
                rep.error("<bank>", "track %s has no debugging challenge" % track)
            if track != "development" and "buildFunction" not in used:
                rep.error("<bank>", "track %s has no build challenge" % track)
        for level in sorted(DIFFICULTIES):
            got = sum(1 for c in challenges if c.get("difficulty") == level)
            if got < 30:
                rep.error("<bank>", "difficulty %d has only %d challenges" % (level, got))
        for c in challenges:
            if not c.get("seriesId"):
                rep.warn(c.get("id", "?"), "not part of a progressive series")
    return rep, pairs


def main(argv):
    strict = "--partial" not in argv
    audit_path = None
    if "--audit" in argv:
        audit_path = Path(argv[argv.index("--audit") + 1])
    data = json.loads((ROOT / "source/practice.json").read_text(encoding="utf-8"))
    rep, pairs = validate(data, strict=strict)
    if audit_path:
        audit_path.write_text(json.dumps({"pairs": pairs}, ensure_ascii=False, indent=2), encoding="utf-8")
    for w in rep.warnings[:20]:
        print("WARN  %s" % w)
    if len(rep.warnings) > 20:
        print("WARN  ... and %d more warnings" % (len(rep.warnings) - 20))
    for e in rep.errors:
        print("ERROR %s" % e)
    n = len(data.get("challenges") or [])
    if rep.errors:
        print("\nFAILED: %d error(s) over %d challenge(s)" % (len(rep.errors), n))
        return 1
    print("OK: %d challenge(s) validated%s" % (n, "" if strict else " (partial mode)"))
    if pairs:
        print("Similar pairs above 0.62: %d (highest %.2f)" % (len(pairs), pairs[0]["score"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
