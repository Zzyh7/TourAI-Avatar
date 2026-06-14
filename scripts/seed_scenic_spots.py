"""
导入灵山胜境景点GPS数据到 scenic_spots 表

用于GPS触发讲解功能：游客进入触发半径后自动提醒
"""
import sys, requests

API = "http://localhost:8000/api/admin/scenic-spots"

# 灵山胜境核心景点 GPS 坐标（近似值）
SPOTS = [
    {
        "name": "灵山大佛",
        "latitude": 31.4235, "longitude": 120.1025,
        "trigger_radius": 200,
        "description": "灵山大佛高88米，由2000块青铜板块拼接而成，是国内最高的巨型青铜佛像之一。大佛面朝太湖，背倚小灵山，右手施无畏印、左手施与愿印，寓意庇佑众生、赐福人间。",
        "category": "核心景点",
        "visit_duration": 30,
    },
    {
        "name": "九龙灌浴",
        "latitude": 31.4240, "longitude": 120.1030,
        "trigger_radius": 200,
        "description": "九龙灌浴是一座大型音乐动态雕塑群，再现佛祖释迦牟尼诞生时九龙喷水沐浴的场景。每天定时有多场音乐喷泉表演，莲花缓缓绽放露出太子佛像，九条龙口中喷出水柱，场面极为震撼。",
        "category": "核心景点",
        "visit_duration": 20,
    },
    {
        "name": "梵宫",
        "latitude": 31.4220, "longitude": 120.1040,
        "trigger_radius": 150,
        "description": "梵宫是灵山胜境中一座金碧辉煌的佛教文化艺术殿堂，内部穹顶布满星空壁画、精美木雕和琉璃装饰。宫内还上演吉祥颂全息投影演出，将佛教故事与现代科技完美融合。",
        "category": "核心景点",
        "visit_duration": 40,
    },
    {
        "name": "五印坛城",
        "latitude": 31.4215, "longitude": 120.1035,
        "trigger_radius": 200,
        "description": "五印坛城是一座临水而建的藏传佛教风格建筑，展示了藏族佛教文化的独特魅力。坛城内陈列着精美的唐卡、佛像和法器，顶层的观景台可以俯瞰景区全貌和水面倒影。",
        "category": "文化景点",
        "visit_duration": 30,
    },
    {
        "name": "拈花湾",
        "latitude": 31.4180, "longitude": 120.0980,
        "trigger_radius": 300,
        "description": "拈花湾是一座以禅意为主题的唐风小镇，青石板路、木制建筑、小桥流水，营造出宁静悠远的东方美学氛围。这里有抄经、茶道、花道等禅修体验项目，还有夜间灯光秀和唐风灯笼街区，非常出片。",
        "category": "休闲景点",
        "visit_duration": 120,
    },
    {
        "name": "灵山胜境牌坊",
        "latitude": 31.4250, "longitude": 120.1000,
        "trigger_radius": 150,
        "description": "灵山胜境牌坊是景区的正门入口，高大的石牌坊上镌刻着灵山胜境四个大字。穿过牌坊即进入景区主轴线，正对远处的灵山大佛，是游客入园后的第一个打卡点。",
        "category": "入口",
        "visit_duration": 5,
    },
    {
        "name": "阿育王柱",
        "latitude": 31.4228, "longitude": 120.1018,
        "trigger_radius": 100,
        "description": "阿育王柱是佛教的重要象征物，柱身刻有经文和佛教图案。灵山胜境的阿育王柱位于中轴线上，连接牌坊和大佛，是游览动线上的地标性建筑。",
        "category": "文化景点",
        "visit_duration": 10,
    },
    {
        "name": "天下第一掌",
        "latitude": 31.4230, "longitude": 120.1020,
        "trigger_radius": 100,
        "description": "天下第一掌是按灵山大佛右手1比1比例复制的青铜巨掌。游客纷纷排队触摸佛手祈求福气，摸摸佛手沾福气已成为灵山胜境最受欢迎的互动体验之一。",
        "category": "互动景点",
        "visit_duration": 10,
    },
    {
        "name": "百子戏弥勒",
        "latitude": 31.4238, "longitude": 120.1028,
        "trigger_radius": 100,
        "description": "百子戏弥勒是一座大型青铜群雕，描绘了一百个孩童围绕在弥勒佛身旁嬉戏的欢乐场景。雕像生动有趣，充满童真，是亲子游客最喜欢的景点之一。",
        "category": "互动景点",
        "visit_duration": 10,
    },
    {
        "name": "降魔浮雕",
        "latitude": 31.4225, "longitude": 120.1022,
        "trigger_radius": 100,
        "description": "降魔浮雕是一组描绘佛祖成道前降服魔军的大型浮雕墙，画面气势磅礴，雕刻工艺精湛。浮雕生动展现了佛教经典故事场景，是了解佛教文化的重要窗口。",
        "category": "文化景点",
        "visit_duration": 10,
    },
    {
        "name": "曼飞龙塔",
        "latitude": 31.4210, "longitude": 120.1038,
        "trigger_radius": 150,
        "description": "曼飞龙塔是一座南传佛教风格的白塔建筑群，主塔高耸，周围环绕多座小塔，造型独特优美。白塔在阳光下熠熠生辉，与周围山水相映成趣。",
        "category": "文化景点",
        "visit_duration": 15,
    },
]

def main():
    # 1. 查已有
    resp = requests.get(API, timeout=10)
    existing = {s['name'] for s in resp.json()} if resp.ok else set()
    print(f"已有 {len(existing)} 个景点")

    # 2. 导入新景点
    added = 0
    for spot in SPOTS:
        if spot['name'] in existing:
            print(f"  跳过: {spot['name']} (已存在)")
            continue
        r = requests.post(API, json=spot, timeout=10)
        if r.ok:
            print(f"  导入: {spot['name']} ({spot['latitude']},{spot['longitude']}) r={spot['trigger_radius']}m")
            added += 1
        else:
            print(f"  失败: {spot['name']} - {r.text[:100]}")

    print(f"\n导入 {added} 个新景点，共 {len(SPOTS)} 个")
    print("管理后台: http://localhost:5174 → 景点管理")

if __name__ == '__main__':
    main()
