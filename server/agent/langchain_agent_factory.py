"""LangchainAgentFactory：基于 LangChain 的 Agent 工厂实现。"""

import logging

from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from config.configs import get_config, ModelConfig, AgentConfig
from server.tools.tool_register import get_tools_by_names
from server.agent.agent_factory import AgentFactory
from server.agent.agent_inst import AgentInst
from server.agent.langchain_agent_inst import LangchainAgentInst, LangchainAgentState

logger = logging.getLogger(__name__)

# 对话总结触发阈值：消息数达到 50 条时触发总结
_SUMMARIZATION_TRIGGER = ("messages", 50)
# 总结后保留最近 10 条消息
_SUMMARIZATION_KEEP = ("messages", 10)


class LangchainAgentFactory(AgentFactory):
    """使用 LangChain / LangGraph 创建 Agent 的具体工厂。"""

    def build_agent(self, name: str, agent_cfg: AgentConfig) -> AgentInst:
        """根据配置创建 LangChain Agent 实例。

        Args:
            name: Agent 名称。
            agent_cfg: Agent 配置。

        Returns:
            包装后的 LangchainAgentInst 实例。
        """
        config = get_config()
        model_cfg = config.get_model(agent_cfg.model)
        llm = self._create_llm(model_cfg)

        tools = get_tools_by_names(agent_cfg.tools) if agent_cfg.tools else []

        summarization = SummarizationMiddleware(
            model=llm,
            trigger=_SUMMARIZATION_TRIGGER,
            keep=_SUMMARIZATION_KEEP,
        )

        # 限制单次调用（run）的工具调用总次数，防止 LLM 陷入循环
        tool_call_limit = ToolCallLimitMiddleware(
            run_limit=agent_cfg.max_iterations,
            exit_behavior="end",
        )

        runnable = create_agent(
            model=llm,
            tools=tools,
            system_prompt=agent_cfg.system_prompt,
            name=name,
            checkpointer=InMemorySaver(),
            middleware=[summarization, tool_call_limit],
            state_schema=LangchainAgentState,
        )

        inst = LangchainAgentInst(name=name, agent_cfg=agent_cfg, runnable=runnable)

        logger.info(
            "Agent '%s' 创建成功 (模型=%s, 工具=%s)",
            name, agent_cfg.model, agent_cfg.tools,
        )
        return inst

    @staticmethod
    def _create_llm(model_cfg: ModelConfig) -> BaseChatModel:
        """根据 ModelConfig 创建 LLM 实例。

        Args:
            model_cfg: 模型配置。

        Returns:
            LangChain BaseChatModel 实例。
        """
        if model_cfg.provider == "openai":
            return ChatOpenAI(
                model=model_cfg.model_name,
                base_url=model_cfg.base_url,
                api_key=SecretStr(model_cfg.api_key),
                temperature=0,
            )
        if model_cfg.provider == "ollama":
            return ChatOllama(
                model=model_cfg.model_name,
                base_url=model_cfg.base_url,
                temperature=0,
            )
        msg = f"不支持的 provider: '{model_cfg.provider}'"
        raise ValueError(msg)
