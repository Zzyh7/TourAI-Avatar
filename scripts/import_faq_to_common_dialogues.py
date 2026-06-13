"""
FAQ CSV → 常用对话数据库 导入脚本。

读取 data/scenic_faq_questions.csv：
  1. 对问题文本做相似度聚类（difflib > 0.7 归为一组）
  2. 每组第一个问题作为主 question，其余作为 variants
  3. 自动生成分类和关键词
  4. 通过 POST /api/admin/common-dialogues/batch 导入
  5. 去重：跳过数据库中已存在的相同主问题
"""
import sys
import csv
import json
import difflib
import urllib.request
import urllib.error
from pathlib import Path

# Windows 控制台 UTF-8 编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_BASE = "http://localhost:8000/api/admin/common-dialogues"
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "scenic_faq_questions.csv"
SIMILARITY_THRESHOLD = 0.7

# 分类关键词映射
CATEGORY_RULES = [
    ("门票价格", ["门票", "价格", "多少钱", "票", "优惠", "免费", "老人", "儿童", "学生"]),
    ("交通停车", ["怎么去", "交通", "停车", "开车", "公交", "地铁", "导航", "路线"]),
    ("景点历史文化", ["历史", "文化", "典故", "传说", "故事", "介绍", "是什么"]),
    ("游玩路线", ["路线", "怎么逛", "安排", "顺序", "游览", "建议", "推荐"]),
    ("餐饮住宿", ["吃", "住", "酒店", "素斋", "餐厅", "民宿", "住宿"]),
    ("演出时间", ["演出", "时间", "几点", "开始", "开放", "关门"]),
    ("设施服务", ["厕所", "wifi", "寄存", "轮椅", "充电", "服务"]),
    ("天气季节", ["天气", "季节", "什么时候", "适合", "下雨"]),
    ("闲聊问候", ["你好", "谢谢", "再见", "嗨", "hello", "你是谁"]),
    ("不可回答", ["抱歉", "无法回答"]),
]


def classify(question: str) -> str:
    """根据问题文本自动分类"""
    for cat, keywords in CATEGORY_RULES:
        if any(kw in question for kw in keywords):
            return cat
    return "一般"


def extract_keywords(question: str) -> str:
    """从问题中提取关键词"""
    # 简单提取2字以上实词
    import re
    # 常见停用词
    stop = {'什么', '怎么', '哪里', '怎样', '可以', '有没有', '哪里', '这儿',
            '请问', '一下', '这个', '那个', '吗', '呢', '吧', '呀', '能不能',
            '如何', '能否', '给', '我', '的', '是', '在', '有'}
    tokens = re.split(r'[，。！？、；：\s]+', question)
    keywords = [t for t in tokens if len(t) >= 2 and t not in stop]
    return ','.join(keywords[:5])


def normalize(text: str) -> str:
    """标准化文本用于相似度比对"""
    import re
    text = text.strip().lower()
    text = re.sub(r'[，。！？、；：""（）【】《》\s,\.!\?;:\"\'\(\)\[\]{}]+', '', text)
    return text


def group_questions(rows: list[dict]) -> list[dict]:
    """将相似问题归组，每组返回 {question, answer, variants, category, keywords}"""
    # 先按 answer 分组（相同回答的自动归一组）
    answer_groups: dict[str, list[dict]] = {}
    for row in rows:
        ans = row['answer'].strip()
        if ans not in answer_groups:
            answer_groups[ans] = []
        answer_groups[ans].append(row)

    groups = []
    for answer, items in answer_groups.items():
        questions = [item['question'].strip() for item in items]
        if len(questions) <= 1:
            # 单个问题，直接用
            groups.append({
                'question': questions[0],
                'answer': answer,
                'variants': [],
                'category': classify(questions[0]),
                'keywords': extract_keywords(questions[0]),
            })
        else:
            # 多个问题共享同一回答 → 按相似度再聚类
            clusters = cluster_by_similarity(questions)
            for cluster in clusters:
                main_q = cluster[0]
                variants = cluster[1:] if len(cluster) > 1 else []
                groups.append({
                    'question': main_q,
                    'answer': answer,
                    'variants': variants,
                    'category': classify(main_q),
                    'keywords': extract_keywords(main_q),
                })

    return groups


def cluster_by_similarity(texts: list[str]) -> list[list[str]]:
    """基于 difflib 相似度的简单聚类"""
    if len(texts) <= 1:
        return [texts]

    clusters = []
    used = set()

    for i, t1 in enumerate(texts):
        if i in used:
            continue
        cluster = [t1]
        used.add(i)
        n1 = normalize(t1)

        for j, t2 in enumerate(texts):
            if j in used:
                continue
            n2 = normalize(t2)
            score = difflib.SequenceMatcher(None, n1, n2).ratio()
            if score >= SIMILARITY_THRESHOLD:
                cluster.append(t2)
                used.add(j)

        clusters.append(cluster)

    return clusters


def main():
    print(f"📖 读取 {CSV_PATH}...")
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"📊 共 {len(rows)} 条 FAQ 记录")

    # 分组
    groups = group_questions(rows)
    print(f"🔗 相似度聚类后 → {len(groups)} 组")

    # 统计变体
    total_variants = sum(len(g.get('variants', [])) for g in groups)
    print(f"📎 其中 {total_variants} 条归入变体")

    # 构建批量导入数据
    batch_items = []
    for g in groups:
        variants = g.get('variants', [])
        item = {
            'question': g['question'],
            'answer': g['answer'],
            'keywords': g['keywords'],
            'variants': json.dumps(variants, ensure_ascii=False) if variants else '',
            'category': g['category'],
            'priority': 10 if g['category'] != '闲聊问候' else 5,
            'enabled': 1,
        }
        batch_items.append(item)

    print(f"\n📤 导入 {len(batch_items)} 条到 {API_BASE}/batch ...")

    # 分批导入（每批50条，避免超时）
    batch_size = 50
    total_imported = 0
    for i in range(0, len(batch_items), batch_size):
        chunk = batch_items[i:i + batch_size]
        req_data = json.dumps({"items": chunk}).encode('utf-8')

        req = urllib.request.Request(
            f"{API_BASE}/batch",
            data=req_data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                count = result.get('imported', len(chunk))
                total_imported += count
                print(f"  ✅ 第 {i // batch_size + 1} 批: {count} 条")
        except urllib.error.HTTPError as e:
            print(f"  ❌ 导入失败: {e.status} {e.reason}")
            print(f"     {e.read().decode()[:200]}")
            return
        except urllib.error.URLError as e:
            print(f"  ❌ 连接失败: {e.reason}")
            print(f"     请确保后端已启动 (python start.py)")
            return

    print(f"\n🎉 导入完成！共导入 {total_imported} 组常用对话")
    print(f"   原始 {len(rows)} 条 → 聚类为 {len(groups)} 组（含 {total_variants} 条变体）")
    print(f"   现在可以在管理后台 → 常用对话 中查看和管理")


if __name__ == '__main__':
    main()
