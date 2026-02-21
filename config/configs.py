from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


# ---- 数据类 ----

#服务器配置
@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


#模型配置
@dataclass
class ModelConfig:
    provider: str = "openai"
    model_name: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"


#Agent配置，可以选配模型
@dataclass
class AgentConfig:
    system_prompt: str = "你是一个智能助手"
    max_iterations: int = 15
    model: str = ""
    tools: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    active_agents: list[str] = field(default_factory=list)

    def get_model(self, name: str) -> ModelConfig:
        """根据名称获取模型配置，找不到则抛出 KeyError。"""
        if name not in self.models:
            available = ", ".join(self.models.keys()) or "(空)"
            msg = f"模型 '{name}' 未定义，可用模型: {available}"
            raise KeyError(msg)
        return self.models[name]

    @staticmethod
    def from_raw(raw: dict) -> AppConfig:
        """从原始字典构建 AppConfig 实例。"""
        models = {
            name: ModelConfig(**cfg)
            for name, cfg in raw.get("models", {}).items()
        }
        agents = {
            name: AgentConfig(**cfg)
            for name, cfg in raw.get("agents", {}).items()
        }
        return AppConfig(
            server=ServerConfig(**raw.get("server", {})),
            models=models,
            agents=agents,
            active_agents=raw.get("active_agents", []),
        )


# ---- 深度合并工具 ----

def _deep_merge(base: dict, override: dict) -> dict:
    """递归深度合并两个字典，override 中的值覆盖 base 中的同名键。

    对于嵌套字典会递归合并，非字典类型直接替换。

    Args:
        base: 基础字典。
        override: 覆盖字典。

    Returns:
        合并后的新字典（不修改原始输入）。
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # result[key] 已经是 deepcopy 的产物，直接原地合并即可
            result[key] = _deep_merge_inplace(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _deep_merge_inplace(base: dict, override: dict) -> dict:
    """原地递归合并，用于已经是副本的字典，避免多余拷贝。"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_inplace(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _load_yaml(path: Path) -> dict:
    """加载单个 YAML 文件，文件不存在则返回空字典。"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---- 层级加载核心逻辑 ----

def _resolve_layered_raw(
    config_dir: Path,
    env: str | None = None,
    namespace: str | None = None,
) -> dict:
    """按层级顺序加载并合并原始配置字典。

    加载顺序（后者覆盖前者）：
      1. config_dir/config.yaml          — 基础配置
      2. config_dir/{env}/config.yaml     — 环境级配置（可选）
      3. config_dir/{env}/{namespace}/config.yaml — 命名空间级配置（可选）

    Args:
        config_dir: 配置根目录。
        env: 环境名称，如 ``develop``、``release``。
        namespace: 命名空间，如 ``bluepigwx``。

    Returns:
        层级合并后的原始字典。
    """
    # 第 1 层：基础配置
    base_path = config_dir / "config.yaml"
    raw = _load_yaml(base_path)
    logger.info("加载基础配置: %s (存在: %s)", base_path, base_path.exists())

    # 第 2 层：环境级配置
    if env:
        env_path = config_dir / env / "config.yaml"
        env_raw = _load_yaml(env_path)
        if env_raw:
            logger.info("加载环境配置: %s", env_path)
            raw = _deep_merge(raw, env_raw)
        else:
            logger.info("环境配置不存在，跳过: %s", env_path)

        # 第 3 层：命名空间级配置（仅在指定 env 时才有意义）
        if namespace:
            ns_path = config_dir / env / namespace / "config.yaml"
            ns_raw = _load_yaml(ns_path)
            if ns_raw:
                logger.info("加载命名空间配置: %s", ns_path)
                raw = _deep_merge(raw, ns_raw)
            else:
                logger.info("命名空间配置不存在，跳过: %s", ns_path)

    return raw


# ---- 全局单例 ----

_global_config: AppConfig | None = None
_current_env: str | None = None
_current_namespace: str | None = None


def load_config(
    config_dir: str | Path | None = None,
    *,
    env: str | None = None,
    namespace: str | None = None,
) -> AppConfig:
    """加载/重载全局配置，支持层级覆盖。

    加载顺序：基础 config.yaml → 环境级 → 命名空间级，
    后加载的同名配置项会覆盖先加载的。

    Args:
        config_dir: 配置根目录，默认为本模块所在的 config 目录。
        env: 环境名称（如 ``develop``、``release``），为 None 则跳过。
        namespace: 命名空间（如 ``bluepigwx``），为 None 则跳过。

    Returns:
        合并后的全局 AppConfig 实例。
    """
    global _global_config, _current_env, _current_namespace

    if config_dir is None:
        config_dir = Path(__file__).parent
    config_dir = Path(config_dir)

    raw = _resolve_layered_raw(config_dir, env=env, namespace=namespace)
    _global_config = AppConfig.from_raw(raw)
    _current_env = env
    _current_namespace = namespace

    logger.info(
        "配置加载完成 [env=%s, namespace=%s] models=%s, agents=%s, active_agents=%s",
        env, namespace,
        list(_global_config.models.keys()),
        list(_global_config.agents.keys()),
        _global_config.active_agents,
    )
    return _global_config


def get_config() -> AppConfig:
    """获取全局配置，未初始化则抛出异常。"""
    if _global_config is None:
        msg = "配置尚未初始化，请先调用 load_config()"
        raise RuntimeError(msg)
    return _global_config


def get_config_context() -> tuple[str | None, str | None]:
    """获取当前配置的环境和命名空间。

    Returns:
        (env, namespace) 元组。
    """
    return _current_env, _current_namespace
