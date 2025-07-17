from __future__ import annotations

import os
from pathlib import Path
import sys
import typing as t

import nltk

from researchagent_server import __version__
from .pydantic_settings import *


# 数据目录，必须通过环境变量设置。如未设置则自动使用当前目录。
CHATCHAT_ROOT = Path(os.environ.get("RESEARCHAGENT_LANGCHAIN_ROOT", ".")).resolve()
print(f"RESEARCHAGENT_LANGCHAIN_ROOT: {CHATCHAT_ROOT}")

XF_MODELS_TYPES = {
    "text2image": {"model_family": ["stable_diffusion"]},
    "image2image": {"model_family": ["stable_diffusion"]},
    "speech2text": {"model_family": ["whisper"]},
    "text2speech": {"model_family": ["ChatTTS"]},
}


class BasicSettings(BaseFileSettings):
    """
    服务器基本配置信息
    除 log_verbose/HTTPX_DEFAULT_TIMEOUT 修改后即时生效
    其它配置项修改后都需要重启服务器才能生效，服务运行期间请勿修改
    """

    model_config = SettingsConfigDict(yaml_file=CHATCHAT_ROOT / "basic_settings.yaml")

    version: str = __version__
    """生成该配置模板的项目代码版本，如这里的值与程序实际版本不一致，建议重建配置文件模板"""

    log_verbose: bool = False
    """是否开启日志详细信息"""

    HTTPX_DEFAULT_TIMEOUT: float = 300
    """httpx 请求默认超时时间（秒）。如果加载模型或对话较慢，出现超时错误，可以适当加大该值。"""

    # @computed_field
    @cached_property
    def PACKAGE_ROOT(self) -> Path:
        """代码根目录"""
        return Path(__file__).parent

    # @computed_field
    @cached_property
    def DATA_PATH(self) -> Path:
        """用户数据根目录"""
        p = CHATCHAT_ROOT / "data"
        return p

    # @computed_field
    @cached_property
    def IMG_DIR(self) -> Path:
        """项目相关图片目录"""
        p = self.PACKAGE_ROOT / "img"
        return p

    # @computed_field
    @cached_property
    def NLTK_DATA_PATH(self) -> Path:
        """nltk 模型存储路径"""
        p = self.PACKAGE_ROOT / "data/nltk_data"
        return p

    # @computed_field
    @cached_property
    def LOG_PATH(self) -> Path:
        """日志存储路径"""
        p = self.DATA_PATH / "logs"
        return p

    # @computed_field
    @cached_property
    def MEDIA_PATH(self) -> Path:
        """模型生成内容（图片、视频、音频等）保存位置"""
        p = self.DATA_PATH / "media"
        return p

    # @computed_field
    @cached_property
    def BASE_TEMP_DIR(self) -> Path:
        """临时文件目录，主要用于文件对话"""
        p = self.DATA_PATH / "temp"
        (p / "openai_files").mkdir(parents=True, exist_ok=True)
        return p

    KB_ROOT_PATH: str = str(CHATCHAT_ROOT / "data/knowledge_base")
    """知识库默认存储路径"""

    DB_ROOT_PATH: str = str(CHATCHAT_ROOT / "data/knowledge_base/info.db")
    """数据库默认存储路径。如果使用sqlite，可以直接修改DB_ROOT_PATH；如果使用其它数据库，请直接修改SQLALCHEMY_DATABASE_URI。"""

    SQLALCHEMY_DATABASE_URI:str = "sqlite:///" + str(CHATCHAT_ROOT / "data/knowledge_base/info.db")
    """知识库信息数据库连接URI"""

    OPEN_CROSS_DOMAIN: bool = False
    """API 是否开启跨域"""

    DEFAULT_BIND_HOST: str = "0.0.0.0" if sys.platform != "win32" else "127.0.0.1"
    """
    各服务器默认绑定host。如改为"0.0.0.0"需要修改下方所有XX_SERVER的host
    Windows 下 WEBUI 自动弹出浏览器时，如果地址为 "0.0.0.0" 是无法访问的，需要手动修改地址栏
    """

    API_SERVER: dict = {"host": DEFAULT_BIND_HOST, "port": 7861, "public_host": "127.0.0.1", "public_port": 7861}
    """API 服务器地址。其中 public_host 用于生成云服务公网访问链接（如知识库文档链接）"""

    WEBUI_SERVER: dict = {"host": DEFAULT_BIND_HOST, "port": 8501}
    """WEBUI 服务器地址"""

    def make_dirs(self):
        '''创建所有数据目录'''
        for p in [
            self.DATA_PATH,
            self.MEDIA_PATH,
            self.LOG_PATH,
            self.BASE_TEMP_DIR,
        ]:
            p.mkdir(parents=True, exist_ok=True)
        for n in ["image", "audio", "video"]:
            (self.MEDIA_PATH / n).mkdir(parents=True, exist_ok=True)
        Path(self.KB_ROOT_PATH).mkdir(parents=True, exist_ok=True)
