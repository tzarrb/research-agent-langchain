from sqlalchemy.orm.session import Session
from typing import Any, Generator, Optional, AsyncGenerator
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from ..utils.log_util import build_logger
from ..config.settings import Settings
from .models.base import BaseEntity


logger = build_logger("database")


# --- 1. 核心组件：全局引擎与会话工厂 ---

# 同步Session工厂（用于批量处理等场景）
_sync_engine: Optional[Any] = None
_SyncSessionFactory: Optional[sessionmaker[Session]] = None

# 异步Session工厂（用于大数据处理等场景）
_async_engine: Optional[AsyncEngine] = None
_AsyncSessionFactory: Optional[async_sessionmaker[AsyncSession]] = None


# --- 2. 生命周期钩子：初始化与关闭 ---

# ==================== 初始化数据连接 ====================
async def setup_database_connection():
    setup_sync_session_factory()
    await setup_async_session_factory()

# 同步Session工厂（用于批量处理等场景）
def setup_sync_session_factory():
    """获取同步Session工厂"""
    global _sync_engine, _SyncSessionFactory
    if _sync_engine is not None:
        logger.info("同步数据库已初始化，跳过重复设置。")
        return
    
    logger.info("同步正在创建数据库引擎...")
    # 创建同步引擎
    _sync_engine = create_engine(
        Settings.db_settings.SQLALCHEMY_DATABASE_URI,
        pool_size=Settings.db_settings.POOL_SIZE,
        max_overflow=Settings.db_settings.MAX_OVERFLOW,
        pool_timeout=Settings.db_settings.POOL_TIMEOUT,
        pool_recycle=Settings.db_settings.POOL_RECYCLE,
        echo=Settings.db_settings.ECHO,
        pool_pre_ping=True,
    )
    
    _SyncSessionFactory = sessionmaker(
        bind=_sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
        
    logger.info("同步数据库引擎和会话工厂已成功创建。")

# 异步Session工厂(用于大SQL数据处理)
async def setup_async_session_factory():
    """在应用启动时，初始化全局的数据库引擎和会话工厂。"""
    global _async_engine, _AsyncSessionFactory
    if _async_engine is not None:
        logger.info("异步数据库已初始化，跳过重复设置。")
        return

    logger.info("异步正在创建数据库引擎...")
    _async_engine = create_async_engine(
        # settings 对象中读取计算生成的数据库连接字符串
        Settings.db_settings.SQLALCHEMY_DATABASE_URI,
        pool_size=Settings.db_settings.POOL_SIZE,
        max_overflow=Settings.db_settings.MAX_OVERFLOW,
        pool_timeout=Settings.db_settings.POOL_TIMEOUT,
        pool_recycle=Settings.db_settings.POOL_RECYCLE,
        echo=Settings.db_settings.ECHO,
        pool_pre_ping=True,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    )
    
    # SessionFactory 是一个“会话的工厂”，配置一次，随处使用
    _AsyncSessionFactory = async_sessionmaker(
        class_=AsyncSession, expire_on_commit=False, bind=_async_engine
    )
    logger.info("异步数据库引擎和会话工厂已成功创建。")
    
    

# ==================== 关闭数据连接 ====================   
async def close_database_connection():
    close_sync_session_factory()
    await close_async_session_factory()

# 关闭同步数据库引擎连接池
def close_sync_session_factory():
    global _sync_engine, _SyncSessionFactory
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
        _SyncSessionFactory = None
        logger.info("同步数据库引擎连接池已关闭。")

# 关闭异步据库引擎连接池
async def close_async_session_factory():
    """在应用关闭时，关闭全局的数据库引擎连接池。"""
    global _async_engine, _AsyncSessionFactory
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _AsyncSessionFactory = None
        logger.info("异步数据库引擎连接池已关闭。")


# --- 3. 依赖注入魔法：获取会话 ---
# 获取异步会话连接
def get_sync_db()  -> Generator[Session, Any, None]:
    """
    FastAPI 依赖注入函数，为每个请求提供一个独立的数据库会话。
    """
    if _SyncSessionFactory is None:
        raise RuntimeError("数据库会话工厂未初始化！")

    # 从会话工厂中创建一个新的会话
    with _SyncSessionFactory() as session:
        # 使用 yield 将会话提供给路径函数
        yield session
    # 当请求处理完成后，sync with 会自动处理会话的关闭
    
# 获取异步会话连接
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入函数，为每个请求提供一个独立的数据库会话。
    """
    if _AsyncSessionFactory is None:
        raise RuntimeError("数据库会话工厂未初始化！")

    # 从会话工厂中创建一个新的会话
    async with _AsyncSessionFactory() as session:
        # 使用 yield 将会话提供给路径函数
        yield session
    # 当请求处理完成后，async with 会自动处理会话的关闭


# --- 4. 辅助工具：创建数据库表 ---
async def create_db_and_tables():
    """
    一个开发工具，用于在应用启动前创建所有定义的数据库表。
    注意：在生产环境中你可能需要更专业的迁移工具如 Alembic。
    """
    if not _async_engine:
        raise RuntimeError("数据库引擎未初始化，无法创建表。")
    async with _async_engine.begin() as conn:
        # 导入所有模型以确保它们被注册
        from agent_server.db import models
        
        # Base.metadata 是所有继承了 Base 的模型类的元数据集合
        # 让 SQLAlchemy 根据所有继承了 Base 的模型类去创建表
        await conn.run_sync(BaseEntity.metadata.create_all)
    logger.info("数据库表已成功同步/创建。")
    