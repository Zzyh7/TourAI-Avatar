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
        分析情感倾向。默认偏向满意，只有明确不满才标负面。

        返回: "正面" | "中性" | "负面"
        """
        if not message.strip():
            return "正面"  # 空消息默认满意

        prompt = SENTIMENT_PROMPT.format(message=message)

        try:
            result = await self.llm.ainvoke(prompt)
            text = result.content.strip()
            # 规范化输出
            if "负面" in text:
                return "负面"
            elif "中性" in text:
                return "中性"
            else:
                return "正面"  # LLM 没有明确判断时，默认正面
        except Exception:
            return "正面"  # 出错时默认正面

    def analyze_sync(self, message: str) -> str:
        """同步版本（用于非异步上下文）"""
        if not message.strip():
            return "正面"

        prompt = SENTIMENT_PROMPT.format(message=message)

        try:
            result = self.llm.invoke(prompt)
            text = result.content.strip()
            if "负面" in text:
                return "负面"
            elif "中性" in text:
                return "中性"
            else:
                return "正面"
        except Exception:
            return "正面"
