from state import plan_state
from langgraph.prebuilt import tools_condition
from langgraph.graph.state import StateGraph, CompiledStateGraph, END
def decide_to_tool(state: plan_state):
    route = tools_condition(state)
    # if route == END:
    #     return END
    if state["messages"][-1].tool_calls:
        for call in state["messages"][-1].tool_calls:
            if 'name' in call:
                return call['name']
    else:
        return "update_plan_agent"

def decide_to_report(state: plan_state):
    for i in state["steps2results"]:
        if "未执行" in i:
            return "solve_agent"
    return "report_agent"