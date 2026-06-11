"""
文本分块器 —— 将解析后的文档内容转为 LangChain Document 列表。

两种分块策略:
  1. structured_rows_to_documents()  — 结构化表格行 → 自然语言文本块
  2. narrative_paragraphs_to_documents() — 叙述性文档 → 300~500字语义段落块
"""
import json
import os
import re
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document


# BGE 模型最大 token 数 ≈ 512，中文字符:token ≈ 1:1.2~1.5
# 保守取 500 字为上限，300 字为理想长度
MAX_CHUNK_CHARS = 500   # 硬上限（不超过此值）
TARGET_CHUNK_CHARS = 380  # 理想长度（尽量在此附近切分）
MIN_CHUNK_CHARS = 100     # 最小块长度（太小则合并到前一块）


# ============================================================================
# 结构化表格 → 文本块
# ============================================================================

# 字段映射：数据库列名 → 中文标签（用于生成自然语言描述）
FIELD_LABELS = {
    "景区名称": "景区名称",
    "景点ID": "景点ID",
    "景点名称": "景点名称",
    "具体位置": "具体位置",
    "建筑/景观参数": "建筑参数",
    "核心功能": "核心功能",
    "文化内涵": "文化内涵",
    "详细介绍": "详细介绍",
    "游玩亮点": "游玩亮点",
    "演艺/开放信息": "演艺/开放信息",
    "备注": "备注",
}

# 哪些字段应该优先排在前面
PRIORITY_FIELDS = [
    "景区名称", "景点ID", "景点名称", "具体位置",
    "建筑/景观参数", "核心功能", "文化内涵",
    "详细介绍", "游玩亮点", "演艺/开放信息", "备注",
]


def structured_rows_to_documents(
    tables: List[Dict[str, Any]],
    source_file: str,
    source_type: str = "structured",
) -> List[Document]:
    """
    将表格行转为 LangChain Document 列表。

    每行景点 → 一个 Document:
      - page_content: 自然语言文本（所有字段拼接）
      - metadata: {
            "source": 文件名,
            "source_type": "structured",
            "table_caption": 子表名（如"灵山胜境景点"）,
            "scenic_spot_id": 景点ID,
            "scenic_spot_name": 景点名称,
            "scenic_area": 景区名称,
            "raw_fields": {...},   # 原始字段副本（JSON 子对象）
        }

    Args:
        tables: DocxParser.extract_tables() 的返回结果
        source_file: 原始文件名
        source_type: 元数据类型标签

    Returns:
        List[Document]
    """
    documents = []

    for table_info in tables:
        caption = table_info.get("caption") or f"表格_{table_info['table_index']}"
        columns = table_info["columns"]

        for row_idx, row_dict in enumerate(table_info["rows"]):
            # 提取关键字段
            spot_id = row_dict.get("景点ID", "") or row_dict.get("景点ID", "")
            spot_name = row_dict.get("景点名称", "")
            scenic_area = row_dict.get("景区名称", "")

            # 如果没有景点ID也没有景点名称，跳过（可能是空行或汇总行）
            if not spot_id and not spot_name:
                continue

            # 生成自然语言文本块
            text_parts = []
            for field in PRIORITY_FIELDS:
                value = row_dict.get(field, "")
                if value and value.strip():
                    label = FIELD_LABELS.get(field, field)
                    text_parts.append(f"【{label}】{value.strip()}")

            page_content = "\n".join(text_parts)

            # 构建 metadata
            metadata = {
                "source": source_file,
                "source_type": source_type,
                "table_caption": caption,
                "table_index": table_info["table_index"],
                "row_index": row_idx,
                "scenic_spot_id": spot_id,
                "scenic_spot_name": spot_name,
                "scenic_area": scenic_area,
                "raw_fields": json.dumps(row_dict, ensure_ascii=False),
            }

            doc = Document(page_content=page_content, metadata=metadata)
            documents.append(doc)

    return documents


# ============================================================================
# 叙述性文档 → 语义段落块
# ============================================================================

