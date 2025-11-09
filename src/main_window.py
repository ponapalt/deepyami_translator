"""
メインウィンドウUIモジュール
アプリケーションのメイン画面
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from src.config_manager import ConfigManager
from src.settings_dialog import SettingsDialog
from src.llm_service import TranslationService


class MainWindow:
    """メインウィンドウクラス"""

    # 対応言語リスト
    LANGUAGES = [
        "Japanese",
        "Chinese-Simplified",
        "Chinese-Traditional",
        "Korean",
        "English"
    ]

    def __init__(self, root: tk.Tk, config_manager: ConfigManager):
        """
        Args:
            root: Tkルートウィンドウ
            config_manager: 設定管理オブジェクト
        """
        self.root = root
        self.config_manager = config_manager
        self.translation_service = None

        # ウィンドウの設定
        self.root.title("DeepYami翻訳アプリ")
        self.root.geometry("1000x600")

        # メニューバーの作成
        self._create_menu()

        # UI要素の作成
        self._create_widgets()

        # 初期状態の設定
        self._update_ui_state()

        # 翻訳サービスの初期化
        if self.config_manager.is_configured():
            self._initialize_translation_service()

    def _create_menu(self):
        """メニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self._on_exit)

        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="API設定", command=self._on_settings)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._on_about)

    def _create_widgets(self):
        """UI要素を作成"""
        # 警告バナーフレーム
        self.warning_frame = tk.Frame(self.root, bg="#ffeb3b", height=50)
        self.warning_label = tk.Label(
            self.warning_frame,
            text="⚠ API設定を完了してください",
            bg="#ffeb3b",
            font=('Arial', 11, 'bold')
        )
        self.warning_label.pack(side=tk.LEFT, padx=20, pady=10)

        warning_btn = tk.Button(
            self.warning_frame,
            text="設定を開く",
            command=self._on_settings,
            bg="#ffc107",
            activebackground="#ffb300",
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        warning_btn.pack(side=tk.RIGHT, padx=20, pady=10)

        # コントロールフレーム
        self.control_frame = ttk.Frame(self.root, padding="10")
        self.control_frame.pack(fill=tk.X)

        # 翻訳先言語選択
        lang_frame = ttk.Frame(self.control_frame)
        lang_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(lang_frame, text="翻訳先:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_lang_var = tk.StringVar()
        self.target_lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.target_lang_var,
            values=self.LANGUAGES,
            state="readonly",
            width=20
        )
        self.target_lang_combo.pack(side=tk.LEFT)

        # 翻訳ボタン
        self.translate_btn = ttk.Button(
            self.control_frame,
            text="翻訳 →",
            command=self._on_translate,
            width=15
        )
        self.translate_btn.pack(side=tk.LEFT, padx=20)

        # PanedWindowで左右分割（自動リサイズ対応）
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 左側: 翻訳元テキスト
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)

        ttk.Label(left_frame, text="翻訳元テキスト").pack(anchor=tk.W, pady=(0, 5))

        source_frame = ttk.Frame(left_frame)
        source_frame.pack(fill=tk.BOTH, expand=True)

        self.source_text = tk.Text(
            source_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            undo=True,
            maxundo=-1
        )
        self.source_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        source_scrollbar = ttk.Scrollbar(source_frame, command=self.source_text.yview)
        source_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.source_text.config(yscrollcommand=source_scrollbar.set)

        # 右側: 翻訳結果テキスト
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        ttk.Label(right_frame, text="翻訳結果").pack(anchor=tk.W, pady=(0, 5))

        target_frame = ttk.Frame(right_frame)
        target_frame.pack(fill=tk.BOTH, expand=True)

        self.target_text = tk.Text(
            target_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            state=tk.DISABLED,
            bg="#f5f5f5"
        )
        self.target_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        target_scrollbar = ttk.Scrollbar(target_frame, command=self.target_text.yview)
        target_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.target_text.config(yscrollcommand=target_scrollbar.set)

        # ステータスバー
        self.status_bar = ttk.Label(
            self.root,
            text="準備完了",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 最後に使用した言語を設定
        _, target_lang = self.config_manager.get_last_languages()
        self.target_lang_var.set(target_lang)

    def _update_ui_state(self):
        """UI状態を更新"""
        is_configured = self.config_manager.is_configured()

        if is_configured:
            # 設定完了時: 警告バナーを非表示、コントロールを有効化
            self.warning_frame.pack_forget()
            self.source_text.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)
            self.target_lang_combo.config(state="readonly")
            self.status_bar.config(text="準備完了")
        else:
            # 設定未完了時: 警告バナーを表示、コントロールを無効化
            self.warning_frame.pack(fill=tk.X, before=self.control_frame)
            self.source_text.config(state=tk.DISABLED)
            self.translate_btn.config(state=tk.DISABLED)
            self.target_lang_combo.config(state=tk.DISABLED)
            self.status_bar.config(text="API設定が必要です")

    def _initialize_translation_service(self):
        """翻訳サービスを初期化"""
        try:
            model_type = self.config_manager.config.get("model_type")
            api_key = self.config_manager.get_current_api_key()

            if model_type and api_key:
                self.translation_service = TranslationService(model_type, api_key)
                self.status_bar.config(text=f"翻訳サービス準備完了 ({model_type.upper()})")
        except Exception as e:
            messagebox.showerror("エラー", f"翻訳サービスの初期化に失敗しました:\n{str(e)}")
            self.status_bar.config(text="翻訳サービスエラー")

    def _on_translate(self):
        """翻訳ボタンクリック時の処理"""
        if not self.translation_service:
            messagebox.showerror("エラー", "翻訳サービスが初期化されていません。")
            return

        source_text = self.source_text.get("1.0", tk.END).strip()
        if not source_text:
            messagebox.showwarning("警告", "翻訳するテキストを入力してください。")
            return

        target_lang = self.target_lang_var.get()

        if not target_lang:
            messagebox.showwarning("警告", "翻訳先の言語を選択してください。")
            return

        # 言語設定を保存（翻訳元は自動検出なので空文字列）
        self.config_manager.set_last_languages("", target_lang)
        self.config_manager.save()

        # 翻訳処理を別スレッドで実行
        self.status_bar.config(text="翻訳中...")
        self.translate_btn.config(state=tk.DISABLED)

        def translate_thread():
            try:
                result = self.translation_service.translate(
                    source_text,
                    target_lang
                )

                # UIスレッドで結果を表示
                self.root.after(0, lambda: self._show_translation_result(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_translation_error(str(e)))

        threading.Thread(target=translate_thread, daemon=True).start()

    def _show_translation_result(self, result: str):
        """翻訳結果を表示"""
        if result:
            self.target_text.config(state=tk.NORMAL)
            self.target_text.delete("1.0", tk.END)
            self.target_text.insert("1.0", result)
            self.target_text.config(state=tk.DISABLED)
            self.status_bar.config(text="翻訳完了")
        else:
            messagebox.showerror("エラー", "翻訳に失敗しました。")
            self.status_bar.config(text="翻訳エラー")

        self.translate_btn.config(state=tk.NORMAL)

    def _show_translation_error(self, error_msg: str):
        """翻訳エラーを表示"""
        messagebox.showerror("エラー", f"翻訳中にエラーが発生しました:\n{error_msg}")
        self.status_bar.config(text="翻訳エラー")
        self.translate_btn.config(state=tk.NORMAL)

    def _on_exit(self):
        """終了"""
        self.root.quit()

    def _on_settings(self):
        """設定ダイアログを開く"""
        dialog = SettingsDialog(self.root, self.config_manager)
        if dialog.show():
            # 設定が保存された場合、翻訳サービスを再初期化
            self._initialize_translation_service()
            self._update_ui_state()

    def _on_about(self):
        """バージョン情報"""
        messagebox.showinfo(
            "バージョン情報",
            "DeepYami翻訳アプリ v1.0\n\n"
            "LangChainと複数のLLMモデルを使用した翻訳アプリケーション\n\n"
            "対応モデル:\n"
            "- OpenAI GPT-4.1\n"
            "- Anthropic Claude Sonnet 4.5\n"
            "- Google Gemini 2.5 Pro"
        )
