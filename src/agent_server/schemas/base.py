from pydantic import BaseModel, ConfigDict

# 基类，我们所有的 pydantic 模型都需要继承它
class BaseSchema(BaseModel):
    # 配置Pydantic模型以兼容ORM对象
    # from_attributes=True 允许Pydantic直接从SQLAlchemy模型实例中读取数据
    model_config = ConfigDict(from_attributes=True)
    
    # class Config:
    #     from_attributes = True  # 告诉 Pydantic 模型可以从 ORM 对象属性中读取数据
