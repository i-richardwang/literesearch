"""
Langfuse工具类，提供统一的监控配置和管理
"""

import os
import logging
import uuid
from typing import Optional, Dict, Any
from langfuse.callback import CallbackHandler

logger = logging.getLogger(__name__)


class LangfuseManager:
    """
    Langfuse监控管理器，用于统一管理LLM调用的监控
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LangfuseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._enabled = self._check_langfuse_config()
            self._initialized = True
    
    def _check_langfuse_config(self) -> bool:
        """
        检查langfuse配置是否可用
        
        Returns:
            bool: 如果配置完整则返回True，否则返回False
        """
        langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        
        if langfuse_secret_key and langfuse_public_key:
            logger.info("✅ Langfuse配置检测成功")
            return True
        else:
            logger.warning("⚠️  Langfuse配置未完整设置，监控功能将被禁用")
            return False
    
    def get_callback_handler(self, trace_name: Optional[str] = None, 
                           metadata: Optional[Dict[str, Any]] = None,
                           session_id: Optional[str] = None) -> Optional[CallbackHandler]:
        """
        获取langfuse回调处理器
        
        Args:
            trace_name: 可选的追踪名称
            metadata: 可选的元数据
            session_id: 可选的会话ID
            
        Returns:
            CallbackHandler或None: 如果langfuse可用则返回回调处理器，否则返回None
        """
        if not self._enabled:
            return None
        
        try:
            handler = CallbackHandler()
            if trace_name:
                handler.trace_name = trace_name
            if metadata:
                handler.metadata = metadata
            if session_id:
                handler.session_id = session_id
            return handler
        except Exception as e:
            logger.error(f"❌ 创建Langfuse回调处理器失败: {e}")
            return None
    
    def get_config_with_callbacks(self, trace_name: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None,
                                 existing_config: Optional[Dict[str, Any]] = None,
                                 session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取包含langfuse回调的配置字典
        
        Args:
            trace_name: 可选的追踪名称
            metadata: 可选的元数据
            existing_config: 现有的配置字典
            session_id: 可选的会话ID
            
        Returns:
            Dict[str, Any]: 包含callbacks的配置字典
        """
        config = existing_config.copy() if existing_config else {}
        
        handler = self.get_callback_handler(trace_name, metadata, session_id)
        if handler:
            if "callbacks" not in config:
                config["callbacks"] = []
            config["callbacks"].append(handler)
        
        return config
    
    @property
    def is_enabled(self) -> bool:
        """
        检查langfuse是否启用
        
        Returns:
            bool: 如果启用则返回True
        """
        return self._enabled


# 创建全局实例
langfuse_manager = LangfuseManager()


def get_langfuse_config(trace_name: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       existing_config: Optional[Dict[str, Any]] = None,
                       session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    便利函数：获取包含langfuse回调的配置
    
    Args:
        trace_name: 可选的追踪名称
        metadata: 可选的元数据
        existing_config: 现有的配置字典
        session_id: 可选的会话ID
        
    Returns:
        Dict[str, Any]: 包含callbacks的配置字典
    """
    # 添加应用标识到metadata
    enhanced_metadata = {"application": "LiteResearch"}
    if metadata:
        enhanced_metadata.update(metadata)
    
    return langfuse_manager.get_config_with_callbacks(trace_name, enhanced_metadata, existing_config, session_id)


def get_langfuse_handler(trace_name: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None,
                        session_id: Optional[str] = None) -> Optional[CallbackHandler]:
    """
    便利函数：获取langfuse回调处理器
    
    Args:
        trace_name: 可选的追踪名称
        metadata: 可选的元数据
        session_id: 可选的会话ID
        
    Returns:
        CallbackHandler或None: 回调处理器
    """
    # 添加应用标识到metadata
    enhanced_metadata = {"application": "LiteResearch"}
    if metadata:
        enhanced_metadata.update(metadata)
    
    return langfuse_manager.get_callback_handler(trace_name, enhanced_metadata, session_id)


def generate_session_id() -> str:
    """
    生成一个新的会话ID
    
    Returns:
        str: 唯一的会话ID (UUID格式)
    """
    return str(uuid.uuid4()) 