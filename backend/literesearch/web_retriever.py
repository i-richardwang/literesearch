# backend/literesearch/web_retriever.py

import os
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from tavily import TavilyClient
from duckduckgo_search import DDGS

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import (
    DocumentCompressorPipeline,
    EmbeddingsFilter,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class TavilyAPIError(Exception):
    """Tavily API相关错误"""
    pass


class ScrapingError(Exception):
    """网页抓取相关错误"""
    pass


class TavilySearch:
    """Tavily搜索API"""

    def __init__(
        self, query: str, headers: Dict[str, str] = None, topic: str = "general"
    ):
        self.query = query
        self.headers = headers or {}
        self.client = TavilyClient(api_key=self._get_api_key())
        self.topic = topic

    def _get_api_key(self) -> str:
        """
        获取Tavily API密钥

        :return: API密钥
        :raises TavilyAPIError: 如果未找到API密钥
        """
        api_key = self.headers.get("tavily_api_key") or os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise TavilyAPIError("未找到Tavily API密钥。请设置TAVILY_API_KEY环境变量。")
        return api_key

    def search(self, max_results: int = 7) -> List[Dict[str, str]]:
        """
        执行搜索

        :param max_results: 最大结果数
        :return: 搜索结果列表
        """
        try:
            results = self.client.search(
                self.query,
                search_depth="basic",
                max_results=max_results,
                topic=self.topic,
            )
            sources = results.get("results", [])
            if not sources:
                raise TavilyAPIError("Tavily API搜索未找到结果。")
            return [{"href": obj["url"], "body": obj["content"]} for obj in sources]
        except TavilyAPIError:
            raise  # 重新抛出Tavily特定错误
        except Exception as e:
            print(f"Tavily搜索错误: {e}。回退到DuckDuckGo搜索API...")
            try:
                ddg = DDGS()
                results = list(
                    ddg.text(self.query, region="wt-wt", max_results=max_results)
                )
                if not results:
                    print("DuckDuckGo搜索也未找到结果。")
                return results
            except Exception as ddg_error:
                print(f"DuckDuckGo搜索错误: {ddg_error}。获取源失败。返回空响应。")
                return []


def get_retriever(retriever: str):
    """
    获取检索器

    :param retriever: 检索器名称
    :return: 检索器类
    """
    return TavilySearch if retriever == "tavily" else TavilySearch


def get_default_retriever():
    """
    获取默认检索器

    :return: 默认检索器类
    """
    return TavilySearch


class BeautifulSoupScraper:
    """使用BeautifulSoup的网页抓取器"""

    def __init__(self, link: str, session: requests.Session = None, config=None):
        """
        初始化抓取器

        :param link: 要抓取的URL
        :param session: 请求会话
        :param config: 配置对象
        """
        self.link = link
        self.session = session or requests.Session()
        self.config = config

    def scrape(self) -> str:
        """
        抓取网页内容

        :return: 抓取的内容
        :raises ScrapingError: 抓取失败时抛出
        """
        try:
            timeout = self.config.DEFAULT_TIMEOUT if self.config else 4
            response = self.session.get(self.link, timeout=timeout)
            response.raise_for_status()  # 检查HTTP错误
            
            soup = BeautifulSoup(
                response.content, "lxml", from_encoding=response.encoding
            )

            for script_or_style in soup(["script", "style"]):
                script_or_style.extract()

            raw_content = self._get_content_from_url(soup)
            lines = (line.strip() for line in raw_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)

        except requests.exceptions.RequestException as e:
            print(f"网络请求错误 {self.link}: {str(e)}")
            return ""
        except Exception as e:
            print(f"抓取 {self.link} 时出错: {str(e)}")
            return ""

    def _get_content_from_url(self, soup: BeautifulSoup) -> str:
        """
        从BeautifulSoup对象中提取内容

        :param soup: BeautifulSoup对象
        :return: 提取的文本内容
        """
        text = ""
        tags = ["p", "h1", "h2", "h3", "h4", "h5"]
        for element in soup.find_all(tags):
            text += element.text + "\n"
        return text


class Scraper:
    """网页抓取器"""

    def __init__(
        self, urls: List[str], user_agent: str, config=None, scraper_class=BeautifulSoupScraper
    ):
        """
        初始化抓取器

        :param urls: 要抓取的URL列表
        :param user_agent: 用户代理字符串
        :param config: 配置对象
        :param scraper_class: 使用的抓取器类
        """
        self.urls = urls
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.scraper_class = scraper_class
        self.config = config

    def run(self) -> List[Dict[str, Any]]:
        """
        执行抓取任务

        :return: 抓取结果列表
        """
        partial_extract = partial(self._extract_data_from_link, session=self.session)
        max_workers = self.config.DEFAULT_MAX_WORKERS if self.config else 20
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            contents = executor.map(partial_extract, self.urls)
        return [content for content in contents if content["raw_content"] is not None]

    def _extract_data_from_link(
        self, link: str, session: requests.Session
    ) -> Dict[str, Any]:
        """
        从链接中提取数据

        :param link: 要抓取的URL
        :param session: 请求会话
        :return: 包含抓取结果的字典
        """
        try:
            scraper = self.scraper_class(link, session, self.config)
            content = scraper.scrape()

            min_length = self.config.MIN_CONTENT_LENGTH if self.config else 100
            if len(content) < min_length:
                return {"url": link, "raw_content": None}
            return {"url": link, "raw_content": content}
        except Exception as e:
            print(f"从 {link} 提取数据时出错: {str(e)}")
            return {"url": link, "raw_content": None}


def scrape_urls(urls: List[str], cfg: Any) -> List[Dict[str, Any]]:
    """
    抓取多个URL

    :param urls: 要抓取的URL列表
    :param cfg: 配置对象
    :return: 抓取结果列表
    """
    scraper = Scraper(urls, cfg.user_agent, cfg)
    return scraper.run()


class SearchAPIRetriever(BaseRetriever):
    """搜索API检索器"""

    pages: List[Dict[str, Any]] = []

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        获取相关文档

        :param query: 查询字符串
        :return: 相关文档列表
        """
        return [
            Document(
                page_content=page.get("raw_content", ""),
                metadata={
                    "title": page.get("title", ""),
                    "source": page.get("url", ""),
                },
            )
            for page in self.pages
        ]


class ContextCompressor:
    """上下文压缩器"""

    def __init__(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Any,
        max_results: int = 5,
        **kwargs,
    ):
        """
        初始化上下文压缩器

        :param documents: 文档列表
        :param embeddings: 嵌入模型
        :param max_results: 最大结果数
        :param kwargs: 其他参数
        """
        self.max_results = max_results
        self.documents = documents
        self.kwargs = kwargs
        self.embeddings = embeddings
        self.similarity_threshold = float(os.environ.get("SIMILARITY_THRESHOLD", 0.38))

    def get_contextual_retriever(self) -> ContextualCompressionRetriever:
        """
        获取上下文压缩检索器

        :return: 上下文压缩检索器
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        relevance_filter = EmbeddingsFilter(
            embeddings=self.embeddings, similarity_threshold=self.similarity_threshold
        )
        pipeline_compressor = DocumentCompressorPipeline(
            transformers=[splitter, relevance_filter]
        )
        base_retriever = SearchAPIRetriever()
        base_retriever.pages = self.documents
        return ContextualCompressionRetriever(
            base_compressor=pipeline_compressor, base_retriever=base_retriever
        )

    def pretty_print_docs(self, docs: List[Document], top_n: int) -> str:
        """
        美化打印文档

        :param docs: 文档列表
        :param top_n: 要打印的顶部文档数
        :return: 格式化的文档字符串
        """
        return "\n".join(
            f"来源: {d.metadata.get('source')}\n"
            f"标题: {d.metadata.get('title')}\n"
            f"内容: {d.page_content}\n"
            for i, d in enumerate(docs)
            if i < top_n
        )

    async def get_context(self, query: str, max_results: int = 5) -> str:
        """
        获取查询的上下文

        :param query: 查询字符串
        :param max_results: 最大结果数
        :return: 压缩后的上下文字符串
        """
        compressed_docs = self.get_contextual_retriever()
        relevant_docs = compressed_docs.invoke(query)
        return self.pretty_print_docs(relevant_docs, max_results)
