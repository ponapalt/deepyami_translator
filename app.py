"""
DeepYami翻訳アプリ
アプリケーションエントリーポイント
"""

import tkinter as tk
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.main_window import MainWindow


def main():
    """メイン関数"""
    # Tkルートウィンドウを作成
    root = tk.Tk()

    # 設定管理オブジェクトを作成
    config_manager = ConfigManager()

    # メインウィンドウを作成
    app = MainWindow(root, config_manager)

    # イベントループを開始
    root.mainloop()


if __name__ == "__main__":
    main()
