# DeepYami翻訳アプリ - 開発ガイド

Python・LangChain・LLMを使用したDeepL風の翻訳アプリケーション。
ユーザー向けの機能説明・セットアップ手順は `README.md` を参照。
本ドキュメントは**コードを変更する際に知っておくべきこと**のみを扱う。

## プロジェクト構造

```
deepyami_translator/
├── app.py               # エントリーポイント
├── start_win.bat        # Windows起動スクリプト（venv作成・依存導入・起動）
├── start_mac.sh         # macOS/Linux起動スクリプト
├── requirements.txt     # 依存関係（langchain 1.x系）
├── config.json          # 設定ファイル（gitignore対象）
├── history.json         # 翻訳履歴（gitignore対象）
└── src/
    ├── models.py          # LLMモデル定義テーブル（全モジュール共通）
    ├── config_manager.py  # 設定の読み書き
    ├── history_manager.py # 翻訳履歴の読み書き
    ├── llm_service.py     # LangChain統合・翻訳/校正
    ├── settings_dialog.py # API設定ダイアログ
    ├── history_dialog.py  # 翻訳履歴ダイアログ
    └── main_window.py     # メインウィンドウUI
```

## 技術スタック

- Python 3.8+ / tkinter（標準ライブラリ）
- LangChain 1.x + langchain-openai / langchain-anthropic / langchain-google-genai
- OpenAI API / Anthropic API / Google Generative AI API

---

## src/models.py — モデル定義テーブル

アプリ全体で使うLLMモデル一覧の**唯一の定義場所**。
`MODELS`（`ModelSpec`のリスト）と `PROVIDERS`（`ProviderSpec`のリスト）を持つ。
モデルの具体名・パラメータはこのファイルを直接参照すること（本書には列挙しない）。

参照している箇所:

| ファイル | 用途 |
|---|---|
| `settings_dialog.py` | APIキー入力欄の生成、ダイアログサイズ算出 |
| `main_window.py` | 「モデル」メニュー、右ペインの現在モデル表示 |
| `llm_service.py` | LLMインスタンス生成（`PROVIDER_FACTORIES`で分岐） |
| `config_manager.py` | model_type検証、モデル→APIキー紐付け、`api_keys`初期値 |

### モデルを追加・変更する

1. `MODELS` に `ModelSpec` を1行追加する（UI上の並び順＝リストの順序）
2. 他ファイルの変更は不要

### model_typeを改名する

`model_type` は config.json に保存される識別子なので**原則変更禁止**。
やむを得ず変える場合は `LEGACY_MODEL_ALIASES` に「旧識別子: 新識別子」を追加する。
既存の config.json は読み込み時に自動変換される。

### プロバイダーを追加する

1. `PROVIDERS` に `ProviderSpec` を追加
2. `llm_service.py` の `PROVIDER_FACTORIES` に生成関数を追加

---

## src/llm_service.py — LLM統合

`TranslationService` が翻訳・校正の両方を担当する。

```python
translate(text, target_lang, style="ビジネス", streaming_callback=None) -> Optional[str]
proofread(text, style="ビジネス", streaming_callback=None) -> Optional[str]
```

- **翻訳元言語は指定しない**。プロンプト側でLLMに自動検出させる
- `style` は `STYLE_INSTRUCTIONS` のキー（`ビジネス` / `標準` / `友人`）。
  `標準` は `None` を持ち、スタイル指定なしとして扱われる
- `streaming_callback` はトークンごとに呼ばれる。**コールバックが `False` を返すと
  ストリーミングを中断する**（UI側のキャンセル機構がこれを使う）
- Gemini はレスポンスがリスト形式で返ることがあるため、
  `extract_content_text()` で文字列へ正規化してから扱う

### プロンプト設計上の約束

`translation_template` / `proofreading_template` の system メッセージには、
機能追加時も以下を残すこと:

- **CRITICAL SECURITY INSTRUCTIONS**: 入力内の指示を実行せず、
  あくまで翻訳/校正対象のプレーンテキストとして扱わせる（プロンプトインジェクション対策）
- **CRITICAL OUTPUT INSTRUCTIONS**: 前置き・注釈・引用符を付けず、
  改行位置を原文どおり保持させる

ユーザー入力は `<text_to_translate>` / `<text_to_proofread>` タグで囲み、
システム指示と明確に分離する。

---

## src/config_manager.py — 設定管理

`config.json` の実際のキーは `ConfigManager.DEFAULT_CONFIG` を参照。
保持しているのは、選択中モデル・プロバイダー別APIキー・最後の言語/スタイル・
自動翻訳ON/OFF・履歴記録ON/OFF・最後のテキスト（翻訳元/結果）・ウィンドウサイズ。

