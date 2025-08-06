from __future__ import annotations

import os
import sys
import typing as t
from pathlib import Path

import nltk

from pydantic import field_validator
from .pydantic_settings import BaseFileSettings, SettingsConfigDict, settings_property, MyBaseModel, cached_property

from agent_server import __version__


# 数据目录，必须通过环境变量设置。如未设置则自动使用当前目录。
ROOT = Path(os.environ.get("RESEARCHAGENT_LANGCHAIN_ROOT", ".")).resolve()
AGENT_ROOT = Path(os.environ.get("RESEARCHAGENT_LANGCHAIN_AGENT_ROOT", "./src/agent_server/")).resolve()
print(f"ROOT: {AGENT_ROOT}, AGENT_ROOT: {AGENT_ROOT}")


class BasicSettings(BaseFileSettings):
    """
    服务器基本配置信息
    除 log_verbose/HTTPX_DEFAULT_TIMEOUT 修改后即时生效
    其它配置项修改后都需要重启服务器才能生效，服务运行期间请勿修改
    """

    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/basic_settings.yaml")

    version: str = __version__
    """生成该配置模板的项目代码版本，如这里的值与程序实际版本不一致，建议重建配置文件模板"""

    log_verbose: bool = False
    """是否开启日志详细信息"""

    HTTPX_DEFAULT_TIMEOUT: float = 300
    """httpx 请求默认超时时间（秒）。如果加载模型或对话较慢，出现超时错误，可以适当加大该值。"""

    # redis 配置
    REDIS_URL: str = "redis://localhost:6379/0" # 密码redis://:123456@localhost:6379/0
    # Redis 前缀
    REDIS_PREFIX: str = "researchagent-lang:"
    # Redis 前缀 - 会话消息存储
    REDIS_PREFIX_CHAT_MEMORY: str = REDIS_PREFIX + "chat:memory:"

    # 使用 @computed_field，可以在模型内部根据其他字段动态生成新字段
    # 这比在模型外部手动拼接字符串要优雅得多。
    # @computed_field
    @cached_property
    def CONFIG_ROOT(self) -> Path:
        """配置文件目录"""
        p = Path(__file__).parent
        return p

    # @computed_field
    @cached_property
    def DOC_PATH(self) -> Path:
        """服务文档根目录"""
        p = AGENT_ROOT / "docs"
        return p

    # @computed_field
    @cached_property
    def IMG_DIR(self) -> Path:
        """项目相关图片目录"""
        p = self.DOC_PATH / "image"
        return p

    # @computed_field
    @cached_property
    def DATA_PATH(self) -> Path:
        """用户数据根目录"""
        p = AGENT_ROOT / "data"
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
    def NLTK_DATA_PATH(self) -> Path:
        """nltk 模型存储路径"""
        p = self.DATA_PATH / "nltk"
        return p

    # @computed_field
    @cached_property
    def TEMP_PATH(self) -> Path:
        """临时文件目录，主要用于文件对话"""
        p = self.DATA_PATH / "temp"
        (p / "files").mkdir(parents=True, exist_ok=True)
        (p / "openai_files").mkdir(parents=True, exist_ok=True)
        return p
    
    @cached_property
    def TEMP_FILE_PATH(self) -> Path:
        """临时文件目录"""
        p = self.TEMP_PATH / "files"
        p.mkdir(parents=True, exist_ok=True)
        return p

    KN_ROOT_PATH: str = str(AGENT_ROOT / "data/knowledge")
    """知识库默认存储路径"""

    DB_ROOT_PATH: str = str(AGENT_ROOT / "data/knowledge/info.db")
    """数据库默认存储路径。如果使用sqlite，可以直接修改DB_ROOT_PATH；如果使用其它数据库，请直接修改SQLALCHEMY_DATABASE_URI。"""

    OPEN_CROSS_DOMAIN: bool = True
    """API 是否开启跨域"""

    DEFAULT_BIND_HOST: str = "0.0.0.0" if sys.platform != "win32" else "127.0.0.1"
    """
    各服务器默认绑定host。如改为"0.0.0.0"需要修改下方所有XX_SERVER的host
    Windows 下 WEBUI 自动弹出浏览器时，如果地址为 "0.0.0.0" 是无法访问的，需要手动修改地址栏
    """

    API_SERVER: dict[str, t.Any] = {"host": DEFAULT_BIND_HOST, "port": 18081, "public_host": "127.0.0.1", "public_port": 18081}
    """API 服务器地址。其中 public_host 用于生成云服务公网访问链接（如知识库文档链接）"""

    WEBUI_SERVER: dict[str, t.Any] = {"host": DEFAULT_BIND_HOST, "port": 18082}
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
        Path(self.KN_ROOT_PATH).mkdir(parents=True, exist_ok=True)


