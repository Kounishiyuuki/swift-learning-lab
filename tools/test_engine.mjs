// tools/test_engine.mjs — 実装練習エンジンの回帰テスト（Node標準ライブラリのみ、外部依存なし）
//
//   node tools/test_engine.mjs
//
// index.html の <script> を最小限のDOMスタブ上で実行し、10種類すべての challenge type について
// 描画・採点・入力判定・ヒント進行・解答表示・スコア・保存・復習・絞り込み・推薦・HTMLエスケープを検証する。
// ブラウザを起動しないため CI でもそのまま実行できる。
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
// const/let はスクリプトのレキシカルスコープに入り sandbox のプロパティにならないため、
// 末尾で必要な名前だけを明示的に公開する。
const exposed = [
  "CHALLENGES", "TYPE_INFO", "SKILL_LABELS", "MASTERY_SCORE", "practiceState", "practiceStats",
  "escapeHtml", "workspaceHtml", "solutionHtml", "practiceDetailHtml", "hintsHtml",
  "evaluateChallenge", "answerReady", "normalizeCode", "practiceScore", "practiceSummary",
  "practiceSkillStats", "skillDashboardHtml", "practiceReviewHtml", "reviewChallenges",
  "practiceRecord", "practiceStatus", "loadPracticeStats", "filteredChallenges",
  "recommendNext", "recommendationCard", "openChallenge", "resetAttempt", "practiceHint",
  "practiceRetry", "practiceReveal", "practiceCheck", "handleWorkAct", "challengeCard"
];
const src = html.match(/<script>([\s\S]*)<\/script>/)[1] +
  "\n;Object.assign(globalThis, {" + exposed.join(",") + "});\n";

let failures = 0, checks = 0;
function ok(cond, label) {
  checks++;
  if (!cond) { failures++; console.log("FAIL " + label); }
}

/* ---- 最小限のDOMスタブ ---- */
const store = {};
function makeEl(id) {
  const el = {
    id, innerHTML: "", textContent: "", value: "", disabled: false, dataset: {},
    style: { display: "" }, classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    children: [],
    addEventListener(){}, removeEventListener(){}, focus(){}, setSelectionRange(){},
    scrollIntoView(){}, appendChild(c){ this.children.push(c); },
    querySelectorAll(){ return []; }, querySelector(){ return null; },
    getAttribute(){ return null; }, setAttribute(){}
  };
  return el;
}
const elements = {};
function getEl(id) { return (elements[id] ||= makeEl(id)); }

const document = {
  documentElement: { dataset: {} },
  body: makeEl("body"),
  activeElement: { tagName: "BODY" },
  getElementById: (id) => getEl(id),
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: (t) => makeEl(t),
  addEventListener(){}
};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; }
};
const sandbox = {
  document, localStorage, console,
  window: { scrollTo(){} },
  matchMedia: () => ({ matches: false }),
  alert(){}, confirm: () => true,
  CSS: { escape: (s) => String(s) },
  setTimeout: (fn) => { fn(); return 0; },
  requestAnimationFrame: (fn) => { fn(); return 0; },
  navigator: { userAgent: "node" }
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "index.html:script" });

const S = sandbox;
const CH = S.CHALLENGES;

/* ---- 1. データの取り込み ---- */
ok(CH.length === 300, "CHALLENGES に300問読み込まれる (got " + CH.length + ")");
ok(Object.keys(S.TYPE_INFO).length === 10, "TYPE_INFO が10種類");

/* ---- 2. 全問の描画（10種すべて） ---- */
const rendered = {};
for (const c of CH) {
  S.practiceState.challengeId = c.id;
  S.resetAttempt(c);
  let html2;
  try { html2 = S.workspaceHtml(c); } catch (e) { html2 = null; console.log("RENDER ERROR " + c.id + " " + e.message); }
  ok(typeof html2 === "string" && html2.length > 0, "workspaceHtml: " + c.id);
  try { S.solutionHtml(c); S.practiceDetailHtml(c); } catch (e) { ok(false, "solution/detail render: " + c.id + " " + e.message); }
  rendered[c.type] = (rendered[c.type] || 0) + 1;
}
ok(Object.keys(rendered).length === 10, "10種すべてを描画した (" + Object.keys(rendered).join(",") + ")");

