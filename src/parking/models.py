"""Create LangChain clients when the application starts, without startup probes."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def create_embeddings() -> OpenAIEmbeddings:
    embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)
    return embeddings


def create_llm() -> ChatOpenAI:
    llm = ChatOpenAI(model="gpt-6-luna")
    return llm