class PlatformConfig(MyBaseModel):
    """模型加载平台配置"""

    platform_name: str = "deepseek"
    """平台名称"""

    platform_type: t.Literal["deepseek", "openai", "gemini", "ollama", "openrouter", "dashscope", "oneapi"] = "deepseek"
    """平台类型"""

    api_base_url: str = "https://api.deepseek.com/v1"
    """openai api url"""

    api_key: str = ""
    """api key if available"""

    api_proxy: str = ""
    """API 代理"""

    api_concurrencies: int = 5
    """该平台单模型最大并发数"""

    auto_detect_model: bool = False
    """是否自动获取平台可用模型列表。设为 True 时下方不同模型类型可自动检测"""

    llm_models: t.Literal["auto"] | list[str] = []
    """该平台支持的大语言模型列表，auto_detect_model 设为 True 时自动检测"""

    embed_models: t.Literal["auto"] | list[str] = []
    """该平台支持的嵌入模型列表，auto_detect_model 设为 True 时自动检测"""

    text2image_models: t.Literal["auto"] | list[str] = []
    """该平台支持的图像生成模型列表，auto_detect_model 设为 True 时自动检测"""

    image2text_models: t.Literal["auto"] | list[str] = []
    """该平台支持的多模态模型列表，auto_detect_model 设为 True 时自动检测"""

    rerank_models: t.Literal["auto"] | list[str] = []
    """该平台支持的重排模型列表，auto_detect_model 设为 True 时自动检测"""

    speech2text_models: t.Literal["auto"] | list[str] = []
    """该平台支持的 STT 模型列表，auto_detect_model 设为 True 时自动检测"""

    text2speech_models: t.Literal["auto"] | list[str] = []
    """该平台支持的 TTS 模型列表，auto_detect_model 设为 True 时自动检测"""

    # @field_validator("api_key")
    # def validate_api_key(cls, v):
    #     if not v or v == "":
    #         raise ValueError("API key不能为空")
    #     return v
 
 