/* ---- 3. 正解データで採点すると必ず正解になる ---- */
function correctWork(c) {
  const s = c.solution || {}, ct = c.content || {};
  switch (c.type) {
    case "reorder": return { order: [...s.order], pool: [] };
    case "buildFunction": return { order: [...s.order], pool: [] };
    case "chooseBlocks": return { order: [...(ct.requireOrder ? s.order : (s.selected || s.order))], pool: [] };
    case "trace": return ct.mode === "sequence" ? { order: [...s.order], pool: [] } : { choice: s.optionId };
    case "fillBlank": return { blanks: { ...s.answers } };
    case "matching": return { pairs: { ...s.pairs } };
    case "shortCode": return { text: s.accepted[0] };
    default: return { choice: s.optionId };
  }
}
function wrongWork(c) {
  const s = c.solution || {}, ct = c.content || {};
  switch (c.type) {
    case "reorder":
    case "buildFunction": return { order: [...s.order].reverse(), pool: [] };
    case "chooseBlocks": {
      const sel = [...(ct.requireOrder ? s.order : (s.selected || s.order))];
      return { order: sel.slice(0, Math.max(sel.length - 1, 0)), pool: [] };
    }
    case "trace": return ct.mode === "sequence"
      ? { order: [...s.order].reverse(), pool: [] }
      : { choice: (ct.options.find(o => o.id !== s.optionId) || {}).id };
    case "fillBlank": {
      const b = ct.blanks[0];
      const other = b.options.find(o => o !== s.answers[b.id]);
      return { blanks: { ...s.answers, [b.id]: other } };
    }
    case "matching": {
      const l = ct.left[0];
      const other = ct.right.find(r => r.id !== s.pairs[l.id]);
      return { pairs: { ...s.pairs, [l.id]: other.id } };
    }
    case "shortCode": return { text: "definitely not the answer" };
    default: {
      const lines = ct.lines || ct.options || [];
      return { choice: (lines.find(o => o.id !== s.optionId) || {}).id };
    }
  }
}
let evalBad = 0, readyBad = 0, wrongBad = 0;
for (const c of CH) {
  const w = correctWork(c);
  if (!S.evaluateChallenge(c, w)) { evalBad++; console.log("EVAL FAIL " + c.id + " (" + c.type + ")"); }
  if (!S.answerReady(c, w)) { readyBad++; console.log("READY FAIL " + c.id); }
  const bad = wrongWork(c);
  if (S.evaluateChallenge(c, bad)) { wrongBad++; console.log("WRONG-ACCEPTED " + c.id + " (" + c.type + ")"); }
}
ok(evalBad === 0, "全300問で正解データが正解と判定される");
ok(readyBad === 0, "全300問で正解データが入力済みと判定される");
ok(wrongBad === 0, "全300問で誤答データが不正解と判定される");

/* ---- 4. 未入力は answerReady が false（reorder/trace順序は初期状態が既に並びなので除く） ---- */
let notReady = 0;
for (const c of CH) {
  if (c.type === "reorder") continue;
  if (c.type === "trace" && (c.content || {}).mode === "sequence") continue;
  S.resetAttempt(c);
  if (S.answerReady(c, S.practiceState.work)) notReady++;
}
ok(notReady === 0, "未入力状態は answerReady が false");

/* ---- 5. shortCode の正規化（空白・インデント差を吸収する） ---- */
const short = CH.find(c => c.type === "shortCode");
ok(S.evaluateChallenge(short, { text: "  " + short.solution.accepted[0] + "  " }), "shortCode: 前後の空白を無視");
ok(S.evaluateChallenge(short, { text: short.solution.accepted[0].replace(/ /g, "  ") }) ||
   S.normalizeCode("a  b") === "a b", "shortCode: 連続する空白を1つに正規化");

/* ---- 6. スコアリング（ヒント段階と解答表示を区別する） ---- */
ok(S.practiceScore(0, false) === 100, "スコア: ヒントなし=100");
ok(S.practiceScore(1, false) === 85, "スコア: ヒント1=85");
ok(S.practiceScore(2, false) === 65, "スコア: ヒント2=65");
ok(S.practiceScore(3, false) === 45, "スコア: ヒント3=45");
ok(S.practiceScore(0, true) === 0, "スコア: 解答表示=0");
ok(S.MASTERY_SCORE === 65, "習得の閾値は65（ヒント2までは習得扱い）");

