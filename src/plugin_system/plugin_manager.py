#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件管理器模块"""
import os
import sys
import importlib.util
import logging
import json
import asyncio
from typing import Dict, List, Optional, Type, Any

from .plugin import Plugin
from .event import EventManager, EventPriority
from .exceptions import PluginLoadError, PluginExecutionError

logger = logging.getLogger(__name__)

class PluginManager:
    """插件管理器，负责加载、注册和管理所有插件"""
    
    def __init__(self, controller=None, main_window=None):
        """初始化插件管理器
        
        参数:
            controller: DGLabController实例，用于控制DG-LAB设备
            main_window: MainWindow实例，主窗口引用
        """
        self.controller = controller
        self.main_window = main_window
        self.plugins: Dict[str, Plugin] = {}
        self.event_manager = EventManager()
        self.plugin_dirs: List[str] = []
        self.disabled_plugins: List[str] = []
        
        # 注册内置事件
        self._register_builtin_events()
    
    def _register_builtin_events(self):
        """注册内置事件"""
        # 插件生命周期事件
        self.event_manager.register_event_handler(
            "plugin_enabled", 
            self._on_plugin_enabled,
            priority=EventPriority.MONITOR
        )
        self.event_manager.register_event_handler(
            "plugin_disabled", 
            self._on_plugin_disabled,
            priority=EventPriority.MONITOR
        )
        
        # 设备相关事件
        self.event_manager.register_event_handler(
            "connection_status_changed", 
            self._on_connection_status_changed
        )
        self.event_manager.register_event_handler(
            "strength_data_received", 
            self._on_strength_data_received
        )
        self.event_manager.register_event_handler(
            "feedback_button_pressed", 
            self._on_feedback_button_pressed
        )
    
    def add_plugin_dir(self, plugin_dir: str):
        """添加插件目录
        
        参数:
            plugin_dir: 插件目录路径
        """
        if os.path.isdir(plugin_dir) and plugin_dir not in self.plugin_dirs:
            self.plugin_dirs.append(plugin_dir)
            if plugin_dir not in sys.path:
                sys.path.append(plugin_dir)
            logger.info(f"已添加插件目录: {plugin_dir}")
    
    def set_disabled_plugins(self, disabled_plugins: List[str]):
        """设置禁用的插件列表
        
        参数:
            disabled_plugins: 禁用的插件名称列表
        """
        self.disabled_plugins = disabled_plugins
    
    async def load_all_plugins(self) -> int:
        """加载所有插件
        
        返回:
            int: 成功加载的插件数量
        """
        loaded_count = 0
        
        # 遍历所有插件目录
        for plugin_dir in self.plugin_dirs:
            loaded_count += await self._load_plugins_from_dir(plugin_dir)
        
        # 启用非禁用的插件
        await self._enable_non_disabled_plugins()
        
        logger.info(f"插件加载完成，共加载 {loaded_count} 个插件")
        return loaded_count
    
    async def _load_plugins_from_dir(self, plugin_dir: str) -> int:
        """从指定目录加载插件
        
        参数:
            plugin_dir: 插件目录路径
            
        返回:
            int: 成功加载的插件数量
        """
        loaded_count = 0
        
        try:
            # 遍历插件目录下的所有子目录和文件
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # 跳过__pycache__目录
                if item == '__pycache__' and os.path.isdir(item_path):
                    continue
                
                # 处理单个Python文件
                if os.path.isfile(item_path) and item.endswith('.py'):
                    try:
                        plugin = await self._load_plugin_from_file(item_path)
                        if plugin:
                            loaded_count += 1
                    except Exception as e:
                        logger.error(f"加载插件文件 {item_path} 时出错: {e}")
                
                # 处理插件目录
                elif os.path.isdir(item_path):
                    try:
                        plugin_info = None
                        plugin_info_path = os.path.join(item_path, 'plugin_info.json')
                        
                        # 尝试加载plugin_info.json
                        if os.path.exists(plugin_info_path):
                            with open(plugin_info_path, 'r', encoding='utf-8') as f:
                                plugin_info = json.load(f)
                        
                        # 查找Python文件
                        py_files = [f for f in os.listdir(item_path) if f.endswith('.py') and not f.startswith('__')]
                        for py_file in py_files:
                            py_file_path = os.path.join(item_path, py_file)
                            try:
                                plugin = await self._load_plugin_from_file(py_file_path, plugin_info)
                                if plugin:
                                    loaded_count += 1
                            except Exception as e:
                                logger.error(f"加载插件文件 {py_file_path} 时出错: {e}")
                    except Exception as e:
                        logger.error(f"处理插件目录 {item_path} 时出错: {e}")
        except Exception as e:
            logger.error(f"扫描插件目录 {plugin_dir} 时出错: {e}")
        
        return loaded_count
    
    async def _load_plugin_from_file(self, file_path: str, plugin_info: Optional[Dict] = None) -> Optional[Plugin]:
        """从单个文件加载插件
        
        参数:
            file_path: 插件文件路径
            plugin_info: 插件信息字典（可选）
            
        返回:
            Plugin: 加载的插件实例，如果加载失败则返回None
        """
        try:
            # 获取文件名（不包含扩展名）
            file_name = os.path.basename(file_path)[:-3]
            
            # 使用importlib.util模块动态导入文件
            spec = importlib.util.spec_from_file_location(file_name, file_path)
            if spec is None:
                logger.error(f"无法为文件 {file_path} 创建模块规范")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[file_name] = module
            
            # 执行模块代码
            spec.loader.exec_module(module)
            
            # 查找继承自Plugin的类
            plugin_classes = self._find_plugin_classes(module)
            
            # 注册找到的插件类
            for plugin_class in plugin_classes:
                # 将插件信息添加到插件类中
                if plugin_info:
                    plugin_class.PLUGIN_INFO = plugin_info
                
                plugin = await self.register_plugin(plugin_class)
                if plugin:
                    logger.info(f"已加载插件: {plugin}")
                    return plugin
        except Exception as e:
            logger.error(f"加载插件文件 {file_path} 时出错: {e}")
            raise PluginLoadError(f"无法加载插件 {file_path}: {str(e)}") from e
        
        return None
    
    def _find_plugin_classes(self, module) -> List[Type[Plugin]]:
        """在模块中查找所有继承自Plugin的类
        
        参数:
            module: 已导入的模块
            
        返回:
            List[Type[Plugin]]: 插件类列表
        """
        plugin_classes = []
        
        # 遍历模块中的所有属性
        for name, obj in vars(module).items():
            # 检查是否是类，是否继承自Plugin，但不是Plugin本身
            if (isinstance(obj, type) and \
                issubclass(obj, Plugin) and \
                obj is not Plugin):
                plugin_classes.append(obj)
                logger.debug(f"在模块中发现插件类: {name}")
        
        return plugin_classes
    
    async def register_plugin(self, plugin_class: Type[Plugin]) -> Optional[Plugin]:
        """注册一个插件类
        
        参数:
            plugin_class: 继承自Plugin的插件类
            
        返回:
            Plugin: 注册的插件实例，如果注册失败则返回None
        """
        try:
            # 创建插件实例
            plugin = plugin_class(self, self.controller, self.main_window)
            plugin_name = plugin.name
            
            # 检查是否已存在同名插件
            if plugin_name in self.plugins:
                logger.warning(f"插件名称 '{plugin_name}' 已存在，使用类名作为唯一标识")
                plugin_name = f"{plugin_name}_{id(plugin)}"
            
            # 注册插件
            self.plugins[plugin_name] = plugin
            logger.info(f"已注册插件: {plugin}")
            
            # 注册插件的事件处理器（如果有）
            self._register_plugin_handlers(plugin)
            
            return plugin
        except Exception as e:
            logger.error(f"注册插件时出错: {e}")
            raise PluginLoadError(f"无法注册插件 {plugin_class.__name__}: {str(e)}") from e
    
    def _register_plugin_handlers(self, plugin: Plugin):
        """注册插件的事件处理器、命令处理器和设置项
        
        参数:
            plugin: 插件实例
        """
        # 确保插件有设置项字典
        if not hasattr(plugin, '_plugin_settings'):
            plugin._plugin_settings = {}
        
        # 查找插件中使用装饰器注册的处理器和设置项
        for attr_name in dir(plugin):
            attr = getattr(plugin, attr_name)
            if hasattr(attr, '_event_handler'):
                event_data = attr._event_handler
                self.event_manager.register_event_handler(
                    event_data['name'],
                    attr,
                    priority=event_data.get('priority', EventPriority.NORMAL),
                    plugin=plugin
                )
            if hasattr(attr, '_command_handler'):
                command_data = attr._command_handler
                plugin.register_command_handler(command_data['name'], attr)
            if hasattr(attr, '_plugin_setting'):
                setting_data = attr._plugin_setting
                plugin._plugin_settings[attr_name] = setting_data
                # 初始化设置项的默认值
                if setting_data.get('default') is not None:
                    plugin._settings[attr_name] = setting_data['default']
    
    async def _enable_non_disabled_plugins(self):
        """启用非禁用的插件"""
        for plugin_name, plugin in self.plugins.items():
            # 检查插件是否在禁用列表中
            if plugin_name not in self.disabled_plugins:
                try:
                    await self._enable_plugin_async(plugin_name)
                except Exception as e:
                    logger.error(f"启用插件 {plugin_name} 时出错: {e}")
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用指定的插件
        
        参数:
            plugin_name: 插件名称
            
        返回:
            bool: 启用是否成功
        """
        return await self._enable_plugin_async(plugin_name)
    
    async def _enable_plugin_async(self, plugin_name: str) -> bool:
        """异步启用插件的内部方法"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            # 创建异步任务来启用插件
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, plugin.enable
            )
            return success
        return False
    
    async def disable_plugin(self, plugin_name: str):
        """禁用指定的插件
        
        参数:
            plugin_name: 插件名称
        """
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            # 创建异步任务来禁用插件
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, plugin.disable
            )
            # 注销插件的事件处理器
            self.event_manager.unregister_plugin_events(plugin)
    
    async def enable_all_plugins(self):
        """启用所有已注册的插件"""
        for plugin_name in self.plugins:
            await self.enable_plugin(plugin_name)
    
    async def disable_all_plugins(self):
        """禁用所有已注册的插件"""
        for plugin_name in self.plugins:
            await self.disable_plugin(plugin_name)
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """获取指定名称的插件实例
        
        参数:
            plugin_name: 插件名称
            
        返回:
            Plugin: 插件实例，如果不存在则返回None
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Plugin]:
        """获取所有已注册的插件
        
        返回:
            Dict[str, Plugin]: 插件名称到插件实例的映射
        """
        return self.plugins.copy()
    
    async def emit_event(self, event_name: str, **kwargs) -> Any:
        """触发事件并通知所有插件
        
        参数:
            event_name: 事件名称
            **kwargs: 事件参数
            
        返回:
            Any: 事件处理结果
        """
        try:
            return await self.event_manager.emit(event_name, **kwargs)
        except Exception as e:
            logger.error(f"触发事件 {event_name} 时出错: {e}")
            raise PluginExecutionError(f"事件执行失败 {event_name}: {str(e)}") from e
    
    async def execute_plugin_command(self, plugin_name: str, command_name: str, **kwargs) -> Any:
        """执行插件的命令
        
        参数:
            plugin_name: 插件名称
            command_name: 命令名称
            **kwargs: 命令参数
            
        返回:
            Any: 命令执行结果
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            try:
                return await plugin.execute_command(command_name, **kwargs)
            except Exception as e:
                logger.error(f"插件 {plugin_name} 执行命令 {command_name} 时出错: {e}")
                raise PluginExecutionError(f"插件命令执行失败 {plugin_name}.{command_name}: {str(e)}") from e
        return None
    
    # 事件通知方法
    def notify_plugin_enabled(self, plugin: Plugin):
        """通知插件已启用
        
        参数:
            plugin: 插件实例
        """
        asyncio.create_task(self.emit_event("plugin_enabled", plugin=plugin))
    
    def notify_plugin_disabled(self, plugin: Plugin):
        """通知插件已禁用
        
        参数:
            plugin: 插件实例
        """
        asyncio.create_task(self.emit_event("plugin_disabled", plugin=plugin))
    
    def notify_connection_status_changed(self, is_connected: bool):
        """通知所有插件连接状态已改变
        
        参数:
            is_connected: bool，连接状态
        """
        asyncio.create_task(self.emit_event("connection_status_changed", is_connected=is_connected))
    
    def notify_strength_data_received(self, strength_data):
        """通知所有插件强度数据已接收
        
        参数:
            strength_data: StrengthData对象
        """
        asyncio.create_task(self.emit_event("strength_data_received", strength_data=strength_data))
    
    def notify_feedback_button_pressed(self, button_data):
        """通知所有插件反馈按钮已按下
        
        参数:
            button_data: 按钮数据对象
        """
        asyncio.create_task(self.emit_event("feedback_button_pressed", button_data=button_data))
    
    # 内置事件处理器
    def _on_plugin_enabled(self, event):
        """处理插件启用事件"""
        plugin = event['plugin']
        logger.debug(f"插件 {plugin.name} 已启用，触发plugin_enabled事件")
    
    def _on_plugin_disabled(self, event):
        """处理插件禁用事件"""
        plugin = event['plugin']
        logger.debug(f"插件 {plugin.name} 已禁用，触发plugin_disabled事件")
    
    async def _on_connection_status_changed(self, event):
        """处理连接状态变化事件"""
        is_connected = event['is_connected']
        for plugin in self.plugins.values():
            if plugin.enabled and hasattr(plugin, 'on_connection_status_changed'):
                try:
                    if asyncio.iscoroutinefunction(plugin.on_connection_status_changed):
                        await plugin.on_connection_status_changed(is_connected)
                    else:
                        plugin.on_connection_status_changed(is_connected)
                except Exception as e:
                    logger.error(f"插件 {plugin.name} 处理连接状态变化时出错: {e}")
    
    async def _on_strength_data_received(self, event):
        """处理强度数据接收事件"""
        strength_data = event['strength_data']
        for plugin in self.plugins.values():
            if plugin.enabled and hasattr(plugin, 'on_strength_data_received'):
                try:
                    if asyncio.iscoroutinefunction(plugin.on_strength_data_received):
                        await plugin.on_strength_data_received(strength_data)
                    else:
                        plugin.on_strength_data_received(strength_data)
                except Exception as e:
                    logger.error(f"插件 {plugin.name} 处理强度数据时出错: {e}")
    
    async def _on_feedback_button_pressed(self, event):
        """处理反馈按钮按下事件"""
        button_data = event['button_data']
        for plugin in self.plugins.values():
            if plugin.enabled and hasattr(plugin, 'on_feedback_button_pressed'):
                try:
                    if asyncio.iscoroutinefunction(plugin.on_feedback_button_pressed):
                        await plugin.on_feedback_button_pressed(button_data)
                    else:
                        plugin.on_feedback_button_pressed(button_data)
                except Exception as e:
                    logger.error(f"插件 {plugin.name} 处理反馈按钮时出错: {e}")