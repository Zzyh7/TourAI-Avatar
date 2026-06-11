#!/usr/bin/env python3
"""
将灵山胜境示范景区文档导入 RAG 知识库。

使用方式:
    cd d:/TravelAgent
    python scripts/ingest_lingshan.py

    # 或指定文档路径
    python scripts/ingest_lingshan.py --structured "path/to/数据集.docx" --guide "path/to/指南.docx"

    # 全量重建模式（清空旧数据）
    python scripts/ingest_lingshan.py --rebuild

    # 仅预览（不写入）
    python scripts/ingest_lingshan.py --dry-run

文档说明:
  1. 灵山胜境 景点结构化数据集.docx
     - 含两个子表: 灵山胜境景点、拈花湾景点
     - 每行一个景点，包含景区名称、景点ID、景点名称、具体位置、文化内涵等
     - 每行 → 一个自然语言文本块，metadata 含景点ID、景点名称、原始字段副本

  2. 灵山胜境：历史、文化、景点特色与个性化游览指南.docx
     - 长篇叙述性文档，含景区概况、历史渊源、文化内涵、景点特色、游览路线等
     - 按二级标题语义切块，每块 300~500 字，metadata 含章节标题
"""
import sys
import os
import argparse

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 将 backend 加入路径
backend_path = os.path.join(PROJECT_ROOT, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# 默认文档路径
DESKTOP_DIR = os.path.expandvars(r"%USERPROFILE%\Desktop")
DEFAULT_DOC_DIR = os.path.join(DESKTOP_DIR, "新建文件夹", "示范景区公开资料包")

DEFAULT_STRUCTURED = os.path.join(
    DEFAULT_DOC_DIR, "灵山胜境 景点结构化数据集.docx"
)
DEFAULT_GUIDE = os.path.join(
    DEFAULT_DOC_DIR, "灵山胜境：历史、文化、景点特色与个性化游览指南.docx"
)


def print_banner():
    print("=" * 60)
    print("  灵山胜境 RAG 知识库 — 文档摄入工具")
    print("=" * 60)


def print_separator(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def main():
    parser = argparse.ArgumentParser(
        description="将灵山胜境文档导入 RAG 知识库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ingest_lingshan.py
  python ingest_lingshan.py --structured "data/景点数据.docx" --guide "data/指南.docx"
  python ingest_lingshan.py --rebuild
  python ingest_lingshan.py --dry-run
        """,
    )
    parser.add_argument(
        "--structured",
        default=DEFAULT_STRUCTURED,
        help="结构化表格文档路径",
    )
    parser.add_argument(
        "--guide",
        default=DEFAULT_GUIDE,
        help="叙述性指南文档路径",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="清空现有索引，从零重建（默认：增量合并）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览解析结果，不写入存储",
    )

    args = parser.parse_args()
    print_banner()

    # ================================================================
    # 1. 检查文件
    # ================================================================
    print_separator("1. 检查文档文件")

    missing = []
    for label, path in [("结构化数据集", args.structured), ("游览指南", args.guide)]:
        exists = os.path.exists(path)
        status = "✓" if exists else "✗ 不存在"
        print(f"   [{status}] {label}: {path}")
        if not exists:
            missing.append(path)

    if missing:
        print(f"\n⚠ 以下文件未找到，请确认路径:")
        for p in missing:
            print(f"   - {p}")
        if args.dry_run:
            print("   (dry-run 模式，继续预览可用文件)")
        else:
            print("   请使用 --structured 和 --guide 指定正确路径")
            sys.exit(1)

    # ================================================================
    # 2. 初始化 RAG 服务
    # ================================================================
    if not args.dry_run:
        print_separator("2. 初始化 RAG 服务")

        from rag_system import init_rag
        init_rag()

        from rag_system.ingestion import IngestionPipeline
        pipeline = IngestionPipeline()

        # 打印初始状态
        stats = pipeline.get_stats()
        print(f"   FAISS 向量: {stats['faiss_vectors']}")
        print(f"   BM25 文档:  {stats['bm25_documents']}")
        print(f"   SQLite 文档: {stats['documents_count']}")
        print(f"   SQLite 块:  {stats['chunks_count']}")
        print(f"   对齐状态:   {'✓' if stats['aligned'] else '⚠ 未对齐'}")

        # 如果需要全量重建
        if args.rebuild:
            print_separator("2b. 全量重建索引")
            print("⚠ 将清空现有 FAISS/BM25 索引并从 SQLite 重建...")

            # 注意: rebuild 是保留 SQLite 数据，仅重建向量索引
            # 如果要完全清空，需要先清理 SQLite
            if stats['chunks_count'] > 0:
                response = input("   是否同时清空 SQLite 数据？[y/N] ")
                if response.lower() == 'y':
                    # 这里不做自动清空（太危险），提示用户手动操作
                    print("   请手动删除 data/rag_data/chunks.db 后再运行 --rebuild")
                    sys.exit(0)

            pipeline.rebuild_from_existing()
    else:
        print_separator("2. DRY-RUN 模式（仅预览，不写入）")

    # ================================================================
    # 3. 解析预览
    # ================================================================
    print_separator("3. 文档解析预览")

    from rag_system.ingestion.parser import DocxParser

    # --- 结构化文档预览 ---
    if os.path.exists(args.structured):
        try:
            parser_s = DocxParser(args.structured)
            tables = parser_s.extract_tables()
            info_s = parser_s.get_info()
            print(f"\n   📊 结构化数据集: {info_s['file_name']}")
            print(f"   文件大小: {info_s['file_size']:,} 字节")
            print(f"   表格数:   {len(tables)}")
            for t in tables:
                print(f"     └─ [{t['table_index']}] {t['caption'] or '(无标题)'}")
                print(f"        列: {', '.join(t['columns'][:8])}{'...' if len(t['columns']) > 8 else ''}")
                print(f"        行: {t['row_count']}")

                # 展示第一行样例
                if t['rows']:
                    sample = t['rows'][0]
                    spot_name = sample.get('景点名称', '?')
                    spot_id = sample.get('景点ID', '?')
                    print(f"        样例: {spot_name} (ID: {spot_id})")
        except Exception as e:
            print(f"   ⚠ 结构化文档解析失败: {e}")

    # --- 叙述性文档预览 ---
    if os.path.exists(args.guide):
        try:
            parser_g = DocxParser(args.guide)
            paragraphs = parser_g.extract_paragraphs()
            info_g = parser_g.get_info()
            headings = [p for p in paragraphs if p['is_heading']]
            print(f"\n   📝 叙述性文档: {info_g['file_name']}")
            print(f"   文件大小: {info_g['file_size']:,} 字节")
            print(f"   非空段落: {len(paragraphs)}")
            print(f"   标题段落: {len(headings)}")
            if headings:
                print(f"   标题结构预览:")
                for h in headings[:10]:
                    indent = "  " * (h['level'] - 1)
                    print(f"     {indent}[H{h['level']}] {h['text'][:60]}")
                if len(headings) > 10:
                    print(f"     ... 共 {len(headings)} 个标题")
        except Exception as e:
            print(f"   ⚠ 叙述性文档解析失败: {e}")

    # ================================================================
    # 4. 执行摄入
    # ================================================================
    if args.dry_run:
        print_separator("DRY-RUN 完成（未写入任何数据）")
        return

    print_separator("4. 执行文档摄入")

    results = []

    # --- 结构化数据集 ---
    if os.path.exists(args.structured):
        print("\n   📊 摄入结构化数据集...")
        result_s = pipeline.ingest_structured_docx(args.structured)
        results.append(result_s)
        print(f"   {result_s.summary()}")

    # --- 叙述性文档 ---
    if os.path.exists(args.guide):
        print("\n   📝 摄入叙述性文档...")
        result_g = pipeline.ingest_narrative_docx(args.guide)
        results.append(result_g)
        print(f"   {result_g.summary()}")

    # ================================================================
    # 5. 最终状态
    # ================================================================
    print_separator("5. 最终状态")

    stats = pipeline.get_stats()
    print(f"   FAISS 向量: {stats['faiss_vectors']}")
    print(f"   BM25 文档:  {stats['bm25_documents']}")
    print(f"   SQLite 文档: {stats['documents_count']}")
    print(f"   SQLite 块:  {stats['chunks_count']}")
    print(f"   对齐状态:   {'✓ 已对齐' if stats['aligned'] else '⚠ 未对齐'}")

    # 按类型统计
    doc_store = pipeline.doc_store
    all_docs = doc_store.get_all_documents()
    print(f"\n   已存储文档:")
    for doc in all_docs:
        chunks = doc_store.get_chunks_by_document(doc['id'])
        source_types = set()
        for ch in chunks:
            meta_raw = ch.get("metadata", "{}")
            try:
                meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                if isinstance(meta, dict) and meta.get("source_type"):
                    source_types.add(meta["source_type"])
            except Exception:
                pass
        types_str = ", ".join(source_types) if source_types else "未知"
        print(f"     [{doc['id']}] {doc['filename']} ({doc['chunk_count']} 块, 类型: {types_str})")

    # 最终对齐校验
    if not stats['aligned']:
        print("\n⚠ FAISS 与 SQLite 未对齐! 建议运行 rebuild:")
        print("   python scripts/ingest_lingshan.py --rebuild")

    # 成功/失败汇总
    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n❌ {len(failed)} 个文档摄入失败:")
        for r in failed:
            print(f"   - {r.file_name}: {r.error}")
        sys.exit(1)
    else:
        print(f"\n✓ 全部 {len(results)} 个文档摄入成功!")


if __name__ == "__main__":
    import json  # 用于最终状态展示
    main()
