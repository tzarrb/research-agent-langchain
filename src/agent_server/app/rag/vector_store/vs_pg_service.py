from gc import collect
import json
from typing import override

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session

from langchain.schema import Document
from langchain.vectorstores.pgvector import DistanceStrategy, PGVector

from .base import VsService, SupportedVSType
from ...llm.mode_factory import ModelFactory
from ....utils.log_util import build_logger
from ....config.settings import Settings
from ....db.session import with_session


logger = build_logger("vector-store-service")

class VsPGService(VsService):
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
        self.pg_vector =  PGVector(
            embedding_function=ModelFactory.get_embeddings(embed_model=self.embed_model),
            connection=VsPGService.engine,
            collection_name=Settings.kn_settings.VS_CONFIG.get(SupportedVSType.RELYT).get("collection_name"),
            connection_string=Settings.kn_settings.VS_CONFIG.get(SupportedVSType.RELYT).get("connection_uri"),
            distance_strategy=DistanceStrategy.COSINE, # 可选值: DistanceStrategy.COSINE, DistanceStrategy.EUCLIDEAN
        )
        
    @override
    def save_vector_store(self, session, docs: list[Document]) -> None:
        """
        保存向量库:FAISS保存到磁盘，milvus,PGVector,ES保存到数据库。
        """
        if not docs:
            logger.warning("No documents to save in vector store.")
            return
        
        splitter_docs = self.text_splitter(docs)
        
        self.pg_vector.add_documents(splitter_docs)
        logger.info(f"Saved {len(docs)} documents to PGVector store.")
         

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