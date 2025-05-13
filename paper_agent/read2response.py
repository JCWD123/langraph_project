from llm import get_model
from state import plan_state
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
from state import plan_state

def get_report(state:plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的任务总结助手。请根据以下信息生成清晰的执行报告：

任务概述: {task}
原始计划: {current_plan}

执行情况分析:
{execution_results}

请按以下要求生成报告:
1. 详细按照步骤执行结果总结生成专业的报告
2. 报告必须与用户任务直接相关
3. 报告必须包含以下内容：
   - 任务概述
   - 执行计划和步骤
   - 每个步骤的执行结果
   - 总结整体结果
注意：
1. 确保报告清晰、准确，符合Markdown格式要求

"""),
        ("user",
         "请根据历史消息更新计划结果，如果某个计划步骤未执行则写未执行。并且你可以根据步骤执行结果优化计划和具体的步骤。")
    ])
    planner = prompt | model
    template_vars = {
        "task": state["task"],
        "current_plan": state["plan"],
        "execution_results": state["plan_steps_results"]
    }
    state["messages"].append(planner.invoke(template_vars))

    # 格式化输出
    return state

if __name__ == "__main__":
    state = {
        "task": "写一个关于Python的博客",
        "plan": "完成一篇Python基础教程",
        "plan_steps": [
            "step1:确定主题（选择Python核心概念）",
            "step2:收集资料（官方文档和教程）",
            "step3:编写初稿（含代码示例）"
        ],
        "plan_steps_results": {
            "step1:主题为python的主要数据类型",
            "step2:选定讲解Python的6种核心数据类型（数字/字符串/列表/元组/字典/集合）",
            "step3:Python的6种核心数据类型（数字/字符串/列表/元组/字典/集合）"

        },
        "messages":[]
    }
    result = generate_response(state)
    print(result)