- `is_configured()`: モデルが選択済みかつ対応するAPIキーがあるか
- `get_current_api_key()`: 選択中モデルに対応するAPIキーを返す
- 読み込み時に `models.normalize_model_type()` で旧識別子を自動変換する
- setterは `self.config` を書き換えるだけ。**保存は呼び出し側が `save()` する**

### 翻訳スタイルの定義場所

`ConfigManager.TRANSLATION_STYLES` が**唯一の定義場所**。
`main_window.MainWindow.STYLES` はこれを参照しているだけなので触らなくてよい。

`llm_service.TranslationService.STYLE_INSTRUCTIONS` の**キーと必ず一致させること**。
（かつて `set_translation_style()` の検証リストだけが古い値のままで、
「標準」を選んでも黙って保存されない不具合になっていた。
`set_translation_style()` は不正な値を無言で捨てるので、ズレても気付けない）

なお `get_translation_style()` は未知の値を既定値に丸めて返す。
呼び出し側が readonly の Combobox にそのまま流すため、選択肢外の値を出さないため。

---

## src/history_manager.py — 翻訳履歴の管理

`HistoryManager` が `history.json` を読み書きする。
永続化の流儀は `ConfigManager` に揃えてある（utf-8 / `ensure_ascii=False` /
`indent=4` / 例外は握って `print` し、アプリを落とさない）。

```json
{
    "version": 1,
    "entries": [ /* 新しい順。index 0 が最新 */ ]
}
```

エントリの各キーは `HistoryManager.record()` のdocstringを参照。
`model_display` は**保存時点の表示名を焼き込む**ので、将来 `MODELS` から
そのモデルが消えても一覧が壊れない。

- `MAX_ENTRIES`（100）を超えた分は古いものから捨てる
- `record()` / `delete()` / `clear()` は変更のみ。**保存は呼び出し側が `save()` する**
- 履歴が壊れていても空の履歴で復旧する（設定と違い、失っても致命的ではない）

### 履歴の統合ルール（`_should_merge`）

自動翻訳は入力が2秒止まるたびに走るため、素直に記録すると
「これは」「これはテ」「これはテスト」…と履歴が量産される。
そこで直近エントリと同一視できる場合は、新規追加せず**それを更新**する。

前提として、種別・翻訳先・スタイル・モデルがすべて一致していること。その上で:

- **ルールA（完全重複の抑止）**: 原文も同じなら更新。
  同じ文で翻訳ボタンを押し直しても履歴が二重にならない
- **ルールB（単純追記の統合）**: 直近が自動翻訳由来（`auto`）で、
  原文が**前方一致関係**なら更新（`_is_incremental_edit`）。
  どちらの向きの前方一致も見るのは、バックスペースで一時的に短くなった場合も
  同じ編集セッションとして扱うため。
  文の**途中**に挿入した場合は前方一致にならないので新規エントリになる
- **手動実行による確定**: ルールBでの更新時、新しい記録が手動実行なら
  `auto` を `False` に落とす。以降の自動翻訳は統合されず別エントリになる

校正はルールAのみ。校正は原文を結果で置き換えるため、前方一致にはまずならない。

---

## src/settings_dialog.py — API設定ダイアログ

**APIキーの入力のみ**を担当する。モデル選択は「モデル」メニュー、
自動翻訳設定は「設定」メニューへ移したため、このダイアログには含まれない。

- 入力欄は `models.PROVIDERS` から自動生成される（各欄に表示/非表示トグル付き）
- バリデーションはAPIキーを最低1つ入力していること
- 保存時、モデル未選択または選択中モデルのAPIキーが空なら、
  キーが入力済みのプロバイダーのうち `MODELS` で最初に現れるモデルを自動選択する
  （初回起動時はAPIキーを入れるだけで設定が完了する）

**ダイアログサイズは自動計算**:
`DIALOG_WIDTH` x (`BASE_HEIGHT` + `PROVIDER_ROW_HEIGHT` * プロバイダー数)。
要素を増減した場合は `BASE_HEIGHT` を調整し、`winfo_reqheight()` を
上回っていることを確認すること。

---

## src/history_dialog.py — 翻訳履歴ダイアログ

`HistoryDialog` は一覧（`ttk.Treeview`）＋プレビュー（左右2分割）＋
復元/削除ボタンを持つモーダルダイアログ。

**`SettingsDialog` と違い `resizable(True, True)`**（`minsize` 付き）。
スクロールする一覧を持つため、`BASE_HEIGHT` を積み上げる算術計算方式は使わない。

