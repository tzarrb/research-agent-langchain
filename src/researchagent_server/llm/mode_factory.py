import os
import time

from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.callbacks import Callbacks

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

class ModelFactory:
    
    @staticmethod
    def get_model(
        model_provider: str,
        model_name: str, 
        streaming: bool = False,
        callbacks = None
    ):
        
        # 从.env文件加载环境变量
        load_dotenv()
        
        if model_provider == "openai":
            chat_model = ChatOpenAI(
                    # api_key="...",
                    # base_url="...",
                    model=model_name,
                    streaming=streaming,
                    temperature=0,
                    callbacks=callbacks,
                    )
            return chat_model
        if model_provider == "genai":
            # return init_chat_model(model_name, model_provider=model_provider)
            chat_model = ChatGoogleGenerativeAI(
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
            api_key  = os.getenv("DEEPSEEK_API_KEY")
            api_base = os.getenv("DEEPSEEK_API_BASE")
            if not api_key or not api_base:
                raise EnvironmentError("请在 .env 中设置 DEEPSEEK_API_KEY 和 DEEPSEEK_API_BASE")

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