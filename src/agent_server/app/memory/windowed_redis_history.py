# src/agent_server/app/memory/windowed_redis_history.py

import logging
from typing import List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory
import redis  # 新增导入

logger = logging.getLogger(__name__)

class WindowedRedisChatMessageHistory(BaseChatMessageHistory):
    def __init__(
        self,
        session_id: str,
        url: str = "redis://localhost:6379/0",
        key_prefix: str = "message_store:",
        ttl: Optional[int] = None,
        window_size: int = 5,
    ):
        self.redis_client = redis.Redis.from_url(url)  # 直接使用Redis客户端
        self.session_id = session_id
        self.key = f"{key_prefix}{session_id}"
        self.ttl = ttl
        self.window_size = window_size * 2  # 存储窗口大小（消息数）

    def add_message(self, message: BaseMessage) -> None:
        """添加消息并维护窗口大小"""
        # 序列化消息
        message_data = message.json()
        
        # 使用Redis事务保证原子操作
        with self.redis_client.pipeline() as pipe:
            # 添加新消息
            pipe.rpush(self.key, message_data)
            # 截取窗口：保留最后N条消息
            pipe.ltrim(self.key, -self.window_size, -1)
            # 设置TTL
            if self.ttl:
                pipe.expire(self.key, self.ttl)
            pipe.execute()

    @property
    def messages(self) -> List[BaseMessage]:
        """从Redis获取窗口内的消息"""
        messages_data = self.redis_client.lrange(self.key, 0, -1)
        return [BaseMessage.parse_raw(msg) for msg in messages_data]

    def clear(self) -> None:
        """清除会话历史"""
        self.redis_client.delete(self.key)
