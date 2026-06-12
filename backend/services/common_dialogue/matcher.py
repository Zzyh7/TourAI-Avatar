"""
常用对话匹配器 —— 三级降级匹配策略。

1. 精确匹配：标准化文本完全一致
2. 模糊匹配：difflib.SequenceMatcher 相似度 >= 阈值
3. 关键词匹配：用户问题与对话关键词集合重叠度 >= 阈值

多个命中时取 priority 最高的那条。
"""
import re
import difflib
from typing import Optional

from sqlalchemy.orm import Session

from models.schema import CommonDialogue


class CommonDialogueService:
    """常用对话匹配服务"""

    # 匹配阈值
    FUZZY_THRESHOLD: float = 0.8        # 模糊匹配最低相似度
    KEYWORD_OVERLAP_THRESHOLD: float = 0.5  # 关键词最低重叠率

    # 缓存：已加载的常用对话（实例级缓存，进程生命周期内有效）
    _cache: list[CommonDialogue] | None = None
    _cache_version: int = 0

    def normalize(self, text: str) -> str:
        """标准化文本：去首尾空白、转小写、去标点符号"""
        text = text.strip().lower()
        # 移除常见标点
        text = re.sub(r'[，。！？、；：""（）【】《》\s,\.!\?;:\"\'\(\)\[\]{}]+', '', text)
        return text

    def _tokenize(self, text: str) -> set[str]:
        """将文本分词为关键词集合"""
        # 简单按标点和空格切分，过滤单字
        tokens = re.split(r'[，。！？、；：\s,\.!\?;:]+', text.strip().lower())
        return {t for t in tokens if len(t) >= 2}

    def _get_enabled(self, db: Session) -> list[CommonDialogue]:
        """获取所有启用的常用对话，按优先级降序"""
        return (
            db.query(CommonDialogue)
            .filter(CommonDialogue.enabled == 1)
            .order_by(CommonDialogue.priority.desc())
            .all()
        )

    def match(self, user_text: str, db: Session) -> CommonDialogue | None:
        """
        三级降级匹配用户输入。

        Args:
            user_text: 用户原始输入
            db: 数据库会话

        Returns:
            匹配到的 CommonDialogue 实例，未命中返回 None
        """
        if not user_text or not user_text.strip():
            return None

        dialogues = self._get_enabled(db)
        if not dialogues:
            return None

        normalized = self.normalize(user_text)
        if not normalized:
            return None

        # 1. 精确匹配
        result = self._match_exact(normalized, dialogues)
        if result:
            return result

        # 2. 模糊匹配
        result = self._match_fuzzy(normalized, dialogues)
        if result:
            return result

        # 3. 关键词匹配
        result = self._match_keywords(normalized, dialogues)
        if result:
            return result

        return None

    def _get_question_variants(self, d: CommonDialogue) -> list[str]:
        """获取对话的所有匹配文本：主问题 + variants 中的相似提问"""
        texts = [d.question]
        if d.variants and d.variants.strip():
            import json
            try:
                variants_list = json.loads(d.variants)
                if isinstance(variants_list, list):
                    texts.extend(v for v in variants_list if isinstance(v, str) and v.strip())
            except (json.JSONDecodeError, TypeError):
                pass
        return texts

    def _match_exact(
        self, normalized: str, dialogues: list[CommonDialogue]
    ) -> CommonDialogue | None:
        """精确匹配：标准化文本完全相同（含 variants）"""
        for d in dialogues:
            for text in self._get_question_variants(d):
                if self.normalize(text) == normalized:
                    return d
        return None

    def _match_fuzzy(
        self, normalized: str, dialogues: list[CommonDialogue]
    ) -> CommonDialogue | None:
        """模糊匹配：difflib 序列相似度（含 variants）"""
        best_score = 0.0
        best_match: CommonDialogue | None = None

        for d in dialogues:
            for text in self._get_question_variants(d):
                d_normalized = self.normalize(text)
                score = difflib.SequenceMatcher(None, normalized, d_normalized).ratio()
                if score >= self.FUZZY_THRESHOLD and score > best_score:
                    best_score = score
                    best_match = d

        return best_match

    def _match_keywords(
        self, normalized: str, dialogues: list[CommonDialogue]
    ) -> CommonDialogue | None:
        """关键词匹配：用户输入与对话关键词集合重叠度"""
        user_tokens = self._tokenize(normalized)
        if not user_tokens:
            return None

        best_score = 0.0
        best_match: CommonDialogue | None = None

        for d in dialogues:
            if not d.keywords or not d.keywords.strip():
                continue
            dialogue_tokens = self._tokenize(d.keywords)
            if not dialogue_tokens:
                continue

            # Jaccard 重叠度
            intersection = user_tokens & dialogue_tokens
            union = user_tokens | dialogue_tokens
            score = len(intersection) / len(union) if union else 0

            if score >= self.KEYWORD_OVERLAP_THRESHOLD and score > best_score:
                best_score = score
                best_match = d

        return best_match
