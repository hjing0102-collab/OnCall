"""AIOps 服务 - Plan-Execute-Replan"""

from typing import AsyncGenerator, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from app.agent.aiops import PlanExecuteState, planner, executor, replanner

NODE_PLANNER = "planner"
NODE_EXECUTOR = "executor"
NODE_REPLANNER = "replanner"


class AIOpsService:
    """Plan-Execute-Replan 服务"""

    def __init__(self):
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        logger.info("AIOps 服务初始化完成")

    def _build_graph(self):
        workflow = StateGraph(PlanExecuteState)
        workflow.add_node(NODE_PLANNER, planner)
        workflow.add_node(NODE_EXECUTOR, executor)
        workflow.add_node(NODE_REPLANNER, replanner)
        workflow.set_entry_point(NODE_PLANNER)
        workflow.add_edge(NODE_PLANNER, NODE_EXECUTOR)
        workflow.add_edge(NODE_EXECUTOR, NODE_REPLANNER)

        def should_continue(state: PlanExecuteState) -> str:
            if state is None:
                return END
            try:
                if state.get("response"):
                    return END
                if state.get("plan", []):
                    return NODE_EXECUTOR
            except Exception:
                pass
            return END

        workflow.add_conditional_edges(NODE_REPLANNER, should_continue, {
            NODE_EXECUTOR: NODE_EXECUTOR, END: END
        })
        return workflow.compile(checkpointer=self.checkpointer)

    async def execute(self, user_input: str, session_id: str = "default") -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"[会话 {session_id}] 开始执行")
        try:
            initial_state: PlanExecuteState = {"input": user_input, "plan": [], "past_steps": [], "response": ""}
            config_dict = {"configurable": {"thread_id": session_id}}

            async for event in self.graph.astream(input=initial_state, config=config_dict, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    if node_name == NODE_PLANNER:
                        plan = node_output.get("plan", [])
                        yield {
                            "type": "plan",
                            "message": f"执行计划已制定，共 {len(plan)} 个步骤",
                            "plan": [{"step": i + 1, "description": s} for i, s in enumerate(plan)]
                        }
                    elif node_name == NODE_EXECUTOR:
                        past = node_output.get("past_steps", [])
                        remaining_plan = node_output.get("plan", [])
                        if past:
                            last_step, last_result = past[-1]
                            total = len(past) + len(remaining_plan)
                            yield {
                                "type": "step_progress",
                                "message": f"步骤完成",
                                "step_name": last_step,
                                "step_result": last_result[:500],
                                "current": len(past),
                                "total": total,
                            }
                    elif node_name == NODE_REPLANNER:
                        response = node_output.get("response", "")
                        if response:
                            yield {
                                "type": "report",
                                "message": "诊断报告已生成",
                                "report": response,
                            }

            final_state = self.graph.get_state(config_dict)
            final_response = ""
            if final_state and final_state.values:
                final_response = final_state.values.get("response", "")
            yield {"type": "complete", "message": "诊断完成", "response": final_response}
        except Exception as e:
            logger.opt(exception=True).error(f"执行失败: {e}")
            yield {"type": "error", "message": f"任务执行出错: {str(e)}"}

    async def diagnose(self, session_id: str = "default") -> AsyncGenerator[Dict[str, Any], None]:
        from textwrap import dedent

        aiops_task = dedent("""你是一个运维诊断专家，正在对当前电脑进行实时系统诊断。

请按以下步骤执行（每一步都必须使用工具获取真实数据，不可编造）：

1. 使用 get_current_time 获取当前时间
2. 使用 get_system_overview 获取系统整体概览
3. 使用 get_cpu_usage 获取CPU详情
4. 使用 get_memory_usage 获取内存详情
5. 使用 get_disk_usage 获取磁盘详情
6. 使用 retrieve_knowledge 检索知识库中与当前系统状态最相关的处理方案（query 参数使用实际的告警类型，如"CPU使用率过高处理方案"）

请基于以上所有真实数据生成诊断报告，格式如下：

# 实时运维诊断报告
## 当前时间
[时间]
## 系统实时状态
- CPU: [真实数据] — 状态: [正常/警告/危险]
- 内存: [真实数据] — 状态: [正常/警告/危险]
- 磁盘: [真实数据] — 状态: [正常/警告/危险]
## 问题发现
[基于真实指标发现的问题，如果一切正常请写明"系统运行正常，各指标在安全范围内"]
## 处理建议
[基于知识库检索结果给出针对性建议]

注意：所有数据必须来自工具返回的真实结果，判断标准：CPU>80%警告, 内存>85%警告, 磁盘>90%警告。""")

        async for event in self.execute(aiops_task, session_id):
            yield event


aiops_service = AIOpsService()
