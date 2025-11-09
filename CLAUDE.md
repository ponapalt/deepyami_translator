# DeepYami翻訳アプリ - 実装計画書

## プロジェクト概要

Python・LangChain・LLMを使用した、DeepL風の翻訳アプリケーション

### 主要機能
- 左右2分割のUI（左：翻訳元、右：翻訳先）
- メニューバー付きのメモ帳風UI
- 複数LLMモデル対応（GPT-4.1、Claude Sonnet 4.5、Gemini 2.5 Pro）
- 多言語対応（日本語、中国語簡体字、中国語繁体字、韓国語、英語）
- 設定管理（APIキー、LLMモデル選択）
- Windows環境での簡単起動（start.bat）

## アーキテクチャ設計

### プロジェクト構造

```
deepyami_translator/
├── app.py                    # メインエントリーポイント
├── start.bat                 # Windows起動スクリプト
├── requirements.txt          # Python依存関係
├── config.json              # 設定ファイル（gitignore）
├── .gitignore
├── README.md
├── CLAUDE.md                # 本ドキュメント
└── src/
    ├── __init__.py
    ├── main_window.py       # メインウィンドウUI
    ├── settings_dialog.py   # 設定ダイアログUI
    ├── llm_service.py       # LLM統合サービス
    └── config_manager.py    # 設定管理
```

## 詳細設計

### 1. UI設計（tkinter使用）

#### 1.1 メインウィンドウ（main_window.py）

**構成要素：**
- メニューバー
  - ファイル
    - 新規作成
    - 開く
    - 保存
    - 名前を付けて保存
    - 終了
  - 編集
    - 元に戻す
    - やり直し
    - 切り取り
    - コピー
    - 貼り付け
  - 設定
    - API設定
  - ヘルプ
    - バージョン情報

- 警告バナー（設定未完了時）
  - 「設定を完了してください」メッセージ
  - 設定ボタン

- 言語選択パネル
  - 左側：翻訳元言語選択（コンボボックス）
  - 右側：翻訳先言語選択（コンボボックス）
  - 翻訳ボタン（中央）

- テキストエリア（2分割）
  - 左：翻訳元テキスト（編集可能）
  - 右：翻訳結果（読み取り専用）

**状態管理：**
- 設定完了フラグ
  - True: 通常動作
  - False: テキストエリア無効化、警告バナー表示

#### 1.2 設定ダイアログ（settings_dialog.py）

**構成要素：**
- LLMモデル選択
  - ラジオボタン: GPT-4.1 / Claude Sonnet 4.5 / Gemini 2.5 Pro

- APIキー入力
  - OpenAI APIキー（GPT-4.1選択時に表示）
  - Anthropic APIキー（Claude選択時に表示）
  - Google APIキー（Gemini選択時に表示）
  - 表示/非表示トグルボタン

- 保存・キャンセルボタン

**バリデーション：**
- APIキー形式チェック
- 必須項目入力確認

### 2. LLM統合（llm_service.py）

#### 2.1 LangChain統合

**対応モデル：**
- OpenAI GPT-4.1
  - langchain-openai の ChatOpenAI
  - モデル名: "gpt-4-turbo-preview" または最新のGPT-4.1

- Anthropic Claude Sonnet 4.5
  - langchain-anthropic の ChatAnthropic
  - モデル名: "claude-sonnet-4-5-20250929"

- Google Gemini 2.5 Pro
  - langchain-google-genai の ChatGoogleGenerativeAI
  - モデル名: "gemini-2.5-pro" または "gemini-2.0-flash"

#### 2.2 翻訳プロンプト設計

```python
prompt_template = """
You are a professional translator. Translate the following text from {source_lang} to {target_lang}.
Maintain the original tone, style, and nuance of the text.
Only output the translated text without any explanations.

Text to translate:
{text}

Translation:
"""
```

#### 2.3 翻訳サービスクラス

```python
class TranslationService:
    def __init__(self, model_type: str, api_key: str):
        """
        Args:
            model_type: "gpt4", "claude", "gemini"
            api_key: 対応するAPIキー
        """

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        テキストを翻訳

        Args:
            text: 翻訳対象テキスト
            source_lang: 翻訳元言語
            target_lang: 翻訳先言語

        Returns:
            翻訳されたテキスト
        """
```

