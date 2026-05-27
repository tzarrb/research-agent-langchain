from gc import collect
import json
from typing import Any, override

# import rank_bm25

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_postgres import PGEngine, PGVectorStore
from langchain_postgres.v2.indexes import DistanceStrategy
from langchain.retrievers import EnsembleRetriever, BM25Retriever

from agent_server.app.rag.vector_store.base import VsService, SupportedVSType
from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.utils.log_util import build_logger
from agent_server.config.settings import Settings


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
        获取向量库检索器 
        Builds BM25 and vector-based retrievers and combines them into an ensemble retriever.

        Returns:
            EnsembleRetriever: Combined retriever using BM25 and vector-based methods.
        """
        # logger.info("Building BM25 retriever.")
        # docs_list: list[str] = self.docs_list
        # bm25_retriever = BM25Retriever.from_documents(docs_list, search_kwargs={"k": top_k})

        # logger.info("Building vector-based retrievers.")
        # retriever_vanilla = self.store.as_retriever(
        #     search_type="similarity", search_kwargs={"k": top_k}
        # )
        # retriever_mmr = self.store.as_retriever(
        #     search_type="mmr", search_kwargs={"k": top_k}
        # )

        # logger.info("Combining retrievers into an ensemble retriever.")
        # ensemble_retriever = EnsembleRetriever(
        #     retrievers=[retriever_vanilla, retriever_mmr, bm25_retriever],
        #     weights=[0.3, 0.3, 0.4],
        # )
        # logger.info("Retrievers built successfully.")
        # return ensemble_retriever
        
        retriever = self.store.as_retriever(
            search_type="similarity", # 可选值: "similarity", "similarity_score_threshold", "mmr"
            search_kwargs={"score_threshold": score_threshold, "k": top_k}
            )
        logger.info("Retrieved PGVector store retriever.")
        return retriever

if __name__ == "__main__":
    
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