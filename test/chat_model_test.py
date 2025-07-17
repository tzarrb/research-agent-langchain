import os
import time

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate

# 1. 加载 .env 中的环境变量
load_dotenv()
api_key  = os.getenv("DEEPSEEK_API_KEY")
api_base = os.getenv("DEEPSEEK_API_BASE")
if not api_key or not api_base:
    raise EnvironmentError("请在 .env 中设置 DEEPSEEK_API_KEY 和 DEEPSEEK_API_BASE")

# 2. 定义 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位乐于助人的 AI 助手。"),
    ("human",  "{input}")
])

# 3. 初始化 DeepSeek 聊天模型
chat_model = init_chat_model(
    model="deepseek-chat",
    temperature=0.6,     # 随机性：0.0（最确定）–1.0（最随机）
    max_tokens=512,      # 最多返回多少 token
    api_key=api_key,
    api_base=api_base
)

# 4. 链式组合：Prompt → ChatModel
pipeline = prompt | chat_model

# uv add langchain-deepseek
# 5. 同步调用 
# def main():
#     question = "请用一句话解释什么是 LangChain？"
#     answer   = pipeline.invoke({"input": question})
#     print("Q:", question)
#     print("A:", answer)
# if __name__ == "__main__":
#     main()

import asyncio

async def ask(q):
    return await pipeline.ainvoke({"input": q})

async def batch_questions():
    a1=time.time()
    qs = [
        "LangChain 是什么？",
        "如何配置模型参数？",
        "LangChain 有哪些核心模块？"
    ]
    # 并发执行
    results = await asyncio.gather(*(ask(q) for q in qs))
    for q, r in zip(qs, results):
        print(f"Q: {q}\nA: {r}\n")
    a2=time.time()
    print(a2-a1)#22.283571004867554

if __name__ == "__main__":
    asyncio.run(batch_questions())