
import typing as t
#from typing import Literal, Any

from urllib.parse import urlparse

from langchain.tools import BaseTool
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import DashScopeEmbeddings

from config.settings import Settings,PlatformConfig
from utils.log_util import build_logger


logger = build_logger("llm-util")

"""获取默认聊天模型配置"""
def get_default_llm():
    available_llms = list(get_config_models(model_type="llm").keys())
    if not available_llms:
        raise ValueError("No available llm models found in configuration.")
    if Settings.model_settings.DEFAULT_LLM_MODEL in available_llms:
        return Settings.model_settings.DEFAULT_LLM_MODEL
    else:
        logger.warning(f"default llm model {Settings.model_settings.DEFAULT_LLM_MODEL} is not found in available llms, "
                       f"using {available_llms[0]} instead")
        return available_llms[0]

"""获取默认嵌入模型配置"""
def get_default_embedding():
    available_embeddings = list(get_config_models(model_type="embed").keys())
    if not available_embeddings:
        raise ValueError("No available embedding models found in configuration.")
    if Settings.model_settings.DEFAULT_EMBEDDING_MODEL in available_embeddings:
        return Settings.model_settings.DEFAULT_EMBEDDING_MODEL
    else:
        logger.warning(f"default embedding model {Settings.model_settings.DEFAULT_EMBEDDING_MODEL} is not found in "
                       f"available embeddings, using {available_embeddings[0]} instead")
        return available_embeddings[0]

   

"""获取模型配置信息"""
def get_model_info(
        model_name: str,
        platform_type: str = None,
        multiple: bool = False
) -> t.Any:
    """
    获取配置的模型信息，主要是 api_base_url, api_key
    如果指定 multiple=True, 则返回所有重名模型；否则仅返回第一个
    """
    result = get_config_models(model_name=model_name, platform_type=platform_type)
    if result:
        if multiple:
            return list(result.values())
        else:
            return list(result.values())[0]
    return None

"""获取模型配置"""
def get_config_models(
        model_name: str = None,
        model_type: t.Optional[t.Literal[
            "llm", "embed", "rerank", "text2image", "image2image", "image2text", "speech2text", "text2speech"
        ]] = None,
        platform_type: str = None,
) -> dict[str, dict[str, t.Any]]:
    """
    获取配置的模型列表，返回值为:
    {model_name: {
        "platform_name": xx,
        "platform_type": xx,
        "model_type": xx,
        "model_name": xx,
        "api_base_url": xx,
        "api_key": xx,
        "api_proxy": xx,
    }}
    """
    result = {}
    if model_type is None:
        model_types = [
            "llm_models",
            "embed_models",
            "rerank_models",
            "text2image_models",
            "image2image_models",
            "image2text_models",
            "speech2text_models",
            "text2speech_models",
        ]
    else:
        model_types = [f"{model_type}_models"]

    for m in list(get_config_platforms().values()):
        if platform_type is not None and platform_type != m.get("platform_type"):
            continue

        if m.get("auto_detect_model"):
            # TODO：通过api请求，自动检测模型
            platform_url = get_base_url(m.get("api_base_url"))
            platform_models = detect_models(platform_url)
            if not platform_models:
                logger.warning(f"no models detected for platform {m.get('platform_type')}, using default models")
            else:
                logger.info(f"detected models for platform {m.get('platform_type')}: {platform_models}")
                for m_type in model_types:
                    if m.get(m_type) != "auto":
                        continue
                    m[m_type] = platform_models.get(m_type, [])

        for m_type in model_types:
            models = m.get(m_type, [])
            if models == "auto":
                logger.warning("you should not set `auto` without auto_detect_model=True")
                continue
            elif not models:
                continue
            for m_name in models:
                if model_name is None or model_name == m_name:
                    result[m_name] = {
                        "platform_name": m.get("platform_name"),
                        "platform_type": m.get("platform_type"),
                        "model_type": m_type.split("_")[0],
                        "model_name": m_name,
                        "api_base_url": m.get("api_base_url", ""),
                        "api_key": m.get("api_key", ""),
                        "api_proxy": m.get("api_proxy"),
                    }
    return result


"""
获取配置的模型平台，会将 pydantic model 转换为字典。
"""
def get_config_platforms() -> dict[str, dict[str, t.Any]]:
    platforms = [m.model_dump() for m in Settings.model_settings.MODEL_PLATFORMS]
    return {m["platform_type"]: m for m in platforms}

"""获取指定平台的配置"""
def get_platform_config(platform_type: str) -> PlatformConfig | None:
    platform_config = [x for x in Settings.model_settings.MODEL_PLATFORMS if x.platform_type == platform_type]
    return platform_config[0] if platform_config else None
    
"""获取模型请求的基础 URL"""
def get_base_url(url: t.Optional[str]) -> str:
    if not url:
        return ""
    parsed_url = urlparse(url)  # 解析url
    base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_url)  # 格式化基础url
    return base_url.rstrip('/')

def api_address(is_public: bool = False) -> str:
    '''
    允许用户在 basic_settings.API_SERVER 中配置 public_host, public_port
    以便使用云服务器或反向代理时生成正确的公网 API 地址（如知识库文档下载链接）
    '''

    server = Settings.basic_settings.API_SERVER
    if is_public:
        host = server.get("public_host", "127.0.0.1")
        port = server.get("public_port", "7861")
    else:
        host = server.get("host", "127.0.0.1")
        port = server.get("port", "7861")
        if host == "0.0.0.0":
            host = "127.0.0.1"
    return f"http://{host}:{port}"

"""检测模型平台的模型"""
def detect_models(detect_url: str) -> dict[str, t.Any]:
    # This is a placeholder implementation.
    # You should replace this with actual logic to detect models from Model Platform.
    logger.warning("`detect_models` is not implemented yet. Returning empty model list.")
    return {}


   
if __name__ == "__main__":
    # Example usage
    print(get_default_llm())
    print(get_default_embedding())
    print(get_model_info(model_name="deepseek-chat"))
    print(get_config_models(model_type="llm"))
    print(get_base_url("https://api.deepseek.com/v1"))
    print(api_address(is_public=True))
    