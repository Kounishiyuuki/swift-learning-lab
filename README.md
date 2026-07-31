# Swift Learning Lab v0.3

Swiftを「超基礎（Starter）」「言語」「データ/Foundation」「Concurrency/Memory」「開発実務」「SwiftUI」「UIKit」に分離して学ぶ個人用Web教材です。

初めてSwiftを学ぶ場合は Swift Starter から始めてください。値・型・nil・Optional・`{ }`・引数・property / method といった用語が未知の段階から読めるトラックです。

## 規模
- 7トラック
- 116レッスン
- 252問
- すべて即時正誤 + 解説
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
- PC keyboard: 1〜4回答 / Nで次
- スマホではtrack・lesson dropdownを表示

## 編集
構造化教材は `source/content.json`。
人が読む原本は `source/*.txt`。

`content.json` を編集後:
```bash
python3 tools/build.py
```

## Git
```bash
git init
git add .
git commit -m "Add comprehensive Swift learning curriculum"
```

スマホで継続利用するならGitHub Pagesに置くとURLから開けます。
