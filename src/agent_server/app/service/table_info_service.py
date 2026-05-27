"""
表信息查询服务
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from agent_server.db.session import async_session_scope
from agent_server.utils.log_util import build_logger

logger = build_logger("table_info_service")

class TableInfoService:
    """表信息查询服务"""
    
    async def get_all_tables(self) -> list[str]:
        """获取所有表名"""
        async with async_session_scope(auto_commit=False) as session:
            return await self._get_available_tables(session)
    
    async def get_table_schema(self, table_name: str) -> dict[str, Any]:
        """获取表结构信息"""
        async with async_session_scope(auto_commit=False) as session:
            # 验证表是否存在
            available_tables = await self._get_available_tables(session)
            if table_name not in available_tables:
                raise ValueError(f"表 '{table_name}' 不存在")
            
            # 获取表信息
            # 获取列信息
            columns = await self._get_table_columns(session, table_name)
            # 获取索引信息
            indexes = await self._get_table_indexes(session, table_name)
            # 获取外键信息
            foreign_keys = await self._get_table_foreign_keys(session, table_name)
            
            # 组装完整的表信息
            table_info = f"""
                表名: {table_name}

                列信息:
                {columns}

                索引信息:
                {indexes}

                外键信息:
                {foreign_keys}
                """
            # return table_info.strip()
        
            return {
                "table_name": table_name,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys
            }
    
    async def get_table_row_count(self, table_name: str) -> int:
        """获取表行数"""
        async with async_session_scope(auto_commit=False) as session:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
    
    async def _get_available_tables(self, session: AsyncSession) -> List[str]:
        """获取可用表列表"""
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        return [row[0] for row in result.fetchall()]
    
    async def _get_table_columns(self, session: AsyncSession, table_name: str) -> List[Dict[str, Any]]:
        """获取表列信息"""
        result = await session.execute(text("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """), {"table_name": table_name})
        
        columns = []
        for row in result.fetchall():
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == 'YES',
                "default": row[3],
                "max_length": row[4],
                "precision": row[5],
                "scale": row[6]
            })
        return columns
    
    async def _get_table_indexes(self, session: AsyncSession, table_name: str) -> List[Dict[str, str]]:
        """获取表索引信息"""
        result = await session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE tablename = :table_name 
            AND schemaname = 'public'
            ORDER BY indexname
        """), {"table_name": table_name})
        
        return [{"name": row[0], "definition": row[1]} for row in result.fetchall()]
    
    async def _get_table_foreign_keys(self, session: AsyncSession, table_name: str) -> List[Dict[str, str]]:
        """获取表外键信息"""
        result = await session.execute(text("""
            SELECT 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.constraint_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.referential_constraints rc 
                ON kcu.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu 
                ON rc.unique_constraint_name = ccu.constraint_name
            WHERE kcu.table_name = :table_name
            AND kcu.table_schema = 'public'
            ORDER BY kcu.column_name
        """), {"table_name": table_name})
        
        foreign_keys = []
        for row in result.fetchall():
            foreign_keys.append({
                "column": row[0],
                "foreign_table": row[1],
                "foreign_column": row[2],
                "constraint_name": row[3]
            })
        return foreign_keys
    
    async def _get_simple_table_info(self, session: AsyncSession, table_name: str) -> str:
        """获取简化的表信息（备用方法）"""
        try:
            result = await session.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
            columns = result.keys()
            return f"表 '{table_name}' 包含以下列:\n" + "\n".join([f"  - {col}" for col in columns])
        except Exception as e:
            return f"无法获取表 '{table_name}' 的信息: {str(e)}"
        
        
table_info_service = TableInfoService()        