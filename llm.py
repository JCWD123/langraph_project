from langchain_openai import ChatOpenAI
def get_model():
    model = ChatOpenAI(model="Pro/deepseek-ai/DeepSeek-V3",api_key='sk-hnoditahilyfbrromnmrrcfkiliqiqmecvkwzwgyetllahnd',base_url="https://api.siliconflow.cn/v1")
    return model