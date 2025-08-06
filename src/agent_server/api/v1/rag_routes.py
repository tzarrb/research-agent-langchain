import os
import pandas as pd
import shutil

from pathlib import Path
from fastapi import FastAPI, APIRouter, Request, Response, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse

from langchain_community.document_loaders import TextLoader, CSVLoader, DirectoryLoader, PyPDFLoader, BSHTMLLoader

from config.settings import Settings
from app.rag.vector_store.base import VsServiceFactory, SupportedVSType

# 定义加载器映射
loader_mapping = {
    ".csv": CSVLoader,
    ".pdf": PyPDFLoader,
    ".txt": lambda path: TextLoader(path, autodetect_encoding=True),
    ".html": lambda path: BSHTMLLoader(path, open_encoding='utf-8')
}

router = APIRouter(prefix="/rag", tags=["本地搜索增强生成（RAG）"])

@router.post("/upload", summary="上传文件并保存到向量存储")
async def upload_file(request: Request, file: UploadFile = File(...)):
    # 保存上传的文件
    file_path = f"{Settings.basic_settings.TEMP_FILE_PATH}/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # loader = DirectoryLoader(
    #     path=Settings.basic_settings.TEMP_FILE_PATH,
    #     glob="**/*.*",
    #     loader_cls=lambda file_path: loader_mapping.get(Path(file_path).suffix.lower())(file_path),
    #     use_multithreading=True,
    # )
    loader = loader_mapping.get(Path(file_path).suffix.lower(), TextLoader)(file_path)
    documents = loader.load()
    
    vs_service = VsServiceFactory.get_service(vector_store_type=Settings.kn_settings.DEFAULT_VS_TYPE, kn_name="default")
    vs_service.save_vector_store(documents)
    
    # 删除临时文件
    os.remove(file_path)

    return Response(f"{file.filename} 已成功保存")

@router.post("/multi-upload/")
async def multi_upload(files: list[UploadFile] = File(...)):
    for file in files:
        file_path = f"{Settings.basic_settings.TEMP_FILE_PATH}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return {"filenames": [file.filename for file in files]}