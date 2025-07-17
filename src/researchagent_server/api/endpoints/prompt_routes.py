from fastapi import APIRouter
from chat.chat_service import chat, chat_async

router = APIRouter(prefix="/prompt", tags=["Prompt提示词"])

@router.post("/generate")
async def prompt_generate(data: dict):
    result = await chat_async(
        model_name=data["model_name"],
        model_provider=data["model_provider"],
        input=data["input"]
    )
    return {"result": result}