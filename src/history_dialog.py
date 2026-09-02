"""
翻訳履歴ダイアログUIモジュール
過去の翻訳・校正の結果を一覧・プレビューし、エディタへ復元する

一覧を持つためスクロールが必要で、SettingsDialog と違い
リサイズ可能（resizable(True, True)）にしている。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional

from src.history_manager import HistoryManager

# 一覧表示用の言語の略称（main_window.LANGUAGES に対応）
LANG_ABBREVIATIONS = {
    "Japanese": "JA",
    "Chinese-Simplified": "ZH-CN",
    "Chinese-Traditional": "ZH-TW",
    "Korean": "KO",
    "English": "EN"
}

# 種別の表示名
KIND_LABELS = {
    "translate": "翻訳",
    "proofread": "校正"
}

# 一覧の原文プレビューに表示する文字数
PREVIEW_LENGTH = 40


class HistoryDialog:
    """翻訳履歴ダイアログクラス"""

    DIALOG_WIDTH = 820
    DIALOG_HEIGHT = 560
    MIN_WIDTH = 640
    MIN_HEIGHT = 400

    def __init__(self, parent, history_manager: HistoryManager):
        """
        Args:
            parent: 親ウィンドウ
            history_manager: 履歴管理オブジェクト
        """
        self.parent = parent
        self.history_manager = history_manager
        self.result: Optional[Dict] = None  # 「復元」されたエントリ

        # id -> エントリ の対応（Treeview の iid にエントリIDを使う）
        self.entries_by_id: Dict[str, Dict] = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("翻訳履歴")
        self.dialog.geometry(f"{self.DIALOG_WIDTH}x{self.DIALOG_HEIGHT}")
        self.dialog.resizable(True, True)
        self.dialog.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._center_window()
        self._create_widgets()
        self._reload_entries()

        self.dialog.bind('<Escape>', lambda e: self._on_close())
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
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 履歴一覧 ---
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("timestamp", "kind", "lang", "style", "preview")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=8,
            selectmode="browse",
            yscrollcommand=list_scrollbar.set
        )
        self.tree.heading("timestamp", text="日時")
        self.tree.heading("kind", text="種別")
        self.tree.heading("lang", text="言語")
        self.tree.heading("style", text="スタイル")
        self.tree.heading("preview", text="原文")
        self.tree.column("timestamp", width=110, stretch=False, anchor=tk.W)
        self.tree.column("kind", width=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("lang", width=90, stretch=False, anchor=tk.W)
        self.tree.column("style", width=80, stretch=False, anchor=tk.W)
        self.tree.column("preview", width=380, stretch=True, anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.tree.yview)

        self.tree.bind('<<TreeviewSelect>>', self._on_select_entry)
        self.tree.bind('<Double-Button-1>', self._on_restore_by_double_click)

        # --- プレビュー（左右2分割：メインウィンドウと同じ流儀） ---
        preview_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        preview_pane.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        source_frame = ttk.Frame(preview_pane)
        preview_pane.add(source_frame, weight=1)
        self.source_label = ttk.Label(source_frame, text="原文:")
        self.source_label.pack(anchor=tk.W)
        self.source_preview = self._create_preview_text(source_frame)

        result_frame = ttk.Frame(preview_pane)
        preview_pane.add(result_frame, weight=1)
        self.result_label = ttk.Label(result_frame, text="訳文:")
        self.result_label.pack(anchor=tk.W)
        self.result_preview = self._create_preview_text(result_frame)

        # --- 使用モデル表示 ---
        self.model_label = ttk.Label(main_frame, text="", foreground="gray")
        self.model_label.pack(fill=tk.X, pady=(8, 8))

        # --- ボタン ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # 右詰めのため、右に置きたいものから順にpackする
        ttk.Button(
            button_frame, text="閉じる", command=self._on_close, width=12
        ).pack(side=tk.RIGHT, padx=(5, 0))

        self.clear_btn = ttk.Button(
            button_frame, text="すべて削除", command=self._on_clear, width=12
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.delete_btn = ttk.Button(
            button_frame, text="削除", command=self._on_delete, width=12
        )
        self.delete_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.restore_btn = ttk.Button(
            button_frame, text="復元", command=self._on_restore, width=12
        )
        self.restore_btn.pack(side=tk.RIGHT)

    def _create_preview_text(self, parent) -> tk.Text:
        """読み取り専用のプレビュー用テキストを作成"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(
            frame,
            wrap=tk.WORD,
            font=('Arial', 10),
            bg="#f5f5f5",
            height=6,
            yscrollcommand=scrollbar.set
        )
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)

        # 編集を防ぐために、キー入力をブロック（コピー系のショートカットは許可）
        def block_edit(event):
            if event.state & 0x4:  # Control キーが押されている
                if event.keysym in ('c', 'C', 'a', 'A', 'Insert'):
                    return None
            return "break"

        text.bind('<Key>', block_edit)
        return text

    def _reload_entries(self):
        """履歴を読み直して一覧を再構築"""
        self.tree.delete(*self.tree.get_children())
        self.entries_by_id.clear()

        for entry in self.history_manager.get_entries():
            entry_id = entry.get("id")
            if not entry_id:
                continue
            self.entries_by_id[entry_id] = entry
            self.tree.insert(
                "", tk.END, iid=entry_id,
                values=(
                    self._format_timestamp(entry.get("timestamp", "")),
                    KIND_LABELS.get(entry.get("kind"), entry.get("kind", "")),
                    self._format_languages(entry),
                    entry.get("style", ""),
                    self._format_preview(entry.get("source_text", ""))
                )
            )

        self._clear_preview()
        self._update_button_state()

        # 履歴があれば先頭（最新）を選択しておく
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])

    @staticmethod
    def _format_timestamp(timestamp: str) -> str:
        """ISO 8601 の日時を "MM/DD HH:MM" に整形"""
        # "2026-09-03T12:04:33" を分解する。想定外の形式ならそのまま返す
        try:
            date_part, time_part = timestamp.split("T")
            _, month, day = date_part.split("-")
            hour, minute = time_part.split(":")[:2]
            return f"{month}/{day} {hour}:{minute}"
        except ValueError:
            return timestamp

    @staticmethod
    def _format_languages(entry: Dict) -> str:
        """言語表示（例: JA→EN）を作る。校正は翻訳先がないので原文の言語のみ"""
        source_lang = entry.get("source_lang") or ""
        target_lang = entry.get("target_lang") or ""
        source = LANG_ABBREVIATIONS.get(source_lang, source_lang)
        if not target_lang:
            return source
        target = LANG_ABBREVIATIONS.get(target_lang, target_lang)
        return f"{source}→{target}"

    @staticmethod
    def _format_preview(text: str) -> str:
        """一覧用に原文を1行へ潰して切り詰める"""
        single_line = " ".join(text.split())
        if len(single_line) > PREVIEW_LENGTH:
            return single_line[:PREVIEW_LENGTH] + "…"
        return single_line

    def _selected_entry(self) -> Optional[Dict]:
        """現在選択されているエントリを取得"""
        selection = self.tree.selection()
        if not selection:
            return None
        return self.entries_by_id.get(selection[0])

    def _set_preview_text(self, widget: tk.Text, text: str):
        """プレビュー用テキストの中身を差し替える"""
        widget.delete("1.0", tk.END)
        if text:
            widget.insert("1.0", text)

    def _clear_preview(self):
        """プレビューを空にする"""
        self.source_label.config(text="原文:")
        self.result_label.config(text="訳文:")
        self._set_preview_text(self.source_preview, "")
        self._set_preview_text(self.result_preview, "")
        self.model_label.config(text="")

    def _update_button_state(self):
        """選択の有無に応じてボタンの有効/無効を切り替える"""
        has_selection = self._selected_entry() is not None
        state = tk.NORMAL if has_selection else tk.DISABLED
        self.restore_btn.config(state=state)
        self.delete_btn.config(state=state)
        self.clear_btn.config(
            state=tk.NORMAL if self.entries_by_id else tk.DISABLED
        )

    def _on_select_entry(self, event=None):
        """一覧の選択が変わったときにプレビューを更新"""
        entry = self._selected_entry()
        if entry is None:
            self._clear_preview()
            self._update_button_state()
            return

        # 校正は「原文/訳文」ではなく「校正前/校正後」
        if entry.get("kind") == "proofread":
            self.source_label.config(text="校正前:")
            self.result_label.config(text="校正後:")
        else:
            self.source_label.config(text="原文:")
            self.result_label.config(text="訳文:")

        self._set_preview_text(self.source_preview, entry.get("source_text", ""))
        self._set_preview_text(self.result_preview, entry.get("result_text", ""))
        self.model_label.config(
            text=f"使用モデル: {entry.get('model_display') or '不明'}"
        )
        self._update_button_state()

    def _on_restore_by_double_click(self, event=None):
        """一覧のダブルクリックで復元"""
        # ヘッダーのダブルクリック（列幅調整）では復元しない
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        self._on_restore()

    def _on_restore(self):
        """選択中のエントリを復元して閉じる"""
        entry = self._selected_entry()
        if entry is None:
            return
        self.result = entry
        self.dialog.destroy()

    def _on_delete(self):
        """選択中のエントリを削除"""
        entry = self._selected_entry()
        if entry is None:
            return
        self.history_manager.delete(entry["id"])
        if not self.history_manager.save():
            messagebox.showerror("エラー", "履歴の保存に失敗しました。",
                                 parent=self.dialog)
        self._reload_entries()

    def _on_clear(self):
        """すべての履歴を削除"""
        if not self.entries_by_id:
            return
        if not messagebox.askyesno(
            "確認",
            "翻訳履歴をすべて削除します。よろしいですか？\n"
            "（この操作は元に戻せません）",
            parent=self.dialog
        ):
            return
        self.history_manager.clear()
        if not self.history_manager.save():
            messagebox.showerror("エラー", "履歴の保存に失敗しました。",
                                 parent=self.dialog)
        self._reload_entries()

    def _on_close(self):
        """閉じるボタンクリック時の処理"""
        self.result = None
        self.dialog.destroy()

    def show(self) -> Optional[Dict]:
        """
        ダイアログを表示して結果を返す

        Returns:
            「復元」されたエントリ。復元せずに閉じた場合はNone
        """
        self.dialog.wait_window()
        return self.result
