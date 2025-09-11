
import shutil

from fastapi import FastAPI, APIRouter, Depends,Request, Response, UploadFile, File

from agent_server.config.settings import Settings
from agent_server.app.service.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["RAG检索增强生成"])

@router.post("/upload", summary="上传文件并保存到向量存储")
async def upload_file(file: UploadFile = File(...), service: RagService = Depends()):
    result = await service.upload_file(file)
    return Response(result)

@router.post("/multi-upload/")
async def multi_upload(files: list[UploadFile] = File(...), service: RagService = Depends()):
    for file in files:
        file_path = f"{Settings.basic_settings.TEMP_FILE_PATH}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return {"filenames": [file.filename for file in files]}