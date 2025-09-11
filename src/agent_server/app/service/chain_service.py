"""
chain链可以将多个组件组合在一起，以创建一个单一、连贯的应用程序，例如：创建一个链接受用户输入，使用提示词模板对其进行格式化并传递给LLM。

链在内部把一系列的功能进行封装，而链的外部又可以组合串联。

LangChain中主要有以下几种链：

基础链 LLMChain
路由链 RouterChain,LLMRouterChain
组合链 SequentialChain
转换链 TransformChain
文档链 DocumentsChain
数字链 LLMMathChain
SQL查询链 create_sql_query_chain

注意：LLMChain方式准备被移除了。
"""
from langchain.chains import LLMChain, RouterChain, SequentialChain, TransformChain,DocumentsChain,LLMMathChain,create_sql_query_chain
# from langchain.chains.router import RouterChain, LLMRouterChain
    
def get_llm_chain():
    from langchain.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI

    # 加载model
    model = ChatOpenAI(openai_api_key="google/gemma-3-12b", openai_api_base='http://127.0.0.1:1234/v1')

    # 定义提示词模板
    prompt = PromptTemplate.from_template("请列出5个流行的{subject}品牌，不需要介绍。")

    # 创建链
    llm_chain = LLMChain(
        llm=model,
        prompt=prompt
    )

    content = llm_chain.invoke({"subject" : "手机"})
