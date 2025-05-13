from llm import get_model
from state import plan_state
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List


class PlanStep(BaseModel):
    action: str = Field(description="以动词开头的具体执行步骤")
    details: str = Field(description="该步骤的详细说明")
    result: str = Field(description="该步骤的历史执行结果，如果有，给出历史的全部执行结果，要求完成一致，不添加多余内容。没有则严格写'未执行'")


class plan(BaseModel):
    """响应必须与用户任务直接相关"""
    plan: str = Field(description="用1句话概括总体计划")
    steps2results: List[PlanStep] = Field(description="3-5个具体执行步骤", min_items=3, max_items=5)


def update_plan(state: plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业任务结果总结助手。请根据历史工具或者ai执行的结果总结每个步骤的结果，要求：
    每个步骤的执行结果必须经过加工总结，有可能是参考工具执行的结果，针对步骤进行总结；也有可能是对ai直接生成的结果进行总结概况

    当前任务: {task}
    当前计划: {current_plan}
    当前步骤: {current_steps}
    执行结果: {execution_results}

    注意：你更新计划步骤执行结果只能根据历史的消息去更新，你不能去自己执行"""),
        ("user",
         "请根据历史消息更新计划结果，如果某个计划步骤未执行则写'未执行'。并且你可以根据步骤执行结果优化计划和具体的步骤。")
    ])

    # 准备模板变量
    template_vars = {
        "task": state["task"],
        "current_plan": state["plan"],
        "current_steps": "\n".join(state["steps"]),
        "execution_results": str(state["steps2results"])
    }

    planner = prompt | model.with_structured_output(plan)
    result = planner.invoke(template_vars)
    print(result)
    # 格式化输出
    steps_with_details = [
        f"step{i + 1}:{step.action}（{step.details}）"
        for i, step in enumerate(result.steps2results)
    ]
    results_with_details=[
        f"step{i + 1}:{step.result}"
        for i, step in enumerate(result.steps2results)
    ]

    return {
        "plan": result.plan,
        "steps": steps_with_details,
        "steps2results":results_with_details
    }


if __name__ == "__main__":
    state = {
        "task": "写一个关于Python的博客",
        "plan": "完成一篇Python基础教程",
        "plan_steps": [
            "step1: 确定主题（选择Python核心概念）",
            "step2: 收集资料（官方文档和教程）",
            "step3: 编写初稿（含代码示例）"
        ],
        "plan_steps_results": {
            "step1: 主题为python的主要数据类型",

        }
    }
    result = update_plan(state)
    print("更新后的计划:", result["plan"])
    print("\n优化后的步骤:")
    print("\n".join(result["steps"]))
    print("\n步骤执行结果:")
    print("\n".join(result["steps2results"]))