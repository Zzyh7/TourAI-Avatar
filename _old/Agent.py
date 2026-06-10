"""
智能旅行助手 —— 入口。

用法:
    python Agent.py                # 流式输出（默认）
    python Agent.py --no-stream    # 非流式输出
"""
import asyncio
from config import CONFIG
from agents.planner import TripPlanner
from render import format_plan_cli


# ==================== 演示 ====================

async def demo_stream(planner: TripPlanner, user_input: str):
    """流式输出演示 —— 实时打印 token，结束后渲染格式化计划"""
    print("=" * 60)
    print(f"🚀 正在为您规划旅行...\n输入: {user_input}\n")
    print("=" * 60)

    buffer = ""
    async for token in planner.stream(user_input):
        print(token, end="", flush=True)
        buffer += token

    # 格式化渲染
    formatted = format_plan_cli(buffer)
    if formatted:
        print(formatted)

    print("=" * 60)
    print("✅ 旅行计划生成完毕")


async def demo_invoke(planner: TripPlanner, user_input: str):
    """非流式输出演示"""
    print("=" * 60)
    print(f"🚀 正在为您规划旅行...\n输入: {user_input}\n")
    print("=" * 60)

    result = await planner.invoke(user_input)
    formatted = format_plan_cli(result)
    if formatted:
        print(formatted)
    else:
        print(result)

    print("=" * 60)
    print("✅ 旅行计划生成完毕")


async def main():
    llm = CONFIG.create_llm()
    planner = TripPlanner(llm)

    user_input = "长沙3日游，2026年5月21日-2026年5月23日，喜欢自然风光和历史文化，中等预算，住五一广场"

    # await demo_invoke(planner, user_input)
    await demo_stream(planner, user_input)


if __name__ == "__main__":
    asyncio.run(main())
