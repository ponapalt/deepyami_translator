"""
設定ダイアログUIモジュール
LLMモデルとAPIキーの設定を管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
from src.config_manager import ConfigManager


class SettingsDialog:
    """設定ダイアログクラス"""

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
        self.dialog.geometry("500x500")
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
            text="LLMモデルとAPIキーの設定",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # モデル選択フレーム
        model_frame = ttk.LabelFrame(main_frame, text="LLMモデル", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 20))

        self.model_var = tk.StringVar()
        models = [
            ("GPT-4.1 (OpenAI)", "gpt4"),
            ("Claude Sonnet 4.5 (Anthropic)", "claude"),
            ("Gemini 2.5 Pro (Google)", "gemini")
        ]

        for text, value in models:
            rb = ttk.Radiobutton(
                model_frame,
                text=text,
                variable=self.model_var,
                value=value,
                command=self._on_model_change
            )
            rb.pack(anchor=tk.W, pady=2)

        # APIキーフレーム
        api_frame = ttk.LabelFrame(main_frame, text="APIキー", padding="10")
        api_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # OpenAI APIキー
        self.openai_frame = ttk.Frame(api_frame)
        ttk.Label(self.openai_frame, text="OpenAI API Key:").pack(anchor=tk.W)
        openai_entry_frame = ttk.Frame(self.openai_frame)
        openai_entry_frame.pack(fill=tk.X, pady=(5, 10))
        self.openai_entry = ttk.Entry(openai_entry_frame, show="*", width=40)
        self.openai_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.openai_show_btn = ttk.Button(
            openai_entry_frame,
            text="表示",
            width=6,
            command=lambda: self._toggle_password(self.openai_entry, self.openai_show_btn)
        )
        self.openai_show_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Anthropic APIキー
        self.anthropic_frame = ttk.Frame(api_frame)
        ttk.Label(self.anthropic_frame, text="Anthropic API Key:").pack(anchor=tk.W)
        anthropic_entry_frame = ttk.Frame(self.anthropic_frame)
        anthropic_entry_frame.pack(fill=tk.X, pady=(5, 10))
        self.anthropic_entry = ttk.Entry(anthropic_entry_frame, show="*", width=40)
        self.anthropic_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.anthropic_show_btn = ttk.Button(
            anthropic_entry_frame,
            text="表示",
            width=6,
            command=lambda: self._toggle_password(self.anthropic_entry, self.anthropic_show_btn)
        )
        self.anthropic_show_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Google APIキー
        self.google_frame = ttk.Frame(api_frame)
        ttk.Label(self.google_frame, text="Google API Key:").pack(anchor=tk.W)
        google_entry_frame = ttk.Frame(self.google_frame)
        google_entry_frame.pack(fill=tk.X, pady=(5, 10))
        self.google_entry = ttk.Entry(google_entry_frame, show="*", width=40)
        self.google_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.google_show_btn = ttk.Button(
            google_entry_frame,
            text="表示",
            width=6,
            command=lambda: self._toggle_password(self.google_entry, self.google_show_btn)
        )
        self.google_show_btn.pack(side=tk.LEFT, padx=(5, 0))

        # オプションフレーム
        option_frame = ttk.LabelFrame(main_frame, text="オプション", padding="10")
        option_frame.pack(fill=tk.X, pady=(0, 20))

        # 自動翻訳ON/OFF
        self.auto_translate_var = tk.BooleanVar()
        auto_translate_cb = ttk.Checkbutton(
            option_frame,
            text="自動翻訳を有効にする（編集後2秒で自動的に翻訳）",
            variable=self.auto_translate_var
        )
        auto_translate_cb.pack(anchor=tk.W)

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

    def _on_model_change(self):
        """モデル選択変更時の処理"""
        model = self.model_var.get()

        # すべてのフレームを非表示
        self.openai_frame.pack_forget()
        self.anthropic_frame.pack_forget()
        self.google_frame.pack_forget()

        # 選択されたモデルに対応するフレームを表示
        if model == "gpt4":
            self.openai_frame.pack(fill=tk.X)
        elif model == "claude":
            self.anthropic_frame.pack(fill=tk.X)
        elif model == "gemini":
            self.google_frame.pack(fill=tk.X)

    def _load_current_settings(self):
        """現在の設定を読み込み"""
        config = self.config_manager.config

        # モデルタイプを設定
        model_type = config.get("model_type", "")
        if model_type:
            self.model_var.set(model_type)
            self._on_model_change()

        # APIキーを設定
        api_keys = config.get("api_keys", {})
        self.openai_entry.insert(0, api_keys.get("openai", ""))
        self.anthropic_entry.insert(0, api_keys.get("anthropic", ""))
        self.google_entry.insert(0, api_keys.get("google", ""))

        # 自動翻訳設定を読み込み
        self.auto_translate_var.set(self.config_manager.is_auto_translate_enabled())

    def _on_save(self):
        """保存ボタンクリック時の処理"""
        model = self.model_var.get()

        if not model:
            messagebox.showerror("エラー", "LLMモデルを選択してください。")
            return

        # APIキーを取得
        openai_key = self.openai_entry.get().strip()
        anthropic_key = self.anthropic_entry.get().strip()
        google_key = self.google_entry.get().strip()

        # 選択されたモデルに対応するAPIキーが入力されているか確認
        if model == "gpt4" and not openai_key:
            messagebox.showerror("エラー", "OpenAI API Keyを入力してください。")
            return
        elif model == "claude" and not anthropic_key:
            messagebox.showerror("エラー", "Anthropic API Keyを入力してください。")
            return
        elif model == "gemini" and not google_key:
            messagebox.showerror("エラー", "Google API Keyを入力してください。")
            return

        # 設定を保存
        self.config_manager.set_model_type(model)
        self.config_manager.set_api_key("openai", openai_key)
        self.config_manager.set_api_key("anthropic", anthropic_key)
        self.config_manager.set_api_key("google", google_key)
        self.config_manager.set_auto_translate_enabled(self.auto_translate_var.get())

        if self.config_manager.save():
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("エラー", "設定の保存に失敗しました。")

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
