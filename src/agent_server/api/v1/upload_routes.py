import os
import pandas as pd
import shutil

from fastapi import FastAPI, APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/upload", tags=["Upload文件上传"])

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("show_table.html", {"request": request, "df_html": None})

@router.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    # 保存上传的文件
    file_location = f"temp.xlsx"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 读取Excel内容
    df = pd.read_excel(file_location)
    df_html = df.to_html(classes="table table-bordered", index=False, border=0)

    # 删除临时文件
    os.remove(file_location)

    return templates.TemplateResponse("show_table.html", {"request": request, "df_html": df_html})