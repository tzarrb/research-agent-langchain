from typing import Any, Generic, Type, TypeVar, List
from unittest import result

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc
from sqlalchemy.exc import IntegrityError

from fastapi import Depends

from pydantic import BaseModel

from ...db.models.base import BaseEntity
from ...schemas.base import BaseSchema
from ...core.exceptions import AlreadyExistsException
from ..session import async_with_session, async_session_scope
from ...utils.id_util import id_generator

# 定义类型变量
ModelType = TypeVar('ModelType', bound=BaseEntity)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseSchema)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseSchema)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    一个包含通用 CRUD 操作的、可复用的仓库基类。
    """
    def __init__(self, model: ModelType):
        self.model = model

    # @async_with_session()
    # async def get(self, session: AsyncSession, id: Any) -> ModelType | None:
    #     result = await session.get(self.model, id)
    #     return result

    async def get(self, id: Any) -> ModelType | None:
        async with async_session_scope() as session:
            result = await session.get(self.model, id)
            return result

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[ModelType]:
        async with async_session_scope() as session:
            statement = select(self.model)
            # 应用排序逻辑
            if order_by:
                for ob in order_by:
                    field = ob.get("field", "field")
                    direction = ob.get("direction", "asc")
                    if hasattr(self.model, field):
                        column = getattr(self.model, field)
                        if direction == "desc":
                            statement = statement.order_by(desc(column))
                        else:
                            statement = statement.order_by(asc(column))
            
            statement = statement.offset(skip).limit(limit)
            result = await session.scalars(statement)
            return list(result.all())

    
    async def list(
        self,
        *,
        page_num: int = 1,
        page_size: int = 10,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[ModelType]:
        page_num =  1 if page_num < 1 else page_num
        page_size = 10 if page_size < 1 or page_size > 100 else page_size
        
        return await self.get_multi(
            skip=(page_num - 1) * page_size,
            limit=page_size,
            order_by=order_by
        )
    
    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        async with async_session_scope() as session:
            obj_in_data = obj_in.model_dump()
            db_obj = self.model(**obj_in_data)
            
            if not db_obj.id:
                db_obj.id = id_generator.next_id()

            session.add(db_obj)
            try:
                await session.commit()
                await session.refresh(db_obj)
                return db_obj
            except IntegrityError:
                await session.rollback()
                raise AlreadyExistsException(
                    detail=f"{self.model.__name__} with these unique properties already exists."
                )

    async def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        async with async_session_scope() as session:
            obj_data = db_obj.__dict__
            if isinstance(obj_in, BaseModel):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])
            
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)
            return db_obj

    async def delete(self, *, id: Any) -> None:
        async with async_session_scope() as session:
            obj = await self.get(id)
            if obj:
                await session.delete(obj)
                await session.commit()