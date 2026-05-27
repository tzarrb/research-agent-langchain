from agent_server.api.v1.chat_routes import router as chat_router
from agent_server.api.v1.agent_routes import router as agent_router
from agent_server.api.v1.prompt_routes import router as prompt_router
from agent_server.api.v1.rag_routes import router as rag_router
from agent_server.api.v1.upload_routes import router as upload_router
from agent_server.api.v1.chat_conversation_routes import router as chat_conversation_router

__all__ = ['chat_router', 'agent_router', 'prompt_router', 'rag_router', 'upload_router', 'chat_conversation_router']


routers = [
    {
        "router": chat_router,
        "prefix": "/v1",
        "tags": ["Chat对话"]
    },
    {
        "router": agent_router,
        "prefix": "/api",
        "tags": ["Agent智能体"]
    },
    {
        "router": prompt_router,
        "prefix": "/api",
        "tags": ["Prompt提示词"]
    },
    {
        "router": rag_router,
        "prefix": "/api",
        "tags": ["RAG检索增强生成"]
    },
    {
        "router": upload_router,
        "prefix": "/api",
        "tags": ["Upload文件上传"]
    },
    {
        "router": chat_conversation_router,
        "prefix": "/api",
        "tags": ["Chat会话消息"]
    }
]