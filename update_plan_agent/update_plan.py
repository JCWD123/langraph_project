from model.llm import get_deepseek_model
from graph.state import plan_state
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List


class Plan(BaseModel):
    """响应必须与用户任务直接相关"""
    steps: List[str] = Field(description="具体执行子任务")


def update_plan(state: plan_state):
    model = get_deepseek_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的计划动态调整专家，以用户目标为导向，负责在执行过程中监控任务进展，并根据已完成子任务的结果，智能调整后续计划。
        
        用户目标：{goal}
        原始完整计划：{plan}
        历史执行记录：{steps2results}
        当前可用工具：{tools}
        
        核心职责：
            计划演进：基于历史执行结果优化后续子任务
            上下文保持：严格保留已执行任务及结果，不修改历史子任务和执行结果
            动态适配：确保剩余计划与当前状态匹配
            
        处理逻辑：
            1.输入接收
                原始完整计划：初始全部子任务列表（含工具标注）
                历史执行记录：已完成子任务及其执行结果
                当前可用工具：工具列表
            2.计划分析
                完成度检查：
                    已执行任务：标记为锁定状态（不可修改）
                    待执行任务：标记为可调整状态
                影响评估：识别成功执行结果对后续任务的影响
                    前置任务结果导致后续任务变化
                    发现新的必要子任务
                    是否需要调整任务内容
                    是否需要更换执行工具
            3.计划更新
                禁止操作：
                    修改已执行任务
                    使用未声明工具
                    变更任务顺序
                允许操作：修改后续子任务
                    若需要调整后续任务可选：
                        修改任务描述
                        更换执行工具
                        新增必要任务
                        删除无法执行的任务
                        格式如下：
                            子任务3具体描述（工具：数据库）
                        最后返回所有的子任务列表，包括之前执行的子任务（禁止修改）和后续的子任务（允许修改）
                    若不需要调整
                    返回原始的所有的子任务列表
        输出数量要求：子任务数量需严格为5个以内
        示例计划输入：['确定 Python 报告主题（直接生成）', '收集 Python 技术应用案例资料（工具：网络查询）', '编写 Python 技术应用案例及对应代码示例（直接生成）', '对案例进行结果分析（直接生成）',  '使用专业化表达润色报告（直接生成）']
        示例输出：['确定 Python 报告主题（直接生成）', 'step2_updated：更新的具体子计划', 'step3_updated：更新的具体子计划', 'step4_updated：更新的具体子计划',  'step5_updated：更新的具体子计划']
                    """),
    ])

    # 准备模板变量
    template_vars = {
        "goal": state["goal"],
        "plan": state["steps"],
        "tools": "工具名称：web_search\n"
                 "工具描述：执行联网检索并返回结构化搜索结果。通过 Tavily 搜索引擎获取指定关键词的网页内容，返回 LangChain 格式的文档列表\n"
                 "工具参数接收：要搜索的关键字",
        "steps2results":  state["steps2results"]
    }

    planner = prompt | model.with_structured_output(Plan)
    result = planner.invoke(template_vars)
    # 格式化输出
    steps_with_details = [
        f"step{i + 1}: {step}）"
        for i, step in enumerate(result.steps)
    ]
    state["steps"] = steps_with_details
    return state
