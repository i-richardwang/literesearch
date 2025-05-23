"""
Lite Research - 基于大语言模型的智能研究工具

该项目旨在协助用户进行深入的主题研究，能够根据用户提供的主题自动生成相关子查询，
从多个来源收集信息，并进行分析整理。
"""

__version__ = "1.0.0"
__author__ = "Richard Wang"

# 导入主要类
from backend.literesearch.literesearcher import LiteResearcher
from backend.literesearch.literesearch_config import Config
from backend.literesearch.research_enums import ReportType, Tone, ReportSource

__all__ = [
    'LiteResearcher',
    'Config', 
    'ReportType',
    'Tone',
    'ReportSource'
] 