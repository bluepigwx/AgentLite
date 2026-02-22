from contextlib import asynccontextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from server.api_server.manager_routes import manager_router
from server.api_server.chat_routes import chat_router
from server.api_server.mc_routes import mc_router
from config.configs import get_config
from server.session_mgr import session_mgr
from server.session_mgr.cmd_dispatch import dispatch


logger = logging.getLogger(__name__)

# Agent 对话在线程池中执行，默认线程数适配高并发场景
_THREAD_POOL_SIZE = 256


def _task_exception_callback(task: asyncio.Task[None]) -> None:
    """后台 task 异常回调：记录日志，避免异常被静默吞掉。"""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "后台 dispatch task 异常: %s", exc, exc_info=exc,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. 将主线程事件循环传给工具模块，供线程池中的同步工具跨线程调用异步方法
    from server.tools.mc_builder import set_main_loop
    set_main_loop(asyncio.get_running_loop())

    # 0.5 配置全局线程池，供 run_in_executor 使用
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=_THREAD_POOL_SIZE)
    loop.set_default_executor(executor)

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
        f"{len(agents)} 个Agent, {len(registry)} 个工具, "
        f"线程池={_THREAD_POOL_SIZE}"
    )
    try:
        yield
    finally:
        executor.shutdown(wait=False)
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
    new_app.include_router(mc_router)

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
            # 注意：dispatch 必须在独立 task 中运行，不能 await，
            # 否则长耗时处理（如 Agent chat）会阻塞消息循环，
            # 导致客户端回复（如工具请求的 response）无法被及时读取。
            _background_tasks: set[asyncio.Task[None]] = set()
            while True:
                raw = await session.receive_text()
                logger.debug(
                    "收到消息 [session=%s]: %s",
                    session.session_id, raw[:200],
                )
                task = asyncio.create_task(dispatch(session, raw))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
                task.add_done_callback(_task_exception_callback)

        except WebSocketDisconnect:
            logger.info(
                "客户端断开 [session=%s]", session.session_id,
            )
        finally:
            session.cleanup()
            session_mgr.disconnect(session)

    return new_app


