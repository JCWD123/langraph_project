from model.llm import get_model
from graph.state import plan_state
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List

def get_report(state:plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的任务报告产出助手。请你以【用户目标】为导向，参考【历史子任务执行记录】，完成一份非常专业的报告。
        请根据以下信息生成清晰的执行报告：
        用户目标: {goal}
        计划: {plan}
        历史子任务执行记录:
        {steps2results}

        要求:
        1. 详细按照步骤执行结果总结生成专业的报告
        2. 报告必须与用户目标直接相关
        注意：
        1. 确保报告清晰、准确，符合Markdown格式要求

"""),
    ])
    reporter = prompt | model
    template_vars = {
        "goal": state["goal"],
        "plan": state["steps"],
        "steps2results": state["steps2results"]
    }
    result=reporter.invoke(template_vars)
    state["messages"].append(result)
    # 格式化输出
    return state
