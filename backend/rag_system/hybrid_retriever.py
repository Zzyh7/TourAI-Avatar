"""
混合检索器 —— FAISS 向量检索 + BM25 关键词检索 + RRF 融合。

============================================================================
RRF (Reciprocal Rank Fusion) 融合算法详解
============================================================================

为什么需要 RRF？
  - FAISS 向量检索返回的是余弦相似度 [0, 1]
  - BM25 返回的是关键词匹配分数 [0, +∞)
  - 两种分数的量纲和分布完全不同，不能直接相加或比较
  - RRF 将分数转换为排名，在排名空间进行融合，消除量纲差异

RRF 公式:
  RRF_score(d) = Σ_i 1 / (k + rank_i(d))

  其中:
    - k 是常数（默认60），用于平滑排名差异，防止排名#1 主导一切
    - rank_i(d) 是文档 d 在第 i 个检索器中的排名（1-indexed）
    - 如果文档只在一个检索器中出现，另一个检索器的贡献为 0

示例:
  文档A: FAISS 排名#1, BM25 排名#5
    RRF = 1/(60+1) + 1/(60+5) = 0.01639 + 0.01538 = 0.03178

  文档B: FAISS 排名#3, BM25 排名#2
    RRF = 1/(60+3) + 1/(60+2) = 0.01587 + 0.01613 = 0.03200

  → 文档B 胜出！虽然文档A在向量检索中排名更高，
    但文档B在两种检索方式中都表现不错，综合排名更好。

兜底策略:
  融合后，如果 FAISS 最高余弦相似度 < score_threshold (0.6)，
  说明向量检索没有找到足够语义相关的内容，触发"不知道"响应。
  这避免了 LLM 在缺乏依据时强行编造答案。
============================================================================
"""
import os
import json
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.faiss import DistanceStrategy

from .config import rag_config
from .embedding import EmbeddingService


