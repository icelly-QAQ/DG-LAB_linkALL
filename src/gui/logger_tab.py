#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志显示标签页模块

此模块实现了DG-Lab控制器的日志显示界面，包括日志文本区域、
日志级别过滤和日志清除功能。
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, 
                               QPushButton, QComboBox, QLabel)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor, QFont
import logging
from logging.handlers import QueueHandler
import queue
import threading

# 定义日志级别映射
LOG_LEVELS = {
    "全部": logging.NOTSET,
    "调试": logging.DEBUG,
    "信息": logging.INFO,
    "警告": logging.WARNING,
    "错误": logging.ERROR,
    "严重错误": logging.CRITICAL
}

class QTextEditLogger(logging.Handler):
    """自定义日志处理器，将日志输出到QTextEdit控件"""
    
    def __init__(self, text_edit, parent=None):
        """初始化日志处理器"""
        super().__init__()
        self.text_edit = text_edit
        self.parent = parent
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
    def emit(self, record):
        """处理日志记录"""
        # 格式化日志记录
        log_entry = self.format(record)
        
        # 使用信号槽机制在主线程中更新UI
        if self.parent:
            self.parent.log_signal.emit(log_entry)
        else:
            # 如果没有父窗口引用，直接在当前线程更新（不推荐，但作为备选）
            self.append_log(log_entry)
            
    @Slot(str)
    def append_log(self, log_entry):
        """添加日志到文本框"""
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.append(log_entry)
        self.text_edit.ensureCursorVisible()

class QueueListenerThread(threading.Thread):
    """队列监听器线程，用于从日志队列中获取日志并发送到UI"""
    
    def __init__(self, log_queue, log_handler):
        """初始化队列监听器线程"""
        super().__init__(daemon=True)
        self.log_queue = log_queue
        self.log_handler = log_handler
        self.running = True
        
    def run(self):
        """运行队列监听器"""
        while self.running:
            try:
                # 从队列中获取日志记录，设置超时以便可以检查running标志
                record = self.log_queue.get(timeout=0.1)
                if record is None:  # None是退出信号
                    break
                self.log_handler.handle(record)
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in log queue listener: {e}")
    
    def stop(self):
        """停止队列监听器"""
        self.running = False

class LoggerTab(QWidget):
    """日志显示标签页类，提供DG-Lab控制器的日志显示界面。
    
    属性:
        main_window: 主窗口引用
        log_signal: 用于在主线程中更新日志的信号
        main_layout: 主布局
        log_text_edit: 日志文本编辑控件
        control_layout: 控制按钮布局
        level_filter: 日志级别过滤下拉框
        clear_button: 清除日志按钮
        log_handler: 日志处理器
        log_queue: 日志队列
        queue_listener: 队列监听器线程
    """
    
    # 定义信号，用于在主线程中更新日志
    log_signal = Signal(str)
    
    def __init__(self, main_window):
        """初始化日志显示标签页实例。
        
        参数:
            main_window: 主窗口引用
        """
        super().__init__()
        self.main_window = main_window
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        # 创建日志文本编辑控件
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)  # 设置为只读
        self.log_text_edit.setLineWrapMode(QTextEdit.WidgetWidth)  # 设置自动换行
        self.log_text_edit.setFont(QFont("Consolas", 10))  # 设置等宽字体，便于日志阅读
        
        # 创建控制区域
        self.control_layout = QHBoxLayout()
        
        # 添加日志级别过滤
        self.level_label = QLabel("日志级别:")
        self.level_filter = QComboBox()
        self.level_filter.addItems(LOG_LEVELS.keys())
        self.level_filter.setCurrentText("全部")
        self.level_filter.currentIndexChanged.connect(self.change_log_level)
        
        # 添加清除日志按钮
        self.clear_button = QPushButton("清除日志")
        self.clear_button.clicked.connect(self.clear_log)
        
        # 添加到控制布局
        self.control_layout.addWidget(self.level_label)
        self.control_layout.addWidget(self.level_filter)
        self.control_layout.addStretch()  # 添加伸缩项，将按钮推到右侧
        self.control_layout.addWidget(self.clear_button)
        
        # 添加到主布局
        self.main_layout.addLayout(self.control_layout)
        self.main_layout.addWidget(self.log_text_edit)
        
        # 设置日志处理器
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志系统"""
        # 创建日志处理器
        self.log_handler = QTextEditLogger(self.log_text_edit, self)
        self.log_handler.setLevel(logging.NOTSET)
        
        # 连接信号和槽
        self.log_signal.connect(self.log_handler.append_log)
        
        # 创建日志队列和队列处理器
        self.log_queue = queue.Queue()
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setLevel(logging.NOTSET)
        
        # 获取根日志记录器并添加队列处理器
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        
        # 启动队列监听器线程
        self.queue_listener = QueueListenerThread(self.log_queue, self.log_handler)
        self.queue_listener.start()
        
        # 记录初始化日志
        logging.info("日志系统初始化完成")
    
    @Slot()
    def change_log_level(self):
        """更改日志显示级别"""
        selected_level = self.level_filter.currentText()
        level_value = LOG_LEVELS.get(selected_level, logging.NOTSET)
        self.log_handler.setLevel(level_value)
        logging.info(f"日志级别已更改为: {selected_level} ({level_value})")
    
    @Slot()
    def clear_log(self):
        """清除日志文本"""
        self.log_text_edit.clear()
        logging.info("日志已清除")
    
    def closeEvent(self, event):
        """关闭标签页时清理资源"""
        # 停止队列监听器
        self.queue_listener.stop()
        # 向队列发送退出信号
        self.log_queue.put(None)
        # 等待线程结束
        self.queue_listener.join(timeout=1.0)
        
        # 移除日志处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, QueueHandler):
                root_logger.removeHandler(handler)
        
        event.accept()

logger = logging.getLogger(__name__)