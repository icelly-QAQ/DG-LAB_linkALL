#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件装饰器模块"""
from typing import Callable, Optional, Dict, Any
from functools import wraps

from .event import EventPriority


def plugin(name: Optional[str] = None, 
           version: str = '1.0.0', 
           description: str = '无描述', 
           author: str = '未知',
           **kwargs):
    """插件装饰器，用于标记和配置插件类
    
    参数:
        name: 插件名称
        version: 插件版本
        description: 插件描述
        author: 插件作者
        **kwargs: 其他插件信息
    """
    def decorator(cls):
        # 设置插件信息
        cls.PLUGIN_VERSION = version
        cls.PLUGIN_DESCRIPTION = description
        cls.PLUGIN_AUTHOR = author
        
        # 如果提供了名称，使用提供的名称
        if name:
            cls.PLUGIN_NAME = name
        
        # 合并其他插件信息
        cls.PLUGIN_INFO = {
            'name': name or cls.__name__, 
            'version': version,
            'description': description,
            'author': author
        }
        cls.PLUGIN_INFO.update(kwargs)
        
        return cls
    
    return decorator

def event_handler(event_name: str, priority: EventPriority = EventPriority.NORMAL):
    """事件处理器装饰器，用于注册事件处理函数
    
    参数:
        event_name: 事件名称
        priority: 事件处理优先级
    """
    def decorator(func: Callable) -> Callable:
        # 标记该函数是事件处理器
        func._event_handler = {
            'name': event_name,
            'priority': priority
        }
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def command_handler(command_name: str):
    """命令处理器装饰器，用于注册命令处理函数
    
    参数:
        command_name: 命令名称
    """
    def decorator(func: Callable) -> Callable:
        # 标记该函数是命令处理器
        func._command_handler = {
            'name': command_name
        }
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def setting(name: str, description: str = '', type: str = 'string', default: Any = None, min_value: Any = None, max_value: Any = None):
    """设置项装饰器，用于定义插件设置项
    
    参数:
        name: 设置项名称
        description: 设置项描述
        type: 设置项类型
        default: 默认值
        min_value: 最小值
        max_value: 最大值
    """
    def decorator(func):
        # 标记该方法是设置项
        func._plugin_setting = {
            'name': name,
            'description': description,
            'type': type,
            'default': default,
            'min_value': min_value,
            'max_value': max_value
        }
        
        return func
    
    return decorator

def async_event_handler(event_name: str, priority: EventPriority = EventPriority.NORMAL):
    """异步事件处理器装饰器
    
    参数:
        event_name: 事件名称
        priority: 事件处理优先级
    """
    # 实际上与普通事件处理器相同，因为事件系统会自动处理异步函数
    return event_handler(event_name, priority)

def async_command_handler(command_name: str):
    """异步命令处理器装饰器
    
    参数:
        command_name: 命令名称
    """
    # 实际上与普通命令处理器相同，因为命令系统会自动处理异步函数
    return command_handler(command_name)