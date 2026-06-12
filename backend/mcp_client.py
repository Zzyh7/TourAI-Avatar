"""
MCP 客户端管理器 —— 单例模式，全局共享高德地图 MCP 连接。
"""
from langchain_core.tools import BaseTool
from config import CONFIG

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    MultiServerMCPClient = None

class McpClientManager:
    """
    高德地图 MCP 客户端单例。

    职责：
      1. 管理与高德 MCP 服务器的 SSE 连接
      2. 按领域（poi/weather/route/around/geo）分发工具子集
      3. 缓存已加载工具，避免重复请求

    用法：
      manager = McpClientManager()
      poi_tools = await manager.get_tools_for("poi")
      around_tools = await manager.get_tools_for("around")
    """

    _instance: "McpClientManager | None" = None

    def __new__(cls) -> "McpClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client: MultiServerMCPClient | None = None
        self._tools_cache: dict[str, list[BaseTool]] = {}
        self._initialized = True

    async def _get_client(self) -> MultiServerMCPClient | None:
        """懒加载 MCP 客户端"""
        if MultiServerMCPClient is None:
            return None
        if self._client is None:
            self._client = MultiServerMCPClient({
                "amap": {
                    "transport": CONFIG.mcp_transport,
                    "url": CONFIG.mcp_url,
                }
            })
        return self._client

    async def get_all_tools(self) -> list[BaseTool]:
        """获取 MCP 服务器暴露的全部工具"""
        if "all" not in self._tools_cache:
            client = await self._get_client()
            if client is None:
                self._tools_cache["all"] = []
            else:
                self._tools_cache["all"] = await client.get_tools()
        return self._tools_cache["all"]

    async def get_tools_for(self, domain: str) -> list[BaseTool]:
        """按领域获取工具子集"""
        all_tools = await self.get_all_tools()
        target_names = set(CONFIG.tool_domains.get(domain, []))
        return [t for t in all_tools if t.name in target_names]

    async def close(self):
        """关闭 MCP 连接"""
        self._client = None
        self._tools_cache.clear()

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
