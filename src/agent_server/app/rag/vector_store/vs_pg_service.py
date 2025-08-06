from gc import collect
import json
from typing import override

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_postgres import PGEngine, PGVectorStore
from langchain_postgres.v2.indexes import DistanceStrategy

from .base import VsService, SupportedVSType
from app.llm.mode_factory import ModelFactory
from utils.log_util import build_logger
from config.settings import Settings


logger = build_logger("vector-store-service")

class VsPGService(VsService):
    """
    pgvector向量库服务
    """
    engine = PGEngine.from_connection_string(url=Settings.kn_settings.VS_CONFIG.get(SupportedVSType.PG).get("connection_uri"))

    def do_init(self):
        self.init_vector_store()

    def init_vector_store(self):
        """
        获取pgvector向量库
        """
        table_name = Settings.kn_settings.VS_CONFIG.get(SupportedVSType.PG).get("collection_name", "vector_store")
        # engine.init_vectorstore_table(
        #     table_name=table_name,
        #     id_column="id",
        #     metadata_json_column="metadata",
        #     vector_size=VECTOR_SIZE,
        # )
        self.store = PGVectorStore.create_sync(
            engine=VsPGService.engine,
            embedding_service=ModelFactory.get_embeddings(embed_model=self.embed_model),
            table_name=table_name,
            id_column="id",
            metadata_json_column="metadata",
            distance_strategy=DistanceStrategy.COSINE_DISTANCE, # 可选值: DistanceStrategy.COSINE, DistanceStrategy.EUCLIDEAN
        )
        
    @override
    def save_vector_store(self, docs: list[Document]) -> list[str]:
        """
        保存向量库:FAISS保存到磁盘，milvus,PGVector,ES保存到数据库。
        """
        if not docs:
            logger.warning("No documents to save in vector store.")
            return []
        
        splitter_docs = self.split_document(docs)
        
        doc_ids = self.store.add_documents(splitter_docs)
        logger.info(f"Saved {len(splitter_docs)} documents to PGVector store.")
        return doc_ids
    
    @override
    def get_vector_store(self):
        """
        获取向量库
        """
        logger.info("Retrieved PGVector store.")
        return self.store     
    
    def get_vector_store_retriever(
        self,
        top_k: int = Settings.kn_settings.VECTOR_SEARCH_TOP_K,
        score_threshold: int | float = Settings.kn_settings.VECTOR_SEARCH_SCORE_THRESHOLD,
        ):
        """
        获取向量库检索器 VectorStoreRetriever
        """
        retriever = self.store.as_retriever(
            search_type="similarity", # 可选值: "similarity", "similarity_score_threshold", "mmr"
            search_kwargs={"score_threshold": score_threshold, "k": top_k}
            )
        logger.info("Retrieved PGVector store retriever.")
        return retriever

if __name__ == "__main__":
    
    import os
    import sys
    
    # 把 src 加入 sys.path
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    print("Current sys.path = ", sys.path)


    # 测试向量库服务
    vs_service = VsPGService(embed_model=Settings.model_settings.DEFAULT_EMBEDDING_MODEL)
    #vs_service.init_vector_store()
    
    # 创建测试文档
    test_docs = [
        Document(page_content="This is a test document.", metadata={"source": "test1"}),
        Document(page_content="This is another test document.", metadata={"source": "test2"})
    ]
    
    # 保存文档到向量库
    vs_service.save_vector_store(test_docs)
    
    logger.info("Vector store service initialized and documents saved successfully.")