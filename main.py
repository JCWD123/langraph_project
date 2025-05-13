import uuid
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_core.messages import AIMessage, HumanMessage
from graph import create_graph, stream_graph_updates
from state import plan_state
def main():
    # langchain.debug = True  # 启用langchain调试模式，可以获得如完整提示词等信息
    load_dotenv(verbose=True)  # 加载环境变量配置

    # 创建状态图以及对话相关的设置
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    graph = create_graph()
    state = plan_state(task='',
    messages=[],
    plan='',
    steps=[],
    steps2results=[],
    documents=[])
    # 对话
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        state["messages"].append(HumanMessage(content=user_input))
        # 流式获取AI的回复
        for answer in stream_graph_updates(graph, state, config):
            print(answer, end="")
        print()

    # 打印对话历史
    print("\nHistory: ")
    for message in graph.get_state(config).values["messages"]:
        if isinstance(message, AIMessage):
            prefix = "AI"
        else:
            prefix = "User"
        print(f"{prefix}: {message.content}")

if __name__ == "__main__":
    main()
