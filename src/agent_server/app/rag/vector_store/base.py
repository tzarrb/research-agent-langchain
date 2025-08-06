
import operator
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Union
from webbrowser import get

from sqlalchemy.orm import Session

#from langchain.schema import Document
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_transformers import EmbeddingsRedundantFilter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter, 
    HTMLHeaderTextSplitter, 
    MarkdownHeaderTextSplitter
)

from app.llm.mode_factory import ModelFactory
from config.settings import Settings
from utils.log_util import build_logger
from utils.llm_util import (
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


def get_kn_path(knowledge_name: str):
    return os.path.join(Settings.basic_settings.KN_ROOT_PATH, knowledge_name)


def get_doc_path(knowledge_name: str):
    return os.path.join(get_kn_path(knowledge_name), "content")



class VsService(ABC):

    # CharacterTextSplitter一般用于简单文本的分割，用于将长文本分割成更小的块(chunks)，以便更好地处理大文本数据。
    char_text_splitter: CharacterTextSplitter = CharacterTextSplitter(
            separator="",  # 没有分割符，也就是连贯分割
            chunk_size=Settings.kn_settings.CHUNK_SIZE,  # 文本块的大小
            chunk_overlap=Settings.kn_settings.OVERLAP_SIZE,  # 重叠部分的大小
            length_function=len, # 文本长度计算函数
        )
    
    # RecursiveCharacterTextSplitter采用递归方式尝试多种分隔符来分割文本，直到获得合适大小的块，它会优先在段落、句子等自然边界处分割，保持文本语义完整性。
    recursive_text_splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=Settings.kn_settings.CHUNK_SIZE, # 分块大小
        chunk_overlap=Settings.kn_settings.OVERLAP_SIZE, # 分块重叠大小
        # length_function=len, # 文本长度计算函数
        add_start_index=True,  # 原始文档中每个块的起始位置
        separators=["\n\n", "\n", " ", ""]  # 分隔符优先级列表
    )
    
    # HTMLHeaderTextSplitter可以根据HTML的标题结构（h1-h6）来智能地分割文档内容，同时保留标题和内容的层次关系。
    html_text_splitter = HTMLHeaderTextSplitter(
        headers_to_split_on=Settings.kn_settings.TEXT_SPLITTER.get("HTMLHeaderTextSplitter")
        .get("headers_to_split_on", ["h1", "h2", "h3", "h4", "h5", "h6"])
    )
    # MarkdownHeaderTextSplitter可以根据Markdown的标题结构（#、##、###等）来智能地分割文档内容，同时保留标题和内容的层次关系。
    markdown_text_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=Settings.kn_settings.TEXT_SPLITTER.get("MarkdownHeaderTextSplitter")
        .get("headers_to_split_on", ["# ", "## ", "### ", "#### ", "##### ", "######"])
    )
    
    def __init__(
        self,
        kn_name: str | None = None,
        kn_info: str | None = None,
        embed_model: str = get_default_embedding(),
    ):
        self.kn_name = kn_name or Settings.kn_settings.DEFAULT_KNOWLEDGE_NAME
        self.kn_info = kn_info or Settings.kn_settings.KN_INFO.get(kn_name, f"关于{kn_name}的知识库")
        self.embed_model = embed_model
        self.embeddings = ModelFactory.get_embeddings(self.embed_model)
        # 语义文本分割器, 使用嵌入模型进行文本分割
        self.semantic_text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=30,  # 差异值，百分之五十
            number_of_chunks=None
        )
        self.kn_path = get_kn_path(self.kn_name)
        self.doc_path = get_doc_path(self.kn_name)
        self.do_init()
        
    
    def __repr__(self) -> str:
        return f"{self.kn_name} @ {self.embed_model}"
    
    def do_init(self) -> None:
        pass

    def init_vector_store(self):
        """
        初始化向量库
        """
        raise NotImplementedError("Subclasses should implement this method.")
    
    @abstractmethod
    def save_vector_store(self, docs: list[Document]) -> list[str]:
        """
        保存向量库:FAISS保存到磁盘，milvus,PGVector,ES保存到数据库。
        """
        pass
    
    @abstractmethod
    def get_vector_store(self) -> Any:
        """
        获取向量库
        """
        pass
    
    @abstractmethod
    def get_vector_store_retriever(
        self,
        top_k: int,
        score_threshold: int | float,
        ) -> Any:
        """
        获取向量库检索器 VectorStoreRetriever
        """
        pass
    
    def split_document(self, 
                      documents: list[Document],
                      enable_filter: bool = False,) -> list[Document]:
        """
        递归文本分割器
        """
        if enable_filter:
            # 根据文档嵌入后相似度进行冗余内容的过滤，相似度超过0.8，则会去掉
            docFilter = EmbeddingsRedundantFilter(
                embeddings=self.embeddings, 
                similarity_threshold=0.8)
            documents = list(docFilter.transform_documents(documents))

        docs = self.recursive_text_splitter.split_documents(documents)

        return docs

    def check_embed_model(self) -> tuple[bool, str]:
        return ModelFactory.check_embed_model(self.embed_model)
    
    
class VsServiceFactory:
    @staticmethod
    def get_service(
        vector_store_type: Union[str, SupportedVSType],
        embed_model: str = get_default_embedding(),
        kn_name: str = None,
        kn_info: str = None,
    ) -> VsService:
        if isinstance(vector_store_type, str):
            vector_store_type = getattr(SupportedVSType, vector_store_type.upper())
        
        params = {
            "embed_model": embed_model,
            "kn_name": kn_name,
            "kn_info": kn_info,
        }
        
        if SupportedVSType.PG == vector_store_type:
            from app.rag.vector_store.vs_pg_service import (
                VsPGService,
            )

            return VsPGService(**params)
        elif SupportedVSType.RELYT == vector_store_type:
            from app.rag.vector_store.vs_relyt_service import (
                VsRelytService,
            )

            return VsRelytService(**params)
        # elif SupportedVSType.ES == vector_store_type:
        #     from app.rag.vector_store.vs_es_service import (
        #         VsESService,
        #     )

        #     return VsESService(**params)
        else:  
            from app.rag.vector_store.vs_relyt_service import (
                VsRelytService,
            )

            return VsRelytService(**params)

    # @staticmethod
    # def get_service_by_name(kn_name: str) -> VsService:
    #     _, vs_type, embed_model = load_kn_from_db(kn_name)
    #     if _ is None:  # kb not in db, just return None
    #         return None
    #     return VsServiceFactory.get_service(kn_name, vs_type, embed_model)

    @staticmethod
    def get_default():
        return VsServiceFactory.get_service(SupportedVSType.PG, get_default_embedding())

