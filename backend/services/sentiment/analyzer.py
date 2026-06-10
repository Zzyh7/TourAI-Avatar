"""
情感分析器 —— 基于 LLM prompt 工程，无需训练模型。
"""
from langchain_core.language_models import BaseChatModel
from prompts import SENTIMENT_PROMPT


class SentimentAnalyzer:
    """
    使用 LLM 判断用户消息的情感倾向。

    用法:
        analyzer = SentimentAnalyzer(llm)
        label = await analyzer.analyze("今天玩得很开心！")
        # → "正面"
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def analyze(self, message: str) -> str:
        """
        分析情感倾向。

        返回: "正面" | "中性" | "负面"
        """
        if not message.strip():
            return "中性"

        prompt = SENTIMENT_PROMPT.format(message=message)

        try:
            result = await self.llm.ainvoke(prompt)
            text = result.content.strip()
            # 规范化输出
            if "正面" in text:
                return "正面"
            elif "负面" in text:
                return "负面"
            else:
                return "中性"
        except Exception:
            return "中性"

    def analyze_sync(self, message: str) -> str:
        """同步版本（用于非异步上下文）"""
        if not message.strip():
            return "中性"

        prompt = SENTIMENT_PROMPT.format(message=message)

        try:
            result = self.llm.invoke(prompt)
            text = result.content.strip()
            if "正面" in text:
                return "正面"
            elif "负面" in text:
                return "负面"
            else:
                return "中性"
        except Exception:
            return "中性"
