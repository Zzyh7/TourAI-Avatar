"""
CSV FAQ → JSON → 常用对话管理 导入脚本

读取 data/scenic_faq_questions.csv:
  1. 查数据库已有问题，跳过重复项
  2. 按答案分组 + difflib 相似度聚类 (≥0.7)
  3. 每组首条为主 question，其余为 variants
  4. 自动生成 keywords + category + priority
  5. 清洗回答 (去除 markdown/emoji/拒绝语)
  6. 输出 JSON 文件 + 批量导入

用法: python scripts/import_csv_to_common.py
"""
import sys
import csv
import json
import difflib
import re
import requests
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_BATCH = "http://localhost:8000/api/admin/common-dialogues/batch"
API_LIST  = "http://localhost:8000/api/admin/common-dialogues?enabled=1"
CSV_PATH  = Path(__file__).resolve().parent.parent / "data" / "scenic_faq_questions.csv"
OUT_PATH  = Path(__file__).resolve().parent.parent / "data" / "scenic_faq_dialogues.json"
SIMILARITY_THRESHOLD = 0.7

# ---- 分类规则 ----
CATEGORY_RULES = [
    ("景点介绍",   ["介绍", "是什么", "有什么", "有哪些", "景点", "概况", "概述"]),
    ("地理位置",   ["在哪", "哪里", "什么地方", "地址", "位置", "怎么去", "交通"]),
    ("门票价格",   ["门票", "价格", "多少钱", "票", "优惠", "免费", "老人票", "儿童票", "学生票"]),
    ("开放时间",   ["时间", "几点", "开放", "关门", "演出", "场次", "安排"]),
    ("游玩攻略",   ["路线", "怎么逛", "安排", "顺序", "建议", "推荐", "拍照", "打卡"]),
    ("历史文化",   ["历史", "文化", "典故", "传说", "故事", "佛教", "建造", "年代"]),
    ("设施服务",   ["厕所", "WiFi", "寄存", "轮椅", "充电", "服务", "停车"]),
    ("餐饮住宿",   ["吃", "住", "酒店", "素斋", "餐厅", "民宿", "住宿", "美食"]),
    ("天气季节",   ["天气", "季节", "适合", "下雨", "夏天", "冬天", "什么时候"]),
    ("闲聊问候",   ["你好", "谢谢", "再见", "嗨", "hello", "你是谁", "在吗"]),
]

# ---- 停用词 ----
STOP_WORDS = {
    '什么', '怎么', '哪里', '怎样', '可以', '有没有', '这儿', '那儿',
    '请问', '一下', '这个', '那个', '吗', '呢', '吧', '呀', '能不能',
    '如何', '能否', '给', '我', '的', '是', '在', '有', '了', '个',
    '为什么', '多少', '还是', '或者', '及', '与', '和', '不', '很',
}

# ---- 回答清洗规则 ----
def clean_answer(text: str) -> str:
    """去除 markdown / emoji / 拒绝语"""
    t = text.strip()
    # 去 markdown
    t = t.replace('**', '').replace('##', '').replace('###', '').replace('*', '').replace('#', '')
    t = t.replace('`', '').replace('~~', '')
    # 去常见 emoji
    t = re.sub(r'[\U0001F300-\U0001F9FF☀-➿⭐✅]', '', t)
    # 替换拒绝语
    t = t.replace('抱歉，我无法回答', '您可以到游客中心咨询工作人员')
    t = t.replace('抱歉，我没听懂', '您换个方式问一下，或者去游客中心了解')
    t = t.replace('抱歉，我不太清楚', '具体信息建议您到游客中心确认')
    t = re.sub(r'搜索.*?问题', '', t)
    t = t.strip()
    return t


def normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r'[，。！？、；：""（）【】《》\s,\.!\?;:\"\'\(\)\[\]{}]+', '', t)
    return t


def classify(question: str) -> str:
    for cat, kws in CATEGORY_RULES:
        if any(kw in question for kw in kws):
            return cat
    return "综合问答"


