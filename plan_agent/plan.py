from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List

from model.llm import get_deepseek_model
from graph.state import plan_state

class Plan(BaseModel):
    """响应必须与用户任务直接相关"""
    steps: List[str] = Field(description="具体执行子任务")


def plan_agent(state: plan_state):
    model = get_deepseek_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        你是一个专业的任务规划专家，根据目标描述和当前可用工具将目标分解为可执行的子任务流程，确保每个子任务清晰、具体且可独立执行。
        
        目标描述如下：
        {goal}
        当前可用工具如下
        {tools}
        
        处理逻辑：
            1. 接收目标描述和当前可用工具
            2. 任务分解：
                将目标拆解为逻辑连贯、详细完整的子任务
                每个子任务必须足够具体，可直接交由LLM执行，避免模糊表述
            3.工具匹配
                为每个子任务匹配合适的工具：
                若需调用可用工具，标注 （工具：工具名称）
                若无需工具，直接生成内容，标注 （直接生成）
                严格验证工具可用性，不得虚构未提供的工具
            4.计划验证
                完整性检查：确保所有需求均被覆盖
                逻辑性检查：子任务顺序合理，无漏洞
                可行性检查：每个子任务均可执行
            5.输出格式(强制要求为列表)
                采用任务描述+工具标注的格式，例如：
            [子任务1具体描述（工具：网络查询）,子任务2具体描述（直接生成）,子任务3具体描述（工具：数据库）] 
            6.输出数量要求：子任务数量需严格为5个以内
            
        示例输入：撰写一份结构清晰、内容完整的 Python 报告，包含 Python 技术应用案例、代码示例及结果分析，以专业化表达呈现。
        示例输出：['确定 Python 报告主题（直接生成）', '收集 Python 技术应用案例资料（工具：网络查询）', '编写 Python 技术应用案例及对应代码示例（直接生成）', '对案例进行结果分析（直接生成）',  '使用专业化表达润色报告（直接生成）']
            """)
    ])

    planner = prompt | model.with_structured_output(Plan)
    template_vars = {
        "goal": state["goal"],
        "tools": "工具名称：web_search\n"
                 "工具描述：执行联网检索并返回结构化搜索结果。通过 Tavily 搜索引擎获取指定关键词的网页内容，返回 LangChain 格式的文档列表\n"
                 "工具参数接收：要搜索的关键字"
    }
    result = planner.invoke(template_vars)
    # 格式化输出
    steps = [
        f"step{i + 1}: {step}"
        for i, step in enumerate(result.steps)
    ]
    state["steps"] = steps
    state["current_step"]=0
    return state
if __name__ == "__main__":
    state_1 = {
        "goal": "撰写2023年人工智能领域发展报告",
    }
    state = plan_agent(state_1)
    # print(state)


