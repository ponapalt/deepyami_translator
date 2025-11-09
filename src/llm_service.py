"""
LLM統合サービスモジュール
LangChainを使用して各LLMプロバイダーと統合
"""

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class TranslationService:
    """翻訳サービスを提供するクラス"""

    # 言語名のマッピング
    LANGUAGE_MAP = {
        "Japanese": "日本語",
        "Chinese-Simplified": "中国語（簡体字）",
        "Chinese-Traditional": "中国語（繁体字）",
        "Korean": "韓国語",
        "English": "英語"
    }

    # 翻訳スタイルの説明
    STYLE_INSTRUCTIONS = {
        "ビジネス": "formal business tone with polite and professional language",
        "同僚": "casual professional tone suitable for colleagues",
        "友人": "friendly and casual tone suitable for friends"
    }

    def __init__(self, model_type: str, api_key: str):
        """
        Args:
            model_type: "gpt4", "claude", "gemini"のいずれか
            api_key: 対応するAPIキー
        """
        self.model_type = model_type
        self.api_key = api_key
        self.llm = self._initialize_llm()

        # 翻訳用プロンプトテンプレート
        self.translation_template = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator with expertise in multiple languages.
Your task is to translate text accurately while maintaining the appropriate tone and style.
Automatically detect the source language and translate to the target language.
Use {style_instruction}.
Provide ONLY the translation without any explanations, notes, or additional text."""),
            ("user", """Translate the following text to {target_lang}.

Text to translate:
{text}""")
        ])

        # 校正用プロンプトテンプレート
        self.proofreading_template = ChatPromptTemplate.from_messages([
            ("system", """You are a professional proofreader and editor.
Your task is to proofread and correct the text while maintaining the original language.
Fix grammar, spelling, punctuation, and improve clarity where needed.
Use {style_instruction}.
Provide ONLY the corrected text without any explanations or notes."""),
            ("user", """Proofread and correct the following text in its original language:

{text}""")
        ])

        # 出力パーサー
        self.output_parser = StrOutputParser()

        # 翻訳チェーンの構築
        self.translation_chain = self.translation_template | self.llm | self.output_parser

        # 校正チェーンの構築
        self.proofreading_chain = self.proofreading_template | self.llm | self.output_parser

    def _initialize_llm(self):
        """
        モデルタイプに応じてLLMを初期化

        Returns:
            初期化されたLLMインスタンス

        Raises:
            ValueError: サポートされていないモデルタイプの場合
        """
        if self.model_type == "gpt4":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.3,
                api_key=self.api_key
            )
        elif self.model_type == "claude":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.3,
                api_key=self.api_key
            )
        elif self.model_type == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                temperature=0.3,
                google_api_key=self.api_key
            )
        else:
            raise ValueError(f"サポートされていないモデルタイプ: {self.model_type}")

    def translate(self, text: str, target_lang: str, style: str = "ビジネス") -> Optional[str]:
        """
        テキストを翻訳（自動言語検出）

        Args:
            text: 翻訳対象テキスト
            target_lang: 翻訳先言語（LANGUAGE_MAPのキー）
            style: 翻訳スタイル（"ビジネス", "同僚", "友人"）

        Returns:
            翻訳されたテキスト、エラーの場合はNone
        """
        if not text.strip():
            return ""

        try:
            # 言語名を取得
            target_lang_name = self.LANGUAGE_MAP.get(target_lang, target_lang)

            # スタイル指示を取得
            style_instruction = self.STYLE_INSTRUCTIONS.get(style, self.STYLE_INSTRUCTIONS["ビジネス"])

            # チェーンを実行
            result = self.translation_chain.invoke({
                "target_lang": target_lang_name,
                "text": text,
                "style_instruction": style_instruction
            })

            return result.strip()

        except Exception as e:
            print(f"翻訳エラー: {e}")
            return None

    def proofread(self, text: str, style: str = "ビジネス") -> Optional[str]:
        """
        テキストを校正（言語は維持）

        Args:
            text: 校正対象テキスト
            style: 翻訳スタイル（"ビジネス", "同僚", "友人"）

        Returns:
            校正されたテキスト、エラーの場合はNone
        """
        if not text.strip():
            return ""

        try:
            # スタイル指示を取得
            style_instruction = self.STYLE_INSTRUCTIONS.get(style, self.STYLE_INSTRUCTIONS["ビジネス"])

            # チェーンを実行
            result = self.proofreading_chain.invoke({
                "text": text,
                "style_instruction": style_instruction
            })

            return result.strip()

        except Exception as e:
            print(f"校正エラー: {e}")
            return None

    def test_connection(self) -> tuple[bool, str]:
        """
        API接続をテスト

        Returns:
            (成功フラグ, メッセージ)のタプル
        """
        try:
            # 簡単なテスト翻訳を実行
            result = self.translate(
                "Hello",
                "Japanese"
            )

            if result:
                return True, "接続テスト成功"
            else:
                return False, "翻訳結果が空です"

        except Exception as e:
            return False, f"接続エラー: {str(e)}"
