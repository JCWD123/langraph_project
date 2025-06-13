from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import Document
import os
import time
import random
from langchain_core.tools import tool
from typing import Optional


@tool
def web_search(key_words: Optional[str]):
    """
    使用Tavily执行网络搜索并返回结构化搜索结果。
    """
    os.environ["TAVILY_API_KEY"] = "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"
    search = TavilySearchResults(search_depth="advanced")
    docs = search.invoke({"query": key_words})

    # 添加容错处理，兼容不同的API响应格式
    documents = []
    try:
        if isinstance(docs, list):
            for d in docs:
                if isinstance(d, dict):
                    # 标准格式：字典包含content字段
                    if "content" in d:
                        documents.append(d["content"])
                    # 备选格式：直接使用整个字典的字符串表示
                    elif "url" in d and "snippet" in d:
                        documents.append(f"来源: {d.get('url', '')}\n内容: {d.get('snippet', '')}")
                    else:
                        # 如果没有预期字段，尝试获取所有文本内容
                        content_text = " ".join([str(v) for v in d.values() if isinstance(v, str)])
                        if content_text.strip():
                            documents.append(content_text)
                elif isinstance(d, str):
                    # 如果直接是字符串
                    documents.append(d)
        else:
            # 如果docs不是列表，尝试将其转换为字符串
            documents = [str(docs)]

    except Exception as e:
        print(f"   ⚠️ Tavily响应解析错误: {e}")
        print(f"   📊 响应格式: {type(docs)}")
        if docs:
            print(f"   📝 响应内容示例: {str(docs)[:200]}...")
        # 返回错误信息而不是空列表
        documents = [f"Tavily响应解析失败: {str(e)}"]

    return documents