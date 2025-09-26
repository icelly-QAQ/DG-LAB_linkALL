#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件加载器模块

此模块实现了DG-LAB控制器的插件加载功能，负责扫描plugins目录下的所有Python文件并加载其中的插件。"""
import os
import sys
import logging
import asyncio
from typing import Optional, Dict, Any, List

from src.plugin_system.plugin_manager import PluginManager
from src.plugin_system.exceptions import PluginLoadError

logger = logging.getLogger(__name__)

class PluginLoader:
    """插件加载器，负责扫描和加载plugins目录下的所有插件"""
    
    def __init__(self, plugins_dir=None):
        """初始化插件加载器
        
        参数:
            plugins_dir: str，插件目录路径，如果为None则使用默认路径
        """
        # 确定插件目录路径
        if plugins_dir is None:
            # 获取当前文件所在目录的父目录，然后加上plugins目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.plugins_dir = os.path.join(project_root, 'plugins')
        else:
            self.plugins_dir = plugins_dir
        
        # 确保插件目录存在
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            logger.info(f"已创建插件目录: {self.plugins_dir}")
        
        # 添加插件目录到Python路径，以便可以导入插件
        if self.plugins_dir not in sys.path:
            sys.path.append(self.plugins_dir)
        
        # 初始化插件管理器
        self.plugin_manager = None
    
    def load_all_plugins(self, controller, main_window) -> PluginManager:
        """加载所有插件
        
        参数:
            controller: DGLabController实例
            main_window: MainWindow实例
        
        返回:
            PluginManager: 插件管理器实例
        """
        # 创建插件管理器
        self.plugin_manager = PluginManager(controller, main_window)
        
        # 添加插件目录
        self.plugin_manager.add_plugin_dir(self.plugins_dir)
        
        # 加载所有插件
        try:
            # 使用事件循环运行异步加载
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已运行的事件循环中使用create_task
                    task = loop.create_task(self._async_load_all_plugins())
                    # 等待任务完成
                    loop.run_until_complete(asyncio.wait([task], timeout=30))
                else:
                    # 在非异步环境中使用run_until_complete
                    loop.run_until_complete(self._async_load_all_plugins())
            except RuntimeError:
                # 没有事件循环时创建一个新的
                asyncio.run(self._async_load_all_plugins())
        except Exception as e:
            logger.error(f"加载插件时发生严重错误: {e}")
            raise PluginLoadError(f"插件系统初始化失败: {str(e)}") from e
        
        return self.plugin_manager
    
    async def _async_load_all_plugins(self):
        """异步加载所有插件的内部方法"""
        try:
            # 加载所有插件
            loaded_count = await self.plugin_manager.load_all_plugins()
            logger.info(f"插件系统已加载 {loaded_count} 个插件")
        except Exception as e:
            logger.error(f"异步加载插件时出错: {e}")
            raise
    
    def get_plugin_manager(self) -> Optional[PluginManager]:
        """获取插件管理器实例
        
        返回:
            PluginManager: 插件管理器实例，如果尚未初始化则返回None
        """
        return self.plugin_manager
    
    def get_available_plugins(self) -> List[Dict[str, Any]]:
        """获取所有可用的插件信息
        
        返回:
            List[Dict[str, Any]]: 插件信息列表
        """
        if not self.plugin_manager:
            return []
        
        plugins_info = []
        for plugin_name, plugin in self.plugin_manager.get_all_plugins().items():
            plugins_info.append({
                'name': plugin_name,
                'display_name': getattr(plugin, 'PLUGIN_NAME', plugin_name),
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'enabled': plugin.enabled
            })
        
        return plugins_info
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取指定插件的信息
        
        参数:
            plugin_name: 插件名称
            
        返回:
            Dict[str, Any]: 插件信息字典，如果插件不存在则返回None
        """
        if not self.plugin_manager:
            return None
        
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin:
            return {
                'name': plugin_name,
                'display_name': getattr(plugin, 'PLUGIN_NAME', plugin_name),
                'version': plugin.version,
                'description': plugin.description,
                'author': plugin.author,
                'enabled': plugin.enabled,
                'settings': plugin.settings
            }
        
        return None

# 创建一个默认的插件加载器实例，便于直接导入使用
default_plugin_loader = PluginLoader()