class ModelSettings(BaseFileSettings):
    """模型配置项"""

    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/model_settings.yaml")

    DEFAULT_LLM_PLATFORM: str = "deepseek"
    """默认 LLM 平台"""

    DEFAULT_LLM_MODEL: str = "deepseek-chat"
    """默认选用的 LLM 名称"""

    DEFAULT_EMBEDDING_MODEL: str = "bge-m3"
    """默认选用的 Embedding 名称"""

    HISTORY_LEN: int = 3
    """默认历史对话轮数"""

    MAX_TOKENS: int | None = None 
    """大模型最长支持的长度，如果不填写，则使用模型默认的最大长度，如果填写，则为用户设定的最大长度"""

    TEMPERATURE: float = 0.7
    """LLM通用对话参数"""

    SUPPORT_AGENT_MODELS: list[str] = [
            "deepseek-chat",
            "qwen-max",
            "gpt-4o",
        ]
    """支持的Agent模型"""

    LLM_MODEL_CONFIG: dict[str, dict[str, t.Any]] = {
            # 意图识别不需要输出，模型后台知道就行
            "preprocess_model": {
                "model": "",
                "temperature": 0.05,
                "max_tokens": 4096,
                "history_len": 10,
                "prompt_name": "default",
                "callbacks": False,
            },
            "llm_model": {
                "platform":"",
                "model": "",
                "temperature": 0.9,  # 随机性：0.0（最确定）–1.0（最随机）
                "max_tokens": 4096,
                "history_len": 10,
                "prompt_name": "default",
                "callbacks": True,
            },
            "action_model": {
                "model": "",
                "temperature": 0.01,
                "max_tokens": 4096,
                "history_len": 10,
                "prompt_name": "ChatGLM3",
                "callbacks": True,
            },
            "postprocess_model": {
                "model": "",
                "temperature": 0.01,
                "max_tokens": 4096,
                "history_len": 10,
                "prompt_name": "default",
                "callbacks": True,
            },
            "image_model": {
                "model": "sd-turbo",
                "size": "256*256",
            },
            "embed_model": {
                "model": "",
                "batch_size": 32,
                "chunk_size": 1000,
                "chunk_overlap": 100,
                "max_retries": 3,
                "timeout": 30,
                "max_tokens": 4096,
                "temperature": 0.01,
                "history_len": 10,
                "prompt_name": "default",
                "callbacks": True,
            },
        }
    """
    LLM模型配置，包括了不同模态初始化参数。
    `model` 如果留空则自动使用 DEFAULT_LLM_MODEL
    """

    MODEL_PLATFORMS: list[PlatformConfig] = [
            PlatformConfig(
                platform_name="DeepSeek",
                platform_type="deepseek",
                api_base_url="https://api.deepseek.com/v1",
                api_key="EMPTY",
                api_concurrencies=5,
                auto_detect_model=True,
                llm_models=["deepseek-chat", "deepseek-reasoner"],
                embed_models=[],
                text2image_models=[],
                image2text_models=[],
                rerank_models=[],
                speech2text_models=[],
                text2speech_models=[],
            ),
            PlatformConfig(
                platform_name="OLLama",
                platform_type="ollama",
                api_base_url="http://127.0.0.1:11434/v1",
                api_key="EMPTY",
                api_proxy="",
                api_concurrencies=5,
                auto_detect_model=False,
                llm_models=[
                    "qwen:7b",
                    "qwen2:7b",
                ],
                embed_models=[
                    "quentinz/bge-large-zh-v1.5",
                ],
                text2image_models=[],
                image2text_models=[],
                rerank_models=[],
                speech2text_models=[],
                text2speech_models=[],
            ),
            PlatformConfig(
                platform_name="OneApi",
                platform_type="oneapi",  
                api_base_url="http://127.0.0.1:3000/v1",
                api_key="sk-",
                api_proxy="",
                api_concurrencies=5,
                auto_detect_model=False,
                llm_models=[
                    # 智谱 API
                    "chatglm_pro",
                    "chatglm_turbo",
                    "chatglm_std",
                    "chatglm_lite",
                    # 千问 API
                    "qwen-turbo",
                    "qwen-plus",
                    "qwen-max",
                    "qwen-max-longcontext",
                    # 千帆 API
                    "ERNIE-Bot",
                    "ERNIE-Bot-turbo",
                    "ERNIE-Bot-4",
                    # 星火 API
                    "SparkDesk",
                ],
                embed_models=[
                    # 千问 API
                    "text-embedding-v1",
                    # 千帆 API
                    "Embedding-V1",
                ],
                text2image_models=[],
                image2text_models=[],
                rerank_models=[],
                speech2text_models=[],
                text2speech_models=[],
            ),
            PlatformConfig(
                platform_name="OpenAI",
                platform_type="openai",
                api_base_url="https://api.openai.com/v1",
                api_key="sk-proj-",
                api_proxy="",
                api_concurrencies=5,
                auto_detect_model=False,
                llm_models=[
                    "gpt-4o",
                    "gpt-4.1",
                ],
                embed_models=[
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                ],
                text2image_models=[],
                image2text_models=[],
                rerank_models=[],
                speech2text_models=[],
                text2speech_models=[],
            ),
        ]
    """模型平台配置"""

