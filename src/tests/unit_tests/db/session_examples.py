"""
Session上下文管理器使用示例

这个文件展示了如何使用新的session管理器进行数据库操作
"""

import asyncio
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.researchagent_server.db.session import (
    async_session_scope,
    session_scope,
    async_with_session,
    with_session,
    configure_session,
    get_session_stats,
    reset_session_stats
)
from .models.knowledge_base_model import KnowledgeBaseModel


# ==================== 异步使用示例 ====================

async def example_async_context_manager():
    """异步上下文管理器使用示例"""
    print("=== 异步上下文管理器示例 ===")
    
    # 使用异步上下文管理器
    async with async_session_scope() as session:
        # 查询数据
        result = await session.execute(
            select(KnowledgeBaseModel).limit(5)
        )
        knowledge_bases = result.scalars().all()
        
        print(f"查询到 {len(knowledge_bases)} 个知识库")
        
        # 创建新的知识库
        new_kb = KnowledgeBaseModel(
            kb_name="测试知识库",
            kb_info="这是一个测试知识库",
            vs_type="pg",
            embed_model="bge-m3"
        )
        session.add(new_kb)
        # 事务会自动提交


@async_with_session()
async def create_knowledge_base_async(
    session: AsyncSession,
    name: str,
    info: str,
    vs_type: str = "pg",
    embed_model: str = "bge-m3"
) -> KnowledgeBaseModel:
    """使用异步装饰器创建知识库"""
    print(f"=== 异步装饰器示例：创建知识库 {name} ===")
    
    kb = KnowledgeBaseModel(
        kb_name=name,
        kb_info=info,
        vs_type=vs_type,
        embed_model=embed_model
    )
    session.add(kb)
    await session.flush()  # 获取ID
    
    print(f"创建知识库成功，ID: {kb.id}")
    return kb


@async_with_session()
async def get_knowledge_bases_async(session: AsyncSession) -> List[KnowledgeBaseModel]:
    """使用异步装饰器查询知识库列表"""
    print("=== 异步装饰器示例：查询知识库列表 ===")
    
    result = await session.execute(select(KnowledgeBaseModel))
    knowledge_bases = result.scalars().all()
    
    print(f"查询到 {len(knowledge_bases)} 个知识库")
    for kb in knowledge_bases:
        print(f"  - {kb.kb_name}: {kb.kb_info}")
    
    return list(knowledge_bases)


# ==================== 同步使用示例 ====================

def example_sync_context_manager():
    """同步上下文管理器使用示例"""
    print("=== 同步上下文管理器示例 ===")
    
    # 使用同步上下文管理器
    with session_scope() as session:
        # 查询数据
        result = session.execute(
            select(KnowledgeBaseModel).limit(5)
        )
        knowledge_bases = result.scalars().all()
        
        print(f"查询到 {len(knowledge_bases)} 个知识库")
        
        # 创建新的知识库
        new_kb = KnowledgeBaseModel(
            kb_name="同步测试知识库",
            kb_info="这是一个同步测试知识库",
            vs_type="pg",
            embed_model="bge-m3"
        )
        session.add(new_kb)
        # 事务会自动提交


@with_session()
def create_knowledge_base_sync(
    session: Session,
    name: str,
    info: str,
    vs_type: str = "pg",
    embed_model: str = "bge-m3"
) -> KnowledgeBaseModel:
    """使用同步装饰器创建知识库"""
    print(f"=== 同步装饰器示例：创建知识库 {name} ===")
    
    kb = KnowledgeBaseModel(
        kb_name=name,
        kb_info=info,
        vs_type=vs_type,
        embed_model=embed_model
    )
    session.add(kb)
    session.flush()  # 获取ID
    
    print(f"创建知识库成功，ID: {kb.id}")
    return kb


