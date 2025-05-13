from langgraph.graph.state import StateGraph, CompiledStateGraph, END
from state import plan_state
from langgraph.checkpoint.memory import MemorySaver
from paper_agent.web_search import web_search
from paper_agent.read2response import get_report
from paper_agent.retrieve_docs import retrieve_docs
from paper_agent.solve_agent import solve_agent
from update_plan_agent.update_plan import update_plan
from plan_agent.plan import get_plan
from langgraph.graph import END, StateGraph, START
from rout.rout import decide_to_tool, decide_to_report
from state import create_tool_node_with_fallback
def create_graph() -> CompiledStateGraph:
    """
    创建并配置状态图工作流。

    返回:
        CompiledStateGraph: 编译好的状态图
    """

    workflow = StateGraph(plan_state)
    # 添加节点
    workflow.add_node("report_agent", get_report)
    workflow.add_node("retrieve_docs_tool", retrieve_docs)
    workflow.add_node("web_search", create_tool_node_with_fallback([web_search]))
    workflow.add_node("plan_agent", get_plan)
    workflow.add_node("update_plan_agent", update_plan)
    workflow.add_node("solve_agent", solve_agent)

    workflow.add_edge(START, "plan_agent")
    workflow.add_edge("plan_agent", "solve_agent")
    workflow.add_edge("web_search", "update_plan_agent")
    workflow.add_edge("retrieve_docs_tool", "solve_agent")
    workflow.add_edge("report_agent", END)
    workflow.add_conditional_edges(
        "solve_agent",
        decide_to_tool,
        {"web_search",
         "update_plan_agent"
         },
    )
    workflow.add_conditional_edges(
        "update_plan_agent",
        decide_to_report,
        {"report_agent",
        "solve_agent"
        },
    )

    # 创建图，并使用 `MemorySaver()` 在内存中保存状态
    return workflow.compile(checkpointer=MemorySaver())
# print(create_graph().get_graph().draw_png("./graph.png"))
from state import plan_state
from langgraph.graph.state import StateGraph, CompiledStateGraph, END


def stream_graph_updates(graph: CompiledStateGraph, state: plan_state, config: dict):
    """
    流式处理图更新并返回最终结果。

    参数:
        graph (CompiledStateGraph): 编译好的状态图
        user_input (GraphState): 用户输入的状态
        config (dict): 配置字典

    返回:
        generator: 生成器对象，逐步返回图更新的内容
    """

    for chunk, _ in graph.stream(state, config, stream_mode="messages"):
        yield chunk.content
