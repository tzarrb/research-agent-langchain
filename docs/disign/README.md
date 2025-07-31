# Session上下文管理器

这是一个强大的数据库session管理器，提供了同步和异步两种模式的session管理功能，包括自动事务管理、异常处理、性能监控等特性。

## 功能特性

- ✅ **双模式支持**：同时支持同步和异步数据库操作
- ✅ **自动事务管理**：自动提交成功的事务，异常时自动回滚
- ✅ **上下文管理器**：提供便捷的上下文管理器接口
- ✅ **装饰器支持**：提供装饰器模式的session管理
- ✅ **异常处理**：完善的异常捕获和回滚机制
- ✅ **性能监控**：记录session使用情况和性能指标
- ✅ **重试机制**：对于连接失败等临时性错误提供重试
- ✅ **配置灵活**：支持全局配置和局部配置
- ✅ **兼容性好**：与现有代码完全兼容

## 快速开始

### 1. 异步模式使用

#### 上下文管理器方式
```python
from db.session import async_session_scope

async def create_user():
    async with async_session_scope() as session:
        user = User(name="张三")
        session.add(user)
        # 事务会自动提交
```

#### 装饰器方式
```python
from db.session import async_with_session

@async_with_session()
async def create_user(session: AsyncSession, name: str):
    user = User(name=name)
    session.add(user)
    return user

# 使用
user = await create_user("李四")
```

### 2. 同步模式使用

#### 上下文管理器方式
```python
from db.session import session_scope

def create_user():
    with session_scope() as session:
        user = User(name="王五")
        session.add(user)
        # 事务会自动提交
```

#### 装饰器方式
```python
from db.session import with_session

@with_session()
def create_user(session: Session, name: str):
    user = User(name=name)
    session.add(user)
    return user

# 使用
user = create_user("赵六")
```

## 配置选项

### 全局配置
```python
from db.session import configure_session

configure_session(
    auto_commit=True,        # 是否自动提交
    auto_rollback=True,      # 是否自动回滚
    enable_monitoring=True,  # 是否启用监控
    log_level="INFO",        # 日志级别
    retry_attempts=3,        # 重试次数
    retry_delay=1.0         # 重试延迟（秒）
)
```

### 局部配置
```python
# 上下文管理器局部配置
async with async_session_scope(
    auto_commit=False,
    auto_rollback=True,
    enable_monitoring=False
) as session:
    # 数据库操作
    pass

# 装饰器局部配置
@async_with_session(auto_commit=False)
async def some_function(session: AsyncSession):
    # 数据库操作
    pass
```

## 监控和统计

### 获取统计信息
```python
from db.session import get_session_stats

stats = get_session_stats()
print(f"总session数: {stats['session_count']}")
print(f"活跃session数: {stats['active_sessions']}")
print(f"总事务数: {stats['total_transactions']}")
print(f"失败事务数: {stats['failed_transactions']}")
print(f"成功率: {stats['success_rate']:.2f}%")
```

### 重置统计信息
```python
from db.session import reset_session_stats

reset_session_stats()
```

## 异常处理

session管理器会自动处理异常情况：

```python
@async_with_session()
async def risky_operation(session: AsyncSession):
    try:
        # 一些可能失败的数据库操作
        user = User(name="测试用户")
        session.add(user)
        
        # 模拟异常
        if some_condition:
            raise ValueError("操作失败")
            
    except ValueError:
        # 异常会被重新抛出
        # 但事务已经自动回滚
        raise
```

## 重试机制

对于临时性的数据库连接错误，提供了重试机制：

```python
from db.session import async_with_retry

async def database_operation():
    # 这个操作会在失败时自动重试
    return await async_with_retry(
        some_database_function,
        arg1, arg2,
        max_retries=3,
        retry_delay=1.0
    )
```

## 批量操作

对于批量操作，推荐使用同步模式：

