
import sys
import os
import argparse
# 把 src 加入 sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
print("🔍 当前 sys.path = ", sys.path)

import uvicorn
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from researchagent_server import __version__
# from config.settings import *
from chat.chat_service import chat_async
from api.endpoints.chat_routes import router as chat_router
from api.endpoints.prompt_routes import router as prompt_router



def create_app(run_mode: str = "") -> FastAPI:
    app = FastAPI(
        title="AI Chat API Service",
        description="基于 FastAPI 的聊天机器人接口服务",
        version=__version__
    )
    # MakeFastAPIOffline(app)
    # Add CORS middleware to allow all origins
    # 在config.py中设置OPEN_DOMAIN=True，允许跨域
    # set OPEN_DOMAIN=True in config.py to allow cross-domain
    # if Settings.basic_settings.OPEN_CROSS_DOMAIN:
    #     app.add_middleware(
    #         CORSMiddleware,
    #         allow_origins=["*"],
    #         allow_credentials=True,
    #         allow_methods=["*"],
    #         allow_headers=["*"],
    #     )

    # 添加 CORS 支持
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

    return app


def run_api(host, port, **kwargs):
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


app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="langchain-Chat",
        description="About langchain-Chat, local knowledge based Chat with langchain"
        " ｜ 基于本地知识库的 Chat 问答",
    )
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--ssl_keyfile", type=str)
    parser.add_argument("--ssl_certfile", type=str)
    # 初始化消息
    args = parser.parse_args()
    args_dict = vars(args)

    run_api(
        host=args.host,
        port=args.port,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )
