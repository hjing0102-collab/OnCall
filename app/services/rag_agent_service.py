"""RAG Agent 服务 - 基于 LangGraph + ChatOpenAI"""

from typing import Annotated, Any, AsyncGenerator, Dict, Sequence
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from loguru import logger
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from app.config import config
from app.tools import get_current_time, retrieve_knowledge
from app.utils.http_client import get_http_client, get_async_http_client

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class RagAgentService:
    """RAG Agent 服务"""

    def __init__(self, streaming: bool = True):
        self.model_name = config.dashscope_model
        self.streaming = streaming
        self.system_prompt = self._build_system_prompt()
        self.model = ChatOpenAI(
            model=self.model_name, api_key=config.dashscope_api_key,
            temperature=0.7, streaming=streaming, base_url=DASHSCOPE_BASE_URL,
            http_client=get_http_client(),
            http_async_client=get_async_http_client(),
        )
        self.tools = [retrieve_knowledge, get_current_time]
        self.checkpointer = MemorySaver()
        self.agent = None
        self._agent_initialized = False
        logger.info(f"RAG Agent 服务初始化完成, model={self.model_name}")

    async def _initialize_agent(self):
        if self._agent_initialized:
            return
        self.agent = create_agent(self.model, tools=self.tools, checkpointer=self.checkpointer)
        self._agent_initialized = True

    def _build_system_prompt(self) -> str:
        from textwrap import dedent
        return dedent("""
            你是一个专业的AI助手，能够使用多种工具来帮助用户解决问题。
            工作原则:
            1. 理解用户需求，选择合适的工具来完成任务
            2. 当需要获取实时信息或专业知识时，主动使用相关工具
            3. 基于工具返回的结果提供准确、专业的回答
            4. 如果工具无法提供足够信息，请诚实地告知用户
            回答要求:
            - 保持友好、专业的语气
            - 回答简洁明了，重点突出
            - 基于事实，不编造信息
        """).strip()

    async def query(self, question: str, session_id: str) -> str:
        try:
            await self._initialize_agent()
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=question)]
            result = await self.agent.ainvoke(
                input={"messages": messages},
                config={"configurable": {"thread_id": session_id}},
            )
            messages_result = result.get("messages", [])
            if messages_result:
                last_message = messages_result[-1]
                return last_message.content if hasattr(last_message, 'content') else str(last_message)
            return ""
        except Exception as e:
            logger.error(f"RAG Agent 查询失败: {e}")
            raise

    async def query_stream(self, question: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            await self._initialize_agent()
            config_dict = {"configurable": {"thread_id": session_id}}

            # Step 1: Run the full agent invocation (non-streaming) to handle tool calls + history
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=question)]
            result = await self.agent.ainvoke(
                input={"messages": messages}, config=config_dict,
            )
            all_messages = result.get("messages", [])
            if not all_messages:
                yield {"type": "complete"}
                return

            # Gather context from tool results
            tool_context = []
            for msg in all_messages:
                if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'content'):
                    tool_context.append(str(msg.content))

            # Build messages for streaming: system + history + user question + context
            stream_messages = [SystemMessage(content=self.system_prompt)]
            history = self._get_history(session_id)
            for h in history:
                role = h["role"]
                content = h["content"]
                if role == "user":
                    stream_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    stream_messages.append(AIMessage(content=content))

            # Add current question with context
            current_prompt = question
            if tool_context:
                current_prompt = f"用户问题: {question}\n\n参考知识:\n{chr(10).join(tool_context)}\n\n请基于参考知识回答用户问题。"

            stream_messages.append(HumanMessage(content=current_prompt))

            # Step 2: Stream the final answer token by token
            full = ""
            async for chunk in self.model.astream(stream_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    full += chunk.content
                    yield {"type": "content", "data": chunk.content}

            # Save to checkpointer for memory
            try:
                self.checkpointer.put(
                    config_dict,
                    {"channel_values": {"messages": all_messages}},
                    {},
                    config_dict,
                )
            except Exception:
                pass

            yield {"type": "complete"}
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            yield {"type": "error", "data": str(e)}

    def _get_history(self, session_id: str, limit: int = 10) -> list:
        history = self.get_session_history(session_id)
        return history[-limit:] if len(history) > limit else history

    def get_session_history(self, session_id: str) -> list:
        try:
            config = {"configurable": {"thread_id": session_id}}
            checkpoint_tuple = self.checkpointer.get(config)
            if not checkpoint_tuple:
                return []
            checkpoint_data = getattr(checkpoint_tuple, 'checkpoint',
                                       checkpoint_tuple[0] if checkpoint_tuple else {})
            messages = checkpoint_data.get("channel_values", {}).get("messages", [])
            history = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    continue
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                from datetime import datetime
                history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
            return history
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []

    def clear_session(self, session_id: str) -> bool:
        try:
            self.checkpointer.delete_thread(session_id)
            logger.info(f"已清除会话: {session_id}")
            return True
        except Exception as e:
            logger.error(f"清空会话失败: {e}")
            return False


rag_agent_service = RagAgentService(streaming=True)
