from contextlib import asynccontextmanager
import json
import logging

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from server.api_server.manager_routes import manager_router
from server.api_server.chat_routes import chat_router
from config.configs import get_config
from server.session_mgr import session_mgr
from server.session_mgr.cmd_dispatch import dispatch


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 延迟导入工具包，触发所有工具模块的 @register_tool 注册
    #    不可提前到模块顶层，否则工具注册会在配置加载之前执行
    import server.tools  # noqa: F401

    # 2. 通过 Agent 管理器初始化所有 Agent
    from server.agent.agents_mgr import init_agents, get_all_agents
    init_agents()

    config = get_config()
    from server.tools.tool_register import get_tools_registry
    registry = get_tools_registry()
    agents = get_all_agents()
    logger.info(
        f"[AgentLite] 服务启动，已加载 {len(config.models)} 个模型, "
        f"{len(agents)} 个Agent, {len(registry)} 个工具"
    )
    yield
    logger.info("[AgentLite] 服务关闭")


def create_app() -> FastAPI:
    new_app = FastAPI(
        title="AgentLite",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 全局异常处理，将业务异常转为规范 JSON 响应
    @new_app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @new_app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    @new_app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    new_app.include_router(manager_router)
    new_app.include_router(chat_router)

    @new_app.get("/health")
    async def health_check():
        return {"status": "ok"}



    @new_app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket 连接端点：建立 Session，维持连接直到客户端断开。"""
        session = await session_mgr.accept(websocket)
        try:
            # 连接成功通知
            await session.send_text(json.dumps({
                "cmd": "connected",
                "status": "ok",
                "params": {"session_id": session.session_id},
            }))

            # 消息循环：收到消息后交给分发器处理
            while True:
                raw = await session.receive_text()
                logger.debug(
                    "收到消息 [session=%s]: %s",
                    session.session_id, raw[:200],
                )
                await dispatch(session, raw)

        except WebSocketDisconnect:
            logger.info(
                "客户端断开 [session=%s]", session.session_id,
            )
        finally:
            session_mgr.disconnect(session)

    return new_app


