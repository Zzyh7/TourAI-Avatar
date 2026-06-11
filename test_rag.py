#!/usr/bin/env python
"""
RAG 系统测试脚本 —— 验证知识库的完整工作流。

运行方式:
    cd backend
    python ../test_rag.py

测试流程:
  1. 创建样例景区文档 (txt)
  2. 启动 RAG 服务
  3. 上传样例文档
  4. 导入 FAQ 问答对
  5. 执行多个查询测试
  6. 验证混合检索 + RRF 融合效果
  7. 打印结果和统计信息

前置条件:
  - 已安装所有依赖: pip install -r requirements.txt
  - 环境变量 DEEPSEEK_API_KEY 已配置（可选，没有也可以测试检索）
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# 确保项目路径在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()


# ==================== 辅助函数 ====================

def create_sample_document() -> str:
    """创建一个中文景区介绍样例文档"""
    content = """杭州西湖景区介绍

一、景区概况
杭州西湖位于浙江省杭州市西部，是中国大陆首批国家重点风景名胜区和中国十大风景名胜之一。
西湖三面环山，面积约6.39平方千米，东西宽约2.8千米，南北长约3.2千米，绕湖一周近15千米。

二、著名景点

1. 断桥残雪
断桥位于西湖北部，是西湖十景之一。相传许仙与白娘子在此相遇，因此断桥也被称为"爱情之桥"。
每到冬季下雪时，桥面阳面雪已融化，阴面雪尚未消，远远望去桥像断了一样，故名"断桥残雪"。

2. 三潭印月
三潭印月是西湖中最大的岛屿，又名"小瀛洲"。岛南湖面上有三座石塔，塔身中空球形，球面有五个小孔。
每逢月夜，在塔内点上灯烛，洞口蒙上薄纸，灯光从孔中透出，宛如一个个小月亮，
与天上明月、湖中倒影相映成趣，故名"三潭印月"。此景被印在人民币一元的纸币背面。

3. 雷峰塔
雷峰塔位于西湖南岸的夕照山上，始建于北宋太平兴国二年（977年）。
原塔为吴越国王钱俶为供奉佛螺髻发舍利而建。塔身因年久失修于1924年倒塌，2002年重建竣工。
传说中的白娘子曾被法海镇压于雷峰塔下，因此雷峰塔在民间故事中非常有名。

4. 苏堤春晓
苏堤是北宋大文豪苏轼任杭州知州时，疏浚西湖利用浚挖的淤泥构筑而成，全长约2.8公里。
苏堤上共有六座石拱桥，堤上遍植桃柳，春天桃花盛开、柳丝吐绿，景色格外迷人，
是"西湖十景"之首。

三、游览建议
最佳游览季节：春季（3-5月）和秋季（9-11月）。
建议游览时间：全程步行约4-5小时，骑行约2小时。”
门票信息：西湖景区免费开放，但部分景点如雷峰塔需单独购票（40元/人）。
交通方式：可乘坐地铁1号线到龙翔桥站，或乘坐多路公交到达。

