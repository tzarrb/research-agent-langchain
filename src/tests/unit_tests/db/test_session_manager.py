"""
Session管理器单元测试

测试session上下文管理器的各种功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.researchagent_server.db.session import (
    async_session_scope,
    session_scope,
    async_with_session,
    with_session,
    configure_session,
    get_session_stats,
    reset_session_stats,
    session_config,
    session_monitor,
    SessionConfig,
    SessionMonitor
)


class TestSessionConfig:
    """测试SessionConfig类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SessionConfig()
        assert config.auto_commit is True
        assert config.auto_rollback is True
        assert config.enable_monitoring is True
        assert config.log_level == "INFO"
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SessionConfig(
            auto_commit=False,
            auto_rollback=False,
            enable_monitoring=False,
            log_level="DEBUG",
            retry_attempts=5,
            retry_delay=2.0
        )
        assert config.auto_commit is False
        assert config.auto_rollback is False
        assert config.enable_monitoring is False
        assert config.log_level == "DEBUG"
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0


class TestSessionMonitor:
    """测试SessionMonitor类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.monitor = SessionMonitor()
    
    def test_initial_stats(self):
        """测试初始统计信息"""
        stats = self.monitor.get_stats()
        assert stats["session_count"] == 0
        assert stats["active_sessions"] == 0
        assert stats["total_transactions"] == 0
        assert stats["failed_transactions"] == 0
        assert stats["success_rate"] == 0
    
    def test_session_lifecycle(self):
        """测试session生命周期统计"""
        # 创建session
        self.monitor.session_created()
        assert self.monitor.session_count == 1
        assert self.monitor.active_sessions == 1
        
        # 开始事务
        self.monitor.transaction_started()
        assert self.monitor.total_transactions == 1
        
        # 关闭session
        self.monitor.session_closed()
        assert self.monitor.active_sessions == 0
        
        # 检查统计信息
        stats = self.monitor.get_stats()
        assert stats["session_count"] == 1
        assert stats["active_sessions"] == 0
        assert stats["total_transactions"] == 1
        assert stats["failed_transactions"] == 0
        assert stats["success_rate"] == 100.0
    
    def test_failed_transaction(self):
        """测试失败事务统计"""
        self.monitor.transaction_started()
        self.monitor.transaction_failed()
        
        stats = self.monitor.get_stats()
        assert stats["total_transactions"] == 1
        assert stats["failed_transactions"] == 1
        assert stats["success_rate"] == 0.0


class TestConfigureFunctions:
    """测试配置函数"""
    
    def test_configure_session(self):
        """测试配置session"""
        configure_session(
            auto_commit=False,
            auto_rollback=False,
            enable_monitoring=False,
            log_level="DEBUG",
            retry_attempts=5,
            retry_delay=2.0
        )
        
        assert session_config.auto_commit is False
        assert session_config.auto_rollback is False
        assert session_config.enable_monitoring is False
        assert session_config.log_level == "DEBUG"
        assert session_config.retry_attempts == 5
        assert session_config.retry_delay == 2.0
    
    def test_get_session_stats(self):
        """测试获取统计信息"""
        stats = get_session_stats()
        assert isinstance(stats, dict)
        assert "session_count" in stats
        assert "active_sessions" in stats
        assert "total_transactions" in stats
        assert "failed_transactions" in stats
        assert "success_rate" in stats
    
    def test_reset_session_stats(self):
        """测试重置统计信息"""
        # 先产生一些统计数据
        session_monitor.session_created()
        session_monitor.transaction_started()
        
        # 重置统计信息
        reset_session_stats()
        
        # 验证统计信息已重置
        stats = get_session_stats()
        assert stats["session_count"] == 0
        assert stats["active_sessions"] == 0
        assert stats["total_transactions"] == 0
        assert stats["failed_transactions"] == 0


class TestAsyncSessionScope:
    """测试异步session上下文管理器"""
    
    @pytest.mark.asyncio
    async def test_async_session_scope_success(self):
        """测试异步session成功场景"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            async with async_session_scope() as session:
                assert session == mock_session
                # 模拟一些数据库操作
                await session.execute("SELECT 1")
            
            # 验证session被正确提交和关闭
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_session_scope_exception(self):
        """测试异步session异常场景"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            with pytest.raises(ValueError):
                async with async_session_scope() as session:
                    # 模拟异常
                    raise ValueError("测试异常")
            
            # 验证session被回滚和关闭
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_session_scope_no_auto_commit(self):
        """测试禁用自动提交的异步session"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            async with async_session_scope(auto_commit=False) as session:
                assert session == mock_session
            
            # 验证没有自动提交
            mock_session.commit.assert_not_called()
            mock_session.close.assert_called_once()


