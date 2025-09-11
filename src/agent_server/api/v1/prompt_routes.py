from typing import Any
from fastapi import APIRouter

from agent_server.app.service.chat_service import chat, chat_async

router = APIRouter(prefix="/prompt", tags=["Prompt提示词"])

@router.post("/generate")
async def prompt_generate(data: dict[str, Any]):
    pass