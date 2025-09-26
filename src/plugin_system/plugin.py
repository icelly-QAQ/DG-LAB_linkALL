#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件基类模块"""
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, List

logger = logging.getLogger(__name__)

T = TypeVar('T')

class Plugin(ABC):
    """插件系统的基础抽象类
    
    所有插件必须继承此类并实现必要的方法。插件系统采用装饰器和事件驱动的设计模式，
    提供更灵活的插件开发体验。
    """
    
    def __init__(self, plugin_manager, controller=None, main_window=None):
        """初始化插件
        
        参数:
            plugin_manager: PluginManager实例，插件管理器
            controller: DGLabController实例，用于控制DG-LAB设备
            main_window: MainWindow实例，主窗口引用
        """
        self.plugin_manager = plugin_manager
        self.controller = controller
        self.main_window = main_window
        self.name = self.__class__.__name__
        self.version = getattr(self, 'PLUGIN_VERSION', '1.0.0')
        self.description = getattr(self, 'PLUGIN_DESCRIPTION', '无描述')
        self.author = getattr(self, 'PLUGIN_AUTHOR', '未知')
        self.enabled = False
        self._settings = {}
        self._event_handlers = {}
        self._command_handlers = {}
        
        # 自动注册插件信息
        if hasattr(self, 'PLUGIN_INFO'):
            for key, value in self.PLUGIN_INFO.items():
                setattr(self, key.lower(), value)
        
    @property
    def settings(self) -> Dict[str, Any]:
        """获取插件设置"""
        return self._settings.copy()
    
    @property
    def plugin_settings(self) -> Dict[str, Dict[str, Any]]:
        """获取插件定义的设置项
        
        返回:
            Dict[str, Dict[str, Any]]: 设置项名称到设置项属性的映射
        """
        if hasattr(self, '_plugin_settings'):
            return self._plugin_settings.copy()
        return {}
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取指定设置项的值
        
        参数:
            key: 设置项名称
            default: 默认值，当设置项不存在时返回
        
        返回:
            Any: 设置项的值或默认值
        """
        return self._settings.get(key, default)
    
    def update_settings(self, **kwargs):
        """更新插件设置
        
        参数:
            **kwargs: 设置项及其新值
        """
        self._settings.update(kwargs)
        self.on_settings_changed()
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件
        
        插件启动时调用的方法，用于初始化资源和注册事件处理器。
        
        返回:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """关闭插件
        
        插件停止时调用的方法，用于清理资源。
        """
        pass
    
    def enable(self) -> bool:
        """启用插件
        
        返回:
            bool: 启用是否成功
        """
        if not self.enabled:
            try:
                success = self.initialize()
                if success:
                    self.enabled = True
                    logger.info(f"插件 {self.name} v{self.version} 已启用")
                    self.plugin_manager.notify_plugin_enabled(self)
                return success
            except Exception as e:
                logger.error(f"启用插件 {self.name} 时出错: {e}")
        return False
    
    def disable(self):
        """禁用插件"""
        if self.enabled:
            try:
                self.shutdown()
                self.enabled = False
                logger.info(f"插件 {self.name} 已禁用")
                self.plugin_manager.notify_plugin_disabled(self)
            except Exception as e:
                logger.error(f"禁用插件 {self.name} 时出错: {e}")
    
    def on_settings_changed(self):
        """当插件设置更改时调用的钩子方法"""
        pass
    
    def register_event_handler(self, event_name: str, handler):
        """注册事件处理器
        
        参数:
            event_name: 事件名称
            handler: 事件处理函数
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
    
    def register_command_handler(self, command_name: str, handler):
        """注册命令处理器
        
        参数:
            command_name: 命令名称
            handler: 命令处理函数
        """
        self._command_handlers[command_name] = handler
    
    async def handle_event(self, event_name: str, **kwargs):
        """处理事件
        
        参数:
            event_name: 事件名称
            **kwargs: 事件参数
        """
        if not self.enabled:
            return
        
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception as e:
                logger.error(f"插件 {self.name} 处理事件 {event_name} 时出错: {e}")
    
    async def execute_command(self, command_name: str, **kwargs) -> Any:
        """执行命令
        
        参数:
            command_name: 命令名称
            **kwargs: 命令参数
            
        返回:
            Any: 命令执行结果
        """
        if not self.enabled:
            return None
        
        handler = self._command_handlers.get(command_name)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(**kwargs)
                else:
                    return handler(**kwargs)
            except Exception as e:
                logger.error(f"插件 {self.name} 执行命令 {command_name} 时出错: {e}")
                raise
        return None
    
    def get_config_widget(self):
        """获取插件的配置窗口组件
        
        返回:
            QWidget: 插件的配置窗口组件，如果不需要配置界面则返回None
        """
        return None
    
    # 便捷方法：控制器操作
    async def set_strength(self, channel, value):
        """设置指定通道的强度值
        
        参数:
            channel: 通道对象
            value: 强度值
        """
        if self.enabled and self.controller and hasattr(self.controller, 'set_strength'):
            try:
                await self.controller.set_strength(channel, value)
            except Exception as e:
                logger.error(f"插件 {self.name} 设置强度时出错: {e}")
    
    async def adjust_strength(self, channel, delta):
        """调整指定通道的强度值
        
        参数:
            channel: 通道对象
            delta: 强度调整值
        """
        if self.enabled and self.controller and hasattr(self.controller, 'adjust_strength'):
            try:
                await self.controller.adjust_strength(channel, delta)
            except Exception as e:
                logger.error(f"插件 {self.name} 调整强度时出错: {e}")
    
    async def set_pulse_mode(self, channel, mode):
        """设置指定通道的波形模式
        
        参数:
            channel: 通道对象
            mode: 波形模式
        """
        if self.enabled and self.controller and hasattr(self.controller, 'set_pulse_mode'):
            try:
                await self.controller.set_pulse_mode(channel, mode)
            except Exception as e:
                logger.error(f"插件 {self.name} 设置波形模式时出错: {e}")
    
    async def add_pulses(self, channel, *pulses):
        """向指定通道添加波形数据
        
        参数:
            channel: 通道对象
            *pulses: 波形数据
        """
        if self.enabled and self.controller and hasattr(self.controller, 'add_pulses'):
            try:
                await self.controller.add_pulses(channel, *pulses)
            except Exception as e:
                logger.error(f"插件 {self.name} 添加波形数据时出错: {e}")
    
    def __str__(self) -> str:
        """返回插件的字符串表示"""
        return f"{self.name} v{self.version} ({self.author})"