```python
@with_session()
def batch_create_users(session: Session, users_data: List[dict]):
    users = []
    for data in users_data:
        user = User(**data)
        users.append(user)
    
    session.add_all(users)
    return users
```

## 最佳实践

### 1. 选择合适的模式
- **异步模式**：适用于Web API、高并发场景
- **同步模式**：适用于批量处理、数据迁移脚本

### 2. 异常处理
```python
@async_with_session()
async def safe_operation(session: AsyncSession):
    try:
        # 数据库操作
        result = await session.execute(select(User))
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"数据库操作失败: {e}")
        # 异常会自动触发回滚
        raise
```

### 3. 性能优化
```python
# 对于只读操作，可以禁用自动提交
@async_with_session(auto_commit=False)
async def read_only_operation(session: AsyncSession):
    result = await session.execute(select(User).limit(100))
    return result.scalars().all()
```

### 4. 嵌套事务
```python
async def complex_operation():
    async with async_session_scope() as session:
        # 外层事务
        user = User(name="用户1")
        session.add(user)
        
        # 内层操作（使用同一个session）
        await create_user_profile(session, user.id)
        
        # 整个操作作为一个事务提交

async def create_user_profile(session: AsyncSession, user_id: int):
    profile = UserProfile(user_id=user_id, bio="用户简介")
    session.add(profile)
```

## 与FastAPI集成

session管理器与现有的FastAPI依赖注入完全兼容：

```python
from fastapi import Depends
from db.base import get_db

# 传统方式（仍然支持）
@app.post("/users/")
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    return user

# 新的装饰器方式
@async_with_session()
async def create_user_service(session: AsyncSession, user_data: UserCreate):
    user = User(**user_data.dict())
    session.add(user)
    return user

@app.post("/users/new")
async def create_user_endpoint(user_data: UserCreate):
    return await create_user_service(user_data)
```

## 迁移指南

### 从现有代码迁移

1. **保持现有代码不变**：现有的`get_db()`依赖注入仍然有效
2. **逐步迁移**：可以逐个函数迁移到新的session管理器
3. **混合使用**：新旧方式可以在同一个项目中共存

### 迁移示例

**迁移前：**
```python
async def create_user(db: AsyncSession = Depends(get_db)):
    try:
        user = User(name="测试")
        db.add(user)
        await db.commit()
        return user
    except Exception:
        await db.rollback()
        raise
```

**迁移后：**
```python
@async_with_session()
async def create_user(session: AsyncSession):
    user = User(name="测试")
    session.add(user)
    return user
```

## 故障排除

### 常见问题

1. **"数据库会话工厂未初始化"错误**
   - 确保在使用session管理器前调用了`setup_database_connection()`

2. **事务没有自动提交**
   - 检查`auto_commit`配置是否为`True`
   - 确保没有未捕获的异常

3. **连接池耗尽**
   - 检查是否有session没有正确关闭
   - 查看监控统计中的活跃session数量

### 调试技巧

1. **启用详细日志**
```python
configure_session(log_level="DEBUG")
```

2. **监控session使用情况**
```python
stats = get_session_stats()
if stats['active_sessions'] > 10:
    logger.warning("活跃session数量过多")
```

3. **使用监控装饰器**
```python
@async_with_session(enable_monitoring=True)
async def monitored_operation(session: AsyncSession):
    # 这个操作会被详细监控
    pass
```

## 文件结构

```
db/
├── __init__.py
├── base.py                    # 数据库基础配置
├── session.py                 # Session管理器核心实现
├── session_examples.py        # 使用示例
├── test_session_manager.py    # 单元测试
├── session_manager_design.md  # 设计文档
└── README.md                  # 本文档
```

## 版本历史

- **v1.0.0** - 初始版本，支持基本的session管理
- **v1.1.0** - 添加监控和统计功能
- **v1.2.0** - 添加重试机制和配置选项
- **v1.3.0** - 完善异常处理和日志记录

## 贡献指南

欢迎提交Issue和Pull Request来改进这个session管理器。

## 许可证

MIT License