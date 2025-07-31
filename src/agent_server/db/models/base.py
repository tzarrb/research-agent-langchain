from sqlalchemy.orm.properties import MappedColumn


from sqlalchemy.orm.properties import MappedColumn


from typing import Any


import json

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column

# Base: DeclarativeMeta = declarative_base()

# 基类，我们所有的 ORM 模型都需要继承它
class BaseModel(DeclarativeBase):
    
    id: MappedColumn[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    create_by: MappedColumn[str | None] = mapped_column(String, default=None, comment="创建者")
    update_by: MappedColumn[str | None] = mapped_column(String, default=None, comment="更新者")
