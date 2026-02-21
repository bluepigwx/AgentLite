from fastapi import APIRouter
import logging
from server.tools.tool_register import get_tools_registry, get_tool

logger = logging.getLogger(__name__)


tool_router = APIRouter(prefix="/tools", tags=["Toolkits"])


@tool_router.get("/list")
async def list_tools():
    """获取所有已注册的工具列表。"""
    registry = get_tools_registry()
    return {
        "tools": [
            {
                "name": t.name,
                "title": t.metadata.get("title", t.name),
                "description": t.description,
            }
            for t in registry.values()
        ]
    }


@tool_router.post("/invoke/{tool_name}")
async def invoke_tool(tool_name: str, params: dict):
    """通过 HTTP 直接调用指定工具。"""
    t = get_tool(tool_name)
    result = await t.ainvoke(params)
    return {"tool": tool_name, "result": result}


@tool_router.post("/reload-config")
async def reload_config():
    """重新加载配置文件（保持当前 env/namespace 上下文）。"""
    from config.configs import load_config, get_config_context
    env, namespace = get_config_context()
    config = load_config(env=env, namespace=namespace)
    return {
        "message": "配置重载成功",
        "env": env,
        "namespace": namespace,
        "models": list(config.models.keys()),
        "agents": list(config.agents.keys()),
        "active_agents": config.active_agents,
    }
