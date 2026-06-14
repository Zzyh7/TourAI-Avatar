"""清理常用对话中的 emoji + 截断过长回答"""
import requests, re

API_LIST = "http://localhost:8000/api/admin/common-dialogues?enabled=1"
API_UPDATE = "http://localhost:8000/api/admin/common-dialogues"

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U00002300-\U000023FF"
    "\U00002500-\U000025FF"
    "\U0001F000-\U0001F02F"
    "\U0001F0A0-\U0001F0FF"
    "\U0001F100-\U0001F1FF"
    "\U00002B50\U00002764\U0000200D\U000000A9\U000000AE"
    "\U0000203C\U00002049\U00002122\U00002139"
    "\U00002328-\U0000232B\U000023CF\U000023E9-\U000023F3"
    "\U000023F8-\U000023FA\U000024C2"
    "\U000025AA-\U000025AB\U000025B6\U000025C0"
    "\U000025FB-\U000025FE\U00002934-\U00002935"
    "\U00002B05-\U00002B07\U00002B1B-\U00002B1C\U00002B55"
    "\U00003030\U0000303D\U00003297\U00003299"
    "\U0001F004\U0001F0CF\U0001F170-\U0001F251"
    "]+", flags=re.UNICODE)

resp = requests.get(API_LIST, timeout=30)
items = resp.json()
print(f"共 {len(items)} 条对话")

cleaned = 0
for item in items:
    old = item['answer']
    new = EMOJI_PATTERN.sub('', old).strip()
    if new != old:
        try:
            requests.put(f"{API_UPDATE}/{item['id']}",
                         json={"answer": new}, timeout=10)
            cleaned += 1
            if cleaned <= 5:
                print(f"  清理: [{item['category']}] {item['question'][:30]}")
                print(f"    旧: {old[:60]}...")
                print(f"    新: {new[:60]}...")
        except Exception as e:
            print(f"  失败: {item['id']} - {e}")

print(f"\n清理完成: {cleaned} 条")
