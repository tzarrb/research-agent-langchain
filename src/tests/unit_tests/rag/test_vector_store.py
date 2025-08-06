from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_postgres import PGEngine, PGVectorStore

from langchain_core.embeddings import DeterministicFakeEmbedding

# Replace the connection string with your own Postgres connection string
CONNECTION_STRING = "postgresql+asyncpg://root:123456@127.0.0.1:5433/researchagent"
# CONNECTION_STRING = "postgresql+psycopg2://root:123456@localhost:5433/researchagent"
COLLECTION_NAME = "vector_store"

# Replace the vector size with your own vector size
VECTOR_SIZE = 1536
embedding = DeterministicFakeEmbedding(size=VECTOR_SIZE)

engine = PGEngine.from_connection_string(url=CONNECTION_STRING)
# engine.init_vectorstore_table(
#     table_name=COLLECTION_NAME,
#     id_column="id",
#     metadata_json_column="metadata",
#     vector_size=VECTOR_SIZE,
# )

store = PGVectorStore.create_sync(
    engine=engine,
    table_name=COLLECTION_NAME,
    id_column="id",
    metadata_json_column="metadata",
    embedding_service=embedding,
)

if __name__ == "__main__":
    # 测试向量库服务
    
    # 创建测试文档
    test_docs = [
        Document(page_content="This is a test document.", metadata={"source": "test1"}),
        Document(page_content="This is another test document.", metadata={"source": "test2"})
    ]
    
    # 保存文档到向量库
    result = store.add_documents(test_docs)
    print(f"Saved {len(test_docs)} documents to PGVector store.")
    
    # logger.info("Vector store service initialized and documents saved successfully.")