class ToolSettings(BaseFileSettings):
    """Agent 工具配置项"""
    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/tool_settings.yaml",
                                      json_file=AGENT_ROOT / "config/tool_settings.json",
                                      extra="allow")

    search_local_knowledgebase: dict[str, t.Any] = {
        "use": False,
        "top_k": 3,
        "score_threshold": 2.0,
        "conclude_prompt": {
            "with_result": '<指令>根据已知信息，简洁和专业的来回答问题。如果无法从中得到答案，请说 "根据已知信息无法回答该问题"，'
            "不允许在答案中添加编造成分，答案请使用中文。 </指令>\n"
            "<已知信息>{{ context }}</已知信息>\n"
            "<问题>{{ question }}</问题>\n",
            "without_result": "请你根据我的提问回答我的问题:\n"
            "{{ question }}\n"
            "请注意，你必须在回答结束后强调，你的回答是根据你的经验回答而不是参考资料回答的。\n",
        },
    }
    '''本地知识库工具配置项'''

    search_internet: dict[str, t.Any] = {
        "use": False,
        "search_engine_name": "duckduckgo",
        "search_engine_config": {
            "bing": {
                "bing_search_url": "https://api.bing.microsoft.com/v7.0/search",
                "bing_key": "",
            },
            "metaphor": {
                "metaphor_api_key": "",
                "split_result": False,
                "chunk_size": 500,
                "chunk_overlap": 0,
            },
            "duckduckgo": {},
            "searx": {
                "host": "https://metasearx.com",
                "engines": [],
                "categories": [],
                "language": "zh-CN",
            }
        },
        "top_k": 5,
        "verbose": "Origin",
        "conclude_prompt": "<指令>这是搜索到的互联网信息，请你根据这些信息进行提取并有调理，简洁的回答问题。如果无法从中得到答案，请说 “无法搜索到能回答问题的内容”。 "
        "</指令>\n<已知信息>{{ context }}</已知信息>\n"
        "<问题>\n"
        "{{ question }}\n"
        "</问题>\n",
    }
    '''搜索引擎工具配置项。推荐自己部署 searx 搜索引擎，国内使用最方便。'''

    arxiv: dict[str, t.Any] = {
        "use": False,
    }

    weather_check: dict[str, t.Any] = {
        "use": False,
        "api_key": "",
    }
    '''心知天气（https://www.seniverse.com/）工具配置项'''

    search_youtube: dict[str, t.Any] = {
        "use": False,
    }

    wolfram: dict[str, t.Any] = {
        "use": False,
        "appid": "",
    }

    calculate: dict[str, t.Any] = {
        "use": False,
    }
    '''numexpr 数学计算工具配置项'''

    text2images: dict[str, t.Any] = {
        "use": False,
        "model": "sd-turbo",
        "size": "256*256",
    }
    '''图片生成工具配置项。model 必须是在 model_settings.yaml/MODEL_PLATFORMS 中配置过的。'''

    text2sql: dict[str, t.Any] = {
        # 该工具需单独指定使用的大模型，与用户前端选择使用的模型无关
        "model_name": "qwen-plus",
        "use": False,
        # SQLAlchemy连接字符串，支持的数据库有：
        # crate、duckdb、googlesql、mssql、mysql、mariadb、oracle、postgresql、sqlite、clickhouse、prestodb
        # 不同的数据库请查阅SQLAlchemy用法，修改sqlalchemy_connect_str，配置对应的数据库连接，如sqlite为sqlite:///数据库文件路径，下面示例为mysql
        # 如提示缺少对应数据库的驱动，请自行通过poetry安装
        "sqlalchemy_connect_str": "mysql+pymysql://用户名:密码@主机地址/数据库名称",
        # 务必评估是否需要开启read_only,开启后会对sql语句进行检查，请确认text2sql.py中的intercept_sql拦截器是否满足你使用的数据库只读要求
        # 优先推荐从数据库层面对用户权限进行限制
        "read_only": False,
        # 限定返回的行数
        "top_k": 50,
        # 是否返回中间步骤
        "return_intermediate_steps": True,
        # 如果想指定特定表，请填写表名称，如["sys_user","sys_dept"]，不填写走智能判断应该使用哪些表
        "table_names": [],
        # 对表名进行额外说明，辅助大模型更好的判断应该使用哪些表，尤其是SQLDatabaseSequentialChain模式下,是根据表名做的预测，很容易误判。
        "table_comments": {
            # 如果出现大模型选错表的情况，可尝试根据实际情况填写表名和说明
            # "tableA":"这是一个用户表，存储了用户的基本信息",
            # "tableB":"角色表",
        },
    }
    '''
    text2sql使用建议
    1、因大模型生成的sql可能与预期有偏差，请务必在测试环境中进行充分测试、评估；
    2、生产环境中，对于查询操作，由于不确定查询效率，推荐数据库采用主从数据库架构，让text2sql连接从数据库，防止可能的慢查询影响主业务；
    3、对于写操作应保持谨慎，如不需要写操作，设置read_only为True,最好再从数据库层面收回数据库用户的写权限，防止用户通过自然语言对数据库进行修改操作；
    4、text2sql与大模型在意图理解、sql转换等方面的能力有关，可切换不同大模型进行测试；
    5、数据库表名、字段名应与其实际作用保持一致、容易理解，且应对数据库表名、字段进行详细的备注说明，帮助大模型更好理解数据库结构；
    6、若现有数据库表名难于让大模型理解，可配置下面table_comments字段，补充说明某些表的作用。
    '''

    amap: dict[str, t.Any] = {
        "use": False,
        "api_key": "高德地图 API KEY",
    }
    '''高德地图、天气相关工具配置项。'''

    text2promql: dict[str, t.Any] = {
        "use": False,
        # <your_prometheus_ip>:<your_prometheus_port>
        "prometheus_endpoint": "http://127.0.0.1:9090",
        # <your_prometheus_username>
        "username": "",
        # <your_prometheus_password>
        "password": "",
    }
    '''
    text2promql 使用建议
    1、因大模型生成的 promql 可能与预期有偏差, 请务必在测试环境中进行充分测试、评估;
    2、text2promql 与大模型在意图理解、metric 选择、promql 转换等方面的能力有关, 可切换不同大模型进行测试;
    3、当前仅支持 单prometheus 查询, 后续考虑支持 多prometheus 查询.
    '''

    url_reader: dict[str, t.Any] = {
        "use": False,
        "timeout": "10000",
    }
    '''URL内容阅读（https://r.jina.ai/）工具配置项
    请确保部署的网络环境良好，以免造成超时等问题'''

