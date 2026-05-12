"""Executor 节点——直接调用工具，不依赖 function calling"""

from typing import Dict, Any
import json
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from app.config import config
from app.tools import get_current_time, retrieve_knowledge
from app.tools.system_tools import get_cpu_usage, get_memory_usage, get_disk_usage, get_system_overview
from app.utils.http_client import get_http_client, get_async_http_client
from .state import PlanExecuteState

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


async def _run_tool(name: str, args: dict = None) -> str:
    """直接运行本地工具"""
    args = args or {}
    try:
        if name == "get_current_time":
            return str(get_current_time.invoke(args))
        elif name == "get_cpu_usage":
            return str(get_cpu_usage.invoke({}))
        elif name == "get_memory_usage":
            return str(get_memory_usage.invoke({}))
        elif name == "get_disk_usage":
            return str(get_disk_usage.invoke({}))
        elif name == "get_system_overview":
            return str(get_system_overview.invoke({}))
        elif name == "retrieve_knowledge":
            query = args.get("query", "")
            if not query:
                return "错误：请提供 query 参数"
            from app.services.vector_store_manager import vector_store_manager
            from app.config import config as cfg
            store = vector_store_manager.get_vector_store()
            if store is None:
                return "知识库未就绪，无法检索。"
            retriever = store.as_retriever(search_kwargs={"k": cfg.rag_top_k})
            docs = retriever.invoke(query)
            if not docs:
                return "没有找到相关信息。"
            parts = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("_file_name", "未知")
                parts.append(f"【{i}】来源: {source}\n{doc.page_content}")
            return "\n\n".join(parts)
        else:
            return f"未知工具: {name}"
    except Exception as e:
        return f"工具执行失败: {e}"


async def executor(state: PlanExecuteState) -> Dict[str, Any]:
    logger.info("=== Executor：执行步骤 ===")
    plan = state.get("plan", [])
    if not plan:
        return {}

    task = plan[0]
    logger.info(f"当前任务: {task}")

    try:
        llm = ChatOpenAI(
            model=config.dashscope_model, api_key=config.dashscope_api_key,
            temperature=0, base_url=DASHSCOPE_BASE_URL,
            http_client=get_http_client(),
            http_async_client=get_async_http_client(),
        )

        decide_prompt = f"""你有一个任务需要完成。可用的工具：
1. get_current_time - 获取当前系统时间
2. get_system_overview - 获取系统整体概览（CPU、内存、磁盘、进程数）
3. get_cpu_usage - 获取CPU使用详情和各核心占用率
4. get_memory_usage - 获取内存使用详情和各进程占用
5. get_disk_usage - 获取磁盘使用详情
6. retrieve_knowledge - 从运维知识库中检索信息。需要传入参数 query（搜索关键词）

当前任务：{task}

请用一个简短的 JSON 回复，格式为：
{{"tool": "工具名", "args": {{"参数名": "参数值"}}}} 或 {{"tool": "none"}}（如果不需要工具）
只输出 JSON，不要输出其他内容。"""

        response = await llm.ainvoke([HumanMessage(content=decide_prompt)])
        response_text = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"LLM 决策: {response_text[:200]}")

        tool_result = ""
        try:
            clean = response_text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                lines = [l for l in lines if l != "```"]
                clean = "\n".join(lines[1:]) if len(lines) > 1 else lines[0]
                if clean.endswith("```"):
                    clean = clean[:-3]
            decision = json.loads(clean)
            tool_name = decision.get("tool", "none")
            if tool_name != "none":
                tool_result = await _run_tool(tool_name, decision.get("args", {}))
        except Exception as e:
            logger.warning(f"工具决策解析失败: {e}")
            tool_result = f"工具调用失败: {e}"

        summary_prompt = f"""任务：{task}

工具执行结果：
{tool_result if tool_result else "未使用工具"}

请基于工具结果给出简洁的执行总结（150字以内）。"""
        final = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        result = final.content if hasattr(final, 'content') else str(final)

        logger.info(f"步骤执行完成，结果长度: {len(result.strip())}")
        return {
            "plan": plan[1:],
            "past_steps": [(task, result.strip() or "步骤已完成")],
        }

    except Exception as e:
        logger.error(f"执行步骤失败: {e}")
        return {
            "plan": plan[1:],
            "past_steps": [(task, f"执行遇到问题: {str(e)}，请继续下一步")],
        }
