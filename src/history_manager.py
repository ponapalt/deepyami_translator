"""
翻訳履歴管理モジュール
翻訳・校正の結果を history.json に蓄積する
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional


def _is_incremental_edit(prev: str, new: str) -> bool:
    """
    一方が他方の先頭部分なら、同じ文を編集し続けている途中とみなす

    自動翻訳は入力が2秒止まるたびに走るため、素直に記録すると
    「これは」「これはテ」「これはテスト」…と履歴が量産される。
    前方一致を「どちらの向きでも」見るのは、バックスペースで一時的に
    短くなった場合も同じ編集セッションとして扱うため。

    Args:
        prev: 直前に記録した原文
        new: 今回の原文

    Returns:
        単純追記（または巻き戻し）とみなせるかどうか
    """
    if prev == new:
        return True
    shorter, longer = (prev, new) if len(prev) <= len(new) else (new, prev)
    return bool(shorter) and longer.startswith(shorter)


class HistoryManager:
    """翻訳履歴ファイルの読み書きを管理するクラス"""

    MAX_ENTRIES = 100  # これを超えた分は古いものから捨てる
    FORMAT_VERSION = 1

    def __init__(self, history_path: str = "history.json"):
        """
        Args:
            history_path: 履歴ファイルのパス
        """
        self.history_path = history_path
        # entries は新しい順（index 0 が最新）
        self.entries = self._load()

    def _load(self) -> List[Dict]:
        """
        履歴ファイルを読み込む

        Returns:
            エントリのリスト（新しい順）。読めない場合は空リスト
        """
        if not os.path.exists(self.history_path):
            return []

        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # 履歴が壊れていてもアプリは動かす（設定と違い失っても致命的ではない）
            print(f"履歴ファイルの読み込みに失敗しました: {e}")
            return []

        if not isinstance(data, dict):
            return []

        entries = data.get("entries", [])
        if not isinstance(entries, list):
            return []

        # 想定外の要素が混ざっていても落ちないように、辞書だけを残す
        return [entry for entry in entries if isinstance(entry, dict)][:self.MAX_ENTRIES]

    def save(self) -> bool:
        """
        現在の履歴をファイルに保存

        Returns:
            保存に成功したかどうか
        """
        data = {
            "version": self.FORMAT_VERSION,
            "entries": self.entries
        }
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"履歴ファイルの保存に失敗しました: {e}")
            return False

    def get_entries(self) -> List[Dict]:
        """
        履歴の一覧を取得

        Returns:
            エントリのリスト（新しい順）のコピー
        """
        return list(self.entries)

    def record(self, kind: str, source_text: str, result_text: str,
               source_lang: str, target_lang: Optional[str], style: str,
               model_type: str, model_display: str,
               auto: bool = False) -> Dict:
        """
        履歴に1件記録する（保存は行わないので、呼び出し側で save() すること）

        直近のエントリと同一視できる場合は、新規追加せずそれを更新する。
        判定は _should_merge() を参照。

        Args:
            kind: "translate" または "proofread"
            source_text: 原文（校正の場合は校正前のテキスト）
            result_text: 結果（校正の場合は校正後のテキスト）
            source_lang: 原文の推定言語
            target_lang: 翻訳先言語（校正の場合は None）
            style: 翻訳スタイル
            model_type: 使用したモデルの識別子
            model_display: 使用したモデルの表示名（保存時点の名前を焼き込む）
            auto: 自動翻訳による実行かどうか

        Returns:
            追加または更新されたエントリ
        """
        timestamp = datetime.now().isoformat(timespec="seconds")

        last = self.entries[0] if self.entries else None
        if last is not None and self._should_merge(last, kind, source_text,
                                                   target_lang, style,
                                                   model_type):
            last["source_text"] = source_text
            last["result_text"] = result_text
            last["source_lang"] = source_lang
            last["timestamp"] = timestamp
            # 手動実行はユーザーの明示的な操作なので、ここで確定させる。
            # 以降の自動翻訳はこのエントリに統合されず、新規エントリになる。
            if not auto:
                last["auto"] = False
            return last

        entry = {
            "id": uuid.uuid4().hex[:8],
            "kind": kind,
            "timestamp": timestamp,
            "source_text": source_text,
            "result_text": result_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "style": style,
            "model_type": model_type,
            "model_display": model_display,
            "auto": auto
        }
        self.entries.insert(0, entry)
        del self.entries[self.MAX_ENTRIES:]
        return entry

    def _should_merge(self, last: Dict, kind: str, source_text: str,
                      target_lang: Optional[str], style: str,
                      model_type: str) -> bool:
        """
        直近エントリを更新すべきか（新規追加せずに済むか）を判定

        Returns:
            更新すべきならTrue
        """
        # 条件が違えば別の翻訳として扱う
        if (last.get("kind") != kind or
                last.get("target_lang") != target_lang or
                last.get("style") != style or
                last.get("model_type") != model_type):
            return False

        # ルールA: まったく同じ原文の再実行は履歴を増やさない
        if last.get("source_text") == source_text:
            return True

        # ルールB: 直近が自動翻訳由来なら、単純追記は同じ編集セッションとみなす
        # （校正は原文を結果で置き換えるため、この統合は行わない）
        if kind == "proofread" or not last.get("auto"):
            return False
        return _is_incremental_edit(last.get("source_text", ""), source_text)

    def delete(self, entry_id: str) -> bool:
        """
        指定IDのエントリを削除する（保存は呼び出し側で行う）

        Args:
            entry_id: 削除するエントリのID

        Returns:
            削除したかどうか
        """
        for index, entry in enumerate(self.entries):
            if entry.get("id") == entry_id:
                del self.entries[index]
                return True
        return False

    def clear(self) -> None:
        """すべての履歴を削除する（保存は呼び出し側で行う）"""
        self.entries = []
