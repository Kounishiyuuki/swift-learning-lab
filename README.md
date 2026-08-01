# Swift Learning Lab v0.4

Swiftを「超基礎（Starter）」「言語」「データ/Foundation」「Concurrency/Memory」「開発実務」「SwiftUI」「UIKit」に分離して学ぶ個人用Web教材です。

初めてSwiftを学ぶ場合は Swift Starter から始めてください。値・型・nil・Optional・`{ }`・引数・property / method といった用語が未知の段階から読めるトラックです。

## v0.4.0
- 全252問に、回答後に開ける詳細解説を追加
- 用語・記号の意味、コードの処理順、正解になる理由、誤答選択肢の本来の意味、関連例、覚えるポイントに対応
- 短い解説は従来どおり回答直後に表示。詳細解説は「詳しい解説を見る」で開閉
- 62件の関連Swift例を収録し、コンパイル・実行で出力を検証
- 問題文・解説のHTMLエスケープを強化（`Array<Int>` などがそのまま表示される）
- `source/content.json` から `index.html` と全7トラックのTXTを生成
- 既存の問題ID・正解・localStorage進捗との互換性を維持

## 規模
- 7トラック
- 116レッスン
- 252問
- すべて即時正誤 + 解説（全252問が詳細解説つき）
- PC / スマホ対応
- 完全オフラインで `index.html` を直接開ける

## トラック
- Swift Starter: 20 lessons / 60 questions
- Swift Language: 36 lessons / 72 questions
- Foundation & Data: 16 / 32
- Concurrency & Memory: 12 / 24
- Development Essentials: 20 / 40
- SwiftUI: 6 / 12
- UIKit: 6 / 12

## 機能
- 学ぶ / 問題 / 間違い復習 / 進捗
- 全トラック横断問題
- Starter / Beginner / Basic / Intermediate filter
- 検索 / shuffle
- localStorageで正答率・読了・間違いを保存
- Dark mode
- 詳細解説の開閉（用語 / 処理の流れ / 正解の理由 / 他の選択肢 / 関連例 / 覚えておくこと）
- PC keyboard: 1〜4回答 / Nで次
- スマホではtrack・lesson dropdownを表示

## 編集
教材データの編集元は `source/content.json` のみです。
`index.html` への埋め込みと `source/<track>.txt` の生成は build が行うため、生成物を直接編集しないでください。

`content.json` を編集後:
```bash
python3 tools/build.py
```

## 利用方法
`index.html` をブラウザで直接開けば、完全オフラインで利用できます。
スマホで継続利用する場合はGitHub Pagesから開けます。

https://kounishiyuuki.github.io/swift-learning-lab/
