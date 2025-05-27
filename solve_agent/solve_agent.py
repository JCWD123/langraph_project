from model.llm import get_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
from graph.state import plan_state
from paper_agent.web_search import web_search
def solve_agent(state:plan_state):
    model = get_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
角色定义：
你是一个工具参数识别和精准调用专家。需要调用工具执行【当前任务】。

注意：
执行要以以【用户目标】为导向，
只需要执行当前任务
根据需求选择合适准确的工具调用，否则直接回复
如果当前任务已有工具执行结果，直接进行总结进行回复，不需要再去调用工具(非常重要)
若要工具调用，模型需严格输出LangChain 兼容的 JSON 格式

所需上下文：
用户目标如下：
{goal}
当前子任务如下：
{current_plan}
历史任务执行记录如下：
{steps2results}
""")])
    planner = prompt | model.bind_tools([web_search])
    current_step=state["current_step"]
    template_vars = {
        "goal": state["goal"],
        # "tools": "工具名称：web_search\n"
        #          "工具描述：执行联网检索并返回结构化搜索结果。通过 Tavily 搜索引擎获取指定关键词的网页内容，返回 LangChain 格式的文档列表\n"
        #          "工具参数接收：要搜索的关键字",，
        "current_plan": state["steps"][current_step],
        "steps2results": state["steps2results"]
    }
    print(state["steps2results"])
    result= planner.invoke(template_vars)
    state["messages"].append(result)
    # 格式化输出
    if result.tool_calls:
        if 'name' in result.tool_calls[0]:
            if f"step{current_step+1}" in  state["steps2results"]:
                state["steps2results"][f"step{current_step+1}"]["tool_calls"]=result.tool_calls[0]
            else:
                state["steps2results"][f"step{current_step+1}"]={"sub_task":state["steps"][current_step],
                                           "tool_calls":result.tool_calls[0]}
        state["current_step"]=current_step
    else:
        if f"step{current_step+1}" in state["steps2results"]:
            state["steps2results"][f"step{current_step+1}"]["result"] = result
        else:
            state["steps2results"][f"step{current_step+1}"] = {"sub_task":state["steps"][current_step],
                                               "result":result}
        state["current_step"]=current_step+1
    return state
if __name__ == "__main__":
    state_1 = {
        "goal": "撰写2023年人工智能领域发展报告",
        "steps": [
            "step1: 查询2023年AI领域最重要的技术突破（工具：web_search）",
            "step2: 分析这些突破的技术原理",
            "step3: 总结实际应用案例"
        ],
        "current_step": 0,
        "steps2results": {},
        "messages": []
    }
    state = solve_agent(state_1)
    # print(state)

'''
角色定义：
你是一个专业的任务执行专家，以【用户目标】为导向，参考【历史任务执行记录】和系统可用【工具】，精准执行【当前任务】。

用户目标如下：
{goal}
历史任务执行记录如下：
{steps2results}
当前子任务如下：
{current_plan}


处理逻辑：
    1.输入接收
        用户目标：明确任务总目标
        当前任务：明确子任务描述及要求
        历史任务记录：包含过往任务描述及执行结果（用于上下文参考）
        可用工具列表：系统当前可调用的工具及其功能说明
    2.任务执行
        （1）若当前任务有任务执行记录（工具调用信息和工具执行结果）：
            处理办法：直接对当前任务执行结果进行总结概括
        （2）若当前任务没有任务执行记录（工具调用信息和工具执行结果）：
            处理办法：
                参考当前任务的标注直接生成还是调用工具（根据你系统中的工具和参数，调用工具）
                注意：这个标注只是一个参考，不需要严格按照它执行。你要自主的选择直接生成还是调用工具，调用什么工具等等。
                ①工具调用
                ②直接生成
    3.结果返回
        返回工具调用信息（json)或生成的内容

'''