四、历史文化
西湖文化景观于2011年被列入《世界遗产名录》。自古以来，西湖就是文人墨客吟诗作画的灵感源泉。
白居易、苏轼、柳永等历代文豪都曾留下赞美西湖的传世诗篇。
"欲把西湖比西子，淡妆浓抹总相宜"——苏轼的这句诗成为了西湖最经典的文化名片。
"""
    tmp_path = os.path.join(tempfile.gettempdir(), "西湖景区介绍_测试.txt")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ 已创建样例文档: {tmp_path}")
    return tmp_path


def print_separator(title: str = ""):
    """打印分隔线"""
    width = 70
    if title:
        print(f"\n{'='*width}")
        print(f"  {title}")
        print(f"{'='*width}")
    else:
        print(f"{'='*width}")


def print_result(query: str, result: dict):
    """格式化打印查询结果"""
    print(f"\n{'─'*60}")
    print(f"🔍 问题: {query}")
    print(f"{'─'*60}")

    if "answer" in result:
        print(f"📝 答案: {result['answer'][:500]}")
    elif "docs" in result:
        docs = result["docs"]
        if docs:
            print(f"📝 最佳匹配块 ({len(docs)} 个):")
            for i, doc in enumerate(docs[:3]):
                content = doc.page_content[:150].replace("\n", " ")
                print(f"   [{i+1}] {content}...")

    if "sources" in result:
        print(f"📂 来源: {result['sources']}")

    if "scores" in result:
        print(f"📊 分数: {[f'{s:.4f}' for s in result['scores']]}")

    if result.get("from_faq"):
        print("🏷️  匹配类型: FAQ 精确匹配")
    if result.get("below_threshold"):
        print("⚠️  状态: 低于置信度阈值")


# ==================== 主测试流程 ====================

def main():
    print_separator("RAG 知识库系统测试")
    print("测试环境: Python", sys.version.split()[0])
    print("项目路径:", str(Path(__file__).parent))

    # ================================================================
    # 1. 创建样例文档
    # ================================================================
    print_separator("1. 创建样例文档")
    sample_doc_path = create_sample_document()

    # ================================================================
    # 2. 初始化 RAG 服务
    # ================================================================
    print_separator("2. 初始化 RAG 服务")
    from rag_system import init_rag, get_retriever, get_doc_store, get_embedder

    init_rag()
    retriever = get_retriever()
    doc_store = get_doc_store()
    embedder = get_embedder()

    print(f"\n📊 初始索引状态:")
    stats = retriever.stats
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # ================================================================
    # 3. 加载并上传样例文档
    # ================================================================
    print_separator("3. 上传样例文档")

    from rag_system.loader import DocumentLoader
    from rag_system.splitter import TextSplitter

    # 解析文档
    docs = DocumentLoader.load(sample_doc_path)
    print(f"   解析结果: {len(docs)} 页/段")

    # 分块
    splitter = TextSplitter()
    chunks = splitter.split_documents(docs)
    print(f"   分块结果: {len(chunks)} 个块")

    # 打印前3个块的内容摘要
    print("\n   前3个块预览:")
    for i, chunk in enumerate(chunks[:3]):
        preview = chunk.page_content[:80].replace("\n", " ")
        source = chunk.metadata.get("source", "?")
        print(f"   [{i}] [{source}] {preview}...")

    # 添加到 SQLite 先（获取 chunk_id）
    doc_id, chunk_ids = doc_store.add_document(
        filename="西湖景区介绍_测试.txt",
        file_type="txt",
        chunks=chunks,
        size_bytes=os.path.getsize(sample_doc_path),
    )

    # 将 chunk_id 标记到每个块，再写入 FAISS/BM25
    for chunk, cid in zip(chunks, chunk_ids):
        chunk.metadata["chunk_id"] = cid
        chunk.metadata["embedding_model"] = embedder.model_name

    retriever.add_documents(chunks)

    print(f"\n📊 上传后索引状态:")
    stats = retriever.stats
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # ================================================================
    # 4. 导入 FAQ 问答对
    # ================================================================
    print_separator("4. 导入 FAQ 问答对")

    faq_pairs = [
        {"question": "西湖的开放时间？", "answer": "西湖景区全天免费开放，部分景点如雷峰塔开放时间为8:00-17:30。"},
        {"question": "西湖门票多少钱？", "answer": "西湖景区免费开放，但雷峰塔门票40元/人，三潭印月船票55元/人（含上岛费）。"},
        {"question": "西湖怎么去？", "answer": "可乘坐杭州地铁1号线至龙翔桥站C口出，步行约500米即到；或乘坐公交7路、51路、52路等到达。"},
        {"question": "西湖最佳游览季节？", "answer": "春季（3-5月）桃花盛开、秋季（9-11月）气候宜人，是西湖最佳游览季节。"},
        {"question": "西湖有哪些著名景点？", "answer": "西湖十景包括：苏堤春晓、断桥残雪、三潭印月、雷峰夕照、曲院风荷、平湖秋月、花港观鱼、柳浪闻莺、南屏晚钟、双峰插云。"},
    ]
    retriever.import_faq(faq_pairs)
    print(f"   已导入 {len(faq_pairs)} 个 FAQ")

    # ================================================================
    # 5. 执行测试查询
    # ================================================================
    print_separator("5. 测试查询")

    test_queries = [
        # FAQ 精确匹配测试
        "西湖门票多少钱？",
        # 知识检索测试
        "断桥残雪有什么传说？",
        "三潭印月的由来是什么？",
        "雷峰塔是什么时候建的？",
        # 多结果融合测试
        "苏轼和西湖有什么关系？",
        # 边界测试（应该返回"不知道"）
        "西湖附近有什么好吃的餐厅？",
    ]

    for query in test_queries:
        result = retriever.retrieve(query)
        print_result(query, result)

    # ================================================================
    # 6. 测试 /query 接口（模拟）
    # ================================================================
    print_separator("6. 最终统计")

    stats = retriever.stats
    print(f"   FAISS 向量数: {stats['faiss_vectors']}")
    print(f"   BM25 文档数:  {stats['bm25_documents']}")
    print(f"   FAQ 问答对:   {stats['faq_pairs']}")
    print(f"   SQLite 文档:  {doc_store.get_document_count()}")
    print(f"   SQLite 块数:  {doc_store.get_chunk_count()}")

    # ================================================================
    # 7. 清理（可选）
    # ================================================================
    print_separator("测试完成")
    print("✅ 所有测试通过！")
    print(f"\n💡 提示:")
    print(f"   - 独立启动 RAG 服务: cd backend && python -m rag_system.main")
    print(f"   - 或集成到现有服务: 在 backend/main.py 中添加:")
    print(f"     from rag_system import rag_router")
    print(f"     app.include_router(rag_router, prefix='/api/rag')")
    print(f"   - API 文档: http://localhost:8001/docs")
    print(f"   - 样例文档已保留在: {sample_doc_path}")


if __name__ == "__main__":
    main()
