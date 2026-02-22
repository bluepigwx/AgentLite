from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI
import logging


logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s][%(filename)s:%(funcName)s:%(lineno)d][%(levelname)s][%(message)s]",
                    handlers=[
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)


'''

messages = [
    SystemMessage("你是一个天气查询助理"),
    HumanMessage("帮我查询娜美克星的天气，关注你的工具列表，有可以查询外星球天气的工具")
]


def get_weather(city:str)->str:
    """
    获得指定城市的天气情况
    """
    return f"{city}天气多云转阴AAbc"


def get_alien_weather(city:str)->str:
    """
    获得指定外星球的天气情况
    """
    return f"{city} 有剧毒风暴肆虐，同时基纽特种部队也在上面巡逻，不建议前往"


history = InMemoryChatMessageHistory()

history.add_user_message("帮我查询娜美克星的天气，关注你的工具列表，有可以查询外星球天气的工具")


def main():

    #llm = ChatOllama(model="qwen2.5:7b")
        


# 连接兼容 OpenAI API 的服务（如 Ollama、vLLM、LocalAI 等）
    llm = ChatOpenAI(
        model="qwen2.5:7b",
        base_url="http://localhost:11434/v1",  # Ollama 的 OpenAI 兼容端点
        api_key="ollama"  # Ollama 不需要真实 key，随便填
    )
        
    agent = create_agent(model=llm,
                             tools=[get_weather, get_alien_weather],
                             system_prompt="你是一个天气查询助理")
        

    result = agent.invoke(
            {"messages": messages}
    )

    print("环境验证成功!")
    print(f"模型响应: {result}")
'''


import argparse

import uvicorn
from config.configs import load_config, get_config
from server.api_server.server_app import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentLite 服务")
    parser.add_argument("--env", type=str, default=None,
                        help="环境名称，如 develop、release")
    parser.add_argument("--namespace", type=str, default=None,
                        help="命名空间，如 bluepigwx")
    args = parser.parse_args()

    # 1. 按层级加载全局配置
    #load_config(env=args.env, namespace=args.namespace)
    load_config(env="develop", namespace="bluepigwx")

    # 2. 创建 FastAPI 应用（内部通过 get_config() 获取配置）
    app = create_app()

    # 3. 启动服务
    config = get_config()
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
    )
