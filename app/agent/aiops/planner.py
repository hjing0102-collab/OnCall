"""Planner 节点——纯文本 prompt 驱动，不依赖 structured output"""

from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from app.config import config
from app.tools import retrieve_knowledge
from app.utils.http_client import get_http_client, get_async_http_client
from .state import PlanExecuteState

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


async def planner(state: PlanExecuteState) -> Dict[str, Any]:
    logger.info("=== Planner：制定执行计划 ===")
    input_text = state.get("input", "")

    try:
        experience_docs = ""
        try:
            context = await retrieve_knowledge.ainvoke({"query": input_text})
            if context and isinstance(context, str) and context.strip():
                experience_docs = context
        except Exception as e:
            logger.warning(f"查询知识库失败: {e}")

        experience_context = f"## 相关知识库文档\n{experience_docs}\n---" if experience_docs else ""

        llm = ChatOpenAI(
            model=config.dashscope_model, api_key=config.dashscope_api_key,
            temperature=0, base_url=DASHSCOPE_BASE_URL,
            http_client=get_http_client(),
            http_async_client=get_async_http_client(),
        )

        prompt = f"""作为专家级别的规划者，将以下任务分解为 3-5 个可执行的步骤。

可用工具：
- get_current_time：获取当前系统时间
- get_system_overview：获取系统整体概览（CPU、内存、磁盘、进程）
- get_cpu_usage：获取CPU使用详情和各进程占用
- get_memory_usage：获取内存使用详情和各进程占用
- get_disk_usage：获取磁盘使用详情
- retrieve_knowledge：从运维知识库中检索信息，参数 query

{experience_context}

原始任务：
{input_text}

请列出步骤，每行一个，格式为：
步骤1: [具体描述]
步骤2: [具体描述]
...
只输出步骤列表，不要其他内容。"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        response_text = response.content if hasattr(response, 'content') else str(response)

        import re
        plan_steps = []
        for line in response_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'(?:步骤\d+|Step\s*\d+|\d+)[\.:：、]\s*(.+)', line)
            if match:
                plan_steps.append(match.group(1))
            elif line and not line.startswith("#"):
                plan_steps.append(line)

        if not plan_steps:
            plan_steps = ["获取当前时间", "检索运维知识库", "基于检索结果生成诊断报告"]

        logger.info(f"计划已生成，共 {len(plan_steps)} 个步骤")
        for i, step in enumerate(plan_steps, 1):
            logger.info(f"  步骤{i}: {step}")

        return {"plan": plan_steps}

    except Exception as e:
        logger.error(f"生成计划失败: {e}")
        return {"plan": ["获取当前时间", "检索运维知识库", "基于检索结果生成诊断报告"]}
