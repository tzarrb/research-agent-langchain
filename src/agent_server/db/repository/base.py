from typing import Any, Generic, Type, TypeVar, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc
from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel

from ...db.models.base import BaseEntity
from ...schemas.base import BaseSchema
from ...core.exceptions import AlreadyExistsException
from ..session import async_with_session
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

    @async_with_session()
    async def get(self, session: AsyncSession, id: Any) -> ModelType | None:
        return await session.get(self.model, id)

    @async_with_session()
    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: list[str] | None = None,
    ) -> list[ModelType]:
        statement = select(self.model)
        # 应用排序逻辑
        if order_by:
            for ob in order_by:
                field, direction = ob.rsplit("_", 1)
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    if direction == "desc":
                        statement = statement.order_by(desc(column))
                    else:
                        statement = statement.order_by(asc(column))
        
        statement = statement.offset(skip).limit(limit)
        result = await session.scalars(statement)
        return list(result.all())

    @async_with_session()
    async def create(self, session: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
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

    @async_with_session()
    async def update(
        self, session: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
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

    @async_with_session()
    async def delete(self, session: AsyncSession, *, id: Any) -> None:
        obj = await self.get(session, id)
        if obj:
            await session.delete(obj)
            await session.commit()