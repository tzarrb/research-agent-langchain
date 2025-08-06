from gc import collect
import json
from typing import override

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session

from langchain.schema import Document
from langchain_community.vectorstores.pgvector import PGVector, DistanceStrategy


from .base import VsService, SupportedVSType
from app.llm.mode_factory import ModelFactory
from utils.log_util import build_logger
from config.settings import Settings


logger = build_logger("vector-store-relyt-service")

class VsRelytService(VsService):
    """
    pgvector向量库服务
    """
    engine: Engine = sqlalchemy.create_engine(
        Settings.kn_settings.VS_CONFIG.get(SupportedVSType.RELYT).get("connection_uri"), pool_size=10
    )

    def do_init(self):
        self.init_vector_store()

    def init_vector_store(self):
        """
        获取pgvector向量库
        """
        self.store =  PGVector(
            embedding_function=ModelFactory.get_embeddings(embed_model=self.embed_model),
            connection=VsRelytService.engine,
            collection_name=Settings.kn_settings.VS_CONFIG.get(SupportedVSType.RELYT).get("collection_name"),
            connection_string=Settings.kn_settings.VS_CONFIG.get(SupportedVSType.RELYT).get("connection_uri"),
            distance_strategy=DistanceStrategy.COSINE, # 可选值: DistanceStrategy.COSINE, DistanceStrategy.EUCLIDEAN
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
    
    def get_vector_store_retriever(self):
        """
        获取向量库检索器 VectorStoreRetriever
        """
        retriever = self.store.as_retriever(search_kwargs={"k": Settings.kn_settings.VECTOR_SEARCH_TOP_K})
        logger.info("Retrieved PGVector store retriever.")
        return retriever
         