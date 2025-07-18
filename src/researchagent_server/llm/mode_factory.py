import os
from sysconfig import get_platform
import time

from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.callbacks import Callbacks

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from utils.log_util import build_logger
from config.settings import PlatformConfig, Settings


logger = build_logger("model-factory")

class ModelFactory:
    
    @classmethod
    def get_model(
        cls,
        model_provider: str,
        model_name: str, 
        streaming: bool = False,
        callbacks = None
    ):
        
        # 从.env文件加载环境变量
        # load_dotenv()

        # 模型平台配置
        platform_config = cls.get_platform_config(model_provider)
        if not platform_config:
            raise ValueError(f"Unsupported model provider: {model_provider}")
        if model_name not in platform_config.llm_models:
            raise ValueError(f"Unsupported model name: {model_name}")

        if model_provider == "openai":
            chat_model = ChatOpenAI(
                    api_key=SecretStr(platform_config.api_key),
                    base_url=platform_config.api_base_url,
                    model=model_name,
                    streaming=streaming,
                    temperature=0,
                    callbacks=callbacks,
                    )
            return chat_model
        if model_provider == "genai":
            # return init_chat_model(model_name, model_provider=model_provider)
            chat_model = ChatGoogleGenerativeAI(
                    api_key=SecretStr(platform_config.api_key),
                    model=model_name,
                    streaming=streaming,
                    temperature=0,
                    max_tokens=None,
                    timeout=30,
                    max_retries=2,
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
                    api_key=SecretStr(platform_config.api_key),
                    model=model_name,
                    streaming=streaming,
                    temperature=0.6, # 随机性：0.0（最确定）–1.0（最随机）
                    max_tokens=1024, # 最多返回多少 token
                    max_retries=2,
                    # api_key=SecretStr(api_key),
                    # api_base=api_base,
                    callbacks=callbacks,
            )
            return chat_model
        else:
            raise ValueError(f"Unsupported model provider: {model_provider}")


    @classmethod
    def get_platform_config(cls, platform_type: str) -> PlatformConfig | None:
        platform_config = [x for x in Settings.model_settings.MODEL_PLATFORMS if x.platform_type == platform_type]
        return platform_config[0] if platform_config else None