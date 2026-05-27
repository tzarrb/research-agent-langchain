import os
import shutil

from pathlib import Path
from fastapi import UploadFile

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


class RagService:

    async def upload_file(self, file: UploadFile):
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

        return f"{file.filename} 已成功保存"