def narrative_paragraphs_to_documents(
    paragraphs: List[Dict[str, Any]],
    source_file: str,
    source_type: str = "guide",
    max_chars: int = MAX_CHUNK_CHARS,
    target_chars: int = TARGET_CHUNK_CHARS,
    min_chars: int = MIN_CHUNK_CHARS,
) -> List[Document]:
    """
    将叙述性段落列表切分为 LangChain Document 列表。

    分块策略:
      1. 按二级标题（level=2）作为主切分边界
      2. 在一级标题（level=1）处也切分（作为章节边界）
      3. 每个 section 内按自然段落累计长度，达到 target_chars 时切一块
      4. 小块（< min_chars）合并到前一块
      5. 每个块不超过 max_chars

    metadata:
      {
        "source": 文件名,
        "source_type": "guide",
        "chunk_index": int,
        "section_title": 当前章节标题,
        "sub_section_title": 当前小节标题（如果有）,
        "doc_name": 文件名（不含扩展名）,
      }

    Args:
        paragraphs: DocxParser.extract_paragraphs() 的返回结果
        source_file: 原始文件名
        source_type: 元数据类型标签
        max_chars: 单块最大字符数
        target_chars: 单块目标字符数
        min_chars: 最小块字符数（低于此值合并）

    Returns:
        List[Document]
    """
    if not paragraphs:
        return []

    # ---------- Step 1: 按标题切分为 sections ----------
    sections = _split_into_sections(paragraphs)

    # ---------- Step 2: 每个 section 内按长度切块 ----------
    documents = []
    chunk_index = 0

    for section in sections:
        section_docs = _split_section_into_chunks(
            section,
            source_file=source_file,
            source_type=source_type,
            start_chunk_index=chunk_index,
            max_chars=max_chars,
            target_chars=target_chars,
            min_chars=min_chars,
        )
        documents.extend(section_docs)
        chunk_index += len(section_docs)

    # ---------- Step 3: 后处理 —— 合并过小的尾部块 ----------
    documents = _merge_small_tail_chunks(documents, min_chars, max_chars)

    # 重新编号 chunk_index
    for i, doc in enumerate(documents):
        doc.metadata["chunk_index"] = i

    return documents


