from typing import Any


import time

"""
生成唯一ID
雪花算法生成的ID由64位二进制组成：
1位符号位（始终为0）
41位时间戳
5位数据中心ID
5位工作机器ID
12位序列号

Params:
    datacenter_id (int): 数据中心ID
    worker_id (int): 工作节点ID
    
Raises:
    ValueError: 时钟回拨，无法生成ID

Returns:
    int: 生成的唯一ID
"""
class SnowflakeGenerator:
    def __init__(self, datacenter_id, worker_id):
        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1

    def next_id(self) -> int:
        timestamp = int(time.time() * 1000)

        if timestamp < self.last_timestamp:
            raise ValueError("时钟回拨，无法生成ID")

        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & 4095
            if self.sequence == 0:
                timestamp = self.wait_next_millis(self.last_timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        return ((timestamp - 1288834974657) << 22) | \
               (self.datacenter_id << 17) | \
               (self.worker_id << 12) | \
               self.sequence

    def wait_next_millis(self, last_timestamp):
        timestamp = int(time.time() * 1000)
        while timestamp <= last_timestamp:
            timestamp = int(time.time() * 1000)
        return timestamp

id_generator = SnowflakeGenerator(1, 1)


if __name__ == "__main__":
    # 使用示例
    generator = SnowflakeGenerator(1, 1)
    print(f"id 生成: {generator.next_id()}")