/* ---- 7. ヒント進行と解答表示 ---- */
const target = CH.find(c => c.type === "fillBlank");
S.openChallenge(target.id);
ok(S.practiceState.hintLevel === 0, "初期状態はヒント0");
S.practiceHint(); S.practiceHint();
ok(S.practiceState.hintLevel === 2, "ヒントを2段階まで開ける");
S.practiceHint(); S.practiceHint();
ok(S.practiceState.hintLevel === 3, "ヒントは3段階を超えない");
ok(S.hintsHtml(target).includes("ヒント3"), "開いたヒントが描画される");
S.practiceReveal();
ok(S.practiceState.solutionShown === true, "解答表示フラグが立つ");
ok(S.practiceRecord(target.id).needsReview === true, "解答を見た問題は要復習になる");
ok(S.practiceRecord(target.id).solutionViewed === true, "解答表示が記録される");
ok(S.practiceRecord(target.id).attempts === 0, "未回答で解答を見ても試行回数は増えない");
ok(S.practiceStatus(target.id) === "review", "未回答で解答を見た問題も review と表示される");
ok(S.practiceSummary().review >= 1, "未回答で解答を見た問題も全体の要復習件数に含まれる");
ok(S.practiceSkillStats().some(row => row.review >= 1), "未回答で解答を見た問題もスキル別の要復習件数に含まれる");

/* ---- 8. 採点・保存・復習・クリーンな解き直し ---- */
const t2 = CH.find(c => c.type === "bugHunt");
S.openChallenge(t2.id);
S.practiceState.work = wrongWork(t2);
S.practiceCheck();
let rec = S.practiceRecord(t2.id);
ok(rec.attempts === 1 && rec.solved === false, "不正解: 試行が記録され未クリア");
ok(rec.needsReview === true, "不正解は要復習になる");
ok(S.practiceStatus(t2.id) === "review", "不正解の状態は review");

S.practiceRetry();
S.practiceHint(); S.practiceHint(); S.practiceHint();
S.practiceState.work = correctWork(t2);
S.practiceCheck();
rec = S.practiceRecord(t2.id);
ok(rec.solved === true && rec.bestScore === 45, "ヒント3で正解: bestScore=45");
ok(rec.needsReview === true, "ヒントを使い切った正解はまだ要復習");

S.practiceRetry();
S.practiceState.work = correctWork(t2);
S.practiceCheck();
rec = S.practiceRecord(t2.id);
ok(rec.bestScore === 100, "ヒントなしで解き直すと bestScore=100");
ok(rec.needsReview === false, "クリーンな解き直しで復習から外れる");
ok(S.practiceStatus(t2.id) === "solved", "状態が solved になる");

S.practiceRetry();
S.practiceHint(); S.practiceHint(); S.practiceHint();
S.practiceState.work = correctWork(t2);
S.practiceCheck();
rec = S.practiceRecord(t2.id);
ok(rec.bestScore === 100, "過去の最高スコアは下がらない");
ok(rec.needsReview === true, "ヒントを多用した回は再び要復習になる");

/* ---- 9. 永続化（専用キー・知識問題と別） ---- */
ok(store["swiftLearningPracticeStatsV1"] !== undefined, "実装練習の専用キーに保存される");
const saved = JSON.parse(store["swiftLearningPracticeStatsV1"]);
ok(saved.challenges[t2.id].bestScore === 100, "保存内容に bestScore が含まれる");
ok(saved.challenges[t2.id].attempts >= 4, "保存内容に attempts が含まれる");
ok(saved.challenges[t2.id].hintsUsed === 3, "保存内容に hintsUsed が含まれる");
store["swiftLearningStats"]="knowledge-sentinel";
const persistenceProbe=CH.find(c=>c.type==="trace" && !S.practiceRecord(c.id));
S.openChallenge(persistenceProbe.id);
S.practiceReveal();
ok(store["swiftLearningStats"] === "knowledge-sentinel", "実装練習の保存は知識問題のキーを変更しない");
store["swiftLearningPracticeStatsV1"] = "{{{";
ok(Object.keys(S.loadPracticeStats().challenges).length === 0, "壊れたJSONは空の保存状態として読み込む");
store["swiftLearningPracticeStatsV1"] = JSON.stringify({version:99,challenges:{
  valid:{attempts:2,solved:true,bestScore:85,hintsUsed:1,solutionViewed:false,lastResult:"correct",needsReview:false},
  partial:{attempts:1,needsReview:true}, malformed:["not","a","record"],
  inconsistent:{attempts:1,solved:false,bestScore:100,hintsUsed:0,lastResult:"wrong",needsReview:false}
}});
const sanitized=S.loadPracticeStats();
ok(sanitized.version === 1 && sanitized.challenges.valid.bestScore === 85,
   "保存データを現行versionへ正規化し、有効なレコードを保持する");
