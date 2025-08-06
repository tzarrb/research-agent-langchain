
# ResearchAgent-LangChain

[![License](https://img.shields.io/badge/MIT-blue.svg)](https://opensource.org/license/mit)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/tzarrb/research-agent-langchain)
[![GitHub Stars](https://img.shields.io/github/stars/tzarrb/research-agent-langchain?style=social)](https://github.com/tzarrb/research-agent-langchain)

[![pypi badge](https://img.shields.io/pypi/v/research-agent-langchain.svg)](https://shields.io/)
[![Generic badge](https://img.shields.io/badge/python-3.10%7C3.11%7C3.12-blue.svg)](https://pypi.org/project/pypiserver/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.0-brightgreen.svg)](https://python.langchain.com/)

<p>
<a href="./README.md">简体中文</a> | <a href="./README_en.md">English</a> 
</p>

> 快速构建AIGC项目

ResearchAgent-LangChain是Python生态下基于LangChain框架的AIGC项目解决方案，集成AIGC大模型能力，帮助企业和个人快速定制AI知识库、AI智能体、企业AI机器人等服务和应用。

**开源地址：**

- Gitee：https://gitee.com/tzarrb/research-agent-langchain
- Github：https://github.com/tzarrb/research-agent-langchain
- GitCode: https://gitcode.com/tzarrb/research-agent-langchain

**开源不易，欢迎Star、fork 持续关注**

**支持的AI大模型：** DeepSeek / 阿里通义 / 百度千帆 / 抖音豆包 / 智谱清言 / OpenAI / Gemini / Ollama / Azure / Claude 等大模型。

## 技术栈

- **核心框架**: Python、LangChain、FastApi
- **AI 能力**: LangChain (集成OpenAI/DeepSeek/阿里云 DashScope)
- **向量存储**: PGVector、Redis Vector Store
- **动态配置**: Pydantic+YAML / Nacos
- **检索增强生成**: RAG 架构
- **Agent**: 多Agent路由架构
- **前端框架**: Vue3、Element Plus、Element Plus X

## 功能特性

1. 多模态：支持集成国内外数十家AI大模型，可动态切换和配置
2. 动态配置：支持Pydantic+YAML动态配置，无感刷新、无需每次重启服务
3. 知识库：支持向量化知识库文档，定制化Prompt对话场景
4. 高级RAG：支持Embedding模型，从知识库中精确搜索；集成Web Search等RAG插件
5. 多Agent：支持多Agent路由架构，支持Agent间的协同工作
6. Tool Call：支持定制化Tool工具类，实现本地函数调用，从第三方加载数据并提供给LLM
7. MCP: 支持Nacos3.0 MCP和Router动态配置 
8. 支持动态配置Embedding模型和向量数据库 
9. 更多特性敬请期待...

## 版本更新

- 2025.07.16 正式发布、公开仓库
- 2025.04.12 项目启动

## 预览

![](docs/imgs/chat.png)

## 感谢

- [LangChain](https://python.langchain.com/)


## 联系

- Github: https://github.com/tzarrb
- 邮箱: tzarrb@gmail.com