@with_session()
def get_knowledge_bases_sync(session: Session) -> List[KnowledgeBaseModel]:
    """使用同步装饰器查询知识库列表"""
    print("=== 同步装饰器示例：查询知识库列表 ===")
    
    result = session.execute(select(KnowledgeBaseModel))
    knowledge_bases = result.scalars().all()
    
    print(f"查询到 {len(knowledge_bases)} 个知识库")
    for kb in knowledge_bases:
        print(f"  - {kb.kb_name}: {kb.kb_info}")
    
    return list(knowledge_bases)


# ==================== 异常处理示例 ====================

@async_with_session()
async def example_async_error_handling(session: AsyncSession):
    """异步异常处理示例"""
    print("=== 异步异常处理示例 ===")
    
    try:
        # 创建一个知识库
        kb = KnowledgeBaseModel(
            kb_name="错误测试知识库",
            kb_info="这会导致错误",
            vs_type="pg",
            embed_model="bge-m3"
        )
        session.add(kb)
        
        # 故意引发错误
        raise ValueError("模拟数据库操作错误")
        
    except ValueError as e:
        print(f"捕获到错误: {e}")
        print("事务将自动回滚")
        # 异常会被重新抛出，事务会自动回滚


@with_session()
def example_sync_error_handling(session: Session):
    """同步异常处理示例"""
    print("=== 同步异常处理示例 ===")
    
    try:
        # 创建一个知识库
        kb = KnowledgeBaseModel(
            kb_name="同步错误测试知识库",
            kb_info="这会导致错误",
            vs_type="pg",
            embed_model="bge-m3"
        )
        session.add(kb)
        
        # 故意引发错误
        raise ValueError("模拟同步数据库操作错误")
        
    except ValueError as e:
        print(f"捕获到错误: {e}")
        print("事务将自动回滚")
        # 异常会被重新抛出，事务会自动回滚


# ==================== 配置和监控示例 ====================

def example_configuration():
    """配置示例"""
    print("=== 配置示例 ===")
    
    # 配置session管理器
    configure_session(
        auto_commit=True,
        auto_rollback=True,
        enable_monitoring=True,
        log_level="DEBUG",
        retry_attempts=3,
        retry_delay=1.0
    )
    
    print("Session管理器配置已更新")


def example_monitoring():
    """监控示例"""
    print("=== 监控示例 ===")
    
    # 获取统计信息
    stats = get_session_stats()
    print("Session统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 重置统计信息
    reset_session_stats()
    print("统计信息已重置")


# ==================== 批量操作示例 ====================

@with_session()
def example_batch_operations(session: Session):
    """批量操作示例"""
    print("=== 批量操作示例 ===")
    
    # 批量创建知识库
    knowledge_bases = []
    for i in range(5):
        kb = KnowledgeBaseModel(
            kb_name=f"批量知识库_{i}",
            kb_info=f"这是第{i}个批量创建的知识库",
            vs_type="pg",
            embed_model="bge-m3"
        )
        knowledge_bases.append(kb)
    
    # 批量添加到session
    session.add_all(knowledge_bases)
    
    print(f"批量创建了 {len(knowledge_bases)} 个知识库")


# ==================== 主函数 ====================

async def main():
    """主函数，运行所有示例"""
    print("开始运行Session管理器示例...")
    
    # 配置示例
    example_configuration()
    
    try:
        # 异步示例
        await example_async_context_manager()
        
        kb1 = await create_knowledge_base_async(
            name="异步知识库1",
            info="通过异步装饰器创建"
        )
        
        await get_knowledge_bases_async()
        
        # 异步异常处理示例
        try:
            await example_async_error_handling()
        except ValueError:
            print("异步异常处理完成")
        
        # 同步示例
        example_sync_context_manager()
        
        kb2 = create_knowledge_base_sync(
            name="同步知识库1",
            info="通过同步装饰器创建"
        )
        
        get_knowledge_bases_sync()
        
        # 同步异常处理示例
        try:
            example_sync_error_handling()
        except ValueError:
            print("同步异常处理完成")
        
        # 批量操作示例
        example_batch_operations()
        
        # 监控示例
        example_monitoring()
        
    except Exception as e:
        print(f"运行示例时发生错误: {e}")
    
    print("所有示例运行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())