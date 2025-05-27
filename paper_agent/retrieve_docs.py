from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from graph.state import plan_state
from langchain_core.messages import ToolMessage
import numpy as np
import openai
class VectorStoreRetriever:
    def __init__(self, docs: list, vectors: list, oai_client):
        self._arr = np.array(vectors)
        self._docs = docs
        self._client = oai_client

    @classmethod
    def from_docs(cls, docs, oai_client):
        embeddings = oai_client.embeddings.create(
            model="BAAI/bge-m3", input=[doc["page_content"] for doc in docs]
        )
        vectors = [emb.embedding for emb in embeddings.data]
        return cls(docs, vectors, oai_client)

    def query(self, query: str, k: int = 5) -> list[dict]:
        embed = self._client.embeddings.create(
            model="BAAI/bge-m3", input=[query]
        )
        # "@" is just a matrix multiplication in python
        scores = np.array(embed.data[0].embedding) @ self._arr.T
        top_k_idx = np.argpartition(scores, -k)[-k:]
        top_k_idx_sorted = top_k_idx[np.argsort(-scores[top_k_idx])]
        return [
            {**self._docs[idx], "similarity": scores[idx]} for idx in top_k_idx_sorted
        ]
def retrieve_docs(state: plan_state):
    docs = state["documents"]
    retriever = VectorStoreRetriever.from_docs(docs, openai.Client(base_url="https://api.siliconflow.cn/v1",api_key='sk-hnoditahilyfbrromnmrrcfkiliqiqmecvkwzwgyetllahnd'))
    docs = retriever.query(state['task'], k=2)
    result= "\n\n".join([doc["page_content"] for doc in docs])
    state["messages"] =ToolMessage(result)
    return state