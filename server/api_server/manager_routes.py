from fastapi import APIRouter
import logging
from server.tools.tool_register import get_tools_registry, get_tool
from server.session_mgr import session_mgr

logger = logging.getLogger(__name__)


manager_router = APIRouter(prefix="/manager", tags=["Manager"])


@manager_router.get("/sessions/list")
async def list_sessions():
    """列举当前所有已连接的客户端 Session。"""
    sessions = session_mgr.get_all_sessions()
    return {
        "online_count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "conversation_id": s.conversation_id,
            }
            for s in sessions.values()
        ],
    }


@manager_router.get("/tools/list")
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


@manager_router.post("/tools/invoke/{tool_name}")
async def invoke_tool(tool_name: str, params: dict):
    """通过 HTTP 直接调用指定工具。"""
    t = get_tool(tool_name)
    result = await t.ainvoke(params)
    return {"tool": tool_name, "result": result}


@manager_router.post("/reload-config")
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
