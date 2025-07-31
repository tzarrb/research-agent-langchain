from typing import Any


import os
from sysconfig import get_platform
import time

from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.callbacks import Callbacks
from langchain_core.embeddings import Embeddings
from langchain_community.llms.tongyi import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

#import utils.llm_util
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.llm_util import (
    get_model_info,
    get_default_embedding,
    get_default_llm,
    api_address
)

logger = build_logger("model-factory")

class ModelFactory:
    
    """
    获取聊天模型
    """
    @classmethod
    def get_model(
        cls,
        model_provider: str | None = None,
        model_name: str | None = None, 
        streaming: bool = False,
        callbacks = None
    ):
        
        # 从.env文件加载环境变量
        # load_dotenv()

        # 模型平台配置
        model_provider = model_provider or Settings.model_settings.DEFAULT_LLM_PLATFORM
        model_name = model_name or get_default_llm()
        model_info = get_model_info(model_name=model_name, platform_type=model_provider)
        if not model_info:
            raise ValueError(f"Unsupported model provider: {model_provider} or model name: {model_name}")

        llm_config = Settings.model_settings.LLM_MODEL_CONFIG.get("llm_model", {})
        if model_provider == "openai":
            chat_model = ChatOpenAI(
                    api_key=SecretStr(model_info.api_key),
                    base_url=model_info.api_base_url,
                    model=model_name,
                    streaming=streaming,
                    temperature=llm_config.get("temperature", 0.5),
                    callbacks=callbacks,
                    )
            return chat_model
        if model_provider == "gemini":
            # return init_chat_model(model_name, model_provider=model_provider)
            chat_model = ChatGoogleGenerativeAI(
                    api_key=SecretStr(model_info.api_key),
                    model=model_name,
                    streaming=streaming,
                    temperature=llm_config.get("temperature", 0.5),
                    max_tokens=llm_config.get("max_tokens", 4096),
                    max_retries=llm_config.get("max_retries", 2),
                    timeout=llm_config.get("timeout", 30),
                    callbacks=callbacks,
                )
            return chat_model
        elif model_provider == "deepseek":
            # api_key  = os.getenv("DEEPSEEK_API_KEY")
            # api_base = os.getenv("DEEPSEEK_API_BASE")
            # if not api_key or not api_base:
            #     raise EnvironmentError("请在 .env 中设置 DEEPSEEK_API_KEY 和 DEEPSEEK_API_BASE")

            # 2. 初始化 DeepSeek 聊天模型
            # chat_model = init_chat_model(
            #     model=model_name, # deepseek-chat
            #     temperature=0.6,     # 随机性：0.0（最确定）–1.0（最随机）
            #     max_tokens=1024,      # 最多返回多少 token
            #     max_retries=2,
            #     api_key=api_key,
            #     api_base=api_base
            # )
            chat_model = ChatDeepSeek(
                    api_key=SecretStr(model_info.api_key),
                    model=model_name,
                    streaming=streaming,
                    temperature=llm_config.get("temperature", 0.6), # 随机性：0.0（最确定）–1.0（最随机）
                    max_tokens=llm_config.get("max_tokens", 1024), # 最多返回多少 token
                    max_retries=llm_config.get("max_retries", 2),
                    timeout=llm_config.get("timeout", 30),
                    callbacks=callbacks,
            )
            return chat_model
        elif model_provider == "dashscope":
            chat_model = Tongyi(
                model=model_name,
                api_key=SecretStr(model_info.api_key),
                streaming=streaming,
                temperature=llm_config.get("temperature", 0.5),
                top_p=llm_config.get("top_p", 0.5),
                max_tokens=llm_config.get("max_tokens", 4096),
                max_retries=llm_config.get("max_retries", 2),
                timeout=llm_config.get("timeout", 30),
                callbacks=callbacks,
            )
        else:
            raise ValueError(f"Unsupported model provider: {model_provider}")


    """
    获取嵌入模型
    """
    @classmethod
    def get_embeddings(
        cls, 
        embed_model: str = "",
        local_wrap: bool = False,  # use local wrapped api
    ) -> Embeddings:
        from langchain_community.embeddings import OllamaEmbeddings
        from langchain_openai import OpenAIEmbeddings

        embed_model = embed_model or get_default_embedding()
        model_info = get_model_info(model_name=embed_model)
        if not model_info:
            raise ValueError(f"Embed Model {embed_model} not found in configuration.")

        try:
            platform_type = model_info.get("platform_type")
            api_key = model_info.get("api_key")
            api_base_url = model_info.get("api_base_url")
            
            if platform_type == "dashscope":
                if not api_key:
                    raise ValueError("Dashscope API key is not provided.")
                return DashScopeEmbeddings(model=embed_model, dashscope_api_key=api_key)
            elif platform_type == "ollama":
                if not api_base_url:
                    raise ValueError("Ollama API base URL is not provided.")
                return OllamaEmbeddings(base_url=api_base_url.replace("/v1", ""), model=embed_model)
            else:
                # For other platforms, including OpenAI-compatible ones
                kwargs = {}
                if openai_api_base := api_base_url:
                    kwargs["openai_api_base"] = openai_api_base
                if openai_api_key := api_key:
                    kwargs["openai_api_key"] = openai_api_key
                if openai_proxy := model_info.get("api_proxy"):
                    kwargs["openai_proxy"] = openai_proxy

                if local_wrap:
                    kwargs["openai_api_base"] = f"{api_address()}/v1"
                    kwargs["openai_api_key"] = "EMPTY"

                return OpenAIEmbeddings(
                    model=embed_model,
                    **kwargs,
                )
        except Exception as e:
            logger.exception(f"failed to create Embeddings for model: {embed_model}.")
            raise e
    

    '''
    check weather embed_model accessable, use default embed model if None
    '''
    @classmethod
    def check_embed_model(cls, embed_model: str = "") -> tuple[bool, str]:
        try:
            embed_model = embed_model or get_default_embedding()
            embeddings = cls.get_embeddings(cls, embed_model=embed_model)
            if embeddings is None:
                return False, f"Failed to create Embeddings for model: {embed_model}."
            embeddings.embed_query("this is a test")
            return True, ""
        except Exception as e:
            msg = f"failed to access embed model '{embed_model}': {e}"
            logger.error(msg)
            return False, msg
   