def extract_keywords(question: str) -> str:
    tokens = re.split(r'[，。！？、；：\s]+', question)
    kws = [t for t in tokens if len(t) >= 2 and t not in STOP_WORDS]
    return ','.join(kws[:5])


def cluster_by_similarity(texts: list[str]) -> list[list[str]]:
    if len(texts) <= 1:
        return [texts]
    clusters, used = [], set()
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
            if difflib.SequenceMatcher(None, n1, n2).ratio() >= SIMILARITY_THRESHOLD:
                cluster.append(t2)
                used.add(j)
        clusters.append(cluster)
    return clusters


def fetch_existing_questions() -> set:
    """从数据库获取已存在的问题文本（用于去重）"""
    try:
        resp = requests.get(API_LIST, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        questions = set()
        for item in items:
            q = (item.get('question') or '').strip()
            if q:
                questions.add(q)
        return questions
    except Exception as e:
        print(f"  ⚠️  无法获取已有对话 ({e})，将跳过去重")
        return set()


def main():
    # 1. 获取已有对话
    print("🔍 查询已有对话...")
    existing = fetch_existing_questions()
    print(f"  数据库中已有 {len(existing)} 条")

    # 2. 读取 CSV
    print(f"📖 读取 {CSV_PATH}...")
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    print(f"  CSV 共 {len(rows)} 行")

    # 3. 按答案分组
    answer_groups: dict[str, list[dict]] = {}
    for row in rows:
        ans = clean_answer(row['answer'].strip())
        if not ans:
            continue
        answer_groups.setdefault(ans, []).append(row)

    # 4. 每组内相似度聚类
    all_items = []
    skipped_dup = 0
    for answer, items in answer_groups.items():
        questions = [it['question'].strip() for it in items]
        clusters = cluster_by_similarity(questions)

        for cluster in clusters:
            main_q = cluster[0]
            variants = cluster[1:] if len(cluster) > 1 else []

            # 去重：主问题或变体中任一条已存在则跳过整组
            all_qs = [main_q] + variants
            if any(q in existing for q in all_qs):
                skipped_dup += 1
                continue

            item = {
                "question": main_q,
                "answer": answer,
                "keywords": extract_keywords(main_q),
                "category": classify(main_q),
                "priority": 5 if classify(main_q) == "闲聊问候" else 10,
                "enabled": 1,
                "variants": json.dumps(variants, ensure_ascii=False) if variants else "",
            }
            all_items.append(item)

    print(f"  CSV {len(rows)}行 → 聚类后 {len(all_items) + skipped_dup} 组")
    print(f"  跳过 {skipped_dup} 组（已存在）")
    print(f"  待导入 {len(all_items)} 组")

    if not all_items:
        print("\n✅ 没有新对话需要导入，全部已存在。")
        return

    # 5. 输出 JSON 文件（仅含导入字段，不含 variants）
    json_output = []
    for it in all_items:
        json_output.append({
            "question": it["question"],
            "answer": it["answer"],
            "keywords": it["keywords"],
            "category": it["category"],
            "priority": it["priority"],
            "enabled": it["enabled"],
        })

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 已输出: {OUT_PATH} ({len(json_output)} 条)")

    # 6. 分批导入
    print(f"\n📤 导入到 {API_BATCH} ...")
    BATCH_SIZE = 50
    total_ok = 0
    for i in range(0, len(all_items), BATCH_SIZE):
        chunk = all_items[i:i + BATCH_SIZE]
        try:
            resp = requests.post(API_BATCH, json={"items": chunk}, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            n = result.get('imported', len(chunk))
            total_ok += n
            print(f"  第 {i // BATCH_SIZE + 1} 批: {n} 条 OK")
        except Exception as e:
            print(f"  第 {i // BATCH_SIZE + 1} 批: FAILED — {e}")

    print(f"\n🎉 完成！成功导入 {total_ok} 条")
    print(f"  管理后台: http://localhost:5174 → 常用对话")


if __name__ == '__main__':
    main()
