"""
LLMモデル定義モジュール

アプリ全体で使用するLLMモデルの一覧を一元管理する。
モデルの追加・変更・削除は、原則としてこのファイルの MODELS を編集するだけでよく、
以下のすべてに自動的に反映される。

- 設定ダイアログのモデル選択ラジオボタン（settings_dialog.py）
- メニューバーの「モデル」メニュー（main_window.py）
- 右ペインの現在モデル表示（main_window.py）
- LLMインスタンスの生成（llm_service.py）
- 設定バリデーション・APIキーの紐付け（config_manager.py）

新しいモデルを追加する場合:
    MODELS に ModelSpec を1行追加するだけでよい。
    model_type（config.jsonに保存される識別子）は一度決めたら変更しないこと。
    変更する場合は LEGACY_MODEL_ALIASES に旧名→新名のマッピングを追加する。

新しいプロバイダーを追加する場合:
    PROVIDERS に ProviderSpec を追加し、
    llm_service.py の PROVIDER_FACTORIES に生成関数を追加する。
"""

from typing import Dict, List, NamedTuple, Optional, Tuple


class ProviderSpec(NamedTuple):
    """LLMプロバイダーの定義"""

    key: str           # config.jsonのapi_keys内のキー
    display_name: str  # UI表示名

    @property
    def api_key_label(self) -> str:
        """設定ダイアログのAPIキー入力欄ラベル"""
        return f"{self.display_name} API Key:"


class ModelSpec(NamedTuple):
    """LLMモデルの定義"""

    model_type: str    # config.jsonに保存される識別子（変更禁止）
    display_name: str  # UI表示名
    provider: str      # ProviderSpec.key
    model_name: str    # LangChainに渡す実際のモデル名
    params: Dict       # LangChainコンストラクタに渡す追加パラメータ

    @property
    def menu_label(self) -> str:
        """メニュー・ラジオボタン用のラベル（プロバイダー名付き）"""
        return f"{self.display_name} ({PROVIDER_MAP[self.provider].display_name})"


# プロバイダー定義（設定ダイアログのAPIキー入力欄はこの順で並ぶ）
PROVIDERS: List[ProviderSpec] = [
    ProviderSpec("openai", "OpenAI"),
    ProviderSpec("anthropic", "Anthropic"),
    ProviderSpec("google", "Google"),
]

PROVIDER_MAP: Dict[str, ProviderSpec] = {p.key: p for p in PROVIDERS}


# モデル定義（UI上はこの順で並ぶ。上位モデルを先に記載する）
MODELS: List[ModelSpec] = [
    ModelSpec("gpt-sol", "GPT-5.6 Sol", "openai",
              "gpt-5.6-sol", {"reasoning_effort": "none"}),
    ModelSpec("gpt", "GPT-5.6 Terra", "openai",
              "gpt-5.6-terra", {"reasoning_effort": "none"}),
    ModelSpec("gpt-mini", "GPT-5.6 Luna", "openai",
              "gpt-5.6-luna", {"reasoning_effort": "low"}),
    ModelSpec("claude-opus", "Claude Opus 5", "anthropic",
              "claude-opus-5", {}),
    ModelSpec("claude", "Claude Sonnet 5", "anthropic",
              "claude-sonnet-5", {}),
    ModelSpec("claude-haiku", "Claude Haiku 4.5", "anthropic",
              "claude-haiku-4-5", {}),
    ModelSpec("gemini", "Gemini 3.1 Pro", "google",
              "gemini-3.1-pro-preview", {"thinking_level": "low"}),
    ModelSpec("gemini-flash", "Gemini 3.8 Flash", "google",
              "gemini-3.8-flash", {"thinking_level": "low"}),
    ModelSpec("gemini-flash-lite", "Gemini 3.5 Flash Lite", "google",
              "gemini-3.5-flash-lite", {"thinking_level": "low"}),
]

MODEL_MAP: Dict[str, ModelSpec] = {m.model_type: m for m in MODELS}

# 旧バージョンのconfig.jsonとの互換用（旧model_type → 現行model_type）
LEGACY_MODEL_ALIASES: Dict[str, str] = {
    "gpt4": "gpt",
}


def normalize_model_type(model_type: str) -> str:
    """
    旧いmodel_typeを現行のものに変換

    Args:
        model_type: config.jsonから読み込んだモデル識別子

    Returns:
        現行のモデル識別子（該当がなければ入力値をそのまま返す）
    """
    return LEGACY_MODEL_ALIASES.get(model_type, model_type)


def get_model(model_type: str) -> Optional[ModelSpec]:
    """
    モデル識別子からModelSpecを取得

    Args:
        model_type: モデル識別子

    Returns:
        ModelSpec、未知の識別子の場合はNone
    """
    return MODEL_MAP.get(model_type)


def is_valid_model_type(model_type: str) -> bool:
    """モデル識別子が有効かどうか"""
    return model_type in MODEL_MAP


def get_display_name(model_type: str, default: Optional[str] = None) -> str:
    """
    モデルの表示名を取得

    Args:
        model_type: モデル識別子
        default: 未知の識別子の場合に返す文字列（Noneなら識別子をそのまま返す）

    Returns:
        表示名
    """
    model = MODEL_MAP.get(model_type)
    if model:
        return model.display_name
    return default if default is not None else model_type


def get_provider_key(model_type: str) -> Optional[str]:
    """
    モデルに対応するプロバイダーのキーを取得

    Args:
        model_type: モデル識別子

    Returns:
        "openai" / "anthropic" / "google" 等、未知の識別子の場合はNone
    """
    model = MODEL_MAP.get(model_type)
    return model.provider if model else None


def models_by_provider() -> List[Tuple[ProviderSpec, List[ModelSpec]]]:
    """
    プロバイダーごとにグループ化したモデル一覧を取得

    メニューやラジオボタンの区切り表示に使用する。

    Returns:
        (ProviderSpec, そのプロバイダーのModelSpecリスト)のリスト。
        MODELSに登場する順序を保持する。
    """
    grouped: Dict[str, List[ModelSpec]] = {}
    order: List[str] = []
    for model in MODELS:
        if model.provider not in grouped:
            grouped[model.provider] = []
            order.append(model.provider)
        grouped[model.provider].append(model)
    return [(PROVIDER_MAP[key], grouped[key]) for key in order]
