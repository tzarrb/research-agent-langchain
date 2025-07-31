import operator
import os
from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy.orm import Session

#from langchain.schema import Document
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...llm.mode_factory import ModelFactory
from ....config.settings import Settings
from ....utils.log_util import build_logger
from ....utils.llm_util import (
    get_default_embedding,
)


class SupportedVSType:
    DEFAULT = "default"
    FAISS = "faiss"
    MILVUS = "milvus"
    ZILLIZ = "zilliz"
    PG = "pg"
    RELYT = "relyt"
    ES = "es"
    CHROMADB = "chromadb"


class VsService(ABC):
    # def __init__(
    #     self,
    #     knowledge_name: str,
    #     kb_info: str = None,
    #     embed_model: str = get_default_embedding(),
    # ):
    #     self.kb_name = knowledge_name
    #     self.kb_info = kb_info or Settings.kn_settings.KN_INFO.get(
    #         knowledge_name, f"关于{knowledge_name}的知识库"
    #     )
    #     self.embed_model = embed_model
    #     self.kb_path = get_kb_path(self.kb_name)
    #     self.doc_path = get_doc_path(self.kb_name)
    #     self.do_init()
        
    # def __repr__(self) -> str:
    #     return f"{self.kb_name} @ {self.embed_model}"
    
    def __init__(
        self,
        embed_model: str = get_default_embedding(),
    ):
        self.embed_model = embed_model
        self.do_init()
        
    def do_init(self) -> None:
        pass

    def init_vector_store(self):
        """
        初始化向量库
        """
        raise NotImplementedError("Subclasses should implement this method.")
    
    @abstractmethod
    def save_vector_store(self, session: Session, docs: list[Document]) -> None:
        """
        保存向量库:FAISS保存到磁盘，milvus,PGVector,ES保存到数据库。
        """
        pass
    
    def text_splitter(self, documents: list[Document]) -> list[Document]:
        """
        固定长度文本分割器
        """
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=Settings.kn_settings.CHUNK_SIZE,
            chunk_overlap=Settings.kn_settings.OVERLAP_SIZE,
        )
        docs = text_splitter.split_documents(documents)
        
        return docs

    def check_embed_model(self) -> tuple[bool, str]:
        return ModelFactory.check_embed_model(self.embed_model)
