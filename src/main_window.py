"""
メインウィンドウUIモジュール
アプリケーションのメイン画面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
        self.current_file = None
        self.is_modified = False

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
        file_menu.add_command(label="新規作成", command=self._on_new, accelerator="Ctrl+N")
        file_menu.add_command(label="開く", command=self._on_open, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="保存", command=self._on_save, accelerator="Ctrl+S")
        file_menu.add_command(label="名前を付けて保存", command=self._on_save_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self._on_exit)

        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="元に戻す", command=self._on_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="やり直し", command=self._on_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="切り取り", command=self._on_cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="コピー", command=self._on_copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="貼り付け", command=self._on_paste, accelerator="Ctrl+V")

        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="API設定", command=self._on_settings)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._on_about)

        # キーボードショートカット
        self.root.bind('<Control-n>', lambda e: self._on_new())
        self.root.bind('<Control-o>', lambda e: self._on_open())
        self.root.bind('<Control-s>', lambda e: self._on_save())
        self.root.bind('<Control-Shift-S>', lambda e: self._on_save_as())

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
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        # 左側: 翻訳元言語
        left_lang_frame = ttk.Frame(control_frame)
        left_lang_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(left_lang_frame, text="翻訳元:").pack(side=tk.LEFT, padx=(0, 5))
        self.source_lang_var = tk.StringVar()
        self.source_lang_combo = ttk.Combobox(
            left_lang_frame,
            textvariable=self.source_lang_var,
            values=self.LANGUAGES,
            state="readonly",
            width=20
        )
        self.source_lang_combo.pack(side=tk.LEFT)

        # 中央: 翻訳ボタン
        self.translate_btn = ttk.Button(
            control_frame,
            text="翻訳 →",
            command=self._on_translate,
            width=15
        )
        self.translate_btn.pack(side=tk.LEFT, padx=20)

        # 右側: 翻訳先言語
        right_lang_frame = ttk.Frame(control_frame)
        right_lang_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(right_lang_frame, text="翻訳先:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_lang_var = tk.StringVar()
        self.target_lang_combo = ttk.Combobox(
            right_lang_frame,
            textvariable=self.target_lang_var,
            values=self.LANGUAGES,
            state="readonly",
            width=20
        )
        self.target_lang_combo.pack(side=tk.LEFT)

        # テキストエリアフレーム
        text_frame = ttk.Frame(self.root)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 左側: 翻訳元テキスト
        left_frame = ttk.Frame(text_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ttk.Label(left_frame, text="翻訳元テキスト").pack(anchor=tk.W, pady=(0, 5))

        self.source_text = tk.Text(
            left_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            undo=True,
            maxundo=-1
        )
        self.source_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.source_text.bind('<<Modified>>', self._on_text_modified)

        source_scrollbar = ttk.Scrollbar(left_frame, command=self.source_text.yview)
        source_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.source_text.config(yscrollcommand=source_scrollbar.set)

        # 右側: 翻訳先テキスト
        right_frame = ttk.Frame(text_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ttk.Label(right_frame, text="翻訳結果").pack(anchor=tk.W, pady=(0, 5))

        self.target_text = tk.Text(
            right_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            state=tk.DISABLED,
            bg="#f5f5f5"
        )
        self.target_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        target_scrollbar = ttk.Scrollbar(right_frame, command=self.target_text.yview)
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
        source_lang, target_lang = self.config_manager.get_last_languages()
        self.source_lang_var.set(source_lang)
        self.target_lang_var.set(target_lang)

    def _update_ui_state(self):
        """UI状態を更新"""
        is_configured = self.config_manager.is_configured()

        if is_configured:
            # 設定完了時: 警告バナーを非表示、コントロールを有効化
            self.warning_frame.pack_forget()
            self.source_text.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)
            self.source_lang_combo.config(state="readonly")
            self.target_lang_combo.config(state="readonly")
            self.status_bar.config(text="準備完了")
        else:
            # 設定未完了時: 警告バナーを表示、コントロールを無効化
            self.warning_frame.pack(fill=tk.X, after=self.root.nametowidget(str(self.root.winfo_children()[0])))
            self.source_text.config(state=tk.DISABLED)
            self.translate_btn.config(state=tk.DISABLED)
            self.source_lang_combo.config(state=tk.DISABLED)
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

    def _on_text_modified(self, event=None):
        """テキスト変更時の処理"""
        if self.source_text.edit_modified():
            self.is_modified = True
            self._update_title()
            self.source_text.edit_modified(False)

    def _update_title(self):
        """ウィンドウタイトルを更新"""
        title = "DeepYami翻訳アプリ"
        if self.current_file:
            title = f"{self.current_file} - {title}"
        if self.is_modified:
            title = f"*{title}"
        self.root.title(title)

    def _on_translate(self):
        """翻訳ボタンクリック時の処理"""
        if not self.translation_service:
            messagebox.showerror("エラー", "翻訳サービスが初期化されていません。")
            return

        source_text = self.source_text.get("1.0", tk.END).strip()
        if not source_text:
            messagebox.showwarning("警告", "翻訳するテキストを入力してください。")
            return

        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()

        if not source_lang or not target_lang:
            messagebox.showwarning("警告", "翻訳元と翻訳先の言語を選択してください。")
            return

        if source_lang == target_lang:
            messagebox.showwarning("警告", "翻訳元と翻訳先の言語が同じです。")
            return

        # 言語設定を保存
        self.config_manager.set_last_languages(source_lang, target_lang)
        self.config_manager.save()

        # 翻訳処理を別スレッドで実行
        self.status_bar.config(text="翻訳中...")
        self.translate_btn.config(state=tk.DISABLED)

        def translate_thread():
            try:
                result = self.translation_service.translate(
                    source_text,
                    source_lang,
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

    def _on_new(self):
        """新規作成"""
        if self._confirm_save_changes():
            self.source_text.delete("1.0", tk.END)
            self.target_text.config(state=tk.NORMAL)
            self.target_text.delete("1.0", tk.END)
            self.target_text.config(state=tk.DISABLED)
            self.current_file = None
            self.is_modified = False
            self._update_title()

    def _on_open(self):
        """ファイルを開く"""
        if self._confirm_save_changes():
            file_path = filedialog.askopenfilename(
                title="ファイルを開く",
                filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.source_text.delete("1.0", tk.END)
                    self.source_text.insert("1.0", content)
                    self.current_file = file_path
                    self.is_modified = False
                    self._update_title()
                except Exception as e:
                    messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{str(e)}")

    def _on_save(self):
        """保存"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        """名前を付けて保存"""
        file_path = filedialog.asksaveasfilename(
            title="名前を付けて保存",
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            self._save_to_file(file_path)

    def _save_to_file(self, file_path: str):
        """ファイルに保存"""
        try:
            content = self.source_text.get("1.0", tk.END)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.current_file = file_path
            self.is_modified = False
            self._update_title()
            self.status_bar.config(text=f"保存しました: {file_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの保存に失敗しました:\n{str(e)}")

    def _confirm_save_changes(self) -> bool:
        """変更を保存するか確認"""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "確認",
                "変更を保存しますか?"
            )
            if result is True:  # Yes
                self._on_save()
                return True
            elif result is False:  # No
                return True
            else:  # Cancel
                return False
        return True

    def _on_exit(self):
        """終了"""
        if self._confirm_save_changes():
            self.root.quit()

    def _on_undo(self):
        """元に戻す"""
        try:
            self.source_text.edit_undo()
        except tk.TclError:
            pass

    def _on_redo(self):
        """やり直し"""
        try:
            self.source_text.edit_redo()
        except tk.TclError:
            pass

    def _on_cut(self):
        """切り取り"""
        try:
            self.source_text.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def _on_copy(self):
        """コピー"""
        try:
            self.source_text.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def _on_paste(self):
        """貼り付け"""
        try:
            self.source_text.event_generate("<<Paste>>")
        except tk.TclError:
            pass

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
