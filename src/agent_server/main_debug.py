import os
import sys
import json
import logging
import logging.config
from dotenv import load_dotenv

# 把 src 加入 sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
print("Current sys.path = ", sys.path)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 简化配置，避免Redis依赖
class SimpleSettings:
    basic_settings = type('obj', (object,), {
        'API_SERVER': {'host': '127.0.0.1', 'port': 18081},
        'OPEN_CROSS_DOMAIN': True,
        'version': '0.1.0'
    })()

logger = logging.getLogger("main")

# 使用 lifespan 管理应用生命周期事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    logger.info("🚀 应用启动（调试模式）。")
    yield
    # 应用关闭时执行
    logger.info("应用关闭。")

def create_app() -> FastAPI:
    # 从.env文件加载环境变量
    load_dotenv()

    # 创建 FastAPI 应用
    app = FastAPI(
        title="AI Chat API Service (Debug)",
        description="基于 FastAPI 的聊天机器人接口服务 - 调试模式",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # 添加 CORS 支持
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "running"}

    @app.get("/")
    async def document():
        return {"message": "Debug server is running"}

    return app

app = create_app()

if __name__ == "__main__":
    # 简化日志配置
    logging.basicConfig(level=logging.INFO)
    
    host = "127.0.0.1"
    port = 18081
    
    print(f"Starting debug server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
