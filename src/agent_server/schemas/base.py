from pydantic import BaseModel

# 基类，我们所有的 pydantic 模型都需要继承它
class BaseSchema(BaseModel):
    
    class Config:
        from_attributes = True  # 告诉 Pydantic 模型可以从 ORM 对象属性中读取数据
