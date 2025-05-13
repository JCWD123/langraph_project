from llm import get_model
from state import plan_state
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List


class PlanStep(BaseModel):
    action: str = Field(description="以动词开头的具体执行步骤")
    details: str = Field(description="该步骤的详细说明")

class Plan(BaseModel):
    """响应必须与用户任务直接相关"""
    plan: str = Field(description="用1句话概括总体计划")
    steps: List[PlanStep] = Field(description="3-5个具体执行步骤", min_items=3, max_items=5)


def get_plan(state: plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业任务规划师。请根据用户任务生成具体可行的计划，要求：
1. 所有内容必须严格围绕用户任务
2. 给出3-5个以动词开头的具体步骤
3. 每个步骤附带简要说明

当前任务: {task}"""),
        ("user", "请根据上述任务生成执行计划")
    ])

    planner = prompt | model.with_structured_output(Plan)
    state["task"] = state["messages"][-1].content
    print("state[task]",state["task"])
    result = planner.invoke({"task": state["task"]})

    # 格式化输出
    steps_with_details = [
        f"step{i + 1}: {step.action}（{step.details}）"
        for i, step in enumerate(result.steps)
    ]
    state["plan"] = result.plan
    state["steps"] = steps_with_details
    return state

if __name__ == "__main__":
    state = {"task": "写一个关于Python的博客"}
    result = get_plan(state)
    print(result)