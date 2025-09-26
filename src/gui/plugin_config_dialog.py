#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件配置对话框模块

此模块实现了一个弹出式对话框，用于显示和管理插件的配置界面。"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class PluginConfigDialog(QDialog):
    """插件配置对话框类，用于显示插件的配置界面。
    
    属性:
        plugin: Plugin实例，要配置的插件
        config_widget: 插件提供的配置组件
    """
    
    def __init__(self, plugin, parent=None):
        """初始化插件配置对话框实例。
        
        参数:
            plugin: Plugin实例，要配置的插件
            parent: 父窗口
        """
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(f"{plugin.name} 配置")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 获取插件的配置组件
        self.config_widget = plugin.get_config_widget()
        
        if self.config_widget:
            # 如果插件提供了配置组件，添加到对话框
            main_layout.addWidget(self.config_widget)
        else:
            # 如果插件没有提供配置组件，显示提示信息
            info_label = QLabel("此插件没有配置选项。")
            info_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(info_label)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        
        # 添加到主布局
        main_layout.addLayout(button_layout)
        
        logger.info(f"已打开插件 {plugin.name} 的配置对话框")