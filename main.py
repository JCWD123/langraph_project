import uuid
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from graph.graph import create_graph, stream_graph_updates
from graph.state import plan_state
import json  # 新增：用于保存json

def main():
    # langchain.debug = True  # 启用langchain调试模式，可以获得如完整提示词等信息
    load_dotenv(verbose=True)  # 加载环境变量配置

    # 创建状态图以及对话相关的设置
    config = {
        "configurable": {"thread_id": uuid.uuid4().hex},
        "recursion_limit": 100
    }
    graph = create_graph()
    state = plan_state(
        task='',
        goal='',
        messages=[],
        steps=[],
        steps2results={},documents=[])
    history_data = []  # 新增：用于存储对话内容
    # 对话
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        # 清洗输入，去除非法Unicode字符
        user_input = user_input.encode('utf-8', 'ignore').decode('utf-8')
        state["messages"].append(HumanMessage(content=user_input))
        state["task"]=user_input
        ai_response = ""  # 新增：用于收集AI回复
        # 流式获取AI的回复
        for answer in stream_graph_updates(graph, state, config):
            print(answer, end="")
            # 修复：确保answer为str类型
            if isinstance(answer, list):
                answer = "".join(str(x) for x in answer)
            ai_response += str(answer)
        print()
        # 新增：保存本轮对话到history_data
        history_data.append({
            "user": user_input,
            "assistant": ai_response
        })

    # 打印对话历史
    print("\nHistory: ")
    for message in graph.get_state(config).values["messages"]:
        if isinstance(message, AIMessage):
            prefix = "AI"
        else:
            prefix = "User"
        print(f"{prefix}: {message.content}")

    # 新增：退出时保存为json
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    print("对话内容已保存为 output.json")

if __name__ == "__main__":
    main()
