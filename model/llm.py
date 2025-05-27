from langchain_openai import ChatOpenAI
def get_model():
    model = ChatOpenAI(model="Qwen/Qwen3-235B-A22B",api_key='sk-hnoditahilyfbrromnmrrcfkiliqiqmecvkwzwgyetllahnd',base_url="https://api.siliconflow.cn/v1")
    return model
def get_deepseek_model():
    model = ChatOpenAI(model="deepseek-ai/DeepSeek-V3",api_key='sk-hnoditahilyfbrromnmrrcfkiliqiqmecvkwzwgyetllahnd',base_url="https://api.siliconflow.cn/v1")
    return model