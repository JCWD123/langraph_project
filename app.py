import uuid
import datetime
from dotenv import load_dotenv
from langchain.schema import Document
import streamlit as st
from streamlit_extras.bottom_container import bottom
from graph.graph import create_graph, stream_graph_updates, plan_state

# 设置上传文件的存储路径
file_path = "upload_files/"
# 加载环境变量
load_dotenv(verbose=True)

def upload_pdf(file):
    """保存上传的文件并返回文件路径"""
    with open(file_path + file.name, "wb") as f:
        f.write(file.getbuffer())
        return file_path + file.name

# 设置页面配置信息
st.set_page_config(
    page_title="AI-Powerwd Assistant",
    page_icon="🌐",
    layout="wide"
)

# 初始化会话状态变量，创建图
if "graph" not in st.session_state:
    st.session_state.graph = create_graph()
# 初始化会话ID和向量存储
if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": uuid.uuid4().hex, "vectorstore": load_vector_store("nomic-embed-text")}}
# 初始化对话历史记录
if "history" not in st.session_state:
    st.session_state.history = []
# 初始化上传状态、模型名称和对话类型
if "settings" not in st.session_state:
    st.session_state.settings = {"uploaded": False, "model_name": "qwen2.5:7b", "type": "chat"}

# 显示应用标题
st.header("👽 AI-Powerwd Assistant")

# 定义可选的模型
model_options = {"通义千问 2.5 7B": "qwen2.5:7b", "DeepSeek R1 7B": "deepseek-r1:7b"}
with st.sidebar:
    # 侧边栏设置部分
    st.header("设置")
    # 模型选择下拉框
    st.session_state.settings["model_name"] = model_options[st.selectbox("选择模型", model_options, index=list(model_options.values()).index(st.session_state.settings["model_name"]))]

    st.divider()

    # 显示版本信息
    st.text(f"{datetime.datetime.now().strftime('%Y.%m.%d')} - ZHANG GAOXING")

# 定义对话类型选项
type_options = {"🤖 对话": "chat", "🔍 联网搜索": "websearch", "👾 代码模式": "code"}
question = None
with bottom():
    # 底部容器，包含工具选择、文件上传和输入框
    st.session_state.settings["type"] = type_options[st.radio("工具选择", type_options.keys(), horizontal=True, label_visibility="collapsed", index=list(type_options.values()).index(st.session_state.settings["type"]))]
    # 文件上传组件
    uploaded_file = st.file_uploader("上传文件", type=["pdf", "docx", "xlsx", "txt", "md"], accept_multiple_files=False, label_visibility="collapsed")
    # 聊天输入框
    question = st.chat_input('输入你要询问的内容')

# 显示历史对话内容
for message in st.session_state.history:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

# 处理用户提问
if question:
    # 显示用户问题
    with st.chat_message("user"):
        st.markdown(question)

    # 准备请求状态
    state = []
    if st.session_state.settings["type"] == "code":
        # 代码模式使用专门的代码模型
        state = {"model_name": "qwen2.5-coder:7b", "messages": [{"role": "user", "content": question}], "type": "chat", "documents": []}
    else:
        # 其他模式使用选择的模型
        state = {"model_name": st.session_state.settings["model_name"], "messages": [{"role": "user", "content": question}], "type": st.session_state.settings["type"], "documents": []}

    # 处理文件上传
    if uploaded_file:
        state["type"] = "file"
        if not st.session_state.settings["uploaded"]:
            # 保存上传的文件
            file_path = upload_pdf(uploaded_file)
            # 添加文档到请求
            state["documents"].append(Document(page_content=file_path))
            st.session_state.settings["uploaded"] = True

    # 获取AI回答并以流式方式显示
    answer = st.chat_message("assistant").write_stream(stream_graph_updates(st.session_state.graph, state, st.session_state.config))

    # 将对话保存到历史记录
    st.session_state.history.append({"role": "user", "content": question})
    st.session_state.history.append({"role": "assistant", "content": answer})
