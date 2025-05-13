from llm import get_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
from state import plan_state
from paper_agent.web_search import web_search
def solve_agent(state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的工具调用和智能问题解决助手。请根据以下计划的具体步骤调用工具或者智能回复解决问题：

任务概述: {task}
原始计划: {current_plan}

具体步骤:
{steps}
执行结果：
{steps2results}
注意：
1. 你可以严格按照步骤执行工具调用或者智能回复解决问题。
2. 你必须严格按照步骤执行。
3. 你必须严格按照步骤执行。
4.执行结果中已经执行的不需要再去执行
5.一次只能去执行一个步骤（而且是未完成的）
示例输出：
step1：确定主题（选择Python核心概念）
执行方法：直接生成
执行结果：我将选择一个Python核心概念作为博客重点。"Python列表推导式"是个理想选题，因为这个基础但强大的特性能让许多初学者和中级开发者深入受益。
示例输出：
step1：收集资源（官方文档和教程）
执行方法：调用工具
执行方案（未执行）：接下来需要搜集相关资料，例如Python官方文档和教程，以确保博客的准确性和深度。现在我将使用`web_search`工具搜索关于"Python列表推导式"的官方文档和教程。'
示例输出：
step2：收集资源（官方文档和教程）
执行方法：调用工具
执行方案（未执行）：接下来需要搜集相关资料，例如Python官方文档和教程，以确保博客的准确性和深度。现在我将使用`web_search`工具搜索关于"Python列表推导式"的官方文档和教程。'

""")])
    planner = prompt | model.bind_tools([web_search])
    template_vars = {
        "task": state["task"],
        "current_plan": state["plan"],
        "steps": state["steps"],
        "steps2results": state["steps2results"]
    }
    result= planner.invoke(template_vars)
    print(result)
    state["messages"].append(result)
    # 格式化输出
    return state

if __name__ == "__main__":
    state = {
        "task": "写一个关于Python的博客",
        "plan": "完成一篇Python基础教程",
        "steps": [
            "step1:确定主题（选择Python核心概念）",
            "step2:收集资料（官方文档和教程）",
            "step3:编写初稿（含代码示例）"
        ],
        "steps2results": {

        },
        "messages":[]
    }
    result = solve_agent(state)
    print(result)