ok(sanitized.challenges.partial.attempts === 1 && sanitized.challenges.partial.bestScore === 0 && sanitized.challenges.partial.needsReview,
   "部分的なレコードは安全な既定値で補完する");
ok(!("malformed" in sanitized.challenges), "壊れた1レコードだけを破棄する");
ok(sanitized.challenges.inconsistent.bestScore === 0 && sanitized.challenges.inconsistent.needsReview,
   "未解決レコードの不正な最高点を破棄し、要復習として正規化する");
const inconsistentId=CH.find(c=>!S.practiceRecord(c.id)).id;
S.practiceStats.challenges[inconsistentId]={attempts:1,solved:false,bestScore:100,needsReview:true};
const inconsistentSummary=S.practiceSummary();
ok(inconsistentSummary.mastered <= inconsistentSummary.solved && inconsistentSummary.noHintPct <= 100,
   "矛盾した保存レコードでも未解決を習得扱いせず、割合は100%を超えない");
delete S.practiceStats.challenges[inconsistentId];
store["swiftLearningPracticeStatsV1"] = JSON.stringify(saved);

/* ---- 9b. 状態通知のアクセシビリティ ---- */
S.openChallenge(target.id);
S.practiceHint();
ok(getEl("content").innerHTML.includes('id="pHints" role="status" aria-live="polite"'),
   "ヒント領域が支援技術へ更新を通知する");
S.practiceState.work=wrongWork(target);
S.practiceCheck();
ok(getEl("content").innerHTML.includes('role="status" aria-live="assertive"'),
   "採点結果が支援技術へ即時通知される");

/* ---- 10. 絞り込み ---- */
function count(f) {
  S.practiceState.filters = Object.assign({ track:"all", group:"all", type:"all", level:"all", skill:"all", status:"all" }, f);
  S.practiceState.search = "";
  return S.filteredChallenges().length;
}
ok(count({}) === 300, "絞り込みなしで300問");
ok(count({ track: "swiftui" }) === 27, "トラック絞り込み: swiftui=27");
ok(count({ track: "uikit" }) === 27, "トラック絞り込み: uikit=27");
ok(count({ type: "testReasoning" }) === 20, "形式絞り込み: testReasoning=20");
ok(count({ level: "1" }) === 33, "難易度絞り込み: Lv1=33");
ok(count({ group: "debug" }) === 100, "カテゴリ絞り込み: debug=100 (got " + count({group:"debug"}) + ")");
ok(count({ skill: "swiftui" }) === 30, "スキル絞り込み: swiftui=30");
ok(count({ status: "review" }) >= 1, "状態絞り込み: review が機能する");
S.practiceState.filters = { track:"all", group:"all", type:"all", level:"all", skill:"all", status:"all" };
S.practiceState.search = "Optional";
ok(S.filteredChallenges().length > 0 && S.filteredChallenges().length < 300, "検索が絞り込む");
S.practiceState.search = "";

/* ---- 11. 推薦 ---- */
const recommendation = S.recommendNext();
ok(recommendation && recommendation.challenge && typeof recommendation.reason === "string", "推薦が問題と理由を返す");
ok(S.recommendationCard().includes(recommendation.challenge.title.slice(0, 4)), "推薦カードに推薦問題が出る");
const reviewFirst = S.CHALLENGES.find(c => S.practiceStatus(c.id) === "review");
ok(reviewFirst !== undefined, "要復習の問題が推薦の候補になる状態を作れる");

/* ---- 12. スキルダッシュボード ---- */
const skills = S.practiceSkillStats();
ok(skills.length === 16, "スキル集計が16スキル分ある (got " + skills.length + ")");
const required = ["syntax","controlFlow","functions","optional","collections","debugging","testing","foundation","concurrency","swiftui","uikit","architecture"];
ok(required.every(k => skills.some(s => s.key === k)), "必須12スキルがすべて集計対象");
ok(skills.every(s => s.total > 0 && s.masteryPct >= 0 && s.masteryPct <= 100), "各スキルの習得率が0〜100");
const dash = S.skillDashboardHtml();
ok(dash.includes("実装力"), "ダッシュボードに実装力の見出しがある");
ok(dash.includes("正確に測るスコアではありません"), "ダッシュボードに限界の注記がある");
ok(dash.includes("要復習") && dash.includes("ヒントなし正解"), "ダッシュボードが要復習とヒントなし率を表示");
const reviewHtml = S.practiceReviewHtml();
ok(reviewHtml.includes("復習リスト"), "復習セクションが描画される");

