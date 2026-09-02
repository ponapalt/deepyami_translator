"""
API設定ダイアログUIモジュール
各プロバイダーのAPIキーのみを管理する

モデルの選択はメニューバーの「モデル」メニューで行うため、
このダイアログはAPIキーの入力に専念する。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from src.config_manager import ConfigManager
from src import models


class SettingsDialog:
    """API設定ダイアログクラス"""

    # ダイアログの幅
    DIALOG_WIDTH = 500
    # APIキー欄以外の要素（タイトル・説明・ボタン）に必要な高さ
    BASE_HEIGHT = 200
    # プロバイダー1件あたりのAPIキー入力欄の高さ
    PROVIDER_ROW_HEIGHT = 62

    def __init__(self, parent, config_manager: ConfigManager):
        """
        Args:
            parent: 親ウィンドウ
            config_manager: 設定管理オブジェクト
        """
        self.parent = parent
        self.config_manager = config_manager
        self.result = False  # 保存ボタンが押されたかどうか

        # ダイアログウィンドウの作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("API設定")
        # プロバイダー数に応じて高さを自動調整
        height = self.BASE_HEIGHT + self.PROVIDER_ROW_HEIGHT * len(models.PROVIDERS)
        self.dialog.geometry(f"{self.DIALOG_WIDTH}x{height}")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ウィンドウを中央に配置
        self._center_window()

        # UI要素の作成
        self._create_widgets()

        # 現在の設定を読み込み
        self._load_current_settings()

        # ダイアログをアクティブにする
        self.dialog.focus_set()

    def _center_window(self):
        """ウィンドウを画面中央に配置"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        """UI要素を作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="APIキーの設定",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 5))

        # 説明
        ttk.Label(
            main_frame,
            text="使用するプロバイダーのAPIキーを入力してください。\n"
                 "モデルの切り替えは「モデル」メニューから行えます。",
            justify=tk.LEFT,
            foreground="#555555"
        ).pack(anchor=tk.W, pady=(0, 15))

        # APIキーフレーム
        api_frame = ttk.LabelFrame(main_frame, text="APIキー", padding="10")
        api_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # models.PROVIDERS からAPIキー入力欄を生成（全プロバイダーを常時表示）
        self.api_key_entries = {}
        for provider in models.PROVIDERS:
            ttk.Label(api_frame, text=provider.api_key_label).pack(anchor=tk.W)
            entry_frame = ttk.Frame(api_frame)
            entry_frame.pack(fill=tk.X, pady=(5, 10))
            entry = ttk.Entry(entry_frame, show="*", width=40)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            show_btn = ttk.Button(entry_frame, text="表示", width=6)
            show_btn.config(
                command=lambda e=entry, b=show_btn: self._toggle_password(e, b)
            )
            show_btn.pack(side=tk.LEFT, padx=(5, 0))

            self.api_key_entries[provider.key] = entry

        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="保存",
            command=self._on_save,
            width=15
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            button_frame,
            text="キャンセル",
            command=self._on_cancel,
            width=15
        ).pack(side=tk.RIGHT)

    def _toggle_password(self, entry: ttk.Entry, button: ttk.Button):
        """パスワードの表示/非表示を切り替え"""
        if entry.cget('show') == '*':
            entry.config(show='')
            button.config(text='隠す')
        else:
            entry.config(show='*')
            button.config(text='表示')

    def _load_current_settings(self):
        """現在の設定を読み込み"""
        api_keys = self.config_manager.config.get("api_keys", {})
        for provider_key, entry in self.api_key_entries.items():
            entry.insert(0, api_keys.get(provider_key, ""))

    def _on_save(self):
        """保存ボタンクリック時の処理"""
        # APIキーを取得
        api_keys = {
            provider_key: entry.get().strip()
            for provider_key, entry in self.api_key_entries.items()
        }

        # 最低1つはAPIキーが必要
        if not any(api_keys.values()):
            messagebox.showerror(
                "エラー",
                "APIキーを少なくとも1つ入力してください。"
            )
            return

        # 設定を保存
        for key, value in api_keys.items():
            self.config_manager.set_api_key(key, value)

        # モデル未選択、または選択中モデルのAPIキーが失われた場合は
        # 使用可能なモデルを自動選択する（初回起動時もこの経路で設定が完了する）
        if not self.config_manager.get_current_api_key():
            fallback = self._find_available_model(api_keys)
            if fallback:
                self.config_manager.set_model_type(fallback)

        if self.config_manager.save():
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("エラー", "設定の保存に失敗しました。")

    @staticmethod
    def _find_available_model(api_keys: dict) -> str:
        """
        APIキーが入力済みのプロバイダーのうち、最初に使えるモデルを返す

        Args:
            api_keys: プロバイダーキー → APIキーの辞書

        Returns:
            モデル識別子。該当がない場合は空文字列
        """
        for model in models.MODELS:
            if api_keys.get(model.provider):
                return model.model_type
        return ""

    def _on_cancel(self):
        """キャンセルボタンクリック時の処理"""
        self.result = False
        self.dialog.destroy()

    def show(self) -> bool:
        """
        ダイアログを表示して結果を返す

        Returns:
            保存ボタンが押された場合True
        """
        self.dialog.wait_window()
        return self.result
