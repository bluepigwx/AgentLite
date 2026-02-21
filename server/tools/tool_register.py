"""全局工具注册器。

使用 @register_tool 装饰器将普通函数同时包装为：
1. LangChain BaseTool —— 供 Agent 推理时调用
2. 全局注册表条目   —— 供 FastAPI 路由查询/直接调用
"""

import re
from typing import Any, Callable, Union

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel


# ---- 全局工具注册表 ----
_TOOLS_REGISTRY: dict[str, BaseTool] = {}


def get_tools_registry() -> dict[str, BaseTool]:
    """获取全局工具注册表（只读访问）。"""
    return _TOOLS_REGISTRY


def get_tool(name: str) -> BaseTool:
    """按名称获取工具，找不到则抛出 KeyError。"""
    if name not in _TOOLS_REGISTRY:
        available = ", ".join(_TOOLS_REGISTRY.keys()) or "(空)"
        msg = f"工具 '{name}' 未注册，可用工具: {available}"
        raise KeyError(msg)
    return _TOOLS_REGISTRY[name]


def get_tools_by_names(names: list[str]) -> list[BaseTool]:
    """按名称列表批量获取工具，供 Agent 绑定 tools 时使用。"""
    return [get_tool(name) for name in names]


def register_tool(
    *args: Any,
    title: str = "",
    description: str = "",
    return_direct: bool = False,
    args_schema: type[BaseModel] | None = None,
    infer_schema: bool = True,
) -> Union[Callable, BaseTool]:
    """将函数包装为 LangChain 工具并注册到全局注册表。

    支持两种用法：
        @register_tool
        def my_func(...): ...

        @register_tool(title="我的工具", description="自定义描述")
        def my_func(...): ...
    """

    def _parse_tool(t: BaseTool) -> None:
        nonlocal description, title

        _TOOLS_REGISTRY[t.name] = t

        # 从函数 docstring 提取描述（如果未显式指定）
        if not description:
            if t.func is not None:
                description = t.func.__doc__ or ""
            elif t.coroutine is not None:
                description = t.coroutine.__doc__ or ""
        if description:
            t.description = " ".join(re.split(r"\n+\s*", description.strip()))

        # 自动生成 title（如果未显式指定）
        if not title:
            title_val = "".join([x.capitalize() for x in t.name.split("_")])
        else:
            title_val = title
        t.metadata = {**(t.metadata or {}), "title": title_val}

        # 保留原始函数引用，方便 FastAPI 路由直接调用
        t.metadata["raw_func"] = t.func or t.coroutine

    def wrapper(def_func: Callable) -> BaseTool:
        partial_ = tool(
            return_direct=return_direct,
            args_schema=args_schema,
            infer_schema=infer_schema,
        )
        t = partial_(def_func)
        _parse_tool(t)
        return t

    # 无参调用: @register_tool
    if len(args) == 1 and callable(args[0]):
        return wrapper(args[0])

    # 有参调用: @register_tool(title="xxx")
    if len(args) == 0:
        return wrapper

    # 兜底：直接传入已有的 BaseTool 对象
    if len(args) == 1 and isinstance(args[0], BaseTool):
        _parse_tool(args[0])
        return args[0]

    msg = f"register_tool 不支持的调用方式: args={args}"
    raise TypeError(msg)