/* ---- 13. HTMLエスケープ ---- */
ok(S.escapeHtml('<img src=x onerror=alert(1)>') === "&lt;img src=x onerror=alert(1)&gt;",
   "escapeHtml が < > を無害化");
ok(S.escapeHtml('"&<>') === "&quot;&amp;&lt;&gt;", "escapeHtml が \" & < > を変換 (got " + S.escapeHtml('"&<>') + ")");
const evil = {
  id: "practice-swift-001", track: "swift", type: "shortCode", difficulty: 1,
  title: "<script>alert(1)</script>", prompt: "x",
  content: { context: "<img src=x onerror=alert(1)>", placeholder: '"><b>' },
  solution: { accepted: ["<b>"] }, hints: ["a","b","c"], skills: ["syntax"],
  detail: { concept: "<script>", steps: ["<i>"], commonMistakes: ["<u>"], takeaway: "<s>" },
  explanation: "<script>"
};
S.practiceState.work = { text: "" };
S.practiceState.checked = false; S.practiceState.solutionShown = false;
const evilHtml = S.workspaceHtml(evil) + S.solutionHtml(evil) + S.practiceDetailHtml(evil);
// escapeHtml は < > & " \' を実体参照に変える。危険なのは「タグとして解釈される <」なので、
// 注入されたタグが開いていないこと（= すべて &lt; になっていること）を確認する。
ok(!/<\s*(script|img|svg|iframe)\b/i.test(evilHtml), "注入されたタグが開かれない");
ok(!evilHtml.includes('"><b>'), "属性を閉じる文字列がそのまま出力されない");
ok(evilHtml.includes("&lt;"), "エスケープ済みの形で出力される");
let anyRaw = 0;
for (const c of CH) {
  S.practiceState.challengeId = c.id; S.resetAttempt(c);
  const h = S.workspaceHtml(c) + S.solutionHtml(c) + S.practiceDetailHtml(c);
  if (/<\s*(script|img|svg|iframe)\b/i.test(h) || /javascript:/i.test(h)) { anyRaw++; console.log("UNSAFE HTML in " + c.id); }
}
ok(anyRaw === 0, "全300問の描画結果にスクリプト混入がない");

/* ---- 14. 並べ替え操作（非ドラッグの代替手段） ---- */
const ro = CH.find(c => c.type === "reorder");
S.openChallenge(ro.id);
const first = S.practiceState.work.order[0], second = S.practiceState.work.order[1];
S.handleWorkAct(ro, "down", first);
ok(S.practiceState.work.order[0] === second && S.practiceState.work.order[1] === first, "↓ボタンで並べ替えできる");
S.handleWorkAct(ro, "up", first);
ok(S.practiceState.work.order[0] === first, "↑ボタンで戻せる");
S.handleWorkAct(ro, "pick", first);
S.handleWorkAct(ro, "pick", second);
ok(S.practiceState.work.order[0] === second, "タップ2回で入れ替えできる（ドラッグ不要）");
const bf = CH.find(c => c.type === "buildFunction");
S.openChallenge(bf.id);
ok(S.practiceState.work.order.length === 0 && S.practiceState.work.pool.length > 0, "buildFunction は候補プールから始まる");
const pick = S.practiceState.work.pool[0];
S.handleWorkAct(bf, "add", pick);
ok(S.practiceState.work.order.includes(pick), "＋で解答に追加できる");
S.handleWorkAct(bf, "remove", pick);
ok(!S.practiceState.work.order.includes(pick) && S.practiceState.work.pool.includes(pick), "×で候補に戻せる");

/* ---- 15. ロック中は操作を受け付けない ---- */
S.openChallenge(t2.id);
S.practiceState.work = correctWork(t2);
S.practiceCheck();
const lockedOrder = JSON.stringify(S.practiceState.work);
S.handleWorkAct(t2, "choose", "zzz");
ok(JSON.stringify(S.practiceState.work) === lockedOrder, "採点後は操作がロックされる");

console.log((failures ? "FAILED " : "OK ") + (checks - failures) + "/" + checks + " checks");
process.exit(failures ? 1 : 0);