class PromptSettings(BaseFileSettings):
    """Prompt 模板.除 Agent 模板使用 f-string 外，其它均使用 jinja2 格式"""

    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/prompt_settings.yaml",
                                      json_file=AGENT_ROOT / "config/prompt_settings.json",
                                      extra="allow")

    preprocess_model: dict[str, t.Any] = {
        "default": (
            "你只要回复0 和 1 ，代表不需要使用工具。以下几种问题不需要使用工具:\n"
            "1. 需要联网查询的内容\n"
            "2. 需要计算的内容\n"
            "3. 需要查询实时性的内容\n"
            "如果我的输入满足这几种情况，返回1。其他输入，请你回复0，你只要返回一个数字\n"
            "这是我的问题:"
            ),
    }
    """意图识别用模板"""

    llm_model: dict[str, t.Any] = {
        "default": "{{input}}",
        "with_history": (
            "The following is a friendly conversation between a human and an AI.\n"
            "The AI is talkative and provides lots of specific details from its context.\n"
            "If the AI does not know the answer to a question, it truthfully says it does not know.\n\n"
            "Current conversation:\n"
            "{{history}}\n"
            "Human: {{input}}\n"
            "AI:"
            ),
    }
    '''普通 LLM 用模板'''

    rag: dict[str, t.Any] = {
        "default": (
            "【指令】根据已知信息，简洁和专业的来回答问题。"
            "如果无法从中得到答案，请说 “根据已知信息无法回答该问题”，不允许在答案中添加编造成分，答案请使用中文。\n\n"
            "【已知信息】{{context}}\n\n"
            "【问题】{{question}}\n"
            ),
        "empty": (
            "请你回答我的问题:\n"
            "{{question}}"
        ),
    }
    '''RAG 用模板，可用于知识库问答、文件对话、搜索引擎对话'''

    action_model: dict[str, t.Any] = {
        "GPT-4": (
            "Answer the following questions as best you can. You have access to the following tools:\n"
            "The way you use the tools is by specifying a json blob.\n"
            "Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here).\n"
            'The only values that should be in the "action" field are: {tool_names}\n'
            "The $JSON_BLOB should only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:\n"
            "```\n\n"
            "{{{{\n"
            '  "action": $TOOL_NAME,\n'
            '  "action_input": $INPUT\n'
            "}}}}\n"
            "```\n\n"
            "ALWAYS use the following format:\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action:\n"
            "```\n\n"
            "$JSON_BLOB"
            "```\n\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n"
            "Begin! Reminder to always use the exact characters `Final Answer` when responding.\n"
            "Question:{input}\n"
            "Thought:{agent_scratchpad}\n"
            ),
        "ChatGLM3": (
            "You can answer using the tools.Respond to the human as helpfully and accurately as possible.\n"
            "You have access to the following tools:\n"
            "{tools}\n"
            "Use a json blob to specify a tool by providing an action key (tool name)\n"
            "and an action_input key (tool input).\n"
            'Valid "action" values: "Final Answer" or  [{tool_names}]\n'
            "Provide only ONE action per $JSON_BLOB, as shown:\n\n"
            "```\n"
            "{{{{\n"
            '  "action": $TOOL_NAME,\n'
            '  "action_input": $INPUT\n'
            "}}}}\n"
            "```\n\n"
            "Follow this format:\n\n"
            "Question: input question to answer\n"
            "Thought: consider previous and subsequent steps\n"
            "Action:\n"
            "```\n"
            "$JSON_BLOB\n"
            "```\n"
            "Observation: action result\n"
            "... (repeat Thought/Action/Observation N times)\n"
            "Thought: I know what to respond\n"
            "Action:\n"
            "```\n"
            "{{{{\n"
            '  "action": "Final Answer",\n'
            '  "action_input": "Final response to human"\n'
            "}}}}\n"
            "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary.\n"
            "Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation:.\n"
            "Question: {input}\n\n"
            "{agent_scratchpad}\n"
            ),
        "qwen": (
            "Answer the following questions as best you can. You have access to the following APIs:\n\n"
            "{tools}\n\n"
            "Use the following format:\n\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can be repeated zero or more times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Format the Action Input as a JSON object.\n\n"
            "Begin!\n\n"
            "Question: {input}\n\n"
            "{agent_scratchpad}\n\n"
            ),
        "structured-chat-agent": (
            "Respond to the human as helpfully and accurately as possible. You have access to the following tools:\n\n"
            "{tools}\n\n"
            "Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).\n\n"
            'Valid "action" values: "Final Answer" or {tool_names}\n\n'
            "Provide only ONE action per $JSON_BLOB, as shown:\n\n"
            '```\n{{\n  "action": $TOOL_NAME,\n  "action_input": $INPUT\n}}\n```\n\n'
            "Follow this format:\n\n"
            "Question: input question to answer\n"
            "Thought: consider previous and subsequent steps\n"
            "Action:\n```\n$JSON_BLOB\n```\n"
            "Observation: action result\n"
            "... (repeat Thought/Action/Observation N times)\n"
            "Thought: I know what to respond\n"
            'Action:\n```\n{{\n  "action": "Final Answer",\n  "action_input": "Final response to human"\n}}\n\n'
            "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation\n"
            "{input}\n\n"
            "{agent_scratchpad}\n\n"
            # '(reminder to respond in a JSON blob no matter what)')
            ),
    }
    """Agent 模板"""

    postprocess_model: dict[str, t.Any] = {
        "default": "{{input}}",
    }
    """后处理模板"""


