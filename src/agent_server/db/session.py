from typing import AsyncGenerator, Optional, Any, Callable, TypeVar, Union, Dict, Generator
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
import time
import asyncio
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

from ..utils.log_util import build_logger
from ..config.settings import Settings


logger = build_logger("session_manager")

# 类型变量
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])


@dataclass
class SessionConfig:
    """Session配置类"""
    auto_commit: bool = True
    auto_rollback: bool = True
    enable_monitoring: bool = True
    log_level: str = "INFO"
    retry_attempts: int = 3
    retry_delay: float = 1.0


class SessionMonitor:
    """Session监控类"""
    
    def __init__(self):
        self.session_count = 0
        self.active_sessions = 0
        self.total_transactions = 0
        self.failed_transactions = 0
        
    def session_created(self):
        """记录session创建"""
        self.session_count += 1
        self.active_sessions += 1
        logger.debug(f"Session created. Active sessions: {self.active_sessions}")
        
    def session_closed(self):
        """记录session关闭"""
        self.active_sessions -= 1
        logger.debug(f"Session closed. Active sessions: {self.active_sessions}")
        
    def transaction_started(self):
        """记录事务开始"""
        self.total_transactions += 1
        logger.debug(f"Transaction started. Total: {self.total_transactions}")
        
    def transaction_failed(self):
        """记录事务失败"""
        self.failed_transactions += 1
        logger.warning(f"Transaction failed. Failed: {self.failed_transactions}")
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "session_count": self.session_count,
            "active_sessions": self.active_sessions,
            "total_transactions": self.total_transactions,
            "failed_transactions": self.failed_transactions,
            "success_rate": (
                (self.total_transactions - self.failed_transactions) / self.total_transactions * 100
                if self.total_transactions > 0 else 0
            )
        }


# 全局配置和监控实例
session_config = SessionConfig()
session_monitor = SessionMonitor()


# ==================== 异步Session上下文管理器 ====================