def _split_into_sections(
    paragraphs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    按标题层级将段落分组为 sections。

    切分规则:
      - 遇到 Heading 1/2 → 新 section 开始
      - Heading 3/4 → 作为子标题保留在 section 内
      - 正文段落 → 累积到当前 section

    Returns:
      [
        {
          "section_title": str,          # 一级/二级标题文本
          "section_level": int,          # 触发切分的标题层级
          "sub_section_title": str,      # 最近的三级标题
          "paragraphs": [str, ...],      # 该 section 内的段落文本列表
        },
        ...
      ]
    """
    sections = []
    current_section = None

    # 跟踪当前上下文
    current_h1 = ""   # 最近的一级标题
    current_h2 = ""   # 最近的二级标题
    current_h3 = ""   # 最近的三级标题

    for para in paragraphs:
        level = para["level"]
        text = para["text"]

        if level == 1:
            # 一级标题：开始新 section
            current_h1 = text
            current_h2 = ""
            current_h3 = ""

            if current_section is not None and current_section["paragraphs"]:
                sections.append(current_section)

            current_section = {
                "section_title": text,
                "section_level": 1,
                "sub_section_title": "",
                "paragraphs": [],
            }

        elif level == 2:
            # 二级标题：开始新 section
            current_h2 = text
            current_h3 = ""

            if current_section is not None and current_section["paragraphs"]:
                sections.append(current_section)

            title = f"{current_h1} > {text}" if current_h1 else text
            current_section = {
                "section_title": title,
                "section_level": 2,
                "sub_section_title": "",
                "paragraphs": [],
            }

        elif level >= 3:
            # 三级及以下标题：在当前 section 内作为子标题
            current_h3 = text
            if current_section is None:
                current_section = {
                    "section_title": text,
                    "section_level": level,
                    "sub_section_title": "",
                    "paragraphs": [],
                }
            else:
                current_section["sub_section_title"] = text
                # 子标题也作为段落内容加入
                current_section["paragraphs"].append(f"【{text}】")

        else:
            # 正文段落
            if current_section is None:
                current_section = {
                    "section_title": "文档开头",
                    "section_level": 0,
                    "sub_section_title": "",
                    "paragraphs": [],
                }
            current_section["paragraphs"].append(text)

    # 最后一个 section
    if current_section is not None and current_section["paragraphs"]:
        sections.append(current_section)

    return sections


def _split_section_into_chunks(
    section: Dict[str, Any],
    source_file: str,
    source_type: str,
    start_chunk_index: int,
    max_chars: int,
    target_chars: int,
    min_chars: int,
) -> List[Document]:
    """
    将一个 section 内的段落按长度切分为多个 Document。
    """
    paragraphs = section["paragraphs"]
    section_title = section.get("section_title", "")
    sub_section_title = section.get("sub_section_title", "")
    doc_name = os.path.splitext(os.path.basename(source_file))[0]

    documents = []
    chunk_idx = start_chunk_index
    buffer = ""
    buffer_len = 0

    def flush_buffer():
        nonlocal buffer, buffer_len, chunk_idx
        if not buffer.strip():
            return

        doc = Document(
            page_content=buffer.strip(),
            metadata={
                "source": source_file,
                "source_type": source_type,
                "chunk_index": chunk_idx,
                "section_title": section_title,
                "sub_section_title": sub_section_title,
                "doc_name": doc_name,
            },
        )
        documents.append(doc)
        chunk_idx += 1
        buffer = ""
        buffer_len = 0

    for para_text in paragraphs:
        para_len = len(para_text)

        # 如果单段就超过 max_chars，先 flush 当前 buffer，再拆分该段落
        if para_len > max_chars:
            flush_buffer()

            # 按句子边界拆分超长段落
            sub_chunks = _split_long_paragraph(para_text, max_chars, target_chars)
            for sub_text in sub_chunks:
                doc = Document(
                    page_content=sub_text.strip(),
                    metadata={
                        "source": source_file,
                        "source_type": source_type,
                        "chunk_index": chunk_idx,
                        "section_title": section_title,
                        "sub_section_title": sub_section_title,
                        "doc_name": doc_name,
                    },
                )
                documents.append(doc)
                chunk_idx += 1
            continue

        # 累积到 buffer
        if buffer_len == 0:
            buffer = para_text
            buffer_len = para_len
        else:
            # 当前 buffer + 新段落
            if buffer_len + 1 + para_len <= target_chars:
                buffer += "\n" + para_text
                buffer_len += 1 + para_len
            elif buffer_len + 1 + para_len <= max_chars:
                buffer += "\n" + para_text
                buffer_len += 1 + para_len
                # 超过 target 但在 max 内，如果下一段是标题则 flush
                # 否则继续累积直到达到 max
                if buffer_len >= target_chars:
                    flush_buffer()
            else:
                # 超过 max，flush 当前 buffer 并开始新 buffer
                flush_buffer()
                buffer = para_text
                buffer_len = para_len

    flush_buffer()
    return documents


def _split_long_paragraph(
    text: str, max_chars: int, target_chars: int
) -> List[str]:
    """
    将超长段落按句子边界拆分为多个片段。
    """
    # 按句末标点切分
    sentences = re.split(r'(?<=[。！？；\n])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    buffer = ""
    buffer_len = 0

    for sent in sentences:
        sent_len = len(sent)
        if buffer_len + sent_len <= target_chars:
            buffer += sent
            buffer_len += sent_len
        elif buffer_len + sent_len <= max_chars:
            buffer += sent
            buffer_len += sent_len
            chunks.append(buffer)
            buffer = ""
            buffer_len = 0
        else:
            if buffer:
                chunks.append(buffer)
            # 如果单个句子仍超长，硬切分
            if sent_len > max_chars:
                for i in range(0, sent_len, target_chars):
                    chunks.append(sent[i:i + max_chars])
            else:
                buffer = sent
                buffer_len = sent_len

    if buffer.strip():
        chunks.append(buffer)

    return chunks


def _merge_small_tail_chunks(
    documents: List[Document], min_chars: int, max_chars: int
) -> List[Document]:
    """
    合并过小的尾部块到前一块。
    仅合并 source_type 相同的相邻块。
    """
    if len(documents) <= 1:
        return documents

    merged = []
    for doc in documents:
        if (
            merged
            and len(doc.page_content) < min_chars
            and doc.metadata.get("source_type") == merged[-1].metadata.get("source_type")
            and doc.metadata.get("source") == merged[-1].metadata.get("source")
        ):
            # 检查合并后是否超限
            combined = merged[-1].page_content + "\n" + doc.page_content
            if len(combined) <= max_chars:
                merged[-1].page_content = combined
                # 合并 metadata（保留前者的标题信息）
                continue

        merged.append(doc)

    return merged