class TestSyncSessionScope:
    """测试同步session上下文管理器"""
    
    def test_sync_session_scope_success(self):
        """测试同步session成功场景"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            with session_scope() as session:
                assert session == mock_session
                # 模拟一些数据库操作
                session.execute("SELECT 1")
            
            # 验证session被正确提交和关闭
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_sync_session_scope_exception(self):
        """测试同步session异常场景"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            with pytest.raises(ValueError):
                with session_scope() as session:
                    # 模拟异常
                    raise ValueError("测试异常")
            
            # 验证session被回滚和关闭
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_sync_session_scope_no_auto_commit(self):
        """测试禁用自动提交的同步session"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            with session_scope(auto_commit=False) as session:
                assert session == mock_session
            
            # 验证没有自动提交
            mock_session.commit.assert_not_called()
            mock_session.close.assert_called_once()


class TestAsyncDecorator:
    """测试异步装饰器"""
    
    @pytest.mark.asyncio
    async def test_async_with_session_decorator(self):
        """测试异步装饰器"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        @async_with_session()
        async def test_function(session, value):
            assert session == mock_session
            return value * 2
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            result = await test_function(5)
            assert result == 10
            
            # 验证session被正确处理
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_with_session_decorator_exception(self):
        """测试异步装饰器异常处理"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        @async_with_session()
        async def test_function(session):
            raise ValueError("测试异常")
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            with pytest.raises(ValueError):
                await test_function()
            
            # 验证session被回滚
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestSyncDecorator:
    """测试同步装饰器"""
    
    def test_with_session_decorator(self):
        """测试同步装饰器"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        @with_session()
        def test_function(session, value):
            assert session == mock_session
            return value * 2
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            result = test_function(5)
            assert result == 10
            
            # 验证session被正确处理
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_with_session_decorator_exception(self):
        """测试同步装饰器异常处理"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        @with_session()
        def test_function(session):
            raise ValueError("测试异常")
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            with pytest.raises(ValueError):
                test_function()
            
            # 验证session被回滚
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        reset_session_stats()
        configure_session(
            auto_commit=True,
            auto_rollback=True,
            enable_monitoring=True,
            log_level="INFO",
            retry_attempts=3,
            retry_delay=1.0
        )
    
    @pytest.mark.asyncio
    async def test_async_integration(self):
        """测试异步集成场景"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session._SessionFactory', mock_factory):
            # 测试上下文管理器
            async with async_session_scope() as session:
                await session.execute("SELECT 1")
            
            # 测试装饰器
            @async_with_session()
            async def async_operation(session, data):
                await session.execute(f"INSERT INTO test VALUES ('{data}')")
                return "success"
            
            result = await async_operation("test_data")
            assert result == "success"
        
        # 验证统计信息
        stats = get_session_stats()
        assert stats["session_count"] == 2  # 上下文管理器 + 装饰器
        assert stats["total_transactions"] == 2
    
    def test_sync_integration(self):
        """测试同步集成场景"""
        mock_session = Mock(spec=Session)
        mock_factory = Mock(return_value=mock_session)
        
        with patch('src.researchagent_server.db.session.get_sync_session_factory', return_value=mock_factory):
            # 测试上下文管理器
            with session_scope() as session:
                session.execute("SELECT 1")
            
            # 测试装饰器
            @with_session()
            def sync_operation(session, data):
                session.execute(f"INSERT INTO test VALUES ('{data}')")
                return "success"
            
            result = sync_operation("test_data")
            assert result == "success"
        
        # 验证统计信息
        stats = get_session_stats()
        assert stats["session_count"] == 2  # 上下文管理器 + 装饰器
        assert stats["total_transactions"] == 2


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])