class KNSettings(BaseFileSettings):
    """知识库相关配置"""

    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/kn_settings.yaml")

    DEFAULT_KNOWLEDGE_NAME: str = "samples"
    """默认使用的知识库"""

    DEFAULT_VS_TYPE: t.Literal["faiss", "milvus", "zilliz", "pg", "es", "relyt", "chromadb"] = "pg"
    """默认向量库/全文检索引擎类型"""

    CACHED_VS_NUM: int = 1
    """缓存向量库数量（针对FAISS）"""

    CACHED_MEMO_VS_NUM: int = 10
    """缓存临时向量库数量（针对FAISS），用于文件对话"""

    CHUNK_SIZE: int = 750
    """知识库中单段文本长度(不适用MarkdownHeaderTextSplitter)"""

    OVERLAP_SIZE: int = 150
    """知识库中相邻文本重合长度(不适用MarkdownHeaderTextSplitter)"""

    VECTOR_SEARCH_TOP_K: int = 3 # TODO: 与 tool 配置项重复
    """知识库匹配向量数量"""
    
    VECTOR_SEARCH_SCORE_THRESHOLD: float = 0.5
    """知识库匹配向量相关度阈值，取值范围在0-2之间，SCORE越小，相关度越高，取到2相当于不筛选，建议设置在0.5左右"""

    DEFAULT_SEARCH_ENGINE: t.Literal["bing", "baidu", "tavily"] = "tavily"
    """默认搜索引擎"""

    SEARCH_ENGINE_TOP_K: int = 3
    """搜索引擎匹配结果数量"""

    ZH_TITLE_ENHANCE: bool = False
    """是否开启中文标题加强，以及标题增强的相关配置"""

    PDF_OCR_THRESHOLD: tuple[float, float] = (0.6, 0.6)
    """
    PDF OCR 控制：只对宽高超过页面一定比例（图片宽/页面宽，图片高/页面高）的图片进行 OCR。
    这样可以避免 PDF 中一些小图片的干扰，提高非扫描版 PDF 处理速度
    """

    KN_INFO: dict[str, str] = {"samples": "关于本项目issue的解答"} # TODO: 都存在数据库了，这个配置项还有必要吗？
    """每个知识库的初始化介绍，用于在初始化知识库时显示和Agent调用，没写则没有介绍，不会被Agent调用。"""

    VS_CONFIG: dict[str, dict[str, t.Any]] = {
            "faiss": {},
            "milvus": {
                "host": "127.0.0.1",
                "port": "19530",
                "user": "",
                "password": "",
                "secure": False
            },
            "zilliz": {
                "host": "in01-a7ce524e41e3935.ali-cn-hangzhou.vectordb.zilliz.com.cn",
                "port": "19530",
                "user": "",
                "password": "",
                "secure": True
            },
            "pg": {
                "connection_uri": "postgresql://postgres:postgres@127.0.0.1:5432/researchagent"
            },
            "relyt": {
                "connection_uri": "postgresql+psycopg2://postgres:postgres@127.0.0.1:7000/researchagent"
            },
            "es": {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": "9200",
                "index_name": "vector-researchagent",
                "user": "",
                "password": "",
                "verify_certs": True,
                "ca_certs": None,
                "client_cert": None,
                "client_key": None
            },
            "milvus_kwargs": {
                "search_params": {
                    "metric_type": "L2"
                },
                "index_params": {
                    "metric_type": "L2",
                    "index_type": "HNSW"
                }
            },
            "chromadb": {}
        }
    """可选向量库类型及对应配置"""

    """
    # 可选的文本分割器配置
    # 目前支持的文本分割器有：ChineseRecursiveTextSplitter, SpacyTextSplitter, RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
    # 其中ChineseRecursiveTextSplitter使用了中文分词器，SpacyTextSplitter使用了Spacy分词器，
    # RecursiveCharacterTextSplitter使用了tiktoken分词器，MarkdownHeaderTextSplitter使用了Markdown标题分割器
    # TextSplitter配置项，如果你不明白其中的含义，就不要修改。
    # source 如果选择tiktoken则使用openai的方法 "huggingface"
    """
    TEXT_SPLITTER: dict[str, dict[str, t.Any]] = {
            "ChineseRecursiveTextSplitter": {
                "source": "",
                "tokenizer_name_or_path": "",
            },
            "SpacyTextSplitter": {
                "source": "huggingface",
                "tokenizer_name_or_path": "gpt2",
            },
            "RecursiveCharacterTextSplitter": {
                "source": "tiktoken",
                "tokenizer_name_or_path": "cl100k_base",
            },
            "MarkdownHeaderTextSplitter": {
                "headers_to_split_on": [
                    ("#", "head1"),
                    ("##", "head2"),
                    ("###", "head3"),
                    ("####", "head4"),
                ]
            },
            "HTMLHeaderTextSplitter": {
                "headers_to_split_on": [
                    ("h1", "Header 1"),
                    ("h2", "Header 2"),
                    ("h3", "Header 3"),
                ]
            },
        }

    TEXT_SPLITTER_NAME: str = "ChineseRecursiveTextSplitter"
    """TEXT_SPLITTER 名称"""

    EMBEDDING_KEYWORD_FILE: str = "embedding_keywords.txt"
    """Embedding模型定制词语的词表文件"""


