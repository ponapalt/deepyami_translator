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

    def __init__(self, model_type: str, api_key: str):
        """
        Args:
            model_type: "gpt4", "claude", "gemini"のいずれか
            api_key: 対応するAPIキー
        """
        self.model_type = model_type
        self.api_key = api_key
        self.llm = self._initialize_llm()

        # プロンプトテンプレート
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator with expertise in multiple languages.
Your task is to translate text accurately while maintaining the original tone, style, and nuance.
Provide ONLY the translation without any explanations, notes, or additional text."""),
            ("user", """Translate the following text from {source_lang} to {target_lang}.

Text to translate:
{text}""")
        ])

        # 出力パーサー
        self.output_parser = StrOutputParser()

        # チェーンの構築
        self.chain = self.prompt_template | self.llm | self.output_parser

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

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        テキストを翻訳

        Args:
            text: 翻訳対象テキスト
            source_lang: 翻訳元言語（LANGUAGE_MAPのキー）
            target_lang: 翻訳先言語（LANGUAGE_MAPのキー）

        Returns:
            翻訳されたテキスト、エラーの場合はNone
        """
        if not text.strip():
            return ""

        # 同じ言語の場合は翻訳不要
        if source_lang == target_lang:
            return text

        try:
            # 言語名を取得
            source_lang_name = self.LANGUAGE_MAP.get(source_lang, source_lang)
            target_lang_name = self.LANGUAGE_MAP.get(target_lang, target_lang)

            # チェーンを実行
            result = self.chain.invoke({
                "source_lang": source_lang_name,
                "target_lang": target_lang_name,
                "text": text
            })

            return result.strip()

        except Exception as e:
            print(f"翻訳エラー: {e}")
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
                "English",
                "Japanese"
            )

            if result:
                return True, "接続テスト成功"
            else:
                return False, "翻訳結果が空です"

        except Exception as e:
            return False, f"接続エラー: {str(e)}"
