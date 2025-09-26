#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例插件"""
import asyncio
from src.plugin_system.decorators import plugin
from src.plugin_system.plugin import Plugin
from src.dglab_controller import DGLabController
from src.command_types import Channel
import logging

logger = logging.getLogger(__name__)

@plugin(
    name="明日方舟 X DG-LAB",
    description="让你的明日方舟连接DG-LAB！",
    version="1.0.0",
    author="icelly_QAQ",
    is_game_plugin=True
)
class ArkForDGLAB(Plugin):
    """明日方舟 X DG-LAB 插件类"""
    def initialize(self):
        """初始化插件资源
        
        参数:
            controller: Controller实例，用于与设备交互
        """
        self.controller = DGLabController
        self.task = None  # 定时任务
        logger.info(f"插件 {self.name} 已初始化")
        return True
    
    def shutdown(self):
        """关闭插件，清理资源"""
        # 停止定时任务
        if self.task and not self.task.done():
            self.task.cancel()
        logger.info(f"插件 {self.name} 已关闭")
    
    def on_enable(self):
        """插件启用时调用"""
        # 启动定时任务
        if self.controller:
            self.task = asyncio.create_task(self.strength_cycle())
        logger.info(f"插件 {self.name} 已启用")
    
    def on_disable(self):
        """插件禁用时调用"""
        # 停止定时任务
        if self.task and not self.task.done():
            self.task.cancel()
        logger.info(f"插件 {self.name} 已禁用")
    
    async def strength_cycle(self):
        """强度循环任务：每5秒将A通道强度设置为30，5秒后设置为5"""
        try:
            while True:
                # 设置A通道强度为30
                if self.controller and hasattr(self.controller, 'set_strength'):
                    await self.set_strength(Channel.A, 30)
                    logger.info("设置A通道强度为30")
                
                # 等待5秒
                await asyncio.sleep(5)
                
                # 设置A通道强度为5
                if self.controller and hasattr(self.controller, 'set_strength'):
                    await self.set_strength(Channel.A, 5)
                    logger.info("设置A通道强度为5")
                
                # 等待5秒
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("强度循环任务已取消")
        except Exception as e:
            logger.error(f"强度循环任务出错: {e}")
    
    def get_config_widget(self):
        """获取插件配置界面组件
        
        返回:
            QWidget或None: 插件配置界面组件，如果没有配置项则返回None
        """
        return None