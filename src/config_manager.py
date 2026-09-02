"""
設定管理モジュール
APIキーとLLMモデル選択を管理
"""

import json
import os
from typing import Dict, Optional

from src import models


class ConfigManager:
    """設定ファイルの読み書きを管理するクラス"""

    # 翻訳スタイルの一覧（唯一の定義場所）
    # llm_service.TranslationService.STYLE_INSTRUCTIONS のキーと一致させること
    TRANSLATION_STYLES = ["ビジネス", "標準", "友人"]

    DEFAULT_CONFIG = {
        "model_type": "",  # models.MODELS のいずれかの model_type
        # プロバイダーが増えても models.PROVIDERS を編集するだけでよい
        "api_keys": {provider.key: "" for provider in models.PROVIDERS},
        "last_source_lang": "Japanese",
        "last_target_lang": "English",
        "auto_translate_enabled": False,  # 自動翻訳のON/OFF
        "translation_style": "ビジネス",  # 翻訳スタイル: "ビジネス", "標準", "友人"
        "last_source_text": "",  # 最後に編集した翻訳元テキスト
        "last_target_text": "",   # 最後の翻訳結果
        "window_width": 1000,  # ウィンドウの幅
        "window_height": 600,  # ウィンドウの高さ
        "history_enabled": True  # 翻訳履歴の記録ON/OFF
    }

    def __init__(self, config_path: str = "config.json"):
        """
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self._load()

    def _load(self) -> Dict:
        """
        設定ファイルを読み込む

        Returns:
            設定辞書
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # デフォルト設定とマージ（新しいキーが追加された場合に対応）
                    config = self._default_config()
                    config.update(loaded_config)
                    # api_keysも個別にマージ
                    if "api_keys" in loaded_config:
                        api_keys = self.DEFAULT_CONFIG["api_keys"].copy()
                        api_keys.update(loaded_config["api_keys"])
                        config["api_keys"] = api_keys

                    # 後方互換性：古いモデル名を新しいモデル名に自動変換
                    model_type = config.get("model_type", "")
                    normalized = models.normalize_model_type(model_type)
                    if normalized != model_type:
                        config["model_type"] = normalized
                        print(f"設定ファイルのモデル名を '{model_type}' から "
                              f"'{normalized}' に自動変換しました")

                    return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"設定ファイルの読み込みに失敗しました: {e}")
                return self._default_config()
        else:
            return self._default_config()

    @classmethod
    def _default_config(cls) -> Dict:
        """
        デフォルト設定のコピーを生成

        Returns:
            DEFAULT_CONFIGのコピー（api_keysもコピーするため、
            返り値を書き換えてもDEFAULT_CONFIGは汚染されない）
        """
        config = cls.DEFAULT_CONFIG.copy()
        config["api_keys"] = cls.DEFAULT_CONFIG["api_keys"].copy()
        return config

    def save(self) -> bool:
        """
        現在の設定をファイルに保存

        Returns:
            保存に成功したかどうか
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"設定ファイルの保存に失敗しました: {e}")
            return False

    def is_configured(self) -> bool:
        """
        設定が完了しているかチェック

        Returns:
            モデルとAPIキーが設定されているかどうか
        """
        model_type = self.config.get("model_type", "")
        if not model_type:
            return False

        return self.get_api_key_for_model(model_type) is not None

    def get_api_key_for_model(self, model_type: str) -> Optional[str]:
        """
        指定したモデルに対応するAPIキーを取得

        Args:
            model_type: モデル識別子

        Returns:
            APIキー、または設定されていない場合はNone
        """
        provider = models.get_provider_key(model_type)
        if provider is None:
            return None

        api_keys = self.config.get("api_keys", {})
        return api_keys.get(provider, "").strip() or None

    def get_current_api_key(self) -> Optional[str]:
        """
        現在選択されているモデルのAPIキーを取得

        Returns:
            APIキー、または設定されていない場合はNone
        """
        return self.get_api_key_for_model(self.config.get("model_type", ""))

    def get_model_type(self) -> str:
        """
        現在選択されているモデル識別子を取得

        Returns:
            モデル識別子（未設定の場合は空文字列）
        """
        return self.config.get("model_type", "")

    def set_model_type(self, model_type: str) -> None:
        """
        使用するLLMモデルを設定

        Args:
            model_type: models.MODELS に定義されたモデル識別子
        """
        if models.is_valid_model_type(model_type):
            self.config["model_type"] = model_type

    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        APIキーを設定

        Args:
            provider: models.PROVIDERS に定義されたプロバイダーキー
            api_key: APIキー
        """
        if provider in models.PROVIDER_MAP:
            self.config["api_keys"][provider] = api_key

    def get_last_languages(self) -> tuple:
        """
        最後に使用した言語ペアを取得

        Returns:
            (source_lang, target_lang)のタプル
        """
        return (
            self.config.get("last_source_lang", "Japanese"),
            self.config.get("last_target_lang", "English")
        )

    def set_last_languages(self, source_lang: str, target_lang: str) -> None:
        """
        最後に使用した言語ペアを保存

        Args:
            source_lang: 翻訳元言語
            target_lang: 翻訳先言語
        """
        self.config["last_source_lang"] = source_lang
        self.config["last_target_lang"] = target_lang

    def is_auto_translate_enabled(self) -> bool:
        """
        自動翻訳が有効かどうかを取得

        Returns:
            自動翻訳の有効/無効
        """
        return self.config.get("auto_translate_enabled", False)

    def set_auto_translate_enabled(self, enabled: bool) -> None:
        """
        自動翻訳の有効/無効を設定

        Args:
            enabled: 有効/無効
        """
        self.config["auto_translate_enabled"] = enabled

    def is_history_enabled(self) -> bool:
        """
        翻訳履歴の記録が有効かどうかを取得

        Returns:
            履歴記録の有効/無効
        """
        return self.config.get("history_enabled", True)

    def set_history_enabled(self, enabled: bool) -> None:
        """
        翻訳履歴の記録の有効/無効を設定

        Args:
            enabled: 有効/無効
        """
        self.config["history_enabled"] = enabled

    def get_translation_style(self) -> str:
        """
        翻訳スタイルを取得

        Returns:
            翻訳スタイル（TRANSLATION_STYLES のいずれか）
            設定ファイルに未知の値が入っていた場合は既定値を返す
            （呼び出し側は readonly の Combobox にそのまま流すため）
        """
        style = self.config.get("translation_style", "ビジネス")
        if style not in self.TRANSLATION_STYLES:
            return "ビジネス"
        return style

    def set_translation_style(self, style: str) -> None:
        """
        翻訳スタイルを設定

        Args:
            style: TRANSLATION_STYLES のいずれか
        """
        if style in self.TRANSLATION_STYLES:
            self.config["translation_style"] = style

    def get_last_texts(self) -> tuple:
        """
        最後に編集したテキストを取得

        Returns:
            (source_text, target_text)のタプル
        """
        return (
            self.config.get("last_source_text", ""),
            self.config.get("last_target_text", "")
        )

    def set_last_texts(self, source_text: str, target_text: str) -> None:
        """
        最後に編集したテキストを保存

        Args:
            source_text: 翻訳元テキスト
            target_text: 翻訳先テキスト
        """
        self.config["last_source_text"] = source_text
        self.config["last_target_text"] = target_text

    def get_window_size(self) -> tuple:
        """
        ウィンドウサイズを取得

        Returns:
            (width, height)のタプル
        """
        return (
            self.config.get("window_width", 1000),
            self.config.get("window_height", 600)
        )

    def set_window_size(self, width: int, height: int) -> None:
        """
        ウィンドウサイズを保存

        Args:
            width: ウィンドウの幅
            height: ウィンドウの高さ
        """
        self.config["window_width"] = width
        self.config["window_height"] = height