@asynccontextmanager
async def async_session_scope(
    auto_commit: Optional[bool] = None,
    auto_rollback: Optional[bool] = None,
    enable_monitoring: Optional[bool] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    异步Session上下文管理器
    
    Args:
        auto_commit: 是否自动提交，默认使用全局配置
        auto_rollback: 是否自动回滚，默认使用全局配置
        enable_monitoring: 是否启用监控，默认使用全局配置
        
    Usage:
        async with async_session_scope() as session:
            # 数据库操作
            user = User(name="test")
            session.add(user)
            # 自动提交或回滚
    """
    # 使用传入参数或全局配置
    _auto_commit = auto_commit if auto_commit is not None else session_config.auto_commit
    _auto_rollback = auto_rollback if auto_rollback is not None else session_config.auto_rollback
    _enable_monitoring = enable_monitoring if enable_monitoring is not None else session_config.enable_monitoring

    # 动态获取会话工厂
    from .base import get_async_session_factory
    session_factory = get_async_session_factory()
    
    if session_factory is None:
        raise RuntimeError("数据库异步会话工厂未初始化！请先调用 setup_database_connection()")
    
    session = None
    start_time = time.time()
    
    try:
        # 创建session
        session = session_factory()

        if _enable_monitoring:
            session_monitor.session_created()
            session_monitor.transaction_started()
            
        logger.debug("异步Session已创建")
        
        yield session
        
        # 如果启用自动提交，则提交事务
        if _auto_commit:
            await session.commit()
            logger.debug("异步Session事务已提交")
            
    except Exception as e:
        # 如果启用自动回滚，则回滚事务
        if session and _auto_rollback:
            try:
                await session.rollback()
                logger.warning(f"异步Session事务已回滚: {str(e)}")
            except Exception as rollback_error:
                logger.error(f"异步Session回滚失败: {str(rollback_error)}")
                
        if _enable_monitoring:
            session_monitor.transaction_failed()
            
        raise
        
    finally:
        # 关闭session
        if session:
            try:
                await session.close()
                logger.debug("异步Session已关闭")
            except Exception as close_error:
                logger.error(f"异步Session关闭失败: {str(close_error)}")
                
        if _enable_monitoring:
            session_monitor.session_closed()
            execution_time = time.time() - start_time
            logger.debug(f"异步Session执行时间: {execution_time:.3f}秒")


# ==================== 同步Session上下文管理器 ====================

@contextmanager
def session_scope(
    auto_commit: Optional[bool] = True,
    auto_rollback: Optional[bool] = True,
    enable_monitoring: Optional[bool] = True
) -> Generator[Session, None, None]:
    """
    同步Session上下文管理器
    
    Args:
        auto_commit: 是否自动提交，默认使用全局配置
        auto_rollback: 是否自动回滚，默认使用全局配置
        enable_monitoring: 是否启用监控，默认使用全局配置
        
    Usage:
        with session_scope() as session:
            # 数据库操作
            user = User(name="test")
            session.add(user)
            # 自动提交或回滚
    """
    # 使用传入参数或全局配置
    _auto_commit = auto_commit if auto_commit is not None else session_config.auto_commit
    _auto_rollback = auto_rollback if auto_rollback is not None else session_config.auto_rollback
    _enable_monitoring = enable_monitoring if enable_monitoring is not None else session_config.enable_monitoring
    
    # 动态获取会话工厂
    from .base import get_sync_session_factory
    session_factory = get_sync_session_factory()

    if session_factory is None:
        raise RuntimeError("数据库同步会话工厂未初始化！请先调用 setup_database_connection()")
    
    session = None
    start_time = time.time()
    
    try:
        # 创建session
        session = session_factory()
        
        if _enable_monitoring:
            session_monitor.session_created()
            session_monitor.transaction_started()
            
        logger.debug("同步Session已创建")
        
        yield session
        
        # 如果启用自动提交，则提交事务
        if _auto_commit:
            session.commit()
            logger.debug("同步Session事务已提交")
            
    except Exception as e:
        # 如果启用自动回滚，则回滚事务
        if session and _auto_rollback:
            try:
                session.rollback()
                logger.warning(f"同步Session事务已回滚: {str(e)}")
            except Exception as rollback_error:
                logger.error(f"同步Session回滚失败: {str(rollback_error)}")
                
        if _enable_monitoring:
            session_monitor.transaction_failed()
            
        raise
        
    finally:
        # 关闭session
        if session:
            try:
                session.close()
                logger.debug("同步Session已关闭")
            except Exception as close_error:
                logger.error(f"同步Session关闭失败: {str(close_error)}")
                
        if _enable_monitoring:
            session_monitor.session_closed()
            execution_time = time.time() - start_time
            logger.debug(f"同步Session执行时间: {execution_time:.3f}秒")


# ==================== 装饰器支持 ====================

def async_with_session(
    auto_commit: Optional[bool] = True,
    auto_rollback: Optional[bool] = True,
    enable_monitoring: Optional[bool] = True
):
    """
    异步Session装饰器
    
    Args:
        auto_commit: 是否自动提交
        auto_rollback: 是否自动回滚
        enable_monitoring: 是否启用监控
        
    Usage:
        @async_with_session()
        async def create_user(session: AsyncSession, name: str):
            user = User(name=name)
            session.add(user)
            return user
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with async_session_scope(
                auto_commit=auto_commit,
                auto_rollback=auto_rollback,
                enable_monitoring=enable_monitoring
            ) as session:
                # 将session作为第一个参数传递给函数
                return await func(session, *args, **kwargs)
        return wrapper
    return decorator


def sync_with_session(
    auto_commit: Optional[bool] = True,
    auto_rollback: Optional[bool] = True,
    enable_monitoring: Optional[bool] = True
):
    """
    同步Session装饰器
    
    Args:
        auto_commit: 是否自动提交
        auto_rollback: 是否自动回滚
        enable_monitoring: 是否启用监控
        
    Usage:
        @with_session()
        def create_user(session: Session, name: str):
            user = User(name=name)
            session.add(user)
            return user
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with session_scope(
                auto_commit=auto_commit,
                auto_rollback=auto_rollback,
                enable_monitoring=enable_monitoring
            ) as session:
                # 将session作为第一个参数传递给函数
                return func(session, *args, **kwargs)
        return wrapper
    return decorator


# ==================== 重试机制 ====================

async def async_with_retry(
    func: Callable[..., Any],
    *args,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    **kwargs
):
    """
    异步重试机制
    
    Args:
        func: 要执行的异步函数
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        *args, **kwargs: 传递给函数的参数
    """
    _max_retries = max_retries if max_retries is not None else session_config.retry_attempts
    _retry_delay = retry_delay if retry_delay is not None else session_config.retry_delay
    
    last_exception = None
    
    for attempt in range(_max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except (DisconnectionError, SQLAlchemyError) as e:
            last_exception = e
            if attempt < _max_retries:
                logger.warning(f"数据库操作失败，第{attempt + 1}次重试: {str(e)}")
                await asyncio.sleep(_retry_delay)
            else:
                logger.error(f"数据库操作重试{_max_retries}次后仍然失败: {str(e)}")
                
    if last_exception:
        raise last_exception
    raise RuntimeError("重试失败但没有记录异常")


def with_retry(
    func: Callable[..., Any],
    *args,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    **kwargs
):
    """
    同步重试机制
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        *args, **kwargs: 传递给函数的参数
    """
    _max_retries = max_retries if max_retries is not None else session_config.retry_attempts
    _retry_delay = retry_delay if retry_delay is not None else session_config.retry_delay
    
    last_exception = None
    
    for attempt in range(_max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (DisconnectionError, SQLAlchemyError) as e:
            last_exception = e
            if attempt < _max_retries:
                logger.warning(f"数据库操作失败，第{attempt + 1}次重试: {str(e)}")
                time.sleep(_retry_delay)
            else:
                logger.error(f"数据库操作重试{_max_retries}次后仍然失败: {str(e)}")
                
    if last_exception:
        raise last_exception
    raise RuntimeError("重试失败但没有记录异常")


# ==================== 工具函数 ====================

def configure_session(
    auto_commit: bool = True,
    auto_rollback: bool = True,
    enable_monitoring: bool = True,
    log_level: str = "INFO",
    retry_attempts: int = 3,
    retry_delay: float = 1.0
):
    """
    配置全局Session设置
    
    Args:
        auto_commit: 是否自动提交
        auto_rollback: 是否自动回滚
        enable_monitoring: 是否启用监控
        log_level: 日志级别
        retry_attempts: 重试次数
        retry_delay: 重试延迟
    """
    global session_config
    session_config.auto_commit = auto_commit
    session_config.auto_rollback = auto_rollback
    session_config.enable_monitoring = enable_monitoring
    session_config.log_level = log_level
    session_config.retry_attempts = retry_attempts
    session_config.retry_delay = retry_delay
    
    logger.info(f"Session配置已更新: {session_config}")


def get_session_stats() -> Dict[str, Any]:
    """获取Session统计信息"""
    return session_monitor.get_stats()


def reset_session_stats():
    """重置Session统计信息"""
    global session_monitor
    session_monitor = SessionMonitor()
    logger.info("Session统计信息已重置")


# ==================== 兼容性支持 ====================

# 保持与原有代码的兼容性
def with_session_legacy(func):
    """
    兼容原有的with_session装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with session_scope() as session:
            try:
                result = func(session, *args, **kwargs)
                return result
            except Exception:
                raise
    return wrapper
