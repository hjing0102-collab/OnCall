"""Replanner 节点——简化逻辑，2步后直接生成报告"""

from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from app.config import config
from app.utils.http_client import get_http_client, get_async_http_client
from .state import PlanExecuteState

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


async def replanner(state: PlanExecuteState) -> Dict[str, Any]:
    logger.info("=== Replanner：重新规划 ===")
    plan = state.get("plan", [])
    past_steps = state.get("past_steps", [])

    llm = ChatOpenAI(model=config.dashscope_model, api_key=config.dashscope_api_key,
                     temperature=0, base_url=DASHSCOPE_BASE_URL,
                     http_client=get_http_client(),
                     http_async_client=get_async_http_client())

    if len(past_steps) >= 2 or not plan:
        return await _generate_response(state, llm)

    logger.info("继续执行下一步")
    return {}


async def _generate_response(state: PlanExecuteState, llm: ChatOpenAI) -> Dict[str, Any]:
    logger.info("生成最终诊断报告...")
    input_text = state.get("input", "")
    past_steps = state.get("past_steps", [])

    if not past_steps:
        return {"response": "# 运维诊断\n\n诊断流程已执行，未获取到执行步骤信息。"}

    execution_history = "\n\n".join([
        f"### 步骤: {step}\n**结果:**\n{result}"
        for step, result in past_steps
    ])

    prompt = f"""请根据以下信息生成一份运维诊断报告（Markdown 格式）：

原始任务：{input_text}

执行历史：
{execution_history}

报告要求：
# 运维诊断报告
## 当前状态
[基于执行结果总结]
## 发现
[列出关键发现]
## 建议
[给出处理建议]

请直接输出报告，不要输出其他内容。"""

    try:
        final_response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = final_response.content if hasattr(final_response, 'content') else str(final_response)
        logger.info(f"诊断报告生成完成，长度: {len(result)}")
        return {"response": result}
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        return {"response": f"# 运维诊断报告\n\n{execution_history}\n\n## 说明\n以上为诊断执行过程记录。"}
