
import json
import sys
import os
import argparse
import logging
import logging.config

from dotenv import load_dotenv

# 把 src 加入 sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
print("Current sys.path = ", sys.path)

import uvicorn
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from contextlib import asynccontextmanager

from agent_server.app.chat.chat_service import chat_async
from agent_server.api.v1.chat_routes import router as chat_router
from agent_server.api.v1.prompt_routes import router as prompt_router
from agent_server.api.v1.rag_routes import router as rag_router
from agent_server.core.exceptions import global_exception_handler
from agent_server.config.settings import Settings
from agent_server.utils.log_util import (
    build_logger,
    get_log_file,
    get_config_dict,
    get_timestamp_ms,
)
from agent_server.db.base import (
    setup_database_connection,
    close_database_connection,
    create_db_and_tables,
)

logger = build_logger("main")

# 使用 lifespan 管理应用生命周期事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    # 配置自动加载
    Settings.set_auto_reload(True)
    await setup_database_connection()
    # [可选] 在开发时创建表
    # env = os.getenv("ENVIRONMENT", "dev")
    # if env == "dev":
        # Settings.create_all_templates()
        # await create_db_and_tables()

    logger.info("🚀 应用启动，数据库已连接。")
    yield
    # 应用关闭时执行
    await close_database_connection()
    logger.info("应用关闭，数据库连接已释放。")

def create_app(run_mode: str = "") -> FastAPI:
    logger.info(f"🔧 Starting API with basic settings: {json.dumps(Settings.basic_settings.model_dump(), ensure_ascii=False, indent=2)}")
    logger.info(f"🔧 Starting API with model settings: {json.dumps(Settings.model_settings.model_dump(), ensure_ascii=False, indent=2)}")
    # logger.info(f"🔧 Starting API with platforms configurations: {json.dumps(get_config_platforms(), ensure_ascii=False, indent=2)}")
    # logger.info(f"🔧 Starting API with model configurations: {json.dumps(get_config_models(platform_type='deepseek'), ensure_ascii=False, indent=2)}")
    # logger.info(f"🔧 Starting API with model info: {json.dumps(get_model_info(model_name='deepseek-chat', platform_type='deepseek'), ensure_ascii=False, indent=2)}")

    # 从.env文件加载环境变量
    load_dotenv()

    # 创建 FastAPI 应用
    app = FastAPI(
        title="AI Chat API Service",
        description="基于 FastAPI 的聊天机器人接口服务",
        version=Settings.basic_settings.version,
        lifespan=lifespan,
    )
    
    # 添加 CORS 支持
    # MakeFastAPIOffline(app)
    # Add CORS middleware to allow all origins
    # 在config.py中设置OPEN_DOMAIN=True，允许跨域
    if Settings.basic_settings.OPEN_CROSS_DOMAIN:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    
    # 注册路由
    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(prompt_router, prefix="/api", tags=["Prompt"])
    app.include_router(rag_router, prefix="/api", tags=["RAG"])

    # 媒体文件
    # app.mount("/media", StaticFiles(directory=Settings.basic_settings.MEDIA_PATH), name="media")

    # 项目相关图片
    # img_dir = str(Settings.basic_settings.IMG_DIR)
    # app.mount("/img", StaticFiles(directory=img_dir), name="img")

    @app.get("/health")
    def health():
        return {"status": "running"}

    @app.get("/", summary="swagger 文档", include_in_schema=False)
    async def document():
        return RedirectResponse(url="/docs")

    # 其它接口
    app.post(
        "/other/completion",
        tags=["Other"],
        summary="要求llm模型补全(通过LLMChain)",
    )(chat_async)

    # 注册全局异常处理器
    # 这会捕获所有类型为 Exception 的异常
    app.add_exception_handler(Exception, global_exception_handler)

    return app

app = create_app()


def run_api(**kwargs):
    logging_conf = get_config_dict(
        "INFO",
        get_log_file(log_path=str(Settings.basic_settings.LOG_PATH), sub_dir=f"run_api_server_{get_timestamp_ms()}"),
        1024 * 1024 * 1024 * 3,
        1024 * 1024 * 1024 * 3,
    )
    logging.config.dictConfig(logging_conf)  # type: ignore
    
    host= kwargs.get("host", Settings.basic_settings.API_SERVER.get("host", "localhost"))
    port= kwargs.get("port", Settings.basic_settings.API_SERVER.get("port", 18081))

    if kwargs.get("ssl_keyfile") and kwargs.get("ssl_certfile"):
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=kwargs.get("ssl_keyfile"),
            ssl_certfile=kwargs.get("ssl_certfile"),
        )
    else:
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="resarch-agent-langchain",
        description="About resarch-agent-langchaint, local knowledge based Agent with langchain"
        " ｜ 基于本地知识库的 Chat 问答和智能体",
    )
    parser.add_argument("--host", type=str, default=Settings.basic_settings.API_SERVER.get("host", "localhost"))
    parser.add_argument("--port", type=int, default=Settings.basic_settings.API_SERVER.get("port", 18081))
    parser.add_argument("--ssl_keyfile", type=str)
    parser.add_argument("--ssl_certfile", type=str)
    # 初始化消息
    args = parser.parse_args()
    args_dict = vars(args)

    run_api(**args_dict)
