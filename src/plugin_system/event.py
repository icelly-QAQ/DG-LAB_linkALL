#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事件系统模块"""
import logging
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """事件优先级枚举"""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    MONITOR = 5

@dataclass
class EventHandler:
    """事件处理器数据类"""
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL
    plugin: Optional[Any] = None

    def __lt__(self, other):
        """用于排序的比较方法"""
        if not isinstance(other, EventHandler):
            return False
        return self.priority.value < other.priority.value

class Event:
    """事件基类"""
    def __init__(self, name: str, **kwargs):
        """初始化事件
        
        参数:
            name: 事件名称
            **kwargs: 事件参数
        """
        self.name = name
        self.args = kwargs
        self._cancelled = False
    
    def cancel(self):
        """取消事件的进一步传播"""
        self._cancelled = True
    
    @property
    def is_cancelled(self) -> bool:
        """检查事件是否被取消"""
        return self._cancelled
    
    def __getitem__(self, key: str) -> Any:
        """通过索引访问事件参数"""
        return self.args.get(key)
    
    def __str__(self) -> str:
        """返回事件的字符串表示"""
        return f"Event({self.name}, {self.args})"

class EventManager:
    """事件管理器，负责注册和分发事件"""
    def __init__(self):
        """初始化事件管理器"""
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        self._plugin_events: Dict[str, Dict[str, EventHandler]] = {}
    
    def register_event_handler(self, 
                             event_name: str, 
                             handler: Callable, 
                             priority: EventPriority = EventPriority.NORMAL, 
                             plugin: Optional[Any] = None):
        """注册事件处理器
        
        参数:
            event_name: 事件名称
            handler: 事件处理函数
            priority: 事件优先级
            plugin: 插件实例（可选）
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        handler_obj = EventHandler(handler, priority, plugin)
        self._event_handlers[event_name].append(handler_obj)
        
        # 按优先级排序
        self._event_handlers[event_name].sort()
        
        # 如果提供了插件，记录插件注册的事件
        if plugin:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_events:
                self._plugin_events[plugin_id] = {}
            self._plugin_events[plugin_id][f"{event_name}_{id(handler)}"] = handler_obj
            
        logger.debug(f"已注册事件处理器: {event_name} (优先级: {priority.name})")
    
    def unregister_event_handler(self, event_name: str, handler: Callable):
        """注销事件处理器
        
        参数:
            event_name: 事件名称
            handler: 事件处理函数
        """
        if event_name not in self._event_handlers:
            return
        
        self._event_handlers[event_name] = [
            h for h in self._event_handlers[event_name] 
            if h.handler != handler
        ]
        
        # 清理空列表
        if not self._event_handlers[event_name]:
            del self._event_handlers[event_name]
    
    def unregister_plugin_events(self, plugin: Any):
        """注销插件注册的所有事件处理器
        
        参数:
            plugin: 插件实例
        """
        plugin_id = id(plugin)
        if plugin_id in self._plugin_events:
            for event_key, handler_obj in self._plugin_events[plugin_id].items():
                # 从事件处理器列表中移除
                event_name = event_key.split('_')[0]
                if event_name in self._event_handlers:
                    self._event_handlers[event_name] = [
                        h for h in self._event_handlers[event_name] 
                        if h.handler != handler_obj.handler
                    ]
                    # 清理空列表
                    if not self._event_handlers[event_name]:
                        del self._event_handlers[event_name]
            
            # 删除插件事件记录
            del self._plugin_events[plugin_id]
            logger.debug(f"已注销插件 {plugin.name} 的所有事件处理器")
    
    async def emit(self, event_name: str, **kwargs) -> Event:
        """触发事件
        
        参数:
            event_name: 事件名称
            **kwargs: 事件参数
            
        返回:
            Event: 触发的事件对象
        """
        # 创建事件对象
        event = Event(event_name, **kwargs)
        logger.debug(f"触发事件: {event}")
        
        # 处理特定事件名称的处理器
        if event_name in self._event_handlers:
            for handler_obj in self._event_handlers[event_name]:
                if event.is_cancelled:
                    break
                
                try:
                    if asyncio.iscoroutinefunction(handler_obj.handler):
                        await handler_obj.handler(event)
                    else:
                        # 如果是非异步函数，在默认执行器中运行
                        await asyncio.get_event_loop().run_in_executor(
                            None, handler_obj.handler, event
                        )
                except Exception as e:
                    plugin_name = handler_obj.plugin.name if handler_obj.plugin else "未知"
                    logger.error(f"插件 {plugin_name} 处理事件 {event_name} 时出错: {e}")
        
        # 处理通配符事件
        if "*" in self._event_handlers:
            for handler_obj in self._event_handlers["*"]:
                if event.is_cancelled:
                    break
                
                try:
                    if asyncio.iscoroutinefunction(handler_obj.handler):
                        await handler_obj.handler(event)
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            None, handler_obj.handler, event
                        )
                except Exception as e:
                    plugin_name = handler_obj.plugin.name if handler_obj.plugin else "未知"
                    logger.error(f"插件 {plugin_name} 处理通配符事件时出错: {e}")
        
        return event
    
    def get_event_names(self) -> List[str]:
        """获取所有已注册的事件名称
        
        返回:
            List[str]: 事件名称列表
        """
        return list(self._event_handlers.keys())
    
    def get_handler_count(self, event_name: str) -> int:
        """获取指定事件的处理器数量
        
        参数:
            event_name: 事件名称
            
        返回:
            int: 处理器数量
        """
        if event_name not in self._event_handlers:
            return 0
        return len(self._event_handlers[event_name])