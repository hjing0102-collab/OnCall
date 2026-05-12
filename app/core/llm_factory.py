"""LLM 工厂类 - OpenAI 兼容模式调用阿里云 DashScope"""

from langchain_openai import ChatOpenAI
from app.config import config
from app.utils.http_client import get_http_client, get_async_http_client

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LLMFactory:
    """LLM 工厂类"""

    @staticmethod
    def create_chat_model(
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            model=model or config.dashscope_model,
            temperature=temperature,
            streaming=streaming,
            base_url=DASHSCOPE_BASE_URL,
            api_key=config.dashscope_api_key,
            http_client=get_http_client(),
            http_async_client=get_async_http_client(),
        )


llm_factory = LLMFactory()