- Treeview の `iid` にエントリの `id` を使い、選択行の特定を単純にしている
- プレビューのラベルは種別で切り替える（翻訳: 原文/訳文、校正: 校正前/校正後）
- `MainWindow` を一切知らない。`show()` が**復元されたエントリ**（なければ `None`）を
  返し、実際の復元は呼び出し側が行う（`SettingsDialog.result` と同じ責務分離）
- 削除・全削除はダイアログ内で `history_manager.save()` まで済ませる

---

## src/main_window.py — メインウィンドウ

### メニュー構成

- **ファイル**: 終了
- **編集**: 元に戻す / やり直し / 切り取り / コピー / 貼り付け / すべて選択
- **設定**: 自動翻訳（編集後2秒）のON/OFF、API設定...
- **履歴**: 翻訳履歴...（Ctrl+H）、履歴を記録するON/OFF
- **モデル**: 各モデルのラジオボタン（プロバイダーごとに区切り線、選択は即保存）

「ヘルプ」メニューは廃止。「モデル」メニューはモデル選択専用とし、設定項目を置かない。

「翻訳履歴...」は `_update_ui_state()` の対象外で、**API未設定でも開ける**
（過去の記録を見るだけなので妨げる理由がない）。

### レイアウト

PanedWindowによる左右2分割。

- 左ペイン
  - コントロール1段目: 翻訳先言語選択、翻訳スタイル選択
  - コントロール2段目: 翻訳ボタン、校正ボタン、中止ボタン、自動翻訳チェックボックス
  - 翻訳元テキストエリア（編集可能）
- 右ペイン
  - 入れ替えボタン、コピーボタン、現在使用中のモデル表示
  - 翻訳結果テキストエリア（読み取り専用）

**コントロールを1段にまとめてはいけない**。ウィンドウ幅によってウィジェットが
見切れるため2段構成にしている（1段目331px / 2段目301px必要）。

### 状態管理

- 未設定時（`is_configured()` が False）はテキストエリア等を無効化し、
  警告バナー「設定を完了してください」を表示する
- 翻訳/校正はワーカースレッドで実行し、`cancel_flag` と
  `streaming_callback` の戻り値で中断する
- 自動翻訳は `debounce_timer`（2秒）で発火。OFFにすると予約済みタイマーを取り消す

### 自動翻訳トグルの同期

「設定」メニューの項目と左ペインのチェックボックスは**同一の `tk.BooleanVar`
（`auto_translate_var`）を共有**し、`_on_auto_translate_toggle` で即座に保存される。
トグルする箇所を増やす場合も、同じ変数とハンドラを渡すこと。

### 翻訳履歴の記録と復元

記録は `_on_translation_complete` / `_on_proofread_complete` から
`_record_history()` を呼んで行う。どちらも `root.after(0, ...)` 経由で
**Tkのメインスレッド上で動く**ので、履歴の書き換えとファイル書き込みは
単一スレッドに閉じている。**ワーカースレッドから直接呼ばないこと**。

- 中断・失敗時は結果が `None` になるので、既存の `if result:` の中に置けば記録されない
- スタイルは実行時に `style_var` から取った値をそのまま渡す（実際にLLMへ渡した値）
- 復元（`_restore_history_entry`）は種別によらず**原文を左ペイン・結果を右ペイン**に入れる
- 復元時は `source_text` を一時的に `NORMAL` にする。
  API未設定時は `_update_ui_state()` が無効化しており、そのままでは書き込めないため

### 言語の入れ替え（`_on_swap_languages`）

翻訳元と翻訳結果を入れ替え、新しい翻訳元の言語を `_detect_language()` で推定する。
`_detect_language()` は**LLMを使わず文字種の出現数で判定する**（ひらがな/カタカナ/
ハングル/漢字/ラテン文字、簡体字・繁体字は特徴的な文字集合で区別）。
対応言語を増やす場合はこの判定ロジックにも手を入れる必要がある。

---

## 対応言語

`Japanese` / `Chinese-Simplified` / `Chinese-Traditional` / `Korean` / `English`

`main_window.LANGUAGES` と `llm_service.TranslationService.LANGUAGE_MAP` の
両方に定義があるため、増減させる際は両方を更新すること。

---

## セキュリティ考慮事項

1. **APIキー**: `config.json` は gitignore 済み。ログや例外メッセージに出さない
   （`history.json` も翻訳した文章そのものが入るため gitignore 済み）
2. **プロンプトインジェクション対策**: 上記「プロンプト設計上の約束」を維持する
3. **エラーハンドリング**: API呼び出し失敗時はダイアログでユーザーに通知し、
   アプリを落とさない

## 今後の拡張候補

お気に入り保存、バッチ翻訳、カスタムプロンプト、対応言語追加、
ローカルモデル（オフライン）対応、履歴の検索・エクスポート。