### 3. 設定管理（config_manager.py）

#### 3.1 設定ファイル構造（config.json）

```json
{
    "model_type": "gpt4",
    "api_keys": {
        "openai": "",
        "anthropic": "",
        "google": ""
    },
    "last_source_lang": "Japanese",
    "last_target_lang": "English"
}
```

#### 3.2 ConfigManagerクラス

```python
class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        """設定ファイルの読み込み・初期化"""

    def load(self) -> dict:
        """設定を読み込む"""

    def save(self, config: dict) -> None:
        """設定を保存"""

    def is_configured(self) -> bool:
        """設定が完了しているかチェック"""

    def get_current_api_key(self) -> str:
        """現在選択されているモデルのAPIキーを取得"""
```

### 4. 言語定義

**対応言語：**
- Japanese（日本語）
- Chinese-Simplified（中国語簡体字）
- Chinese-Traditional（中国語繁体字）
- Korean（韓国語）
- English（英語）

### 5. Windows起動スクリプト（start.bat）

```batch
@echo off
chcp 65001 >nul
echo DeepYami翻訳アプリを起動しています...

REM venvの存在確認
if not exist "venv\" (
    echo 仮想環境を作成しています...
    python -m venv venv
    if errorlevel 1 (
        echo エラー: 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)

REM venv有効化
call venv\Scripts\activate.bat

REM 依存関係インストール
echo 依存関係をインストールしています...
pip install -r requirements.txt
if errorlevel 1 (
    echo エラー: 依存関係のインストールに失敗しました
    pause
    exit /b 1
)

REM アプリ起動
echo アプリケーションを起動します...
python app.py

pause
```

### 6. 依存関係（requirements.txt）

```
langchain==0.1.0
langchain-openai==0.0.5
langchain-anthropic==0.1.0
langchain-google-genai==0.0.6
openai>=1.0.0
anthropic>=0.8.0
google-generativeai>=0.3.0
```

## 実装手順

### フェーズ1: 基盤構築
1. プロジェクト構造作成
2. requirements.txt作成
3. start.bat作成
4. .gitignore作成

### フェーズ2: バックエンド実装
1. config_manager.py実装
   - ConfigManagerクラス
   - 設定ファイルI/O
   - バリデーション

2. llm_service.py実装
   - TranslationServiceクラス
   - LangChain統合
   - プロンプト設計

### フェーズ3: フロントエンド実装
1. settings_dialog.py実装
   - 設定ダイアログUI
   - APIキー入力
   - モデル選択

2. main_window.py実装
   - メインウィンドウUI
   - メニューバー
   - 2分割テキストエリア
   - 言語選択
   - 翻訳ボタン
   - 状態管理

3. app.py実装
   - アプリケーション起動
   - 初期化処理

### フェーズ4: テスト・調整
1. 動作確認
2. エラーハンドリング改善
3. UI/UX調整

## 技術スタック

- **言語**: Python 3.8+
- **GUI**: tkinter（Python標準ライブラリ）
- **LLM統合**: LangChain
- **API**:
  - OpenAI API（GPT-4.1）
  - Anthropic API（Claude）
  - Google Generative AI API（Gemini）

## セキュリティ考慮事項

1. APIキーの安全な保管
   - config.jsonをgitignore
   - メモリ上での適切な管理

2. 入力検証
   - テキスト長制限
   - 不正な入力の拒否

3. エラーハンドリング
   - API呼び出し失敗時の適切な処理
   - ユーザーへのフィードバック

## 今後の拡張可能性

- 翻訳履歴機能
- お気に入り翻訳の保存
- バッチ翻訳機能
- カスタムプロンプト設定
- より多くの言語対応
- オフラインモード（ローカルモデル）
- プラグインシステム

## 完成基準

- ✅ start.batで起動可能
- ✅ 初回起動時に設定ダイアログが表示
- ✅ 設定完了後に翻訳機能が有効化
- ✅ 5言語間の翻訳が正常動作
- ✅ 3種類のLLMモデルが選択可能
- ✅ 基本的なメモ帳機能（開く・保存）が動作
- ✅ エラーが適切にハンドリングされる