class DBSettings(BaseFileSettings):
    """数据库相关配置"""
    
    model_config = SettingsConfigDict(yaml_file=AGENT_ROOT / "config/db_settings.yaml")
    
    # SQLALCHEMY_DATABASE_URI:str = "sqlite:///" + str(AGENT_ROOT / "data/knowledge/info.db")
    SQLALCHEMY_DATABASE_URI:str = "postgresql+asyncpg://root:123456@127.0.0.1:5433/researchagent"
    """知识库信息数据库连接URI"""

    POOL_SIZE: int = 10
    """数据库连接池大小"""
    
    MAX_OVERFLOW: int = 5
    """数据库连接池最大溢出数"""
    
    POOL_TIMEOUT: int = 30
    """数据库连接池超时时间，单位秒"""
    
    POOL_RECYCLE: int = 1800
    """数据库连接池回收时间，单位秒"""
    
    ECHO: bool = False
    """是否打印SQL语句"""


class SettingsContainer:
    basic_settings: BasicSettings = settings_property(BasicSettings())
    model_settings: ModelSettings = settings_property(ModelSettings())
    tool_settings: ToolSettings = settings_property(ToolSettings())
    prompt_settings: PromptSettings = settings_property(PromptSettings())
    kn_settings: KNSettings = settings_property(KNSettings())
    db_settings: DBSettings = settings_property(DBSettings())

    # sub_comments={"MODEL_PLATFORMS": {"model_obj": PlatformConfig(), "is_entire_comment": True}}
    def create_all_templates(self):
        self.basic_settings.create_template_file(write_file=True, file_format="yaml", model_obj=BasicSettings())
        self.model_settings.create_template_file(write_file=True, file_format="yaml", model_obj=ModelSettings(),
                                                 sub_comments={"MODEL_PLATFORMS": {"model_obj": PlatformConfig(), "is_entire_comment": True}})
        self.tool_settings.create_template_file(write_file=True, file_format="yaml", model_obj=ToolSettings())
        self.prompt_settings.create_template_file(write_file=True, file_format="yaml", model_obj=PromptSettings())
        self.kn_settings.create_template_file(write_file=True, file_format="yaml", model_obj=KNSettings())
        self.db_settings.create_template_file(write_file=True, file_format="yaml", model_obj=DBSettings())

    def set_auto_reload(self, flag: bool=True):
        self.basic_settings.auto_reload = flag
        self.model_settings.auto_reload = flag
        self.tool_settings.auto_reload = flag
        self.prompt_settings.auto_reload = flag
        self.kn_settings.auto_reload = flag
        self.db_settings.auto_reload = flag


Settings = SettingsContainer()
nltk.data.path.append(str(Settings.basic_settings.NLTK_DATA_PATH))


if __name__ == "__main__":
    Settings.create_all_templates()
