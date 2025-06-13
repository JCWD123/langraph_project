from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import Document
import os
from langchain_core.tools import tool
from typing import Optional


@tool
def web_search(key_words: Optional[str]):
    """
    执行网络搜索并返回结构化搜索结果。

    通过 Tavily 搜索引擎获取指定关键词的网页内容，返回 LangChain 格式的文档列表。

    Args:
        key_words: 搜索关键词字符串，支持自然语言查询。
                   示例: "Python 3.12最新特性"

    Returns:
        包含搜索结果的文档列表，每个文档包含:
        - page_content: 网页文本内容（自动拼接多个结果）
        - metadata: 原始搜索结果的元数据
    """
    documents = []
    os.environ["TAVILY_API_KEY"] = "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"
    search = TavilySearchResults()
    docs = search.invoke({"query": key_words})
    documents=[d["content"] for d in docs]
    # web_results = "\n".join([d["content"] for d in docs])
    # web_results = Document(page_content=web_results)
    # documents.append(web_results)
    return documents

