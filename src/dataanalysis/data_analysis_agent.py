import os
import json
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import pymysql

from dotenv import load_dotenv

from pydantic import BaseModel, Field

from langgraph.prebuilt import create_react_agent
# from langgraph.prebuilt import create_tool_calling_agent
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek


# 加载环境变量
load_dotenv(override=True)

host = os.getenv('MYSQL_HOST')
port = os.getenv('MYSQL_PORT')
user = os.getenv('MYSQL_USER')
mysql_pw = os.getenv('MYSQL_PASSWORD')
db = os.getenv('MYSQL_DATABASE')

# 创建连接
connection = pymysql.connect(
    host=host,
    user=user,
    passwd=mysql_pw,
    db=db,
    port=int(port),
    charset='utf8'
)


# 创建SQL查询工具
description = """
当用户需要进行数据库查询工作时，请调用该函数。
该函数用于在指定MySQL服务器上运行一段SQL代码，完成数据查询相关工作，
并且当前函数是使用pymsql连接MySQL数据库。
本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
"""

# 定义结构化参数模型
class SQLQuerySchema(BaseModel):
    sql_query: str = Field(description=description)


# 封装为 LangGraph 工具
@tool(args_schema=SQLQuerySchema)
def sql_inter(sql_query: str) -> str:
    """
    当用户需要进行数据库查询工作时，请调用该函数。
    该函数用于在指定MySQL服务器上运行一段SQL代码，完成数据查询相关工作，
    并且当前函数是使用pymsql连接MySQL数据库。
    本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
    :param sql_query: 字符串形式的SQL查询语句，用于执行对MySQL中telco_db数据库中各张表进行查询，并获得各表中的各类相关信息
    :return：sql_query在MySQL中的运行结果。
    """
    # print("正在调用 sql_inter 工具运行 SQL 查询...")

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            # print("SQL 查询已成功执行，正在整理结果...")
    finally:
        connection.close()

    # 将结果以 JSON 字符串形式返回
    return json.dumps(results, ensure_ascii=False)


# 创建数据提取工具
# 定义结构化参数
class ExtractQuerySchema(BaseModel):
    sql_query: str = Field(description="用于从 MySQL 提取数据的 SQL 查询语句。")
    df_name: str = Field(description="指定用于保存结果的 pandas 变量名称（字符串形式）。")


# 注册为 Agent 工具
@tool(args_schema=ExtractQuerySchema)
def extract_data(sql_query: str, df_name: str) -> str:
    """
    用于在MySQL数据库中提取一张表到当前Python环境中，注意，本函数只负责数据表的提取，
    并不负责数据查询，若需要在MySQL中进行数据查询，请使用sql_inter函数。
    同时需要注意，编写外部函数的参数消息时，必须是满足json格式的字符串，
    :param sql_query: 字符串形式的SQL查询语句，用于提取MySQL中的某张表。
    :param df_name: 将MySQL数据库中提取的表格进行本地保存时的变量名，以字符串形式表示。
    :return：表格读取和保存结果
    """
    print("正在调用 extract_data 工具运行 SQL 查询...")

    try:
        # 执行 SQL 并保存为全局变量
        df = pd.read_sql(sql_query, connection)
        globals()[df_name] = df
        # print("数据成功提取并保存为全局变量：", df_name)
        return f"成功创建 pandas 对象 `{df_name}`，包含从 MySQL 提取的数据。"
    except Exception as e:
        return f"执行失败：{e}"
    finally:
        connection.close()
        

# 创建Python代码执行工具
# Python代码执行工具结构化参数说明
class PythonCodeInput(BaseModel):
    py_code: str = Field(description="一段合法的 Python 代码字符串，例如 '2 + 2' 或 'x = 3\ny = x * 2'")


@tool(args_schema=PythonCodeInput)
def python_inter(py_code):
    """
    当用户需要编写Python程序并执行时，请调用该函数。
    该函数可以执行一段Python代码并返回最终结果，需要注意，本函数只能执行非绘图类的代码，若是绘图相关代码，则需要调用fig_inter函数运行。
    """
    g = globals()
    try:
        # 尝试如果是表达式，则返回表达式运行结果
        return str(eval(py_code, g))
    # 若报错，则先测试是否是对相同变量重复赋值
    except Exception as e:
        global_vars_before = set(g.keys())
        try:
            exec(py_code, g)
        except Exception as e:
            return f"代码执行时报错{e}"
        global_vars_after = set(g.keys())
        new_vars = global_vars_after - global_vars_before
        # 若存在新变量
        if new_vars:
            result = {var: g[var] for var in new_vars}
            # print("代码已顺利执行，正在进行结果梳理...")
            return str(result)
        else:
            # print("代码已顺利执行，正在进行结果梳理...")
            return "已经顺利执行代码"
        

