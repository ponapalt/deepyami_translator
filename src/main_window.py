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


class ToolTip:
    """ツールチップを表示するクラス（他のWindowsアプリと同様、遅延表示）"""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay  # ミリ秒単位の遅延時間
        self.tooltip_window = None
        self.timer_id = None
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        self.widget.bind('<Motion>', self.on_motion)

    def on_enter(self, event=None):
        """マウスがウィジェットに入った時"""
        self.schedule_tooltip(event)

    def on_motion(self, event=None):
        """マウスが動いた時（タイマーをリセット）"""
        self.cancel_tooltip()
        self.schedule_tooltip(event)

    def on_leave(self, event=None):
        """マウスがウィジェットから離れた時"""
        self.cancel_tooltip()
        self.hide_tooltip()

    def schedule_tooltip(self, event):
        """遅延後にツールチップを表示するようスケジュール"""
        self.cancel_tooltip()
        self.last_event = event
        self.timer_id = self.widget.after(self.delay, self.show_tooltip)

    def cancel_tooltip(self):
        """スケジュールされたツールチップをキャンセル"""
        if self.timer_id:
            self.widget.after_cancel(self.timer_id)
            self.timer_id = None

    def show_tooltip(self):
        """ツールチップを表示"""
        if self.tooltip_window or not self.text:
            return

        # マウスカーソルの位置にツールチップを表示
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 9))
        label.pack()

    def hide_tooltip(self):
        """ツールチップを非表示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


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

    # 翻訳スタイルリスト
    STYLES = [
        "ビジネス",
        "標準",
        "友人"
    ]

    # モデル名の表示マッピング
    MODEL_DISPLAY_NAMES = {
        "gpt4": "GPT-4.1",
        "gpt4-mini": "GPT-4.1-mini",
        "claude": "Claude Sonnet 4.5",
        "claude-haiku": "Claude Haiku 4.5",
        "gemini": "Gemini 2.5 Pro",
        "gemini-flash": "Gemini Flash 2.5"
    }

    def __init__(self, root: tk.Tk, config_manager: ConfigManager):
        """
        Args:
            root: Tkルートウィンドウ
            config_manager: 設定管理オブジェクト
        """
        self.root = root
        self.config_manager = config_manager
        self.translation_service = None
        self.debounce_timer = None  # 自動翻訳用タイマー

        # ウィンドウの設定
        self.root.title("DeepYami翻訳アプリ - Tcl/TkとLLMを使った翻訳ツール")

        # 保存されたウィンドウサイズを復元
        width, height = self.config_manager.get_window_size()
        self.root.geometry(f"{width}x{height}")

        # メニューバーの作成
        self._create_menu()

        # UI要素の作成
        self._create_widgets()

        # 初期状態の設定
        self._update_ui_state()

        # 翻訳サービスの初期化
        if self.config_manager.is_configured():
            self._initialize_translation_service()
        else:
            # 未設定の場合もモデル表示を初期化
            self._update_model_display(None)

        # 最後に編集したテキストを復元（debounceが発火しないようにイベントを一時解除）
        self._restore_last_texts()

        # ウィンドウ終了時にテキストを保存
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _create_menu(self):
        """メニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self._on_exit, accelerator="Alt+F4")

        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="元に戻す", command=self._on_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="やり直し", command=self._on_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="切り取り", command=self._on_cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="コピー", command=self._on_copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="貼り付け", command=self._on_paste, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="すべて選択", command=self._on_select_all, accelerator="Ctrl+A")

        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="API設定", command=self._on_settings)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._on_about)

        # キーボードショートカット
        # Ctrl+A以外はTextウィジェットのデフォルト動作を使用
        # Ctrl+Aのみカスタム実装（全選択）
        self.root.bind('<Control-a>', lambda e: self._on_select_all())

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

        # PanedWindowで左右分割（自動リサイズ対応）
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 左側: 翻訳元テキスト
        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame, weight=1)

        # 左側コントロール（翻訳先言語、スタイル、ボタン）
        left_control = ttk.Frame(left_frame)
        left_control.pack(fill=tk.X, pady=(0, 5))

        # 翻訳先言語
        ttk.Label(left_control, text="翻訳先:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_lang_var = tk.StringVar()
        self.target_lang_combo = ttk.Combobox(
            left_control,
            textvariable=self.target_lang_var,
            values=self.LANGUAGES,
            state="readonly",
            width=18
        )
        self.target_lang_combo.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.target_lang_combo, "翻訳先の言語を選択")

        # 翻訳スタイル
        ttk.Label(left_control, text="スタイル:").pack(side=tk.LEFT, padx=(0, 5))
        self.style_var = tk.StringVar()
        self.style_combo = ttk.Combobox(
            left_control,
            textvariable=self.style_var,
            values=self.STYLES,
            state="readonly",
            width=10
        )
        self.style_combo.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.style_combo, "翻訳のスタイルを選択")

        # 翻訳ボタン
        self.translate_btn = ttk.Button(
            left_control,
            text="翻訳 →",
            command=self._on_translate,
            width=10
        )
        self.translate_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(self.translate_btn, "選択した言語とスタイルで翻訳を実行")

        # 校正ボタン
        self.proofread_btn = ttk.Button(
            left_control,
            text="校正",
            command=self._on_proofread,
            width=10
        )
        self.proofread_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(self.proofread_btn, "元の言語を維持したまま文法・スペルを修正")

        # 左側テキストエリア
        source_frame = ttk.Frame(left_frame)
        source_frame.pack(fill=tk.BOTH, expand=True)

        # スクロールバー（常に表示）- テキストより先にpackする
        source_scrollbar = ttk.Scrollbar(source_frame)
        source_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.source_text = tk.Text(
            source_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            undo=True,
            maxundo=-1,
            yscrollcommand=source_scrollbar.set
        )
        self.source_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        source_scrollbar.config(command=self.source_text.yview)

        # テキスト変更時のイベントバインディング（自動翻訳用）
        self.source_text.bind('<KeyRelease>', self._on_text_change)

        # コンテキストメニューのバインディング
        self.source_text.bind('<Button-3>', self._show_source_context_menu)  # 右クリック
        self.source_text.bind('<App>', self._show_source_context_menu)  # コンテキストメニューキー
        self.source_text.bind('<Control-F10>', self._show_source_context_menu)  # Ctrl+F10

        # ツールチップを追加（遅延表示）
        ToolTip(self.source_text, "翻訳元テキスト")

        # 右側: 翻訳結果テキスト
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=1)

        # 右側コントロール（入れ替えボタン・コピーボタン）
        right_control = ttk.Frame(right_frame)
        right_control.pack(fill=tk.X, pady=(0, 5))

        # 入れ替えボタン
        self.swap_btn = ttk.Button(
            right_control,
            text="⇄ 入れ替え",
            command=self._on_swap_languages,
            width=12
        )
        self.swap_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(self.swap_btn, "翻訳元と翻訳結果を入れ替える")

        self.copy_result_btn = ttk.Button(
            right_control,
            text="翻訳結果をコピー",
            command=self._on_copy_result,
            width=20
        )
        self.copy_result_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.copy_result_btn, "翻訳結果をクリップボードにコピー")

        # 現在のモデル表示ラベル
        self.current_model_label = ttk.Label(
            right_control,
            text="モデル: 未設定",
            font=('Arial', 9),
            foreground="#666666"
        )
        self.current_model_label.pack(side=tk.LEFT)
        ToolTip(self.current_model_label, "現在使用中のLLMモデル")

        # 右側テキストエリア
        target_frame = ttk.Frame(right_frame)
        target_frame.pack(fill=tk.BOTH, expand=True)

        # スクロールバー（常に表示）- テキストより先にpackする
        target_scrollbar = ttk.Scrollbar(target_frame)
        target_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.target_text = tk.Text(
            target_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            bg="#f5f5f5",
            yscrollcommand=target_scrollbar.set
        )
        self.target_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        target_scrollbar.config(command=self.target_text.yview)

        # 編集を防ぐために、キー入力をブロック（ただしコピー系のショートカットは許可）
        def block_edit(event):
            # Ctrl+C, Ctrl+A などのショートカットは許可
            if event.state & 0x4:  # Control キーが押されている
                if event.keysym in ('c', 'C', 'a', 'A', 'Insert'):
                    return None  # イベントを通す
            # その他のキー入力は全てブロック
            return "break"

        self.target_text.bind('<Key>', block_edit)

        # コンテキストメニューのバインディング
        self.target_text.bind('<Button-3>', self._show_target_context_menu)  # 右クリック
        self.target_text.bind('<App>', self._show_target_context_menu)  # コンテキストメニューキー
        self.target_text.bind('<Control-F10>', self._show_target_context_menu)  # Ctrl+F10

        # ツールチップを追加（遅延表示）
        ToolTip(self.target_text, "翻訳結果")

        # ステータスバー
        self.status_bar = ttk.Label(
            self.root,
            text="準備完了",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 最後に使用した言語とスタイルを設定
        _, target_lang = self.config_manager.get_last_languages()
        self.target_lang_var.set(target_lang)
        self.style_var.set(self.config_manager.get_translation_style())

    def _update_ui_state(self):
        """UI状態を更新"""
        is_configured = self.config_manager.is_configured()

        if is_configured:
            # 設定完了時: 警告バナーを非表示、コントロールを有効化
            self.warning_frame.pack_forget()
            self.source_text.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)
            self.proofread_btn.config(state=tk.NORMAL)
            self.swap_btn.config(state=tk.NORMAL)
            self.target_lang_combo.config(state="readonly")
            self.style_combo.config(state="readonly")
            self.copy_result_btn.config(state=tk.NORMAL)
            self.status_bar.config(text="準備完了")
        else:
            # 設定未完了時: 警告バナーを表示、コントロールを無効化
            self.warning_frame.pack(fill=tk.X, side=tk.TOP, before=self.paned_window)
            self.source_text.config(state=tk.DISABLED)
            self.translate_btn.config(state=tk.DISABLED)
            self.proofread_btn.config(state=tk.DISABLED)
            self.swap_btn.config(state=tk.DISABLED)
            self.target_lang_combo.config(state=tk.DISABLED)
            self.style_combo.config(state=tk.DISABLED)
            self.copy_result_btn.config(state=tk.DISABLED)
            self.status_bar.config(text="API設定が必要です")

    def _initialize_translation_service(self):
        """翻訳サービスを初期化"""
        try:
            model_type = self.config_manager.config.get("model_type")
            api_key = self.config_manager.get_current_api_key()

            if model_type and api_key:
                self.translation_service = TranslationService(model_type, api_key)
                model_display_name = self.MODEL_DISPLAY_NAMES.get(model_type, model_type.upper())
                self.status_bar.config(text=f"翻訳サービス準備完了 ({model_display_name})")
                self._update_model_display(model_type)
        except Exception as e:
            messagebox.showerror("エラー", f"翻訳サービスの初期化に失敗しました:\n{str(e)}")
            self.status_bar.config(text="翻訳サービスエラー")
            self._update_model_display(None)

    def _update_model_display(self, model_type: str = None):
        """現在のモデル表示を更新"""
        if model_type:
            model_display_name = self.MODEL_DISPLAY_NAMES.get(model_type, model_type)
            self.current_model_label.config(text=f"モデル: {model_display_name}")
        else:
            self.current_model_label.config(text="モデル: 未設定")

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

        style = self.style_var.get()

        if not style:
            messagebox.showwarning("警告", "翻訳スタイルを選択してください。")
            return

        # 言語設定とスタイルを保存（翻訳元は自動検出なので空文字列）
        self.config_manager.set_last_languages("", target_lang)
        self.config_manager.set_translation_style(style)
        self.config_manager.save()

        # 翻訳結果エリアをクリア
        self.target_text.delete("1.0", tk.END)

        # 翻訳処理を別スレッドで実行
        self.status_bar.config(text="翻訳中...")
        self.translate_btn.config(state=tk.DISABLED)
        self.proofread_btn.config(state=tk.DISABLED)

        def streaming_callback(token: str):
            """ストリーミング時に各トークンをUIに追加"""
            # UIスレッドで安全に実行
            self.root.after(0, lambda t=token: self.target_text.insert(tk.END, t))

        def translate_thread():
            try:
                result = self.translation_service.translate(
                    source_text,
                    target_lang,
                    style,
                    streaming_callback=streaming_callback
                )

                # UIスレッドで完了処理
                self.root.after(0, lambda: self._on_translation_complete(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_translation_error(str(e)))

        threading.Thread(target=translate_thread, daemon=True).start()

    def _on_translation_complete(self, result: str):
        """翻訳完了時の処理"""
        if result:
            self.status_bar.config(text="翻訳完了")
        else:
            messagebox.showerror("エラー", "翻訳に失敗しました。")
            self.status_bar.config(text="翻訳エラー")

        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _show_translation_result(self, result: str):
        """翻訳結果を表示（非ストリーミング用・後方互換性のため保持）"""
        if result:
            self.target_text.delete("1.0", tk.END)
            self.target_text.insert("1.0", result)
            self.status_bar.config(text="翻訳完了")
        else:
            messagebox.showerror("エラー", "翻訳に失敗しました。")
            self.status_bar.config(text="翻訳エラー")

        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _show_translation_error(self, error_msg: str):
        """翻訳エラーを表示"""
        messagebox.showerror("エラー", f"翻訳中にエラーが発生しました:\n{error_msg}")
        self.status_bar.config(text="翻訳エラー")
        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _on_proofread(self):
        """校正ボタンクリック時の処理"""
        if not self.translation_service:
            messagebox.showerror("エラー", "翻訳サービスが初期化されていません。")
            return

        source_text = self.source_text.get("1.0", tk.END).strip()
        if not source_text:
            messagebox.showwarning("警告", "校正するテキストを入力してください。")
            return

        style = self.style_var.get()

        if not style:
            messagebox.showwarning("警告", "翻訳スタイルを選択してください。")
            return

        # 校正元テキストを保存（ストリーミング表示用）
        original_text = source_text

        # テキストエリアをクリア
        self.source_text.delete("1.0", tk.END)

        # 校正処理を別スレッドで実行
        self.status_bar.config(text="校正中...")
        self.translate_btn.config(state=tk.DISABLED)
        self.proofread_btn.config(state=tk.DISABLED)

        def streaming_callback(token: str):
            """ストリーミング時に各トークンをUIに追加"""
            # UIスレッドで安全に実行
            self.root.after(0, lambda t=token: self.source_text.insert(tk.END, t))

        def proofread_thread():
            try:
                result = self.translation_service.proofread(
                    original_text,
                    style,
                    streaming_callback=streaming_callback
                )

                # UIスレッドで完了処理
                self.root.after(0, lambda: self._on_proofread_complete(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_proofread_error(str(e)))

        threading.Thread(target=proofread_thread, daemon=True).start()

    def _on_proofread_complete(self, result: str):
        """校正完了時の処理"""
        if result:
            self.status_bar.config(text="校正完了")
        else:
            messagebox.showerror("エラー", "校正に失敗しました。")
            self.status_bar.config(text="校正エラー")

        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _show_proofread_result(self, result: str):
        """校正結果を表示（非ストリーミング用・後方互換性のため保持）"""
        if result:
            self.source_text.delete("1.0", tk.END)
            self.source_text.insert("1.0", result)
            self.status_bar.config(text="校正完了")
        else:
            messagebox.showerror("エラー", "校正に失敗しました。")
            self.status_bar.config(text="校正エラー")

        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _show_proofread_error(self, error_msg: str):
        """校正エラーを表示"""
        messagebox.showerror("エラー", f"校正中にエラーが発生しました:\n{error_msg}")
        self.status_bar.config(text="校正エラー")
        self.translate_btn.config(state=tk.NORMAL)
        self.proofread_btn.config(state=tk.NORMAL)

    def _on_copy_result(self):
        """翻訳結果をクリップボードにコピー"""
        result = self.target_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            self.status_bar.config(text="翻訳結果をコピーしました")
        else:
            messagebox.showwarning("警告", "コピーする翻訳結果がありません。")

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

    def _on_select_all(self):
        """すべて選択"""
        try:
            self.source_text.tag_add(tk.SEL, "1.0", tk.END)
            self.source_text.mark_set(tk.INSERT, "1.0")
            self.source_text.see(tk.INSERT)
        except tk.TclError:
            pass
        return "break"  # イベントの伝播を停止

    def _on_text_change(self, event=None):
        """テキスト変更時にdebounceタイマーをリセット"""
        # 既存のタイマーをキャンセル
        if self.debounce_timer:
            self.root.after_cancel(self.debounce_timer)

        # 自動翻訳が有効な場合のみ、2秒後に自動翻訳を実行するタイマーをセット
        if (self.translation_service and
            self.config_manager.is_configured() and
            self.config_manager.is_auto_translate_enabled()):
            self.debounce_timer = self.root.after(2000, self._auto_translate)

    def _auto_translate(self):
        """2秒間の無操作後に自動翻訳を実行"""
        source_text = self.source_text.get("1.0", tk.END).strip()
        if source_text and self.target_lang_var.get():
            self._on_translate()

    def _on_exit(self):
        """アプリケーションを終了"""
        self.root.quit()

    def _on_window_close(self):
        """ウィンドウ閉じる時の処理（テキストとウィンドウサイズを保存）"""
        # 現在のテキストを保存
        source_text = self.source_text.get("1.0", tk.END).strip()
        target_text = self.target_text.get("1.0", tk.END).strip()
        self.config_manager.set_last_texts(source_text, target_text)

        # ウィンドウサイズを保存
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        self.config_manager.set_window_size(width, height)

        self.config_manager.save()
        # ウィンドウを閉じる
        self.root.destroy()

    def _restore_last_texts(self):
        """最後に編集したテキストを復元（debounceを発火させない）"""
        source_text, target_text = self.config_manager.get_last_texts()

        if source_text or target_text:
            # テキスト変更イベントを一時的に解除
            self.source_text.unbind('<KeyRelease>')

            # テキストを復元
            if source_text:
                self.source_text.insert("1.0", source_text)

            if target_text:
                self.target_text.insert("1.0", target_text)

            # イベントバインディングを再設定
            self.source_text.bind('<KeyRelease>', self._on_text_change)

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
            "- OpenAI GPT-4.1-mini\n"
            "- Anthropic Claude Sonnet 4.5\n"
            "- Anthropic Claude Haiku 4.5\n"
            "- Google Gemini 2.5 Pro\n"
            "- Google Gemini Flash 2.5"
        )

    def _detect_language(self, text: str) -> str:
        """
        テキストから言語を推定（アルゴリズム的に判定、LLMは使用しない）

        Args:
            text: 判定するテキスト

        Returns:
            推定された言語名（LANGUAGES内の値）
        """
        if not text or not text.strip():
            return "English"  # デフォルトは英語

        # 文字種のカウント
        hiragana_count = 0
        katakana_count = 0
        kanji_count = 0
        hangul_count = 0
        latin_count = 0
        simplified_chinese_chars = 0
        traditional_chinese_chars = 0

        # 簡体字特有の文字例（一部）
        simplified_chars = set('个们来国际现实认为')
        # 繁体字特有の文字例（一部）
        traditional_chars = set('個們來國際現實認為')

        for char in text:
            code_point = ord(char)

            # ひらがな (U+3040-U+309F)
            if 0x3040 <= code_point <= 0x309F:
                hiragana_count += 1
            # カタカナ (U+30A0-U+30FF)
            elif 0x30A0 <= code_point <= 0x30FF:
                katakana_count += 1
            # ハングル (U+AC00-U+D7AF)
            elif 0xAC00 <= code_point <= 0xD7AF or 0x1100 <= code_point <= 0x11FF:
                hangul_count += 1
            # CJK統合漢字 (U+4E00-U+9FFF)
            elif 0x4E00 <= code_point <= 0x9FFF:
                kanji_count += 1
                # 簡体字・繁体字の判定
                if char in simplified_chars:
                    simplified_chinese_chars += 1
                elif char in traditional_chars:
                    traditional_chinese_chars += 1
            # ラテン文字 (U+0041-U+005A, U+0061-U+007A)
            elif (0x0041 <= code_point <= 0x005A) or (0x0061 <= code_point <= 0x007A):
                latin_count += 1

        # 日本語判定: ひらがなまたはカタカナが含まれる
        if hiragana_count > 0 or katakana_count > 0:
            return "Japanese"

        # 韓国語判定: ハングルが含まれる
        if hangul_count > 0:
            return "Korean"

        # 中国語判定: 漢字が含まれるが日本語文字は含まれない
        if kanji_count > 0:
            # 簡体字と繁体字の判定
            if traditional_chinese_chars > simplified_chinese_chars:
                return "Chinese-Traditional"
            else:
                return "Chinese-Simplified"

        # 英語判定: 主にラテン文字
        if latin_count > 0:
            return "English"

        # デフォルトは英語
        return "English"

    def _show_source_context_menu(self, event):
        """翻訳元テキストエリアのコンテキストメニューを表示"""
        # コンテキストメニューを表示する前にテキストボックスをアクティブにする
        self.source_text.focus_set()

        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="元に戻す", command=self._on_undo, accelerator="Ctrl+Z")
        context_menu.add_command(label="やり直し", command=self._on_redo, accelerator="Ctrl+Y")
        context_menu.add_separator()
        context_menu.add_command(label="切り取り", command=self._on_cut, accelerator="Ctrl+X")
        context_menu.add_command(label="コピー", command=self._on_copy, accelerator="Ctrl+C")
        context_menu.add_command(label="貼り付け", command=self._on_paste, accelerator="Ctrl+V")
        context_menu.add_separator()
        context_menu.add_command(label="すべて選択", command=self._on_select_all, accelerator="Ctrl+A")

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _show_target_context_menu(self, event):
        """翻訳先テキストエリアのコンテキストメニューを表示"""
        # コンテキストメニューを表示する前にテキストボックスをアクティブにする
        self.target_text.focus_set()

        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="すべて選択", command=self._on_select_all_target, accelerator="Ctrl+A")
        context_menu.add_command(label="コピー", command=self._on_copy_target, accelerator="Ctrl+C")

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _on_select_all_target(self):
        """翻訳先テキストのすべて選択"""
        try:
            self.target_text.tag_add(tk.SEL, "1.0", tk.END)
            self.target_text.mark_set(tk.INSERT, "1.0")
            self.target_text.see(tk.INSERT)
        except tk.TclError:
            pass

    def _on_copy_target(self):
        """翻訳先テキストのコピー"""
        try:
            self.target_text.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def _on_swap_languages(self):
        """翻訳元と翻訳先のテキストを入れ替え、言語を自動推定"""
        # 翻訳元テキストと翻訳結果テキストを取得
        source_text = self.source_text.get("1.0", tk.END).strip()
        target_text = self.target_text.get("1.0", tk.END).strip()

        # 両方が空の場合は何もしない
        if not source_text and not target_text:
            messagebox.showwarning("警告", "入れ替えるテキストがありません。")
            return

        # テキスト変更イベントを一時的に解除（自動翻訳を防ぐ）
        self.source_text.unbind('<KeyRelease>')

        # テキストを入れ替え
        self.source_text.delete("1.0", tk.END)
        if target_text:
            self.source_text.insert("1.0", target_text)

        self.target_text.delete("1.0", tk.END)
        if source_text:
            self.target_text.insert("1.0", source_text)

        # 新しい翻訳元テキスト（元の翻訳結果）から言語を推定
        if target_text:
            detected_lang = self._detect_language(target_text)

            # 検出された言語を除く他の言語を翻訳先として設定
            # （同じ言語に翻訳しても意味がないため）
            available_langs = [lang for lang in self.LANGUAGES if lang != detected_lang]
            if available_langs:
                # デフォルトで英語を選択、なければリストの最初
                if "English" in available_langs and detected_lang != "English":
                    self.target_lang_var.set("English")
                else:
                    self.target_lang_var.set(available_langs[0])

        # イベントバインディングを再設定
        self.source_text.bind('<KeyRelease>', self._on_text_change)

        self.status_bar.config(text="テキストを入れ替えました")
