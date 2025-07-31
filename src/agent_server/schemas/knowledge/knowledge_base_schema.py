from datetime import datetime

from schemas.base import BaseSchema

class KnowledgeBaseSchema(BaseSchema):
    id: int
    kb_name: str
    kb_info: str | None
    vs_type: str | None
    embed_model: str | None
    file_count: int | None
    create_time: datetime | None

    # class Config:
    #     from_attributes = True  # 告诉 Pydantic 模型可以从 ORM 对象属性中读取数据