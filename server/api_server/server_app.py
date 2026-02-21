from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from server.api_server.tools_routes import tool_router
from server.api_server.chat_routes import chat_router
from config.configs import get_config


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

    new_app.include_router(tool_router)
    new_app.include_router(chat_router)

    @new_app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return new_app