# 创建绘图工具
# 绘图工具结构化参数说明
class FigCodeInput(BaseModel):
    py_code: str = Field(description="要执行的 Python 绘图代码，必须使用 matplotlib/seaborn 创建图像并赋值给变量")
    fname: str = Field(description="图像对象的变量名，例如 'fig'，用于从代码中提取并保存为图片")


@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str) -> str:
    """
    当用户需要使用 Python 进行可视化绘图任务时，请调用该函数。

    注意：
    1. 所有绘图代码必须创建一个图像对象，并将其赋值为指定变量名（例如 `fig`）。
    2. 必须使用 `fig = plt.figure()` 或 `fig = plt.subplots()`。
    3. 不要使用 `plt.show()`。
    4. 请确保代码最后调用 `fig.tight_layout()`。
    5. 所有绘图代码中，坐标轴标签（xlabel、ylabel）、标题（title）、图例（legend）等文本内容，必须使用英文描述。

    示例代码：
    fig = plt.figure(figsize=(10,6))
    plt.plot([1,2,3], [4,5,6])
    fig.tight_layout()
    """
    # print("正在调用fig_inter工具运行Python代码...")

    current_backend = matplotlib.get_backend()
    matplotlib.use('Agg')

    local_vars = {"plt": plt, "pd": pd, "sns": sns}

    # 设置图像保存路径（这里一定要设置为前端agent chat ui文件夹中的public目录下）
    base_dir = "./chat-ui/public"
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)  # 自动创建 images 文件夹（如不存在）

    try:
        g = globals()
        exec(py_code, g, local_vars)
        g.update(local_vars)

        fig = local_vars.get(fname, None)
        if fig:
            image_filename = f"{fname}.png"
            abs_path = os.path.join(images_dir, image_filename)  # 绝对路径
            rel_path = os.path.join("images", image_filename)  # 返回相对路径（给前端用）

            fig.savefig(abs_path, bbox_inches='tight')
            return f"图片已保存，路径为: {rel_path}"
        else:
            return "图像对象未找到，请确认变量名正确并为 matplotlib 图对象。"
    except Exception as e:
        return f"执行失败：{e}"
    finally:
        plt.close('all')
        matplotlib.use(current_backend)
        


# 创建提示词模板
prompt = """
你是一名经验丰富的智能数据分析助手，擅长帮助用户高效完成以下任务：

1. **数据库查询：**
   - 当用户需要获取数据库中某些数据或进行SQL查询时，请调用`sql_inter`工具，该工具已经内置了pymysql连接MySQL数据库的全部参数，包括数据库名称、用户名、密码、端口等，你只需要根据用户需求生成SQL语句即可。
   - 你需要准确根据用户请求生成SQL语句，例如 `SELECT * FROM 表名` 或包含条件的查询。

2. **数据表提取：**
   - 当用户希望将数据库中的表格导入Python环境进行后续分析时，请调用`extract_data`工具。
   - 你需要根据用户提供的表名或查询条件生成SQL查询语句，并将数据保存到指定的pandas变量中。

3. **非绘图类任务的Python代码执行：**
   - 当用户需要执行Python脚本或进行数据处理、统计计算时，请调用`python_inter`工具。
   - 仅限执行非绘图类代码，例如变量定义、数据分析等。

4. **绘图类Python代码执行：**
   - 当用户需要进行可视化展示（如生成图表、绘制分布等）时，请调用`fig_inter`工具。
   - 你可以直接读取数据并进行绘图，不需要借助`python_inter`工具读取图片。
   - 你应根据用户需求编写绘图代码，并正确指定绘图对象变量名（如 `fig`）。
   - 当你生成Python绘图代码时必须指明图像的名称，如fig = plt.figure()或fig = plt.subplots()创建图像对象，并赋值为fig。
   - 不要调用plt.show()，否则图像将无法保存。

**工具使用优先级：**
- 如需数据库数据，请先使用`sql_inter`或`extract_data`获取，再执行Python分析或绘图。
- 如需绘图，请先确保数据已加载为pandas对象。

**回答要求：**
- 所有回答均使用**简体中文**，清晰、礼貌、简洁。
- 如果调用工具返回结构化JSON数据，你应提取其中的关键信息简要说明，并展示主要结果。
- 若需要用户提供更多信息，请主动提出明确的问题。
- 如果有生成的图片文件，请务必在回答中使用Markdown格式插入图片，如：![Categorical Features vs Churn](images/fig.png)
- 不要仅输出图片路径文字。

**风格：**
- 专业、简洁、以数据驱动。
- 不要编造不存在的工具或数据。

请根据以上原则为用户提供精准、高效的协助。
"""

# 创建工具列表
tools = [python_inter, fig_inter, sql_inter, extract_data]

# 聊天模型
model = ChatDeepSeek(model="deepseek-chat")

# 创建图 （Agent）
graph = create_react_agent(
    model=model, 
    tools=tools, 
    prompt=prompt
)