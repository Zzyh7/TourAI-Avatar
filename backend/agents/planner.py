"""
景区导览总控 Agent (GuideAgent) —— 持有子 Agent 作为工具，统一编排。
改造自原 TripPlanner，新增 RAG 知识检索工具和会话管理。
"""
import re
import time
from typing import AsyncIterator
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel

from mcp_client import McpClientManager
from agents.specialist import SpecialistAgent
from prompts import (
    ATTRACTION_AGENT_PROMPT,
    WEATHER_AGENT_PROMPT,
    ROUTE_AGENT_PROMPT,
    GUIDE_AGENT_PROMPT,
    RAG_PROMPT_TEMPLATE,
)

# 工具名 → 用户友好的中文标签
TOOL_LABELS = {
    "query_weather":          ("🌤️", "查询天气"),
    "search_attraction":      ("🏛️", "搜索景点"),
    "search_route":           ("🗺️", "规划路线"),
    "search_knowledge":       ("📚", "检索知识库"),
}

# 匹配子 Agent 内部泄漏的 [TOOL_CALL:...] 模式
_TOOL_CALL_PATTERN = re.compile(r"\[TOOL_CALL:[^\]]*\]")

# 匹配 LLM 输出中不该出现的符号（即使 prompt 禁止了，LLM 偶尔还是会生成）
_OUTPUT_CLEANUP = re.compile(r"\*\*|~~|```|`|^---+$|^\*{3,}$", re.MULTILINE)


class GuideAgent:
    """
    景区导览总控智能体。

    架构:
      GuideAgent (总控)
        ├── search_attraction → AttractionAgent → MCP POI/Around 工具
        ├── query_weather     → WeatherAgent    → MCP Weather 工具
        ├── search_route      → RouteAgent      → MCP Route 工具
        └── search_knowledge  → RAG 检索函数    → FAISS 向量库

    用法:
        guide = GuideAgent(llm, rag_retriever)
        await guide.build()

        # 非流式
        answer = await guide.invoke("西湖有什么历史故事？", session_id="xxx")

        # 流式
        async for token, audio in guide.stream("西湖有什么历史故事？", session_id="xxx"):
            yield token, audio
    """

    def __init__(self, llm: BaseChatModel, rag_retriever=None):
        self.llm = llm
        self.rag_retriever = rag_retriever  # RAG 检索器实例
        self.mcp = McpClientManager()

        # 子 Agent（build 时初始化）
        self._attraction_agent: SpecialistAgent | None = None
        self._weather_agent: SpecialistAgent | None = None
        self._route_agent: SpecialistAgent | None = None

        # 顶层 Agent
        self._agent = None

    # ==================== 构建 ====================

    async def build(self):
        """初始化所有子 Agent + 组装 GuideAgent"""
        if self._agent is not None:
            return

        # 1. 按领域加载 MCP 工具
        poi_tools = await self.mcp.get_tools_for("poi")
        weather_tools = await self.mcp.get_tools_for("weather")
        route_tools = await self.mcp.get_tools_for("route")
        around_tools = await self.mcp.get_tools_for("around")

        # 2. 创建子 Agent
        self._weather_agent = SpecialistAgent(
            self.llm, "WeatherAgent", WEATHER_AGENT_PROMPT, weather_tools
        )
        self._attraction_agent = SpecialistAgent(
            self.llm, "AttractionAgent", ATTRACTION_AGENT_PROMPT, poi_tools + around_tools
        )
        self._route_agent = SpecialistAgent(
            self.llm, "RouteAgent", ROUTE_AGENT_PROMPT, route_tools
        )
        await self._weather_agent.build()
        await self._attraction_agent.build()
        await self._route_agent.build()

        # 3. 将子 Agent 包装为 Tool
        @tool
        async def query_weather(query: str) -> str:
            """查询景区天气。输入城市名，返回天气信息。"""
            return await self._weather_agent.invoke(query)

        @tool
        async def search_attraction(query: str) -> str:
            """搜索景点和周边POI。输入景点名称或关键词，返回景点列表。"""
            return await self._attraction_agent.invoke(query)

        @tool
        async def search_route(query: str) -> str:
            """规划景点间路线。输入起终点，返回路线方案。"""
            return await self._route_agent.invoke(query)

        # 4. RAG 知识检索工具
        @tool
        async def search_knowledge(query: str) -> str:
            """检索景区知识库。输入问题，返回相关知识片段。
            用于回答历史、文化、景点特色等需要专业知识的问题。"""
            if self.rag_retriever is None:
                return "知识库尚未初始化"
            try:
                result = self.rag_retriever.retrieve(query)
                # 兼容新接口 (dict) 和旧接口 (list)
                if isinstance(result, dict):
                    docs = result.get("docs", [])
                    if result.get("below_threshold"):
                        return "未找到足够相关的知识内容"
                else:
                    docs = result
                if not docs:
                    return "未找到相关知识内容"
                return "\n\n".join(doc.page_content for doc in docs)
            except Exception as e:
                return f"检索出错: {str(e)}"

        # 5. 组装 GuideAgent
        all_tools = [query_weather, search_attraction, search_route, search_knowledge]

        self._agent = create_agent(
            model=self.llm,
            tools=all_tools,
            system_prompt=GUIDE_AGENT_PROMPT,
        )

    # ==================== 非流式调用 ====================

    async def invoke(self, user_input: str, session_id: str = "") -> str:
        """输入游客问题，返回回答文本"""
        await self.build()
        result = await self._agent.ainvoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        return result["messages"][-1].content

    # ==================== 流式调用 ====================

    async def stream(self, user_input: str, session_id: str = "") -> AsyncIterator[dict]:
        """
        流式输出导览回答，逐 token yield 事件。

        事件格式:
          {"type": "token", "data": "文字片段"}
          {"type": "tool_start", "data": {"name": "search_knowledge", "label": "📚 检索知识库"}}
          {"type": "tool_end", "data": {"name": "search_knowledge"}}
          {"type": "done", "data": ""}
        """
        await self.build()

        async for event in self._agent.astream_events(
            {"messages": [{"role": "user", "content": user_input}]},
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # 过滤子 Agent 内部 TOOL_CALL 格式泄漏
                    content = _TOOL_CALL_PATTERN.sub("", content)
                    # 过滤 LLM 偶尔生成的 markdown 符号（** ## ~~ -- 等）
                    content = _OUTPUT_CLEANUP.sub("", content)
                    if content.strip():
                        yield {"type": "token", "data": content}

            elif kind == "on_tool_start":
                name = event.get("name", "unknown")
                emoji_label = TOOL_LABELS.get(name, ("🔧", name))
                label = f"{emoji_label[0]} {emoji_label[1]}"
                yield {"type": "tool_start", "data": {"name": name, "label": label}}

            elif kind == "on_tool_end":
                name = event.get("name", "unknown")
                yield {"type": "tool_end", "data": {"name": name}}

        yield {"type": "done", "data": ""}
