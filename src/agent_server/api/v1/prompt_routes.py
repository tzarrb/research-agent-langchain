from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/prompt", tags=["Prompt提示词"])

@router.post("/generate")
async def prompt_generate(data: dict[str, Any]):
    pass