class HybridRetriever:
    """
    混合检索器：向量语义匹配 + 关键词匹配 → RRF 融合。

    维护三个索引:
      1. FAISS 文档索引 — 语义向量检索 (cosine similarity)
      2. BM25 关键词索引 — 精确关键词匹配 (jieba 分词)
      3. FAQ 独立索引   — 高频问题精确匹配 (更高阈值)

    所有索引支持:
      - 从磁盘加载（启动时自动恢复）
      - 增量添加文档（不重建整个索引）
      - 持久化保存（每次添加后自动保存）

    用法:
        embedder = EmbeddingService()
        retriever = HybridRetriever(embedder)

        # 添加文档
        retriever.add_documents(chunks)

        # 检索
        result = retriever.retrieve("西湖的历史典故有哪些？")
        # result = {
        #     "docs": [Document, ...],
        #     "scores": [0.85, 0.72, ...],
        #     "sources": ["景区介绍.pdf", ...],
        #     "below_threshold": False,
        #     "from_faq": False,
        # }
    """

    def __init__(self, embedding_service: EmbeddingService):
        self.embedder = embedding_service

        # === FAISS 文档索引 ===
        self._faiss_store: FAISS | None = None

        # === BM25 关键词索引 ===
        self._bm25: BM25Okapi | None = None
        self._bm25_corpus: List[str] = []          # 所有块的原始文本
        self._bm25_metadata: List[dict] = []        # 每个块对应的 metadata（source 等）

        # === FAQ 独立索引（更高匹配阈值） ===
        self._faq_store: FAISS | None = None
        self._faq_answers: dict = {}                 # FAQ question → answer 映射

        # === 路径 ===
        self._vector_path = rag_config.vector_store_path
        self._faq_path = rag_config.faq_index_path
        self._corpus_path = rag_config.bm25_corpus_path

        # === 启动时从磁盘恢复所有索引 ===
        self._load_all()

    # =====================================================================
    # 持久化: 加载 / 保存
    # =====================================================================

    def _load_all(self):
        """从磁盘加载所有索引（启动时调用）"""
        self._load_faiss()
        self._load_faq()
        self._load_bm25()

    def _load_faiss(self) -> bool:
        """加载 FAISS 文档索引"""
        index_path = os.path.join(self._vector_path, "index.faiss")
        if not os.path.exists(index_path):
            print("[INFO] FAISS 文档索引不存在，等待文档上传")
            return False

        try:
            self._faiss_store = FAISS.load_local(
                self._vector_path,
                self.embedder.model,
                allow_dangerous_deserialization=True,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
            n = self._faiss_store.index.ntotal
            print(f"[OK] 已加载 FAISS 文档索引 ({n} 个向量)")
            return True
        except Exception as e:
            print(f"[WARN] FAISS 索引加载失败: {e}，将重新构建")
            self._faiss_store = None
            return False

    def _save_faiss(self):
        """保存 FAISS 文档索引到磁盘"""
        if self._faiss_store is None:
            return
        os.makedirs(self._vector_path, exist_ok=True)
        self._faiss_store.save_local(self._vector_path)

    def _load_faq(self) -> bool:
        """加载 FAQ 索引和答案映射"""
        faq_index = os.path.join(self._faq_path, "index.faiss")
        if not os.path.exists(faq_index):
            return False

        try:
            self._faq_store = FAISS.load_local(
                self._faq_path,
                self.embedder.model,
                allow_dangerous_deserialization=True,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
            # 加载 FAQ 答案映射
            answers_path = os.path.join(self._faq_path, "faq_answers.json")
            if os.path.exists(answers_path):
                with open(answers_path, "r", encoding="utf-8") as f:
                    self._faq_answers = json.load(f)
            n = self._faq_store.index.ntotal
            print(f"[OK] 已加载 FAQ 索引 ({n} 个问答对)")
            return True
        except Exception as e:
            print(f"[WARN] FAQ 索引加载失败: {e}")
            self._faq_store = None
            self._faq_answers = {}
            return False

    def _save_faq(self):
        """保存 FAQ 索引和答案映射"""
        if self._faq_store is None:
            return
        os.makedirs(self._faq_path, exist_ok=True)
        self._faq_store.save_local(self._faq_path)

        answers_path = os.path.join(self._faq_path, "faq_answers.json")
        with open(answers_path, "w", encoding="utf-8") as f:
            json.dump(self._faq_answers, f, ensure_ascii=False, indent=2)

    def _load_bm25(self) -> bool:
        """从 JSON 加载 BM25 语料并重建索引"""
        if not os.path.exists(self._corpus_path):
            return False

        try:
            with open(self._corpus_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._bm25_corpus = data.get("corpus", [])
            self._bm25_metadata = data.get("metadata", [])

            if self._bm25_corpus:
                tokenized = [list(jieba.cut(text)) for text in self._bm25_corpus]
                self._bm25 = BM25Okapi(tokenized)
                print(f"[OK] 已重建 BM25 索引 ({len(self._bm25_corpus)} 个文档)")
            return True
        except Exception as e:
            print(f"[WARN] BM25 索引加载失败: {e}")
            self._bm25 = None
            self._bm25_corpus = []
            self._bm25_metadata = []
            return False

    def _save_bm25(self):
        """保存 BM25 语料到 JSON（索引本身不支持序列化，保存原始语料）"""
        os.makedirs(os.path.dirname(self._corpus_path), exist_ok=True)

        data = {
            "corpus": self._bm25_corpus,
            "metadata": self._bm25_metadata,
        }
        with open(self._corpus_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _save_all(self):
        """保存所有索引"""
        self._save_faiss()
        self._save_bm25()
        self._save_faq()

    # =====================================================================
    # 索引构建: 文档添加
    # =====================================================================

    def add_documents(self, documents: List[Document]):
        """
        增量添加文档块到所有索引。

        对 FAISS: 调用 add_documents() 增量追加
        对 BM25:  重建整个索引（BM25 不支持增量更新，但速度很快）
        对 FAQ:   不处理（FAQ 有独立导入接口）

        Args:
            documents: LangChain Document 列表（已分块、带 metadata）
        """
        if not documents:
            return

        # === 1. FAISS 增量添加 ===
        if self._faiss_store is None:
            self._faiss_store = FAISS.from_documents(
                documents, self.embedder.model,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
        else:
            self._faiss_store.add_documents(documents)

        # === 2. BM25 重建（从完整语料） ===
        for doc in documents:
            self._bm25_corpus.append(doc.page_content)
            self._bm25_metadata.append({
                "source": doc.metadata.get("source", "未知"),
                "chunk_index": doc.metadata.get("chunk_index", -1),
                "chunk_id": doc.metadata.get("chunk_id"),       # SQLite chunks.id
                "embedding_model": doc.metadata.get("embedding_model", ""),
            })

        # 对所有语料重新分词 → 构建 BM25 索引
        tokenized = [list(jieba.cut(text)) for text in self._bm25_corpus]
        self._bm25 = BM25Okapi(tokenized)

        # === 3. 持久化 ===
        self._save_all()

        n_faiss = self._faiss_store.index.ntotal
        n_bm25 = len(self._bm25_corpus)
        print(f"[OK] 已添加 {len(documents)} 个块 (FAISS总量:{n_faiss}, BM25总量:{n_bm25})")

    # =====================================================================
    # FAQ 管理
    # =====================================================================

    def import_faq(self, faq_pairs: List[dict]):
        """
        批量导入 FAQ 问答对到独立的 FAQ 索引。

        FAQ 索引使用更高的匹配阈值 (0.85 vs 0.6)，
        因为 FAQ 问题通常是精确或近精确匹配。

        Args:
            faq_pairs: [{"question": "...", "answer": "..."}, ...]
        """
        if not faq_pairs:
            return

        # 提取所有问题文本
        questions = [item["question"] for item in faq_pairs]
        faq_docs = [
            Document(page_content=q, metadata={"type": "faq", "index": i})
            for i, q in enumerate(questions)
        ]

        # 构建/追加 FAQ 索引
        if self._faq_store is None:
            self._faq_store = FAISS.from_documents(
                faq_docs, self.embedder.model,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
        else:
            self._faq_store.add_documents(faq_docs)

        # 更新答案映射（问题文本 → 答案）
        for item in faq_pairs:
            self._faq_answers[item["question"]] = item["answer"]

        self._save_faq()
        print(f"[OK] 已导入 {len(faq_pairs)} 个 FAQ 问答对")

    # =====================================================================
    # 检索核心: 向量 / BM25 / FAQ 三项检索
    # =====================================================================

    def _faiss_search(
        self, query: str, k: int
    ) -> List[Tuple[Document, float]]:
        """
        FAISS 向量语义检索。

        使用 similarity_search_with_score:
          - BGE 模型 normalize_embeddings=True → 向量 L2 归一化
          - FAISS 自动使用 IndexFlatIP (内积)
          - 内积 = 余弦相似度，分数范围 [0, 1]，越高越相似

        Returns:
            [(Document, score), ...]  按分数降序排列
        """
        if self._faiss_store is None or self._faiss_store.index.ntotal == 0:
            return []

        try:
            results = self._faiss_store.similarity_search_with_score(query, k=k)
            return results  # List[Tuple[Document, float]]
        except Exception as e:
            print(f"[WARN] FAISS 检索失败: {e}")
            return []

    def _bm25_search(
        self, query: str, k: int
    ) -> List[Tuple[int, float, dict]]:
        """
        BM25 关键词检索。

        使用 jieba 对查询分词，然后用 BM25Okapi 计算每个文档的分数。

        BM25 公式简介:
          score(d, q) = Σ IDF(q_i) * (f_i * (k1+1)) / (f_i + k1*(1-b+b*|d|/avgdl))
          其中 f_i 是词 q_i 在文档 d 中的频率，|d| 是文档长度

        Returns:
            [(corpus_index, bm25_score, metadata_dict), ...]  按分数降序排列
        """
        if self._bm25 is None or not self._bm25_corpus:
            return []

        try:
            tokenized_query = list(jieba.cut(query))
            scores = self._bm25.get_scores(tokenized_query)

            # 获取 top_k 个最高分的索引
            if len(scores) == 0:
                return []

            # 使用 argpartition 高效获取 top-k（比完整排序快）
            if len(scores) <= k:
                top_indices = np.argsort(scores)[::-1]  # 降序
            else:
                # 部分排序：先分区再对 top-k 排序
                top_indices = np.argpartition(scores, -k)[-k:]
                top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

            # 过滤分数为 0 的结果（完全不匹配）
            result = []
            for idx in top_indices:
                idx = int(idx)
                score = float(scores[idx])
                if score > 0:
                    metadata = (
                        self._bm25_metadata[idx]
                        if idx < len(self._bm25_metadata)
                        else {}
                    )
                    result.append((idx, score, metadata))

            return result
        except Exception as e:
            print(f"[WARN] BM25 检索失败: {e}")
            return []

    def _faq_search(
        self, query: str
    ) -> Tuple[str, str, float] | None:
        """
        FAQ 精确匹配检索。

        使用比文档检索更高的阈值 (0.85)，
        因为 FAQ 是最高质量的数据源，需要确保匹配精度。

        Returns:
            (question, answer, score) 或 None
        """
        if self._faq_store is None or self._faq_store.index.ntotal == 0:
            return None

        try:
            results = self._faq_store.similarity_search_with_score(query, k=1)
            if not results:
                return None

            doc, score = results[0]
            if score >= rag_config.faq_threshold:
                question = doc.page_content
                answer = self._faq_answers.get(question, "")
                if answer:
                    return (question, answer, score)
        except Exception as e:
            print(f"[WARN] FAQ 检索失败: {e}")

        return None

    # =====================================================================
    # RRF 融合算法
    # =====================================================================

    def _rrf_fusion(
        self,
        faiss_results: List[Tuple[Document, float]],
        bm25_results: List[Tuple[int, float, dict]],
    ) -> List[Tuple[Document, float, str]]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法。

        核心思想:
          不直接比较 FAISS 的余弦相似度和 BM25 的关键词分数（量纲不同），
          而是将两种检索结果按排名融合，排名越靠前贡献越大。

        算法步骤:
          1. 遍历 FAISS 结果，按排名给每个文档加上 RRF 贡献
          2. 遍历 BM25 结果，按排名给每个文档加上 RRF 贡献
          3. 按 RRF 总分降序排列

        去重策略:
          使用文档内容的前 80 个字符作为近似标识。
          当同一个文档块同时出现在 FAISS 和 BM25 结果中时，
          它的 RRF 分数 = 1/(k+faiss_rank) + 1/(k+bm25_rank)，
          这意味着在两个检索器中都排名靠前的文档会获得最高分。

        Args:
            faiss_results: [(Document, cosine_similarity), ...]
            bm25_results:  [(corpus_index, bm25_score, metadata), ...]

        Returns:
            [(Document, rrf_score, source_filename), ...]  按 RRF 分数降序
        """
        k = rag_config.rrf_k
        rrf_scores: dict[str, float] = {}      # doc_key → RRF 累积分
        doc_registry: dict[str, Document] = {}  # doc_key → Document
        source_registry: dict[str, str] = {}    # doc_key → source filename

        def _make_key(text: str) -> str:
            """生成文档唯一标识（前80字符作为近似去重key）"""
            return text.strip()[:80]

        # --- 第一步：处理 FAISS 结果 ---
        for rank, (doc, _) in enumerate(faiss_results, start=1):
            key = _make_key(doc.page_content)
            rrf_contribution = 1.0 / (k + rank)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + rrf_contribution
            doc_registry[key] = doc
            source_registry[key] = doc.metadata.get("source", "未知")

        # --- 第二步：处理 BM25 结果 ---
        for rank, (corpus_idx, _, metadata) in enumerate(bm25_results, start=1):
            content = self._bm25_corpus[corpus_idx]
            key = _make_key(content)
            rrf_contribution = 1.0 / (k + rank)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + rrf_contribution

            # 如果这个文档不在 FAISS 结果中，补充 Document 对象
            if key not in doc_registry:
                source = metadata.get("source", "未知")
                doc_registry[key] = Document(
                    page_content=content,
                    metadata={"source": source},
                )
                source_registry[key] = source

        # --- 第三步：按 RRF 分数降序排列 ---
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)

        return [
            (doc_registry[key], rrf_scores[key], source_registry.get(key, "未知"))
            for key in sorted_keys
        ]

    # =====================================================================
    # 公开检索接口
    # =====================================================================

    def retrieve(self, query: str, top_k: int = None) -> dict:
        """
        混合检索主入口 —— 供外部调用。

        完整检索流水线:
          ┌──────────────────────────────────────────────────┐
          │ 1. FAQ 精确匹配 (阈值 0.85)                       │
          │    ├─ 命中 → 直接返回 FAQ 答案（最高优先级）       │
          │    └─ 未命中 → 进入混合检索                        │
          ├──────────────────────────────────────────────────┤
          │ 2. FAISS 向量检索 (top_k=10)                      │
          │    语义相似度 → 余弦分数 [0,1]                     │
          ├──────────────────────────────────────────────────┤
          │ 3. BM25 关键词检索 (top_k=10)                     │
          │    jieba分词 → BM25 分数                          │
          ├──────────────────────────────────────────────────┤
          │ 4. RRF 融合                                       │
          │    排名空间融合 → RRF 分数                         │
          ├──────────────────────────────────────────────────┤
          │ 5. 阈值检查                                        │
          │    FAISS最高分 < 0.6 → 触发"资料不足"              │
          ├──────────────────────────────────────────────────┤
          │ 6. 返回 top_k=5 结果                               │
          └──────────────────────────────────────────────────┘

        Args:
            query:  用户问题文本
            top_k:  最终返回的结果数量（默认 5）

        Returns:
            {
                "docs":            List[Document]   # 检索到的文档块
                "scores":          List[float]      # 对应的 RRF 分数
                "sources":         List[str]        # 去重后的来源文件名
                "best_faiss_score": float           # 最高 FAISS 余弦相似度
                "from_faq":        bool             # 是否来自 FAQ
                "faq_answer":      str | None       # FAQ 答案文本
                "below_threshold": bool             # 是否低于置信度阈值
            }
        """
        k = top_k or rag_config.final_top_k

        # ================================================================
        # 1. FAQ 优先匹配（高质量数据源，优先使用）
        # ================================================================
        faq_match = self._faq_search(query)
        if faq_match:
            question, answer, score = faq_match
            return {
                "docs": [Document(page_content=answer, metadata={"source": "FAQ知识库"})],
                "scores": [score],
                "sources": ["FAQ知识库"],
                "best_faiss_score": score,
                "from_faq": True,
                "faq_answer": answer,
                "below_threshold": False,
            }

        # ================================================================
        # 2. 双路并行检索
        # ================================================================
        faiss_results = self._faiss_search(query, k=rag_config.retrieval_top_k)
        bm25_results = self._bm25_search(query, k=rag_config.retrieval_top_k)

        # ================================================================
        # 3. RRF 融合
        # ================================================================
        fused = self._rrf_fusion(faiss_results, bm25_results)

        # ================================================================
        # 4. 阈值检查 —— 兜底策略
        # ================================================================
        best_faiss_score = faiss_results[0][1] if faiss_results else 0.0
        below_threshold = (
            len(fused) == 0 or best_faiss_score < rag_config.score_threshold
        )

        # ================================================================
        # 5. 截取 top_k 结果
        # ================================================================
        top_results = fused[:k]

        # 提取来源（去重，保持顺序）
        sources = []
        seen_sources = set()
        for _, _, source in top_results:
            if source not in seen_sources:
                sources.append(source)
                seen_sources.add(source)

        return {
            "docs": [doc for doc, _, _ in top_results],
            "scores": [score for _, score, _ in top_results],
            "sources": sources,
            "best_faiss_score": best_faiss_score,
            "from_faq": False,
            "faq_answer": None,
            "below_threshold": below_threshold,
        }

    def get_context(self, query: str, top_k: int = None) -> str:
        """
        检索并拼接为 LLM 上下文文本。

        Returns:
            用 "\\n---\\n" 分隔的文档块文本，如果低于阈值则返回空字符串
        """
        result = self.retrieve(query, top_k)
        if result["below_threshold"] or not result["docs"]:
            return ""
        return "\n---\n".join(doc.page_content for doc in result["docs"])

    # =====================================================================
    # 状态查询
    # =====================================================================

    @property
    def is_ready(self) -> bool:
        """知识库是否就绪（有至少一个文档块）"""
        return self._faiss_store is not None and self._faiss_store.index.ntotal > 0

    @property
    def stats(self) -> dict:
        """获取索引统计信息"""
        return {
            "faiss_vectors": (
                self._faiss_store.index.ntotal
                if self._faiss_store
                else 0
            ),
            "bm25_documents": len(self._bm25_corpus),
            "faq_pairs": (
                self._faq_store.index.ntotal
                if self._faq_store
                else 0
            ),
            "faq_answers": len(self._faq_answers),
        }
