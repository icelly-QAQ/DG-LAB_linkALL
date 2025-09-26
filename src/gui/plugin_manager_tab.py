#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件管理标签页模块

此模块实现了DG-LAB控制器的插件管理界面，包括插件列表显示、启用/禁用功能
和插件信息查看功能。"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QLabel, QHeaderView, 
                               QMessageBox, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class PluginManagerTab(QWidget):
    """插件管理标签页类，提供DG-Lab控制器的插件管理界面。
    
    属性:
        main_window: 主窗口引用
        main_layout: 主布局
        plugin_table: 插件列表表格
        control_layout: 控制按钮布局
        refresh_button: 刷新插件列表按钮
        plugin_info_group: 插件信息分组
        plugin_name_label: 插件名称标签
        plugin_status_label: 插件状态标签
    """
    
    def __init__(self, main_window):
        """初始化插件管理标签页实例。
        
        参数:
            main_window: 主窗口引用
        """
        super().__init__()
        self.main_window = main_window
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        # 创建插件列表表格
        self.plugin_table = QTableWidget(0, 3)
        self.plugin_table.setHorizontalHeaderLabels(["插件名称", "状态", "操作"])
        self.plugin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plugin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.plugin_table.setColumnWidth(2, 150)
        
        # 设置表格属性
        self.plugin_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plugin_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 创建控制区域
        self.control_layout = QHBoxLayout()
        
        # 添加刷新按钮
        self.refresh_button = QPushButton("刷新插件列表")
        self.refresh_button.clicked.connect(self.refresh_plugin_list)
        
        # 添加到控制布局
        self.control_layout.addWidget(self.refresh_button)
        self.control_layout.addStretch()  # 添加伸缩项，将按钮推到左侧
        
        # 创建插件信息区域
        self.plugin_info_group = QGroupBox("插件信息")
        self.plugin_info_layout = QFormLayout()
        
        self.plugin_name_label = QLabel("未选择插件")
        self.plugin_status_label = QLabel("未选择插件")
        self.plugin_desc_label = QLabel("未选择插件")
        self.plugin_type_label = QLabel("未选择插件")
        
        # 设置标签样式，允许自动换行
        self.plugin_name_label.setWordWrap(True)
        self.plugin_status_label.setWordWrap(True)
        self.plugin_desc_label.setWordWrap(True)
        self.plugin_type_label.setWordWrap(True)
        
        self.plugin_info_layout.addRow("插件名称:", self.plugin_name_label)
        self.plugin_info_layout.addRow("插件状态:", self.plugin_status_label)
        self.plugin_info_layout.addRow("插件类型:", self.plugin_type_label)
        self.plugin_info_layout.addRow("插件描述:", self.plugin_desc_label)
        
        self.plugin_info_group.setLayout(self.plugin_info_layout)
        
        # 添加到主布局
        self.main_layout.addLayout(self.control_layout)
        self.main_layout.addWidget(self.plugin_table, 2)
        self.main_layout.addWidget(self.plugin_info_group, 1)
        
        # 初始化插件列表
        self.refresh_plugin_list()
        
        # 连接表格选择变化信号
        self.plugin_table.itemSelectionChanged.connect(self.update_plugin_info)
    
    def refresh_plugin_list(self):
        """刷新插件列表显示"""
        # 清空表格
        self.plugin_table.setRowCount(0)
        
        # 检查是否有插件管理器
        if not hasattr(self.main_window, 'plugin_manager') or self.main_window.plugin_manager is None:
            logger.warning("插件管理器未初始化")
            return
        
        plugin_manager = self.main_window.plugin_manager
        
        # 获取所有插件
        plugins = plugin_manager.get_all_plugins().values()
        
        if not plugins:
            logger.warning("插件管理器中没有插件")
            return
        
        # 遍历所有插件
        for plugin in plugins:
            # 创建新行
            row_position = self.plugin_table.rowCount()
            self.plugin_table.insertRow(row_position)
            
            # 设置插件名称
            name_item = QTableWidgetItem(plugin.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.plugin_table.setItem(row_position, 0, name_item)
            
            # 设置插件状态
            status_text = "已启用" if plugin.enabled else "已禁用"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            
            # 设置状态颜色
            if plugin.enabled:
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            
            self.plugin_table.setItem(row_position, 1, status_item)
            
            # 创建操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建启用/禁用按钮
            toggle_button = QPushButton("禁用" if plugin.enabled else "启用")
            toggle_button.setFixedWidth(60)
            toggle_button.clicked.connect(lambda checked, p=plugin: self.toggle_plugin(p))
            
            # 创建配置按钮
            config_button = QPushButton("配置")
            config_button.setFixedWidth(60)
            config_button.clicked.connect(lambda checked, p=plugin: self.show_plugin_config(p))
            
            action_layout.addWidget(toggle_button)
            action_layout.addWidget(config_button)
            action_layout.addStretch()
            
            self.plugin_table.setCellWidget(row_position, 2, action_widget)
        
        logger.info(f"已刷新插件列表，共显示 {self.plugin_table.rowCount()} 个插件")
    
    def toggle_plugin(self, plugin):
        """切换插件的启用/禁用状态
        
        参数:
            plugin: Plugin实例，要切换状态的插件
        """
        try:
            import asyncio
            plugin_manager = self.main_window.plugin_manager
            
            # 获取当前事件循环或创建新循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果没有当前事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if plugin.enabled:
                # 使用run_coroutine_threadsafe在正确的事件循环中执行异步方法
                future = asyncio.run_coroutine_threadsafe(
                    plugin_manager.disable_plugin(plugin.name),
                    loop
                )
                # 不阻塞主线程，让异步操作在后台完成
                logger.info(f"已开始禁用插件: {plugin.name}")
            else:
                # 使用run_coroutine_threadsafe在正确的事件循环中执行异步方法
                future = asyncio.run_coroutine_threadsafe(
                    plugin_manager.enable_plugin(plugin.name),
                    loop
                )
                # 不阻塞主线程，让异步操作在后台完成
                logger.info(f"已开始启用插件: {plugin.name}")
            
            # 刷新插件列表
            self.refresh_plugin_list()
            # 更新选中插件信息
            self.update_plugin_info()
        except Exception as e:
            logger.error(f"切换插件状态时出错: {e}")
            QMessageBox.critical(self, "错误", f"切换插件状态时出错: {str(e)}")
    
    def show_plugin_config(self, plugin):
        """显示插件的配置对话框
        
        参数:
            plugin: DGPlugin实例，要配置的插件
        """
        try:
            from src.gui.plugin_config_dialog import PluginConfigDialog
            
            # 创建并显示配置对话框
            dialog = PluginConfigDialog(plugin, self.main_window)
            dialog.exec()
        except Exception as e:
            logger.error(f"显示插件配置对话框时出错: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"显示插件配置对话框时出错: {str(e)}")
    
    def update_plugin_info(self):
        """更新选中插件的信息显示"""
        # 获取选中的行
        selected_rows = self.plugin_table.selectionModel().selectedRows()
        
        if not selected_rows:
            # 没有选中行，重置信息
            self.plugin_name_label.setText("未选择插件")
            self.plugin_status_label.setText("未选择插件")
            self.plugin_desc_label.setText("未选择插件")
            self.plugin_type_label.setText("未选择插件")
            return
        
        # 获取选中的插件名称
        selected_row = selected_rows[0].row()
        plugin_name = self.plugin_table.item(selected_row, 0).text()
        
        # 查找对应的插件
        plugin_manager = self.main_window.plugin_manager
        plugin = plugin_manager.get_plugin(plugin_name)
        
        if plugin:
            # 更新插件信息
            self.plugin_name_label.setText(plugin.name)
            self.plugin_status_label.setText("已启用" if plugin.enabled else "已禁用")
            
            # 尝试获取插件类型
            plugin_type = "普通插件"
            if hasattr(plugin, 'is_game_plugin') and plugin.is_game_plugin:
                plugin_type = "玩法插件"
            elif hasattr(plugin, 'PLUGIN_INFO') and plugin.PLUGIN_INFO.get('is_game_plugin', False):
                plugin_type = "玩法插件"
            self.plugin_type_label.setText(plugin_type)
            
            # 尝试获取插件描述
            description = "无描述"
            if hasattr(plugin, 'description'):
                description = plugin.description
            elif hasattr(plugin, 'PLUGIN_INFO'):
                description = plugin.PLUGIN_INFO.get('description', '无描述')
            self.plugin_desc_label.setText(description)
        else:
            logger.warning(f"未找到插件: {plugin_name}")