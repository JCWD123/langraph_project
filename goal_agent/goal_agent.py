from model.llm import get_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
from graph.state import plan_state
from paper_agent.web_search import web_search
def goal_agent(state:plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([("""
角色定义：
    你是一个专业的需求重写专家，负责将用户提出的模糊需求转化为明确、可执行的目标描述。
    
用户输入如下:
{task}

核心职责是确保每个需求都具备以下关键特性：
    逻辑性 - 保持严谨的表述结构
    简明性 - 采用精炼的专业化表达，一到两句话表达
    完整性 - 涵盖所有必要要素
    清晰性 - 使用准确易懂的表达
    流畅性 - 确保自然通顺的叙述
    
注意：不需要其他额外内容输出

示例输入：帮我写一份python报告
示例输出：撰写一份结构清晰、内容完整的 Python 报告，包含 Python 技术应用案例、代码示例及结果分析，以专业化表达呈现。
""")])
    planner = prompt | model
    template_vars = {
        "task": state["task"],
    }
    result= planner.invoke(template_vars)
    state["messages"].append(result)
    state["goal"]=result
    # 格式化输出
    return state

