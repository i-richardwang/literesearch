# backend/literesearch/literesearch_agent.py

import json
import asyncio
from typing import List, Dict, Tuple, Any, Optional
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from backend.literesearch.literesearch_config import Config
from backend.literesearch.research_prompts import (
    auto_agent_instructions,
    generate_search_queries_prompt,
    get_report_by_type,
    generate_report_introduction_prompt,
    generate_subtopics_prompt,
)
from backend.literesearch.web_retriever import (
    get_retriever,
    get_default_retriever,
    scrape_urls,
    ContextCompressor,
)
from backend.literesearch.research_enums import ReportType, ReportSource, Tone
from backend.literesearch.embedding_service import Memory
from utils.llm_tools import init_language_model
from utils.langfuse_tools import get_langfuse_config


class AgentResponse(BaseModel):
    """AI代理响应模型"""

    server: str = Field(
        ..., description="由主题领域确定的服务器类型，与相应的表情符号关联。"
    )
    agent_role_prompt: str = Field(
        ..., description="基于代理角色和专业知识的特定指令。"
    )


class Subtopic(BaseModel):
    """子主题模型"""

    task: str = Field(description="任务名称", min_length=1)


class Subtopics(BaseModel):
    """子主题列表模型"""

    subtopics: List[Subtopic] = []


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def choose_agent(
    query: str, cfg: Config, session_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    选择适合查询的AI代理

    :param query: 查询字符串
    :param cfg: 配置对象
    :param session_id: 可选的会话ID
    :return: 服务器类型和代理角色提示
    """
    try:
        language_model = init_language_model(temperature=cfg.temperature)
        chat = language_model

        system_message = "{auto_agent_instructions}"
        human_message = "task: {query}"

        parser = JsonOutputParser(pydantic_object=AgentResponse)

        format_instructions = """
Output your answer as a JSON object that conforms to the following schema:
```json
{schema}
```

Important instructions:
1. Wrap your entire response between ```json and ``` tags.
2. Ensure your JSON is valid and properly formatted.
3. Do not include the schema definition in your answer.
4. Only output the data instance that matches the schema.
5. Do not include any explanations or comments within the JSON output.
        """

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_message + format_instructions),
                ("human", human_message),
            ]
        ).partial(
            auto_agent_instructions=auto_agent_instructions(),
            schema=AgentResponse.model_json_schema(),
        )

        chain = prompt_template | chat | parser

        # 使用langfuse工具获取配置
        config = get_langfuse_config(
            trace_name="choose_agent",
            metadata={"query": query},
            session_id=session_id
        )
        
        agent_dict = await chain.ainvoke({"query": query}, config=config)

        return agent_dict["server"], agent_dict["agent_role_prompt"]
    except json.JSONDecodeError:
        print("解析JSON时出错。使用默认代理。")
        return "默认代理", (
            "你是一个AI批判性思维研究助手。你的唯一目的是就给定文本撰写结构良好、"
            "批评性强、客观公正的报告。"
        )


async def get_sub_queries(
    query: str,
    agent_role_prompt: str,
    cfg: Config,
    parent_query: Optional[str],
    report_type: str,
    session_id: Optional[str] = None
) -> List[str]:
    """
    生成子查询

    :param query: 主查询
    :param agent_role_prompt: 代理角色提示
    :param cfg: 配置对象
    :param parent_query: 父查询
    :param report_type: 报告类型
    :param session_id: 可选的会话ID
    :return: 子查询列表
    """
    language_model = init_language_model(temperature=cfg.temperature)
    chat = language_model

    system_message = f"{agent_role_prompt}\n\n"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            (
                "human",
                generate_search_queries_prompt(
                    query, parent_query, report_type, max_iterations=cfg.max_iterations
                ),
            ),
        ]
    )

    messages = prompt.format_messages(question=query)
    
    # 使用langfuse工具获取配置
    config = get_langfuse_config(
        trace_name="get_sub_queries",
        metadata={
            "query": query,
            "report_type": report_type,
            "parent_query": parent_query,
            "max_iterations": cfg.max_iterations
        },
        session_id=session_id
    )
    
    response = await chat.ainvoke(messages, config=config)

    try:
        sub_queries = json.loads(response.content)
        return sub_queries
    except json.JSONDecodeError:
        print("解析JSON时出错。返回原始查询。")
        return [query]


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def construct_subtopics(
    task: str, data: str, config: Config, subtopics: List[Dict[str, str]] = [], session_id: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    构建子主题

    :param task: 任务
    :param data: 研究数据
    :param config: 配置对象
    :param subtopics: 现有子主题列表
    :param session_id: 可选的会话ID
    :return: 构建的子主题列表
    """
    try:
        parser = JsonOutputParser(pydantic_object=Subtopics)

        format_instructions = """
输出你的答案为符合以下模式的JSON对象：
```json
{schema}
```

重要说明：
1. 将你的整个响应包裹在 ```json 和 ``` 标签之间。
2. 确保你的JSON是有效的且格式正确。
3. 不要在你的答案中包含模式定义。
4. 只输出与模式匹配的数据实例。
5. 不要在JSON输出中包含任何解释或评论。
        """

        prompt = ChatPromptTemplate.from_template(
            generate_subtopics_prompt() + format_instructions
        ).partial(schema=Subtopics.model_json_schema())

        language_model = init_language_model(temperature=config.temperature)
        chat = language_model

        chain = prompt | chat | parser

        # 使用langfuse工具获取配置
        langfuse_config = get_langfuse_config(
            trace_name="construct_subtopics",
            metadata={
                "task": task,
                "max_subtopics": config.max_subtopics,
                "context_length": len(data)
            },
            session_id=session_id
        )

        output = await chain.ainvoke(
            {
                "task": task,
                "data": data,
                "subtopics": subtopics,
                "max_subtopics": config.max_subtopics,
            },
            config=langfuse_config
        )

        return output["subtopics"]

    except Exception as e:
        print("解析子主题时出现异常：", e)
        return subtopics


async def generate_report(
    query: str,
    context: str,
    agent_role_prompt: str,
    report_type: str,
    tone: Tone,
    report_source: str,
    cfg: Config,
    websocket: Any = None,
    main_topic: str = "",
    existing_headers: List[str] = [],
    session_id: Optional[str] = None,
) -> str:
    """
    生成报告

    :param query: 查询
    :param context: 上下文
    :param agent_role_prompt: 代理角色提示
    :param report_type: 报告类型
    :param tone: 语气
    :param report_source: 报告来源
    :param cfg: 配置对象
    :param websocket: WebSocket对象（可选）
    :param main_topic: 主题（可选）
    :param existing_headers: 现有标题列表（可选）
    :param session_id: 可选的会话ID
    :return: 生成的报告
    """
    generate_prompt = get_report_by_type(report_type)

    if report_type == "subtopic_report":
        content = generate_prompt(
            query,
            existing_headers,
            main_topic,
            context,
            report_format=cfg.report_format,
            total_words=cfg.total_words,
        )
    else:
        content = generate_prompt(
            query,
            context,
            report_source,
            report_format=cfg.report_format,
            total_words=cfg.total_words,
        )

    if tone:
        content += f", tone={tone.value}"

    language_model = init_language_model(temperature=cfg.temperature)
    chat = language_model

    messages = [
        {"role": "system", "content": f"{agent_role_prompt}"},
        {"role": "user", "content": content},
    ]

    # 使用langfuse工具获取配置
    config = get_langfuse_config(
        trace_name="generate_report",
        metadata={
            "query": query,
            "report_type": report_type,
            "tone": tone.value if tone else None,
            "main_topic": main_topic,
            "context_length": len(context)
        },
        session_id=session_id
    )

    response = await chat.ainvoke(messages, config=config)

    return response.content


async def get_report_introduction(
    query: str,
    context: str,
    role: str,
    config: Config,
    websocket: Any = None,
    session_id: Optional[str] = None,
) -> str:
    """
    获取报告引言

    :param query: 查询
    :param context: 上下文
    :param role: 角色
    :param config: 配置对象
    :param websocket: WebSocket对象（可选）
    :param session_id: 可选的会话ID
    :return: 生成的报告引言
    """
    language_model = init_language_model(temperature=config.temperature)
    chat = language_model

    prompt = generate_report_introduction_prompt(query, context)

    messages = [
        {"role": "system", "content": f"{role}"},
        {"role": "user", "content": prompt},
    ]

    # 使用langfuse工具获取配置
    langfuse_config = get_langfuse_config(
        trace_name="get_report_introduction",
        metadata={
            "query": query,
            "role": role,
            "context_length": len(context)
        },
        session_id=session_id
    )

    response = await chat.ainvoke(messages, config=langfuse_config)

    return response.content


# 测试函数已移动到独立的测试文件中
